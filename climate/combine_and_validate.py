"""Combine annual hazard panels and check the analysis keys and ranges."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

KEY = ["adm3_pcode", "year"]


def read_panel(path: Path, name: str) -> pd.DataFrame:
    panel = pd.read_csv(path)
    if panel.duplicated(KEY).any():
        raise ValueError(f"{name} panel contains duplicate upazila-year rows")
    return panel


def validate(panel: pd.DataFrame) -> dict[str, int]:
    if len(panel) != 9_126:
        raise ValueError(f"Expected 9,126 upazila-years; found {len(panel):,}")
    if panel["adm3_pcode"].nunique() != 507:
        raise ValueError("Expected 507 unique ADM3 codes")
    if (panel["year"].min(), panel["year"].max()) != (2007, 2024):
        raise ValueError("Expected annual coverage from 2007 through 2024")

    cyclone = panel.filter(regex=r"^cyc_")
    if not cyclone.ge(0).all().all():
        raise ValueError("Cyclone measures must be nonnegative")

    bounded = [
        column
        for column in panel
        if "frac" in column or "share" in column
    ]
    for column in bounded:
        values = panel[column].dropna()
        if not values.between(0, 1).all():
            raise ValueError(f"{column} contains values outside [0, 1]")

    return {
        "rows": len(panel),
        "upazilas": panel["adm3_pcode"].nunique(),
        "year_min": int(panel["year"].min()),
        "year_max": int(panel["year"].max()),
        "flood80_nonmissing": int(panel["flood_frac_max_gate80"].notna().sum()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cyclone", type=Path, required=True)
    parser.add_argument("--flood", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cyclone = read_panel(args.cyclone, "cyclone")
    flood = read_panel(args.flood, "flood").drop(columns=["adm3_name"])
    panel = cyclone.merge(flood, on=KEY, how="outer", validate="one_to_one")
    checks = validate(panel)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    panel.sort_values(KEY).to_csv(args.out, index=False)
    args.summary.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()

