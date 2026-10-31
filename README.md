# Climate Shocks and Local Financial Development in Bangladesh

> **For visitors:** This is a research coding sample. The underlying datasets are not included. Run `do examples/synthetic_demo.do` from this folder in Stata 17 to try a standalone example using fictional data. The full workflow requires the private inputs described below and cannot be reproduced from this repository alone.

This repository contains the code for an upazila-level study of climate shocks and financial exclusion in Bangladesh. The empirical analysis combines annual banking outcomes with measures of cyclone wind, flood extent, rainfall anomalies, and temperature shocks.

Stata is the main analysis environment. Python is used to construct the cyclone and flood measures from IBTrACS storm tracks, administrative boundaries, and MODIS flood products.

## Where to start

- [`code/01_build_panel.do`](code/01_build_panel.do): merge the climate and financial panels and construct per-person outcomes.
- [`code/03_estimate_models.do`](code/03_estimate_models.do): estimate comparable-sample fixed-effects models.
- [`climate/cyclone/02_build_exposure.py`](climate/cyclone/02_build_exposure.py): calculate grid-level winds and aggregate storm exposure.
- [`climate/flood/03_aggregate_flood.py`](climate/flood/03_aggregate_flood.py): aggregate satellite classifications under alternative coverage rules.

## Run small examples

From the repository root in Stata 17:

```stata
do examples/synthetic_demo.do
```

The demonstration generates fictional observations and illustrates lagged climate exposures and a panel fixed-effects regression using built-in Stata commands. It is independent of the full data pipeline and does not reproduce research estimates.

In a Stata 17 run, the example produced 1,000 observations from 200 fictional upazilas. The illustrative coefficients were −0.0254 for lagged cyclone exposure and −0.0293 for lagged flood exposure. These are simulated examples, not estimates from the RIDGE data.

The Python checks use small numerical examples and the dependencies in `requirements.txt`:

```text
python -m unittest discover -s tests -v
```

## Repository structure

```text
.
├── run.do                       # runs the Stata analysis
├── code/                        # data preparation and econometric analysis
├── climate/                     # Python climate-exposure construction
├── data/
│   ├── raw/                     # source data supplied by the researcher
│   └── derived/                 # analysis panels created by Stata/Python
├── output/
│   ├── figures/
│   └── tables/
└── logs/
```

## Empirical workflow

`01_build_panel.do` merges the climate panel into two financial datasets:

- a long panel for 2008–2024 with aggregate accounts, deposits, and loans;
- a shorter 2020–2024 panel with outcomes by account size, sector, and bank type.

Financial outcomes are expressed per person and log transformed. Climate exposure enters with a one-year lag. The main models include upazila and year fixed effects, with standard errors clustered by upazila. Controlled specifications include private-bank branches, public-bank branches, and mean night lights.

The primary cyclone variable is the annual maximum of storm-level, area-averaged damaging wind. Grid-cell winds below 34 knots are set to zero before aggregation. The primary flood variable is the largest observed three-day flooded share during the June–September monsoon season when at least 80% of the upazila is classifiable. The original archive samples approximately every third day. The robustness script compares 20%, 50%, and 80% coverage rules.

The main results use a common sample for the controlled, uncontrolled, and single-shock specifications: each requires all four lagged climate variables and the controls to be observed. `05_original_specifications.do` also reproduces the latest original regressions using each specification's available observations. The two outputs can differ because their samples differ.

For the shorter panel, per-person outcomes use the supplied 2022 population denominator. Observations with zero or negative outcomes are excluded by the log transformation. Satellite coverage restrictions leave some flood observations missing; missing exposure is not treated as zero. The estimates describe conditional associations and rely on the specification's identifying assumptions for causal interpretation.

## Data

Source data are not committed to this repository. See [`data/README.md`](data/README.md) for the required files and expected directory structure.

## Software

The econometric analysis was written for Stata 17 and requires `reghdfe` and `ftools`. Run the following once if needed:

```stata
do code/00_install_dependencies.do
```

The climate build requires Python 3.11 or later and the packages listed in `requirements.txt`. Flood extraction also requires GDAL command-line tools; a QGIS installation provides a compatible GDAL distribution on Windows.

## Reproduction

From the repository root, run the financial analysis with:

```stata
do run.do
```

To reconstruct the climate measures from the original geospatial inputs, see [`climate/README.md`](climate/README.md). The climate build is kept separate because it is computationally intensive and depends on external geospatial data.

## Code provenance

OpenAI Codex assisted with organizing and revising the code and documentation, and preparing the synthetic example.

## Author

Samin Yasar Anabil




