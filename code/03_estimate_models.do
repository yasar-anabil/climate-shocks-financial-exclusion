* 03_estimate_models.do
* Estimate joint and single-shock fixed-effects models.

clear all
set more off
version 17
do "code/00_config.do"

********************************************************************************
* STEP 1  Create an empty results file
********************************************************************************

tempname results
postfile `results' str8 panel str8 family str40 outcome str80 outcome_label ///
    str24 specification byte controls str16 shock double b se pvalue N ///
    r2_within N_clust using "$TABLES/regression_results.dta", replace

* This helper copies one coefficient and its standard error into the results
* file after each regression.
capture program drop save_one_climate_coefficient
program define save_one_climate_coefficient
    syntax, HANDLE(name) PANEL(string) FAMILY(string) OUTCOME(string) ///
        LABEL(string) SPEC(string) CONTROLS(integer) SHOCK(string) ///
        COEFNAME(string)

    local coefficient = _b[`coefname']
    local standard_error = _se[`coefname']
    local probability = 2 * ttail(e(df_r), ///
        abs(`coefficient' / `standard_error'))

    post `handle' ("`panel'") ("`family'") ("`outcome'") ("`label'") ///
        ("`spec'") (`controls') ("`shock'") (`coefficient') ///
        (`standard_error') (`probability') (e(N)) (e(r2_within)) ///
        (e(N_clust))
end

********************************************************************************
* STEP 2  Define the three regressions used for every financial outcome
********************************************************************************

capture program drop run_three_models
program define run_three_models
    syntax varname, PANEL(string) FAMILY(string) LABEL(string) ///
        STARTYEAR(integer) CONTROLLIST(string) HANDLE(name)

    * Keep one common sample for the controlled, uncontrolled and individual-
    * shock models. This makes their coefficients directly comparable.
    tempvar common_sample
    gen byte `common_sample' = year >= `startyear' & !missing(`varlist') ///
        & !missing(L.cyc_wind10) & !missing(L.flood_10pp) ///
        & !missing(L.RAI) & !missing(L.temp_shock)

    foreach control of local controllist {
        replace `common_sample' = 0 if missing(`control')
    }

    * Model A: all four climate shocks plus the financial controls.
    quietly reghdfe `varlist' L.cyc_wind10 L.flood_10pp L.RAI ///
        L.temp_shock `controllist' if `common_sample', ///
        absorb(upazila_num year) vce(cluster upazila_num)

    foreach pair in "cyclone L.cyc_wind10" "flood L.flood_10pp" ///
        "rainfall L.RAI" "temperature L.temp_shock" {
        gettoken shock_name coefficient_name : pair
        save_one_climate_coefficient, handle(`handle') panel("`panel'") ///
            family("`family'") outcome("`varlist'") label("`label'") ///
            spec("joint_controls") controls(1) shock("`shock_name'") ///
            coefname("`coefficient_name'")
    }

    * Model B: all four climate shocks, but no financial controls.
    quietly reghdfe `varlist' L.cyc_wind10 L.flood_10pp L.RAI ///
        L.temp_shock if `common_sample', absorb(upazila_num year) ///
        vce(cluster upazila_num)

    foreach pair in "cyclone L.cyc_wind10" "flood L.flood_10pp" ///
        "rainfall L.RAI" "temperature L.temp_shock" {
        gettoken shock_name coefficient_name : pair
        save_one_climate_coefficient, handle(`handle') panel("`panel'") ///
            family("`family'") outcome("`varlist'") label("`label'") ///
            spec("joint_no_controls") controls(0) shock("`shock_name'") ///
            coefname("`coefficient_name'")
    }

    * Model C: one climate shock at a time, with financial controls.
    foreach pair in "cyclone L.cyc_wind10" "flood L.flood_10pp" ///
        "rainfall L.RAI" "temperature L.temp_shock" {
        gettoken shock_name coefficient_name : pair
        quietly reghdfe `varlist' `coefficient_name' `controllist' ///
            if `common_sample', absorb(upazila_num year) ///
            vce(cluster upazila_num)

        save_one_climate_coefficient, handle(`handle') panel("`panel'") ///
            family("`family'") outcome("`varlist'") label("`label'") ///
            spec("single_controls") controls(1) shock("`shock_name'") ///
            coefname("`coefficient_name'")
    }

    drop `common_sample'
end

********************************************************************************
* STEP 3  Run the long-panel outcomes
********************************************************************************

use "$DERIVED/master_analysis_long_2008_2024.dta", clear
xtset upazila_num year
local financial_controls private_bank_branch public_bank_branch ntl_mean

run_three_models ln_accounts, panel("long") family("access") ///
    label("Bank accounts") startyear(2008) ///
    controllist("`financial_controls'") handle(`results')
run_three_models ln_deposits, panel("long") family("usage") ///
    label("Deposits") startyear(2008) ///
    controllist("`financial_controls'") handle(`results')
run_three_models ln_loans, panel("long") family("usage") ///
    label("Loans") startyear(2008) ///
    controllist("`financial_controls'") handle(`results')
run_three_models ln_loan_deposit_ratio, panel("long") family("usage") ///
    label("Loan-to-deposit ratio") startyear(2008) ///
    controllist("`financial_controls'") handle(`results')

********************************************************************************
* STEP 4  Run the disaggregated outcomes
********************************************************************************

use "$DERIVED/master_analysis_disaggregated_2020_2024.dta", clear
xtset upazila_num year
local financial_controls private_bank_branch public_bank_branch ntl_mean

run_three_models ln_depacc, panel("disagg") family("access") label("Deposit accounts") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanacc, panel("disagg") family("access") label("Loan accounts") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_depacc_ab1cr, panel("disagg") family("access") label("Deposit accounts above BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_depacc_1crbl1cr, panel("disagg") family("access") label("Deposit accounts at or below BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanacc_ab1cr, panel("disagg") family("access") label("Loan accounts above BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanacc_1crbl1cr, panel("disagg") family("access") label("Loan accounts at or below BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_agri_loanacc, panel("disagg") family("access") label("Agricultural loan accounts") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_ind_loanacc, panel("disagg") family("access") label("Industrial loan accounts") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_priv_depacc, panel("disagg") family("access") label("Private-bank deposit accounts") startyear(2020) controllist("`financial_controls'") handle(`results')

run_three_models ln_depam, panel("disagg") family("usage") label("Deposit amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanam, panel("disagg") family("usage") label("Loan amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_depam_ab1cr, panel("disagg") family("usage") label("Deposit amount above BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_depam_1crbl1cr, panel("disagg") family("usage") label("Deposit amount at or below BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanam_ab1cr, panel("disagg") family("usage") label("Loan amount above BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loanam_1crbl1cr, panel("disagg") family("usage") label("Loan amount at or below BDT 10m") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_agri_loanam, panel("disagg") family("usage") label("Agricultural loan amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_ind_loanam, panel("disagg") family("usage") label("Industrial loan amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_priv_depam, panel("disagg") family("usage") label("Private-bank deposit amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_exportam, panel("disagg") family("usage") label("Export amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_importam, panel("disagg") family("usage") label("Import amount") startyear(2020) controllist("`financial_controls'") handle(`results')
run_three_models ln_loan_deposit_ratio, panel("disagg") family("usage") label("Loan-to-deposit ratio") startyear(2020) controllist("`financial_controls'") handle(`results')

postclose `results'
use "$TABLES/regression_results.dta", clear
sort panel family specification outcome shock
export delimited using "$TABLES/regression_results.csv", replace



