"""Construct annual upazila cyclone exposure from hourly storm tracks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6_371.0088
GRID_DEGREES = 0.025
LAND_FRICTION = 0.8
WIND_34_KNOTS = 34 * 0.514444
WIND_64_KNOTS = 64 * 0.514444
KEY = ["adm3_pcode", "year"]


def haversine(
    latitude_1: float,
    longitude_1: float,
    latitude_2: np.ndarray,
    longitude_2: np.ndarray,
) -> np.ndarray:
    phi_1, phi_2 = np.radians(latitude_1), np.radians(latitude_2)
    delta_phi = phi_2 - phi_1
    delta_lambda = np.radians(longitude_2 - longitude_1)
    a = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi_1) * np.cos(phi_2) * np.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def bearing(
    latitude_1: float,
    longitude_1: float,
    latitude_2: np.ndarray,
    longitude_2: np.ndarray,
) -> np.ndarray:
    phi_1 = np.radians(latitude_1)
    phi_2 = np.radians(latitude_2)
    delta_lambda = np.radians(longitude_2 - longitude_1)
    numerator = np.sin(delta_lambda) * np.cos(phi_2)
    denominator = (
        np.cos(phi_1) * np.sin(phi_2)
        - np.sin(phi_1) * np.cos(phi_2) * np.cos(delta_lambda)
    )
    return np.degrees(np.arctan2(numerator, denominator)) % 360


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def make_grid(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    min_x, min_y, max_x, max_y = boundaries.total_bounds
    longitude = np.arange(min_x, max_x + GRID_DEGREES, GRID_DEGREES)
    latitude = np.arange(min_y, max_y + GRID_DEGREES, GRID_DEGREES)
    grid_x, grid_y = np.meshgrid(longitude, latitude)

    points = gpd.GeoDataFrame(
        {"lon": grid_x.ravel(), "lat": grid_y.ravel()},
        geometry=gpd.points_from_xy(grid_x.ravel(), grid_y.ravel()),
        crs=boundaries.crs,
    )
    points = gpd.sjoin(
        points,
        boundaries[["adm3_pcode", "geometry"]],
        predicate="within",
        how="inner",
    )

    missing = boundaries[
        ~boundaries["adm3_pcode"].isin(points["adm3_pcode"])
    ]
    if not missing.empty:
        representative = missing.geometry.representative_point()
        additions = pd.DataFrame(
            {
                "lon": representative.x,
                "lat": representative.y,
                "adm3_pcode": missing["adm3_pcode"],
            }
        )
        points = pd.concat(
            [points[["lon", "lat", "adm3_pcode"]], additions],
            ignore_index=True,
        )
    return points[["lon", "lat", "adm3_pcode"]]


def model_storm(
    storm: pd.DataFrame,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cells = len(latitude)
    peak = np.zeros(cells)
    hours_34 = np.zeros(cells)
    hours_64 = np.zeros(cells)
    cubic_damage = np.zeros(cells)

    for fix in storm.itertuples(index=False):
        radius = np.maximum(
            haversine(fix.LAT, fix.LON, latitude, longitude), 1.0
        )
        ratio = (fix.rmw_km / radius) ** fix.holland_b
        radial_factor = np.sqrt(
            np.clip(ratio * np.exp(1 - ratio), 0, None)
        )
        theta = np.radians(
            (
                bearing(fix.LAT, fix.LON, latitude, longitude)
                - fix.bearing_deg
            )
            % 360
        )
        effective_vmax = np.maximum(
            fix.vmax_ms_1min
            - (1 - np.sin(theta)) * fix.forward_ms / 2,
            0,
        )
        wind = LAND_FRICTION * effective_vmax * radial_factor

        peak = np.maximum(peak, wind)
        hours_34 += wind >= WIND_34_KNOTS
        hours_64 += wind >= WIND_64_KNOTS
        cubic_damage += np.where(wind >= WIND_34_KNOTS, wind**3, 0.0)

    return peak, hours_34, hours_64, cubic_damage


def area_mean(
    values: np.ndarray,
    group_index: np.ndarray,
    weights: np.ndarray,
    denominator: np.ndarray,
) -> np.ndarray:
    numerator = np.bincount(
        group_index,
        weights=values * weights,
        minlength=len(denominator),
    )
    return numerator / denominator


def aggregate_storm(
    storm_id: str,
    storm: pd.DataFrame,
    codes: np.ndarray,
    group_index: np.ndarray,
    weights: np.ndarray,
    denominator: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> pd.DataFrame:
    peak, hours_34, hours_64, cubic_damage = model_storm(
        storm, latitude, longitude
    )
    damaging_peak = np.where(peak >= WIND_34_KNOTS, peak, 0)
    return pd.DataFrame(
        {
            "adm3_pcode": codes,
            "SID": storm_id,
            "year": int(storm["season"].iloc[0]),
            "storm_name": storm["name"].iloc[0],
            "wind_peak_area_mean_ms": area_mean(
                peak, group_index, weights, denominator
            ),
            "wind_damage_area_mean_ms": area_mean(
                damaging_peak, group_index, weights, denominator
            ),
            "area_share_ge34kt": area_mean(
                peak >= WIND_34_KNOTS,
                group_index,
                weights,
                denominator,
            ),
            "area_share_ge64kt": area_mean(
                peak >= WIND_64_KNOTS,
                group_index,
                weights,
                denominator,
            ),
            "mean_cell_hours_ge34kt": area_mean(
                hours_34, group_index, weights, denominator
            ),
            "mean_cell_hours_ge64kt": area_mean(
                hours_64, group_index, weights, denominator
            ),
            "cubic_damage_wind_integral_m3s3h": area_mean(
                cubic_damage, group_index, weights, denominator
            ),
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--shapefile", type=Path, required=True)
    parser.add_argument("--storm-out", type=Path, required=True)
    parser.add_argument("--year-out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_path = args.tracks.with_name(args.tracks.name + ".metadata.json")
    if not metadata_path.is_file():
        raise ValueError(
            "Track metadata is missing; rebuild tracks using 01_build_tracks.py"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual_hash = hashlib.sha256(args.tracks.read_bytes()).hexdigest()
    if actual_hash != metadata["tracks_sha256"]:
        raise ValueError("Track file differs from its metadata; rebuild the tracks")
    year_min, year_max = int(metadata["year_min"]), int(metadata["year_max"])
    if year_min > year_max:
        raise ValueError("Invalid year range in track metadata")
    boundaries = gpd.read_file(args.shapefile)[
        ["adm3_pcode", "adm3_name", "adm2_name", "geometry"]
    ]
    for column in ["adm3_pcode", "adm3_name", "adm2_name"]:
        boundaries[column] = boundaries[column].map(clean_text)

    tracks = pd.read_csv(args.tracks, parse_dates=["time"])
    if tracks.empty or not tracks["season"].between(year_min, year_max).all():
        raise ValueError("Track seasons do not match the declared year range")
    grid = make_grid(boundaries)
    codes, group_index = np.unique(
        grid["adm3_pcode"].to_numpy(), return_inverse=True
    )
    weights = np.cos(np.radians(grid["lat"].to_numpy()))
    denominator = np.bincount(
        group_index, weights=weights, minlength=len(codes)
    )
    latitude = grid["lat"].to_numpy()
    longitude = grid["lon"].to_numpy()

    records = []
    total_storms = tracks["SID"].nunique()
    for number, (storm_id, storm) in enumerate(
        tracks.groupby("SID"), start=1
    ):
        records.append(
            aggregate_storm(
                storm_id,
                storm,
                codes,
                group_index,
                weights,
                denominator,
                latitude,
                longitude,
            )
        )
        if number % 10 == 0:
            print(f"{number}/{total_storms} storms")

    storm_exposure = pd.concat(records, ignore_index=True)
    args.storm_out.parent.mkdir(parents=True, exist_ok=True)
    storm_exposure.to_csv(args.storm_out, index=False)

    annual = (
        storm_exposure.groupby(KEY)
        .agg(
            cyc_wind_peak_area_mean_ms=("wind_peak_area_mean_ms", "max"),
            cyc_wind_damage_area_mean_ms=(
                "wind_damage_area_mean_ms",
                "max",
            ),
            cyc_area_share_ge34kt=("area_share_ge34kt", "max"),
            cyc_area_share_ge64kt=("area_share_ge64kt", "max"),
            cyc_mean_cell_hours_ge34kt=(
                "mean_cell_hours_ge34kt",
                "sum",
            ),
            cyc_mean_cell_hours_ge64kt=(
                "mean_cell_hours_ge64kt",
                "sum",
            ),
            cyc_cubic_damage_wind_integral_m3s3h=(
                "cubic_damage_wind_integral_m3s3h",
                "sum",
            ),
            cyc_n_storms_ge34kt=(
                "area_share_ge34kt",
                lambda values: int((values > 0).sum()),
            ),
        )
        .reset_index()
    )

    complete_index = pd.MultiIndex.from_product(
        [boundaries["adm3_pcode"], range(year_min, year_max + 1)],
        names=KEY,
    ).to_frame(index=False)
    output = complete_index.merge(annual, on=KEY, how="left")
    climate_columns = [
        column for column in output if column.startswith("cyc_")
    ]
    output[climate_columns] = output[climate_columns].fillna(0)
    output = output.merge(
        boundaries.drop(columns="geometry"),
        on="adm3_pcode",
        how="left",
    )

    columns = ["adm3_pcode", "adm3_name", "adm2_name", "year"]
    columns += [column for column in output if column.startswith("cyc_")]
    args.year_out.parent.mkdir(parents=True, exist_ok=True)
    output[columns].sort_values(KEY).to_csv(args.year_out, index=False)
    print(f"Wrote {len(output):,} upazila-years")


if __name__ == "__main__":
    main()
