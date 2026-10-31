"""Rasterize ADM3 boundaries on the native MCDWD geographic grid."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np

PIXEL_DEGREES = 0.0020833333333333


def run_gdal(executable: Path, arguments: list[object]) -> None:
    command = [str(executable), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)


def snap_to_grid(value: float) -> float:
    return round(value / PIXEL_DEGREES) * PIXEL_DEGREES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapefile", type=Path, required=True)
    parser.add_argument("--gdal-bin", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    boundaries = (
        gpd.read_file(args.shapefile)[
            ["adm3_pcode", "adm3_name", "geometry"]
        ]
        .reset_index(drop=True)
        .copy()
    )
    boundaries["zone_id"] = np.arange(
        1, len(boundaries) + 1, dtype=np.uint16
    )

    min_x, min_y, max_x, max_y = boundaries.total_bounds
    padding = 0.05
    min_x, min_y, max_x, max_y = map(
        snap_to_grid,
        [
            min_x - padding,
            min_y - padding,
            max_x + padding,
            max_y + padding,
        ],
    )
    width = round((max_x - min_x) / PIXEL_DEGREES)
    height = round((max_y - min_y) / PIXEL_DEGREES)
    grid_spec = {
        "xmin": min_x,
        "ymin": min_y,
        "xmax": max_x,
        "ymax": max_y,
        "pixel": PIXEL_DEGREES,
        "width": width,
        "height": height,
    }
    (args.out_dir / "grid_spec.json").write_text(
        json.dumps(grid_spec, indent=2), encoding="utf-8"
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        zones_geojson = temporary / "zones.geojson"
        zones_tif = temporary / "zones.tif"
        boundaries.to_file(zones_geojson, driver="GeoJSON")

        run_gdal(
            args.gdal_bin / "gdal_rasterize.exe",
            [
                "-a",
                "zone_id",
                "-a_nodata",
                "0",
                "-init",
                "0",
                "-ot",
                "UInt16",
                "-te",
                min_x,
                min_y,
                max_x,
                max_y,
                "-tr",
                PIXEL_DEGREES,
                PIXEL_DEGREES,
                zones_geojson,
                zones_tif,
            ],
        )
        run_gdal(
            args.gdal_bin / "gdal_translate.exe",
            [
                "-of",
                "ENVI",
                "-ot",
                "UInt16",
                zones_tif,
                args.out_dir / "zone_raster.bsq",
            ],
        )

    zones = np.fromfile(
        args.out_dir / "zone_raster.bsq", dtype=np.uint16
    ).reshape(height, width)
    pixel_counts = np.bincount(
        zones.ravel(), minlength=len(boundaries) + 1
    )

    lookup = boundaries[["zone_id", "adm3_pcode", "adm3_name"]].copy()
    lookup["total_px"] = lookup["zone_id"].map(
        lambda zone: int(pixel_counts[zone])
    )
    if not (lookup["total_px"] > 0).all():
        raise ValueError("At least one upazila has no raster cells")

    lookup.to_csv(args.out_dir / "zone_lookup.csv", index=False)
    print(f"Wrote zone grid for {len(lookup)} upazilas")


if __name__ == "__main__":
    main()
