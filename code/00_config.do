version 17

capture confirm file "run.do"
if _rc {
    display as error "Run the project from the repository root: do run.do"
    exit 601
}

global PROJECT  "`c(pwd)'"
global CODE     "$PROJECT/code"
global RAW      "$PROJECT/data/raw"
global DERIVED  "$PROJECT/data/derived"
global TABLES   "$PROJECT/output/tables"
global FIGURES  "$PROJECT/output/figures"
global LOGS     "$PROJECT/logs"

foreach directory in "$DERIVED" "$TABLES" "$FIGURES" "$LOGS" {
    capture mkdir "`directory'"
}

global FINANCIAL "$RAW/financial"

global CLIMATE "$DERIVED"
capture confirm file "$CLIMATE/climate_exposure_panel.csv"
if _rc global CLIMATE "$RAW/climate"

capture program drop require_file
program define require_file
    args path
    capture confirm file `"`path'"'
    if _rc {
        display as error "Required input not found: `path'"
        exit 601
    }
end

require_file "$FINANCIAL/financial_panel_long_original_copy.dta"
require_file "$FINANCIAL/financial_panel_disaggregated_original_copy.dta"
require_file "$CLIMATE/climate_exposure_panel.csv"

capture which reghdfe
if _rc {
    display as error "Required package not installed: reghdfe"
    display as error "Run: do code/00_install_dependencies.do"
    exit 199
}



