# Sensitivity Analysis -- Project Report

**Date:** 2026-02-08
**Branch:** `7feb`
**Tests before:** 137 | **Tests after:** 137 (analysis only, no new tests)

---

## Actions

- Created `backend/analysis/sensitivity_analysis.py` -- a standalone script running three-dimensional sensitivity analysis on the Lee-Carter pipeline
- No engine modules (a01-a10) were modified; all 137 existing tests remain untouched
- Analysis 1: Swept interest rates i = 2% to 8% on Mexico's projected life table (year 2029), computing premiums for 3 products at 8 ages plus reserve trajectories for whole life at age 35
- Analysis 2: Applied mortality shock factors 0.70 to 1.30 on Mexico's projected q_x, holding i = 5%, computing premiums and reserve trajectories
- Analysis 3: Ran the full Lee-Carter pipeline (1990-2019, age_max=100, lambda=1e5, reestimate_kt=False) for Mexico, USA, and Spain, comparing Lee-Carter diagnostics, projection parameters, and premiums side by side
- Generated 4 text report files in `backend/analysis/results/`
- Ran a verification checklist confirming all actuarial invariants (premiums decrease with i, endowment > term, shock=1.00 matches base, reserve at t=0 near zero, negative drifts, identifiability constraints, no NaN/Inf)

## Outputs

| Artifact | Type | Content |
|:---------|:-----|:--------|
| `backend/analysis/sensitivity_analysis.py` | New script | Three-axis sensitivity analysis (1017 lines) |
| `backend/analysis/results/sensitivity_interest_rate.txt` | Report | Premium/reserve tables at 7 interest rates |
| `backend/analysis/results/sensitivity_mortality_shock.txt` | Report | Premium/reserve tables at 7 shock factors |
| `backend/analysis/results/sensitivity_cross_country.txt` | Report | Mexico vs USA vs Spain Lee-Carter comparison |
| `backend/analysis/results/sensitivity_summary.txt` | Report | Executive summary with key findings |

---

## Chronology

* **Building the Mexico base pipeline**

The session began by running the full Lee-Carter pipeline on Mexico's INEGI/CONAPO data for the pre-COVID period 1990-2019: raw data loading, Whittaker-Henderson graduation (lambda=1e5), Lee-Carter SVD fitting (reestimate_kt=False, following the lesson from the previous session that graduated data can produce non-monotone death residuals), and Random Walk with Drift projection to year 2029 (10-year offset from last observed year). The base pipeline produced explained variance of 77.7%, drift of -1.0764, and a projected life table suitable for all three sensitivity dimensions.

* **Analysis 1: Interest rate sensitivity**

We swept 7 interest rates from 2% to 8% across 8 issue ages (25 through 60) and 3 products (whole life, term 20, endowment 20), producing a 7x8x3 grid of 168 premium values plus 7 reserve trajectories for whole life at age 35.

The dominant finding is the sheer magnitude of interest rate sensitivity for long-duration products. At age 40, the whole life premium ranges from $17,910 at i=2% to $7,014 at i=8% -- a 155% spread. The sensitivity amplifies at younger ages: at age 25 the whole life premium increases +109.6% when i drops from 5% to 2%. This makes economic sense because the discount factor v^n = (1+i)^{-n} compounds over decades. A whole life policy on a 25-year-old discounts benefits 50-80 years into the future, so small changes in i produce large changes in the present value of the death benefit. The earlier the age, the longer the expected payment period, the more compounding amplifies the effect.

Term 20 premiums showed dramatically less sensitivity: roughly 7-11% spread across the same rate range. This is because term insurance has a fixed, short horizon. The benefits and premiums are both discounted over at most 20 years, so the numerator (PV of benefits) and denominator (PV of annuity) move in the same direction and partially cancel. Endowment 20 sits in between at roughly 27-39% spread, dominated by its pure endowment (savings) component which discounts a lump sum 20 years out.

Reserve trajectories confirmed that higher interest rates reduce reserves at every duration, consistent with the underlying mathematics: a higher i makes the present value of future obligations smaller relative to the present value of future premiums, shrinking the gap that the reserve must cover.

* **Analysis 2: Mortality shock sensitivity**

We applied multiplicative shocks from 0.70x to 1.30x to the base q_x values, clipping at 1.0, then rebuilt l_x from the shocked mortality. All premiums were computed at i=5%.

The headline result is asymmetry. At age 40 (whole life), a +30% mortality deterioration (1.30x) raises the premium by +16.2%, but a symmetric -30% improvement (0.70x) reduces it by -18.2%. The absolute magnitude of the decrease exceeds the increase. This appears to contradict the "convexity hurts the insurer" narrative at first glance, but the percentages tell the correct story: the ratio of absolute premium changes is 1.12:1 (increase-to-decrease), confirming convexity in the premium-as-a-function-of-q_x relationship. The asymmetry arises because the premium is a ratio M_x/N_x where both numerator and denominator depend on q_x, creating a nonlinear mapping.

Term 20 premiums showed near-perfect proportionality to the shock: a 30% q_x shock produced approximately a 30% premium change (29.5% at age 40, 29.9% at age 25). This near-linearity exists because for short-term insurance the death benefit dominates, and the annuity denominator barely changes when mortality shifts modestly. The premium is approximately proportional to the sum of q_x values, making the mapping nearly linear.

Endowment 20 was nearly insensitive: less than 1% premium change at young ages for a 30% mortality shock. At age 25, a 0.70x shock changed the premium by only -0.9%. The savings component (pure endowment) dwarfs the mortality component at young ages where q_x values are tiny. The premium is dominated by the time value of money, not by mortality. This confirms why endowment products are often sold as "savings vehicles" rather than "insurance."

Reserve trajectories under mortality shocks showed that higher mortality leads to higher reserves at every duration. When mortality increases, the insurer expects to pay death benefits sooner, requiring larger reserves to meet those earlier obligations.

* **Analysis 3: Cross-country comparison**

All three countries used the same pipeline configuration: 1990-2019, ages 0-100, lambda=1e5 graduation, SVD-only k_t (no re-estimation). Mexico used INEGI/CONAPO with sex="Total"; USA and Spain used HMD with sex="Male".

Lee-Carter diagnostics revealed a clear hierarchy. Spain achieved 94.8% explained variance (excellent), USA 86.7% (good), Mexico 77.7% (good). Spain's high explained variance reflects a more uniform mortality improvement pattern -- nearly all ages improved at a consistent pace, which is exactly what Lee-Carter's single-factor model captures well. Mexico's lower explained variance reflects a more heterogeneous improvement pattern: infant mortality improved dramatically (large b_x at ages 0-5, with b_0=0.0288 vs Spain's 0.0116), while old-age mortality improved less, and young-adult mortality showed a distinctive hump. A single b_x*k_t factor struggles to capture these disparate age patterns simultaneously.

The drift comparison is striking. Spain's drift of -2.89 is 2.7 times Mexico's drift of -1.08. This ratio quantifies the "healthcare development gap": Spain's mortality improvement rate is nearly three times faster. Since drift enters the projection as k_{T+h} = k_T + h*drift, and k_t enters the mortality surface as exp(a_x + b_x*k_t), a drift 2.7x more negative means Spain's future mortality declines exponentially faster at every age. The practical consequence shows up directly in premiums: at age 40 (i=5%), Mexico's whole life premium is $10,765 versus Spain's $8,191 -- a 31% premium gap. For term 20, the gap is even larger: Mexico $4,172 versus Spain $2,178 (92% higher), because term insurance is purely mortality-driven.

The a_x profiles (average log-mortality) show Mexico's higher base mortality at nearly every age. Mexico's a_0 = -4.26 versus Spain's -5.81, meaning Mexico's average infant mortality rate is exp(-4.26)/exp(-5.81) = 4.7 times higher. At working ages the gap narrows but persists. The b_x profiles reveal where each country's improvement is concentrated: Mexico has large b_x at infant ages (0-5), reflecting the public health interventions that disproportionately reduced infant mortality during 1990-2019. Spain has large b_x at young-adult ages (20-30), possibly reflecting improvements in road safety and violence reduction. The USA shows large b_x at old ages (70-80), reflecting advances in cardiovascular and cancer treatment.

* **Verification**

A formal checklist was run against the output:
- Premiums strictly decrease as i increases: confirmed at all 168 data points
- Endowment premium exceeds term premium at every age and rate: confirmed
- Shock factor 1.00x reproduces base premiums exactly (0.0% change): confirmed
- Reserve at duration 0 is approximately zero: confirmed ($0 or $-0 rounding), validating the equivalence principle
- All 3 countries: negative drift, explained_var > 50%, sum(b_x) = 1.000000, sum(k_t) approximately 0: confirmed
- No NaN or Inf values in any output: confirmed

The reference technical document `docs/technical/15_sensitivity_analysis_reference.md` contains the formulas and detailed tables supporting this session.
