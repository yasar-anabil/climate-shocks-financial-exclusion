clear all
set more off
version 17

capture log close _all
do "code/00_config.do"
log using "$LOGS/run.log", replace text name(master)

display as text _newline "Building analysis panels"
do "$CODE/01_build_panel.do"

display as text _newline "Producing descriptive and regression results"
do "$CODE/02_descriptives.do"
do "$CODE/03_estimate_models.do"
do "$CODE/04_flood_sensitivity.do"
do "$CODE/05_original_specifications.do"
do "$CODE/99_check_outputs.do"

log close master
display as result _newline "Workflow completed successfully."



