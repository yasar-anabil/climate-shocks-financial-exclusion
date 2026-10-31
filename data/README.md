# Required inputs

Source data are not included in the repository. Place the following files under `data/raw`:

```text
data/raw/
├── financial/
│   ├── financial_panel_long_original_copy.dta
│   └── financial_panel_disaggregated_original_copy.dta
└── climate/
    └── climate_exposure_panel.csv
```

`climate_exposure_panel.csv` is created by the Python workflow under `climate`. It contains one row per upazila-year for 2007–2024, including cyclone and flood measures. 

The financial files contain administrative banking records, population, branch counts, night lights, and the existing rainfall and temperature variables. 


