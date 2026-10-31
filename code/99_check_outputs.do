* 99_check_outputs.do
* Verify panel keys, ranges, and expected result files.

clear all
set more off
version 17
do "code/00_config.do"

foreach file in master_analysis_long_2008_2024.dta ///
    master_analysis_disaggregated_2020_2024.dta {
    confirm file "$DERIVED/`file'"
}

foreach file in summary_statistics.csv regression_results.csv ///
    flood_threshold_comparison.csv original_specifications.csv {
    confirm file "$TABLES/`file'"
}

use "$DERIVED/master_analysis_long_2008_2024.dta", clear
isid upazila_num year
assert inrange(flood_10pp, 0, 10) if !missing(flood_10pp)
assert cyc_wind10 >= 0 if !missing(cyc_wind10)
quietly count if inrange(year, 2008, 2024)
assert r(N) > 0
local n_long = r(N)

use "$DERIVED/master_analysis_disaggregated_2020_2024.dta", clear
isid upazila_num year
assert inrange(flood_10pp, 0, 10) if !missing(flood_10pp)
quietly count if inrange(year, 2020, 2024)
assert r(N) > 0

display as result "Output checks passed: `n_long' long-panel observations and " ///
    r(N) " short-panel observations."



