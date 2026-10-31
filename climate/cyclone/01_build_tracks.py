"""Build hourly Bangladesh-relevant IBTrACS tracks on a one-minute wind basis."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

KNOT_TO_MS = 0.514444
EARTH_RADIUS_KM = 6_371.0088
BANGLADESH_BOUNDS = (88.0082, 20.5906, 92.6801, 26.6345)


def haversine(
    latitude_1: np.ndarray,
    longitude_1: np.ndarray,
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


def distance_to_bangladesh(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    xmin, ymin, xmax, ymax = BANGLADESH_BOUNDS
    return haversine(
        latitude,
        longitude,
        np.clip(latitude, ymin, ymax),
        np.clip(longitude, xmin, xmax),
    )


def impute_radius_of_maximum_wind(
    maximum_wind_ms: np.ndarray, latitude: np.ndarray
) -> np.ndarray:
    return 46.4 * np.exp(
        -0.0155 * maximum_wind_ms + 0.0169 * np.abs(latitude)
    )


def holland_shape_parameter(
    radius_km: np.ndarray, latitude: np.ndarray
) -> np.ndarray:
    estimate = 1.881 - 0.00557 * radius_km - 0.01097 * np.abs(latitude)
    return np.clip(estimate, 1.0, 2.5)


def prepare_fixes(
    ibtracs_path: Path,
    year_min: int,
    year_max: int,
    buffer_km: float,
    wind_conversion: float,
) -> tuple[pd.DataFrame, pd.Series]:
    fixes = pd.read_csv(ibtracs_path, skiprows=[1], low_memory=False)
    fixes["SEASON"] = pd.to_numeric(fixes["SEASON"], errors="coerce")
    fixes = fixes[fixes["SEASON"].between(year_min, year_max)].copy()

    for column in ["LAT", "LON"]:
        fixes[column] = pd.to_numeric(fixes[column], errors="coerce")
    fixes["ISO_TIME"] = pd.to_datetime(fixes["ISO_TIME"], errors="coerce")
    fixes = fixes.dropna(subset=["LAT", "LON", "ISO_TIME"])

    usa_wind = pd.to_numeric(fixes["USA_WIND"], errors="coerce")
    wmo_wind = pd.to_numeric(fixes["WMO_WIND"], errors="coerce") * wind_conversion
    delhi_wind = (
        pd.to_numeric(fixes["NEWDELHI_WIND"], errors="coerce") * wind_conversion
    )
    fixes["vmax_kt_1min"] = usa_wind.fillna(wmo_wind).fillna(delhi_wind)
    fixes["wind_source"] = np.select(
        [
            usa_wind.notna(),
            usa_wind.isna() & wmo_wind.notna(),
            usa_wind.isna() & wmo_wind.isna() & delhi_wind.notna(),
        ],
        ["USA_1MIN", "WMO_3MIN_CONVERTED", "NEWDELHI_3MIN_CONVERTED"],
        default="MISSING",
    )
    fixes["rmw_nm"] = pd.to_numeric(fixes["USA_RMW"], errors="coerce")
    fixes["distance_bgd_km"] = distance_to_bangladesh(
        fixes["LAT"].to_numpy(), fixes["LON"].to_numpy()
    )

    closest_approach = fixes.groupby("SID")["distance_bgd_km"].min()
    nearby_storms = closest_approach[closest_approach <= buffer_km].index
    fixes = fixes[fixes["SID"].isin(nearby_storms)].copy()

    has_wind = fixes.groupby("SID")["vmax_kt_1min"].transform(
        lambda values: values.notna().any()
    )
    return fixes[has_wind], closest_approach


def interpolate_storm(fixes: pd.DataFrame) -> pd.DataFrame:
    fixes = (
        fixes.sort_values("ISO_TIME")
        .drop_duplicates("ISO_TIME")
        .set_index("ISO_TIME")
    )
    hourly_index = pd.date_range(
        fixes.index.min(), fixes.index.max(), freq="1h"
    )
    numeric = fixes[["LAT", "LON", "vmax_kt_1min", "rmw_nm"]].astype(float)
    hourly = (
        numeric.reindex(numeric.index.union(hourly_index))
        .interpolate("time", limit_direction="both")
        .reindex(hourly_index)
    )

    hourly["SID"] = fixes["SID"].iloc[0]
    hourly["season"] = int(fixes["SEASON"].iloc[0])
    hourly["name"] = str(fixes["NAME"].iloc[0]).strip() or "UNNAMED"
    hourly["time"] = hourly.index
    hourly["vmax_ms_1min"] = hourly["vmax_kt_1min"] * KNOT_TO_MS

    observed_radius = hourly["rmw_nm"] * 1.852
    hourly["rmw_imputed"] = observed_radius.isna().astype(int)
    fallback_radius = pd.Series(
        impute_radius_of_maximum_wind(
            hourly["vmax_ms_1min"].to_numpy(),
            hourly["LAT"].to_numpy(),
        ),
        index=hourly.index,
    )
    hourly["rmw_km"] = observed_radius.fillna(fallback_radius).clip(8, 150)
    hourly["holland_b"] = holland_shape_parameter(
        hourly["rmw_km"].to_numpy(), hourly["LAT"].to_numpy()
    )

    hourly = hourly.reset_index(drop=True).sort_values("time")
    delta_latitude = hourly["LAT"].diff()
    delta_longitude = hourly["LON"].diff()
    dx = (
        np.radians(delta_longitude)
        * EARTH_RADIUS_KM
        * np.cos(np.radians(hourly["LAT"]))
    )
    dy = np.radians(delta_latitude) * EARTH_RADIUS_KM
    hours = hourly["time"].diff().dt.total_seconds() / 3_600
    speed = np.sqrt(dx**2 + dy**2) * 1_000 / (hours * 3_600)
    hourly["forward_ms"] = speed.bfill().clip(0, 25)
    hourly["bearing_deg"] = (
        np.degrees(np.arctan2(dx, dy)) % 360
    ).bfill()
    return hourly


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ibtracs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--year-min", type=int, default=2007)
    parser.add_argument("--year-max", type=int, default=2024)
    parser.add_argument("--buffer-km", type=float, default=600.0)
    parser.add_argument(
        "--wmo-3min-to-1min",
        type=float,
        default=1.126,
        help="North Indian basin conversion used when USA/JTWC wind is missing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.year_min > args.year_max:
        raise ValueError("The first year must not be after the last year")
    fixes, closest_approach = prepare_fixes(
        args.ibtracs,
        args.year_min,
        args.year_max,
        args.buffer_km,
        args.wmo_3min_to_1min,
    )

    tracks: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for storm_id, storm_fixes in fixes.groupby("SID"):
        if storm_fixes["ISO_TIME"].nunique() < 2:
            continue

        hourly = interpolate_storm(storm_fixes)
        tracks.append(hourly)
        source_counts = storm_fixes["wind_source"].value_counts()
        summaries.append(
            {
                "SID": storm_id,
                "season": int(hourly["season"].iloc[0]),
                "name": hourly["name"].iloc[0],
                "min_distance_bgd_km": float(closest_approach[storm_id]),
                "peak_input_wind_ms_1min": float(
                    hourly["vmax_ms_1min"].max()
                ),
                "original_fixes": len(storm_fixes),
                "hourly_fixes": len(hourly),
                "usa_fix_share": source_counts.get("USA_1MIN", 0)
                / len(storm_fixes),
                "rmw_imputed_hour_share": float(
                    hourly["rmw_imputed"].mean()
                ),
            }
        )

    if not tracks:
        raise ValueError("No storms met the year, distance, and wind filters")

    output = pd.concat(tracks, ignore_index=True)
    columns = [
        "SID",
        "season",
        "name",
        "time",
        "LAT",
        "LON",
        "vmax_ms_1min",
        "rmw_km",
        "rmw_imputed",
        "holland_b",
        "forward_ms",
        "bearing_deg",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    output[columns].to_csv(args.out, index=False)
    metadata = {
        "year_min": args.year_min,
        "year_max": args.year_max,
        "tracks_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
    }
    metadata_path = args.out.with_name(args.out.name + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    pd.DataFrame(summaries).sort_values(["season", "SID"]).to_csv(
        args.summary, index=False
    )
    print(
        f"Wrote {len(output):,} hourly fixes for "
        f"{output['SID'].nunique()} storms"
    )


if __name__ == "__main__":
    main()
