* 01_build_panel.do
* Merge climate exposure into the long and disaggregated financial panels.

clear all
set more off
version 17
do "code/00_config.do"

********************************************************************************
* STEP 1  Read the combined climate file
********************************************************************************

import delimited using "$CLIMATE/climate_exposure_panel.csv", clear ///
    varnames(1) stringcols(1)

* Each row must identify one upazila and one year.
isid adm3_pcode year

* Rescale the two satellite-based measures so coefficients are easy to read.
* A one-unit change in cyc_wind10 means 10 metres per second.
* A one-unit change in flood_10pp means 10 percentage points of flooded area.
gen double cyc_wind10 = cyc_wind_damage_area_mean_ms / 10
* The primary version requires at least 80 percent classifiable coverage.
gen double flood_10pp = flood_frac_max_gate80 / 0.10

* These alternatives are retained for the threshold comparison.
gen double flood_50_10pp = flood_frac_max_3day / 0.10
gen double flood_20_10pp = flood_frac_max_gate20 / 0.10

label variable cyc_wind10 "Cyclone wind exposure per 10 m/s"
label variable flood_10pp "Flooded share per 10 percentage points, 80% coverage"
label variable flood_50_10pp "Flooded share per 10 percentage points, 50% coverage"
label variable flood_20_10pp "Flooded share per 10 percentage points, 20% coverage"

keep adm3_pcode year cyc_wind10 flood_10pp flood_50_10pp flood_20_10pp
tempfile climate_all_years
save `climate_all_years'

* The disaggregated financial data begin in 2020. We retain 2019 because the
* regressions use climate exposure from the previous year.
preserve
    keep if year >= 2019
    tempfile climate_for_disaggregated_data
    save `climate_for_disaggregated_data'
restore

********************************************************************************
* STEP 2  Prepare the long financial panel
********************************************************************************

use "$FINANCIAL/financial_panel_long_original_copy.dta", clear
drop year
rename Year year

* Repair one missing identifier in the 2007 lag row. The value is copied from
* the same upazila in later years and was checked against the ADM3 code.
replace upazila_num = 447 if missing(upazila_num) & year == 2007 ///
    & lower(trim(district)) == "bogura" ///
    & lower(trim(upazila)) == "shajahanpur_bogura"
assert !missing(upazila_num)

* Fill the ADM3 code in each pre-sample lag row from the same upazila's later
* observations. This code is the key used to merge the climate data.
preserve
    keep if trim(adm3_pcode) != ""
    keep upazila_num adm3_pcode
    bysort upazila_num: keep if _n == 1
    rename adm3_pcode adm3_code_from_later_year
    tempfile long_code_lookup
    save `long_code_lookup'
restore

merge m:1 upazila_num using `long_code_lookup', assert(3) nogen
replace adm3_pcode = adm3_code_from_later_year if trim(adm3_pcode) == ""
drop adm3_code_from_later_year

* Add cyclone and flood variables by upazila code and year.
merge 1:1 adm3_pcode year using `climate_all_years', assert(3) nogen

* Construct the four main outcomes used in the paper.
gen double accounts_per_person = TotalNumberofaccount / pop
gen double deposits_per_person = (depam * 100000) / pop
gen double loans_per_person    = (loanam * 100000) / pop
gen double loan_deposit_ratio  = loanam / depam if depam > 0

gen double ln_accounts = ln(accounts_per_person) if accounts_per_person > 0
gen double ln_deposits = ln(deposits_per_person) if deposits_per_person > 0
gen double ln_loans    = ln(loans_per_person) if loans_per_person > 0
gen double ln_loan_deposit_ratio = ln(1 + loan_deposit_ratio) ///
    if loan_deposit_ratio >= 0 & !missing(loan_deposit_ratio)

* Retain district identifiers for alternative geographic clustering checks.
egen district_id = group(District)
bysort upazila_num (year): replace district_id = district_id[_n+1] ///
    if missing(district_id) & _n < _N

xtset upazila_num year
compress
save "$DERIVED/master_analysis_long_2008_2024.dta", replace

********************************************************************************
* STEP 3  Prepare the disaggregated financial panel
********************************************************************************

use "$FINANCIAL/financial_panel_disaggregated_original_copy.dta", clear

* Repair one missing identifier in the 2019 lag row using the verified ADM3
* code carried by the same upazila in 2020 to 2024.
replace upazila_num = 431 if missing(upazila_num) & year == 2019 ///
    & lower(trim(district)) == "tangail" ///
    & lower(trim(upazila)) == "sakhipur"
assert !missing(upazila_num)

preserve
    keep if trim(adm3_pcode) != ""
    keep upazila_num adm3_pcode
    bysort upazila_num: keep if _n == 1
    rename adm3_pcode adm3_code_from_later_year
    tempfile disaggregated_code_lookup
    save `disaggregated_code_lookup'
restore

merge m:1 upazila_num using `disaggregated_code_lookup', assert(3) nogen
replace adm3_pcode = adm3_code_from_later_year if trim(adm3_pcode) == ""
drop adm3_code_from_later_year

merge 1:1 adm3_pcode year using `climate_for_disaggregated_data', ///
    assert(3) nogen

* Count outcomes and amount outcomes are divided by population and logged.
* Exact zeros remain missing because ln(0) is not defined.
local count_outcomes depacc loanacc depacc_ab1cr depacc_1crbl1cr ///
    loanacc_ab1cr loanacc_1crbl1cr agri_loanacc ind_loanacc priv_depacc

local amount_outcomes depam loanam depam_ab1cr depam_1crbl1cr ///
    loanam_ab1cr loanam_1crbl1cr agri_loanam ind_loanam priv_depam ///
    exportam importam

foreach variable of local count_outcomes {
    gen double `variable'_per_person = `variable' / Population2022
    gen double ln_`variable' = ln(`variable'_per_person) ///
        if `variable'_per_person > 0
}

foreach variable of local amount_outcomes {
    gen double `variable'_per_person = `variable' / Population2022
    gen double ln_`variable' = ln(`variable'_per_person) ///
        if `variable'_per_person > 0
}

gen double loan_deposit_ratio = loanam / depam if depam > 0
gen double ln_loan_deposit_ratio = ln(1 + loan_deposit_ratio) ///
    if loan_deposit_ratio >= 0 & !missing(loan_deposit_ratio)

egen district_id = group(district_clust)
bysort upazila_num (year): replace district_id = district_id[_n+1] ///
    if missing(district_id) & _n < _N

xtset upazila_num year
compress
save "$DERIVED/master_analysis_disaggregated_2020_2024.dta", replace



