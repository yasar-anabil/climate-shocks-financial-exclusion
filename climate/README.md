# Climate exposure construction

The Python workflow creates annual cyclone and flood measures for 507 Bangladeshi upazilas from 2007 through 2024.

## Inputs

- Bangladesh ADM3 boundary shapefile, including its companion files;
- IBTrACS v04r01 North Indian Ocean CSV;
- MODIS MCDWD Collection 6.1 HDF files for tiles `h26v06` and `h27v06`;
- GDAL command-line tools for raster conversion and mosaicking.

Place the files under `data/raw/climate` or pass their locations directly to `run_climate.ps1`.

## Cyclone measure

`cyclone/01_build_tracks.py` selects storms within 600 km of Bangladesh, harmonizes reported winds to a one-minute convention, fills missing radius-of-maximum-wind values, and interpolates tracks to hourly observations.

`cyclone/02_build_exposure.py` evaluates a Holland/HURRECON-style wind field on a 0.025-degree grid. Local winds incorporate radial decay, land friction, and forward-motion asymmetry. The primary annual measure retains the largest storm-specific upazila mean after grid-cell winds below 34 knots are set to zero.

The track script records the requested year range and a file checksum in a metadata file alongside the tracks. The exposure script checks this metadata and produces rows only for that range, including zeros for years within it with no qualifying storm. Keep the metadata file with the tracks; regenerate both if the tracks are changed. This check does not establish that the original IBTrACS source is complete.

## Flood measure

The flood scripts rasterize the ADM3 boundaries to the native MCDWD grid, extract three-day flood classifications, and aggregate the flooded share by upazila-year. In the original analysis, the local archive contains June 1–September 30 observations, approximately every third day; the resulting annual value is therefore a monsoon-season maximum, not a full-calendar-year maximum. The scripts process the available files, so another archive with different dates or sampling frequency will produce a different measure. The output retains maximum flooded shares under 20%, 50%, and 80% valid-area requirements. The Stata analysis uses the 80% measure and reports the other rules as sensitivity checks.

## Run

From PowerShell in the repository root:

```powershell
.\climate\run_climate.ps1 `
  -GdalBin "C:\Program Files\QGIS 3.44.9\bin" `
  -Shapefile ".\data\raw\climate\boundaries\bgd_admin3.shp" `
  -Ibtracs ".\data\raw\climate\ibtracs.NI.list.v04r01.csv" `
  -McdwdRaw ".\data\raw\climate\mcdwd"
```

The combined panel is written to `data/derived/climate_exposure_panel.csv`. The Stata workflow will use this file automatically when it is present.

