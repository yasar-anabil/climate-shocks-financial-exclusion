param(
    [string]$Python = "python",
    [Parameter(Mandatory = $true)][string]$GdalBin,
    [Parameter(Mandatory = $true)][string]$Shapefile,
    [Parameter(Mandatory = $true)][string]$Ibtracs,
    [Parameter(Mandatory = $true)][string]$McdwdRaw
)

$ErrorActionPreference = "Stop"
$Project = Split-Path $PSScriptRoot -Parent
$Interim = Join-Path $PSScriptRoot "interim"
$Derived = Join-Path $Project "data\derived"

New-Item -ItemType Directory -Force -Path $Interim, $Derived | Out-Null

function Invoke-PythonStage {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$StageArgs)
    & $Python @StageArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python stage failed: $($StageArgs[0])"
    }
}

Invoke-PythonStage "$PSScriptRoot\cyclone\01_build_tracks.py" `
    --ibtracs $Ibtracs `
    --out "$Interim\tracks.csv" `
    --summary "$Derived\storm_summary.csv"

Invoke-PythonStage "$PSScriptRoot\cyclone\02_build_exposure.py" `
    --tracks "$Interim\tracks.csv" `
    --shapefile $Shapefile `
    --storm-out "$Interim\storm_exposure.csv" `
    --year-out "$Derived\cyclone_panel.csv"

Invoke-PythonStage "$PSScriptRoot\flood\01_build_zone_raster.py" `
    --shapefile $Shapefile `
    --gdal-bin $GdalBin `
    --out-dir "$Interim\flood_zones"

Invoke-PythonStage "$PSScriptRoot\flood\02_extract_mcdwd.py" `
    --raw-dir $McdwdRaw `
    --zone-dir "$Interim\flood_zones" `
    --gdal-bin $GdalBin `
    --out "$Interim\flood_date_level_3day.csv"

Invoke-PythonStage "$PSScriptRoot\flood\03_aggregate_flood.py" `
    --date-level "$Interim\flood_date_level_3day.csv" `
    --zone-lookup "$Interim\flood_zones\zone_lookup.csv" `
    --out "$Derived\flood_panel.csv"

Invoke-PythonStage "$PSScriptRoot\combine_and_validate.py" `
    --cyclone "$Derived\cyclone_panel.csv" `
    --flood "$Derived\flood_panel.csv" `
    --out "$Derived\climate_exposure_panel.csv" `
    --summary "$Derived\climate_validation.json"

