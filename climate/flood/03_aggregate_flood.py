"""Aggregate three-day MCDWD classifications to annual upazila exposure."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["adm3_pcode", "year"]
YEARS = range(2007, 2025)


def summarize_year(windows: pd.DataFrame) -> pd.Series:
    peak = windows.loc[windows["flood_frac_visible"].idxmax()]
    return pd.Series(
        {
            "flood_frac_max_3day": peak["flood_frac_visible"],
            "flood_peak_doy": int(peak["doy"]),
            "flood_valid_share_at_peak": peak["valid_share"],
            "flood_frac_p95_3day": windows[
                "flood_frac_visible"
            ].quantile(0.95),
            "flood_frac_mean_3day": windows[
                "flood_frac_visible"
            ].mean(),
            "flood_n_reliable_windows": len(windows),
            "flood_windows_ge01pct": int(
                (windows["flood_frac_visible"] >= 0.01).sum()
            ),
        }
    )


def maximum_at_gate(
    windows: pd.DataFrame, minimum_valid_share: float
) -> pd.Series:
    selected = windows[windows["valid_share"] >= minimum_valid_share]
    name = f"flood_frac_max_gate{int(minimum_valid_share * 100)}"
    return selected.groupby(KEY)["flood_frac_visible"].max().rename(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-level", type=Path, required=True)
    parser.add_argument("--zone-lookup", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    windows = pd.read_csv(args.date_level)
    lookup = pd.read_csv(args.zone_lookup)[
        ["adm3_pcode", "adm3_name"]
    ]

    windows["valid_share"] = (
        windows["valid_px"] / windows["total_px"]
    )
    windows["flood_frac_visible"] = np.where(
        windows["valid_px"] > 0,
        windows["flood_px"] / windows["valid_px"],
        np.nan,
    )

    reliable = windows[windows["valid_share"] >= 0.50]
    annual = (
        reliable.groupby(KEY, group_keys=False)
        .apply(summarize_year, include_groups=False)
        .reset_index()
    )

    for gate in [0.20, 0.80]:
        annual = annual.merge(
            maximum_at_gate(windows, gate).reset_index(),
            on=KEY,
            how="outer",
        )

    complete_index = pd.MultiIndex.from_product(
        [lookup["adm3_pcode"], YEARS], names=KEY
    ).to_frame(index=False)
    output = (
        complete_index.merge(annual, on=KEY, how="left")
        .merge(lookup, on="adm3_pcode", how="left")
    )
    output["flood_ge10pct"] = (
        output["flood_frac_max_3day"] >= 0.10
    ).where(output["flood_frac_max_3day"].notna()).astype("Int64")

    columns = [
        "adm3_pcode",
        "adm3_name",
        "year",
        "flood_frac_max_3day",
        "flood_frac_p95_3day",
        "flood_frac_mean_3day",
        "flood_peak_doy",
        "flood_valid_share_at_peak",
        "flood_n_reliable_windows",
        "flood_windows_ge01pct",
        "flood_ge10pct",
        "flood_frac_max_gate20",
        "flood_frac_max_gate80",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output[columns].sort_values(KEY).to_csv(args.out, index=False)
    nonmissing = output["flood_frac_max_3day"].notna().sum()
    print(
        f"Wrote {len(output):,} upazila-years; "
        f"50% gate nonmissing={nonmissing:,}"
    )


if __name__ == "__main__":
    main()
