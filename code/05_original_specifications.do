* 05_original_specifications.do
* Estimate the latest original models using each specification’s available sample.

version 17
clear all
set more off
do "code/00_config.do"

tempname results
postfile `results' str6 panel str35 outcome str70 outcome_label str12 controls str12 model str12 shock double coefficient standard_error p_value observations within_r2 clusters using "$TABLES/original_specifications.dta", replace

capture program drop save_result
program define save_result
    syntax, HANDLE(name) PANEL(string) OUTCOME(string) LABEL(string) MODEL(string) SHOCK(string) VARIABLE(string) [CONTROLS(string)]
    local b = _b[`variable']
    local se = _se[`variable']
    local p = 2 * ttail(e(df_r), abs(`b' / `se'))
    post `handle' ("`panel'") ("`outcome'") ("`label'") ("`controls'") ("`model'") ("`shock'") (`b') (`se') (`p') (e(N)) (e(r2_within)) (e(N_clust))
end

capture program drop run_models
program define run_models
    syntax varname, HANDLE(name) PANEL(string) LABEL(string) [CONTROLS(string)]
    quietly reghdfe `varlist' L.cyc_wind10 L.flood_10pp L.RAI L.temp_shock `controls', absorb(upazila_num year) vce(cluster upazila_num)
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("joint") shock("cyclone") variable("L.cyc_wind10")
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("joint") shock("flood") variable("L.flood_10pp")
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("joint") shock("rainfall") variable("L.RAI")
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("joint") shock("temperature") variable("L.temp_shock")

    quietly reghdfe `varlist' L.cyc_wind10 `controls', absorb(upazila_num year) vce(cluster upazila_num)
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("separate") shock("cyclone") variable("L.cyc_wind10")
    quietly reghdfe `varlist' L.flood_10pp `controls', absorb(upazila_num year) vce(cluster upazila_num)
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("separate") shock("flood") variable("L.flood_10pp")
    quietly reghdfe `varlist' L.RAI `controls', absorb(upazila_num year) vce(cluster upazila_num)
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("separate") shock("rainfall") variable("L.RAI")
    quietly reghdfe `varlist' L.temp_shock `controls', absorb(upazila_num year) vce(cluster upazila_num)
    save_result, handle(`handle') panel("`panel'") outcome("`varlist'") label("`label'") controls("`controls'") model("separate") shock("temperature") variable("L.temp_shock")
end

capture program drop run_long
program define run_long
    syntax, HANDLE(name) [CONTROLS(string)]
    run_models ln_accounts, handle(`handle') panel("long") label("Bank accounts per capita") controls("`controls'")
    run_models ln_deposits, handle(`handle') panel("long") label("Deposits per capita") controls("`controls'")
    run_models ln_loans, handle(`handle') panel("long") label("Loans per capita") controls("`controls'")
end

capture program drop run_short
program define run_short
    syntax, HANDLE(name) [CONTROLS(string)]
    run_models ln_depacc, handle(`handle') panel("short") label("Deposit accounts per capita") controls("`controls'")
    run_models ln_loanacc, handle(`handle') panel("short") label("Loan accounts per capita") controls("`controls'")
    run_models ln_depacc_ab1cr, handle(`handle') panel("short") label("Deposit accounts above BDT 10m per capita") controls("`controls'")
    run_models ln_depacc_1crbl1cr, handle(`handle') panel("short") label("Deposit accounts at or below BDT 10m per capita") controls("`controls'")
    run_models ln_loanacc_ab1cr, handle(`handle') panel("short") label("Loan accounts above BDT 10m per capita") controls("`controls'")
    run_models ln_loanacc_1crbl1cr, handle(`handle') panel("short") label("Loan accounts at or below BDT 10m per capita") controls("`controls'")
    run_models ln_agri_loanacc, handle(`handle') panel("short") label("Agricultural loan accounts per capita") controls("`controls'")
    run_models ln_ind_loanacc, handle(`handle') panel("short") label("Industrial loan accounts per capita") controls("`controls'")
    run_models ln_priv_depacc, handle(`handle') panel("short") label("Private-bank deposit accounts per capita") controls("`controls'")
    run_models ln_depam, handle(`handle') panel("short") label("Deposit amount per capita") controls("`controls'")
    run_models ln_loanam, handle(`handle') panel("short") label("Loan amount per capita") controls("`controls'")
    run_models ln_depam_ab1cr, handle(`handle') panel("short") label("Deposit amount above BDT 10m per capita") controls("`controls'")
    run_models ln_depam_1crbl1cr, handle(`handle') panel("short") label("Deposit amount at or below BDT 10m per capita") controls("`controls'")
    run_models ln_loanam_ab1cr, handle(`handle') panel("short") label("Loan amount above BDT 10m per capita") controls("`controls'")
    run_models ln_loanam_1crbl1cr, handle(`handle') panel("short") label("Loan amount at or below BDT 10m per capita") controls("`controls'")
    run_models ln_agri_loanam, handle(`handle') panel("short") label("Agricultural loan amount per capita") controls("`controls'")
    run_models ln_ind_loanam, handle(`handle') panel("short") label("Industrial loan amount per capita") controls("`controls'")
    run_models ln_priv_depam, handle(`handle') panel("short") label("Private-bank deposit amount per capita") controls("`controls'")
end

use "$DERIVED/master_analysis_long_2008_2024.dta", clear
xtset upazila_num year
run_long, handle(`results')
run_long, handle(`results') controls("private_bank_branch public_bank_branch ntl_mean")

use "$DERIVED/master_analysis_disaggregated_2020_2024.dta", clear
xtset upazila_num year
run_short, handle(`results')
run_short, handle(`results') controls("private_bank_branch public_bank_branch ntl_mean")

postclose `results'
use "$TABLES/original_specifications.dta", clear
replace controls = "no" if controls == ""
replace controls = "yes" if controls != "no"
sort panel controls model outcome shock
export delimited using "$TABLES/original_specifications.csv", replace
