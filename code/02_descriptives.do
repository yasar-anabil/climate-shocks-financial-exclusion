* 02_descriptives.do
* Produce panel coverage and summary statistics for the main variables.

clear all
set more off
version 17
do "code/00_config.do"

tempname summary
postfile `summary' str8 panel str40 variable double mean sd p10 p50 p90 N ///
    using "$DERIVED/summary_statistics.dta", replace

use "$DERIVED/master_analysis_long_2008_2024.dta", clear
keep if year >= 2008
local long_vars ln_accounts ln_deposits ln_loans ln_loan_deposit_ratio ///
    cyc_wind10 flood_10pp RAI temp_shock private_bank_branch ///
    public_bank_branch ntl_mean
foreach variable of local long_vars {
    quietly summarize `variable', detail
    post `summary' ("long") ("`variable'") (r(mean)) (r(sd)) ///
        (r(p10)) (r(p50)) (r(p90)) (r(N))
}

use "$DERIVED/master_analysis_disaggregated_2020_2024.dta", clear
keep if year >= 2020
local short_vars ln_depacc ln_loanacc ln_depam ln_loanam ///
    ln_agri_loanam ln_ind_loanam ln_priv_depam ///
    cyc_wind10 flood_10pp RAI temp_shock private_bank_branch ///
    public_bank_branch ntl_mean
foreach variable of local short_vars {
    quietly summarize `variable', detail
    post `summary' ("short") ("`variable'") (r(mean)) (r(sd)) ///
        (r(p10)) (r(p50)) (r(p90)) (r(N))
}

postclose `summary'
use "$DERIVED/summary_statistics.dta", clear
format mean sd p10 p50 p90 %10.3f
export delimited using "$TABLES/summary_statistics.csv", replace



