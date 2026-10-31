"""Extract three-day MCDWD flood classifications by upazila."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

FILE_PATTERN = re.compile(
    r"MCDWD_L3\.A(\d{4})(\d{3})\.(h\d\dv\d\d)\..*\.hdf$"
)
TILES = ["h26v06", "h27v06"]


def run_gdal(executable: Path, arguments: list[object]) -> None:
    command = [str(executable), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)


def find_complete_windows(
    raw_directory: Path,
) -> dict[tuple[int, int], dict[str, Path]]:
    windows: dict[tuple[int, int], dict[str, Path]] = {}
    for tile in TILES:
        for path in (raw_directory / tile).glob("*.hdf"):
            match = FILE_PATTERN.match(path.name)
            if match:
                key = (int(match.group(1)), int(match.group(2)))
                windows.setdefault(key, {})[match.group(3)] = path

    return {
        key: files
        for key, files in windows.items()
        if len(files) == len(TILES) and 2007 <= key[0] <= 2024
    }


def read_zone_grid(
    zone_directory: Path,
) -> tuple[dict[str, float], np.ndarray, pd.DataFrame]:
    grid_spec = json.loads(
        (zone_directory / "grid_spec.json").read_text(encoding="utf-8")
    )
    zones = np.fromfile(
        zone_directory / "zone_raster.bsq", dtype=np.uint16
    ).reshape(grid_spec["height"], grid_spec["width"])
    lookup = pd.read_csv(zone_directory / "zone_lookup.csv")
    return grid_spec, zones, lookup


def extract_window(
    files: dict[str, Path],
    grid_spec: dict[str, float],
    gdal_directory: Path,
) -> np.ndarray:
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        tile_rasters: list[Path] = []
        for tile in TILES:
            raster = temporary / f"{tile}.tif"
            subdataset = (
                f'HDF4_EOS:EOS_GRID:"{files[tile]}"'
                ":Grid_Water_Composite:Flood_3Day_250m"
            )
            run_gdal(
                gdal_directory / "gdal_translate.exe",
                ["-of", "GTiff", "-a_srs", "EPSG:4326", subdataset, raster],
            )
            tile_rasters.append(raster)

        mosaic = temporary / "mosaic.bsq"
        run_gdal(
            gdal_directory / "gdalwarp.exe",
            [
                "-te",
                grid_spec["xmin"],
                grid_spec["ymin"],
                grid_spec["xmax"],
                grid_spec["ymax"],
                "-tr",
                grid_spec["pixel"],
                grid_spec["pixel"],
                "-r",
                "near",
                "-of",
                "ENVI",
                "-ot",
                "Byte",
                "-srcnodata",
                "255",
                "-dstnodata",
                "255",
                *tile_rasters,
                mosaic,
            ],
        )
        return np.fromfile(mosaic, dtype=np.uint8).reshape(
            grid_spec["height"], grid_spec["width"]
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--zone-dir", type=Path, required=True)
    parser.add_argument("--gdal-bin", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    grid_spec, zones, lookup = read_zone_grid(args.zone_dir)
    windows = find_complete_windows(args.raw_dir)
    if not windows:
        raise ValueError("No complete MCDWD tile pairs were found")

    rows: list[tuple[object, ...]] = []
    maximum_zone = int(zones.max())
    for number, ((year, day), files) in enumerate(
        sorted(windows.items()), start=1
    ):
        flood_grid = extract_window(files, grid_spec, args.gdal_bin)
        valid = flood_grid != 255
        flooded = flood_grid == 3
        valid_counts = np.bincount(
            zones[valid], minlength=maximum_zone + 1
        )
        flood_counts = np.bincount(
            zones[flooded], minlength=maximum_zone + 1
        )

        for row in lookup.itertuples(index=False):
            zone = int(row.zone_id)
            rows.append(
                (
                    row.adm3_pcode,
                    year,
                    day,
                    int(flood_counts[zone]),
                    int(valid_counts[zone]),
                    int(row.total_px),
                )
            )

        if number % 25 == 0 or number == len(windows):
            print(f"{number}/{len(windows)} windows")

    columns = [
        "adm3_pcode",
        "year",
        "doy",
        "flood_px",
        "valid_px",
        "total_px",
    ]
    pd.DataFrame(rows, columns=columns).to_csv(args.out, index=False)
    print(f"Wrote {len(rows):,} upazila-window records")


if __name__ == "__main__":
    main()
