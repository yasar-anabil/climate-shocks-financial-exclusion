* Synthetic demonstration of a lagged climate and financial panel.
* All observations are fictional and do not reproduce project estimates.

clear all
set more off
version 17
set seed 241240

* The 2019 row supplies the first lag for the 2020 analysis period.
set obs 200
gen long upazila_num = _n
gen double upazila_effect = rnormal(0, 0.30)
expand 6
bysort upazila_num: gen int year = 2018 + _n
isid upazila_num year
xtset upazila_num year

gen double cyc_wind10 = runiform() * 2
gen double flood_fraction = runiform() * 0.4
gen double flood_10pp = flood_fraction / 0.10
gen double ln_deposits = 7 + upazila_effect + 0.03*(year-2019) ///
    - 0.02*L.cyc_wind10 - 0.03*L.flood_10pp + rnormal(0, 0.15) ///
    if year >= 2020

assert inrange(flood_fraction, 0, 1)
assert flood_10pp == flood_fraction / 0.10
assert !missing(L.cyc_wind10, L.flood_10pp) if year >= 2020

* Upazila and year fixed effects, with upazila-clustered standard errors.
xtreg ln_deposits L.cyc_wind10 L.flood_10pp i.year ///
    if year >= 2020, fe vce(cluster upazila_num)
assert e(N) == 1000
display as result "Synthetic panel checks passed; estimates are illustrative only."

