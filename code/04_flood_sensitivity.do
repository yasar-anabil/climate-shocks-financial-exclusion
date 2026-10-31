* 04_flood_sensitivity.do
* Compare flood estimates across satellite-coverage thresholds.

clear all
set more off
version 17
do "code/00_config.do"

tempname comparison
postfile `comparison' str8 panel str8 family str40 outcome str80 outcome_label ///
    str8 threshold double b se pvalue N r2_within N_clust ///
    using "$TABLES/flood_threshold_comparison.dta", replace

capture program drop compare_flood_rules
program define compare_flood_rules
    syntax varname, PANEL(string) FAMILY(string) LABEL(string) ///
        STARTYEAR(integer) CONTROLLIST(string) HANDLE(name)

    foreach rule in "flood80 L.flood_10pp" ///
        "flood50 L.flood_50_10pp" "flood20 L.flood_20_10pp" {

        gettoken rule_name flood_variable : rule

        quietly reghdfe `varlist' `flood_variable' L.cyc_wind10 L.RAI ///
            L.temp_shock `controllist' if year >= `startyear', ///
            absorb(upazila_num year) vce(cluster upazila_num)

        local coefficient = _b[`flood_variable']
        local standard_error = _se[`flood_variable']
        local probability = 2 * ttail(e(df_r), ///
            abs(`coefficient' / `standard_error'))

        post `handle' ("`panel'") ("`family'") ("`varlist'") ///
            ("`label'") ("`rule_name'") (`coefficient') ///
            (`standard_error') (`probability') (e(N)) ///
            (e(r2_within)) (e(N_clust))
    }
end

********************************************************************************
* Long financial panel
********************************************************************************

use "$DERIVED/master_analysis_long_2008_2024.dta", clear
xtset upazila_num year
local controls private_bank_branch public_bank_branch ntl_mean

compare_flood_rules ln_accounts, panel("long") family("access") label("Bank accounts") startyear(2008) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_deposits, panel("long") family("usage") label("Deposits") startyear(2008) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loans, panel("long") family("usage") label("Loans") startyear(2008) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loan_deposit_ratio, panel("long") family("usage") label("Loan-to-deposit ratio") startyear(2008) controllist("`controls'") handle(`comparison')

********************************************************************************
* Disaggregated financial panel
********************************************************************************

use "$DERIVED/master_analysis_disaggregated_2020_2024.dta", clear
xtset upazila_num year
local controls private_bank_branch public_bank_branch ntl_mean

compare_flood_rules ln_depacc, panel("disagg") family("access") label("Deposit accounts") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanacc, panel("disagg") family("access") label("Loan accounts") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_depacc_ab1cr, panel("disagg") family("access") label("Deposit accounts above BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_depacc_1crbl1cr, panel("disagg") family("access") label("Deposit accounts at or below BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanacc_ab1cr, panel("disagg") family("access") label("Loan accounts above BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanacc_1crbl1cr, panel("disagg") family("access") label("Loan accounts at or below BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_agri_loanacc, panel("disagg") family("access") label("Agricultural loan accounts") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_ind_loanacc, panel("disagg") family("access") label("Industrial loan accounts") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_priv_depacc, panel("disagg") family("access") label("Private-bank deposit accounts") startyear(2020) controllist("`controls'") handle(`comparison')

compare_flood_rules ln_depam, panel("disagg") family("usage") label("Deposit amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanam, panel("disagg") family("usage") label("Loan amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_depam_ab1cr, panel("disagg") family("usage") label("Deposit amount above BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_depam_1crbl1cr, panel("disagg") family("usage") label("Deposit amount at or below BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanam_ab1cr, panel("disagg") family("usage") label("Loan amount above BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loanam_1crbl1cr, panel("disagg") family("usage") label("Loan amount at or below BDT 10m") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_agri_loanam, panel("disagg") family("usage") label("Agricultural loan amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_ind_loanam, panel("disagg") family("usage") label("Industrial loan amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_priv_depam, panel("disagg") family("usage") label("Private-bank deposit amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_exportam, panel("disagg") family("usage") label("Export amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_importam, panel("disagg") family("usage") label("Import amount") startyear(2020) controllist("`controls'") handle(`comparison')
compare_flood_rules ln_loan_deposit_ratio, panel("disagg") family("usage") label("Loan-to-deposit ratio") startyear(2020) controllist("`controls'") handle(`comparison')

postclose `comparison'
use "$TABLES/flood_threshold_comparison.dta", clear
sort panel family outcome threshold
export delimited using "$TABLES/flood_threshold_comparison.csv", replace



