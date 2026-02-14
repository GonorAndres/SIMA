# Real Mexican Data Analysis -- Project Report

**Date:** 2026-02-08
**Branch:** `7feb`
**Tests before:** 137 | **Tests after:** 137 (analysis only, no new tests)

---

## Actions

- Wrote `backend/analysis/mexico_lee_carter.py`, a standalone analysis script that runs the full Lee-Carter pipeline on real INEGI/CONAPO data
- Ran two parallel analyses: pre-COVID (1990-2019, 101 ages x 30 years) and full period (1990-2024, 101 ages x 35 years)
- Compared projected life tables against 7 regulatory tables: CNSF 2000-I (M/F), CNSF 2000-G (M/F), CNSFM 2013, EMSSA 2009 (M/F)
- Computed net annual premiums for 3 products (whole life, term-20, endowment-20) at 8 issue ages (25-60)
- Generated stochastic confidence intervals from 1000 RWD simulations (seed=42)
- Fixed `_reestimate_kt()` in `a08_lee_carter.py` with adaptive bracket search for non-monotone residual functions caused by negative b_x
- Decided on `reestimate_kt=False` for graduated data (SVD k_t is the consistent choice when the mortality surface has been altered by smoothing)
- Generated COVID-19 impact comparison report showing parameter shifts and premium increases

## Outputs

| Artifact | Type | Content |
|:---------|:-----|:--------|
| `backend/analysis/mexico_lee_carter.py` | Analysis script | Full pipeline: load, graduate, fit, project, compare, price |
| `backend/analysis/results/mexico_pre_covid_2019.txt` | Report | Pre-COVID analysis (1990-2019), 7 sections, target year 2029 |
| `backend/analysis/results/mexico_full_2024.txt` | Report | Full-period analysis (1990-2024), 7 sections, target year 2034 |
| `backend/analysis/results/mexico_covid_comparison.txt` | Report | Side-by-side parameter, premium, and k_t trajectory comparison |
| `backend/engine/a08_lee_carter.py` | Modified | Adaptive bracket search in `_reestimate_kt()` |

---

## Chronology

* **Loading real Mexican data**

The session began by running the INEGI/CONAPO data through the `MortalityData.from_inegi()` loader that had been built and tested with mock data in previous sessions. The real data covered deaths from INEGI and mid-year population estimates from CONAPO, combined for both sexes ("Total"), ages 0-100, yielding a 101 x 30 matrix for the pre-COVID window (1990-2019) and a 101 x 35 matrix for the full period (1990-2024). The data loaded cleanly, confirming that the mock data format had been designed to match the real file structure.

* **Graduation and the reestimate_kt decision**

Whittaker-Henderson graduation was applied with lambda=1e5, the same value used in the HMD-based tests. Graduation smooths the log mortality rates, and this creates a fundamental tension with Lee-Carter's k_t re-estimation step. The re-estimation equation `sum_x E_{x,t} * exp(a_x + b_x * k_t) = sum_x D_{x,t}` requires that the graduated rates can reproduce the raw observed death counts. But graduation has already changed the mortality surface: the graduated m_x values no longer satisfy this identity. In effect, the left side of the equation operates on smoothed rates while the right side expects raw deaths, and no single k_t can reconcile this mismatch.

The deeper issue is that Whittaker-Henderson graduation introduces negative b_x values at certain ages (77, 78, 85 in the Mexican data). When all b_x are positive, the death_residual(k) function is strictly monotone in k, and Brent's method always finds a root. But a negative b_x means that increasing k increases mortality at most ages while decreasing it at those specific ages. The net effect makes death_residual(k) U-shaped rather than monotone: it decreases toward a minimum and then increases again. If the observed total deaths fall below this minimum, no root exists.

This led to two code changes. First, the `_reestimate_kt()` method in `a08_lee_carter.py` was hardened with an adaptive bracket search: when the initial [-500, 500] bracket fails, the code samples the function at 201 points across this range, finds the first sign change, and uses that sub-interval for Brent's method. If no sign change is found (the function never reaches zero), it falls back to the k that minimizes |residual|. Second, the analysis script was configured with `reestimate_kt=False`, because the SVD-estimated k_t minimizes error in log-space, which is exactly what the Lee-Carter log-bilinear formulation asks for. Re-estimation is the right choice for raw data; for graduated data, the SVD k_t is the more internally consistent parameter. See `10_lee_carter_implementation_reference.md` for the SVD fitting procedure and `09_whittaker_henderson_reference.md` for the graduation formulas.

* **Pre-COVID results (1990-2019)**

The Lee-Carter model achieved 77.7% explained variance on the pre-COVID data, with RMSE of 0.0618 in log-space. This is a strong fit for a single-factor model applied to total (both-sex) data over 30 years. The k_t time series showed steady mortality improvement from k_t = 23.27 in 1990 down to k_t = -7.95 in 2019, with drift of -1.076 per year and sigma of 1.789. The negative drift confirms that Mexican mortality has been improving substantially over this period.

Projection 10 years forward to 2029 produced plausible mortality rates: q_60 = 0.0105, q_70 = 0.0223, q_80 = 0.0544. The 90% confidence intervals from 1000 stochastic simulations were relatively tight at younger ages (q_30 between 0.00131 and 0.00158) and wider at older ages (q_80 between 0.0533 and 0.0558).

The regulatory comparison showed that the CNSF 2000-I table (the individual life insurance standard) had a mean q_x ratio of 0.9469, meaning projected mortality was about 5% below the regulatory table on average. This is a reasonable and expected result: mortality has improved since 2000, so a table calibrated to turn-of-century experience should be slightly conservative relative to current projections. See `13_mortality_projection_reference.md` for the RWD projection methodology.

* **The EMSSA-2009 comparison and its actuarial significance**

The comparison against EMSSA 2009 (the Mexican social security mortality table used for pension reserves) revealed a striking divergence at older ages. The projected-to-regulatory q_x ratio was close to 1.0 at working ages (0.91 at age 20, 0.98 at age 30, 0.98 at age 40) but climbed sharply thereafter: 1.32 at age 50, 1.74 at age 60, 2.03 at age 70, 2.59 at age 80, and 2.87 at age 90. This means our Lee-Carter projection predicts mortality rates 2-3 times higher than EMSSA assumes at old ages.

This is not a deficiency in the model. EMSSA 2009 was constructed as an experience table for the IMSS (Mexican Social Security Institute) pensioner population, which is a selected and generally healthier subset of the national population. INEGI/CONAPO data covers the entire population including uninsured individuals with worse health outcomes. The divergence at old ages reflects genuine selection effects: pensioners with formal employment histories tend to be healthier than the general population, especially at advanced ages where socioeconomic disparities in mortality are most pronounced.

For insurance pricing, this result has a practical implication: using EMSSA 2009 for life insurance (death benefit) reserves would underestimate mortality risk at ages 50+. The CNSF 2000-I table, which showed a mean ratio of 0.95, is more appropriate for that purpose. The EMSSA table remains appropriate for pension (annuity) reserves on the IMSS population it was designed for.

* **Full-period results and the COVID distortion (1990-2024)**

Including the COVID years (2020-2024) degraded the Lee-Carter fit substantially. Explained variance dropped from 77.7% to 53.5%, RMSE in log-space nearly doubled from 0.0618 to 0.1052, and maximum absolute error jumped from 0.33 to 0.54. The k_t trajectory tells the story: after declining steadily from 20.47 in 1990 to -6.69 in 2018, k_t spiked to -4.72 in 2020 and -3.34 in 2021, representing a massive reversal in the mortality improvement trend. By 2024, k_t had recovered to -8.59, slightly below the pre-COVID level, suggesting the pandemic's direct mortality impact had largely dissipated.

The explained variance drop from 77.7% to 53.5% is the most telling diagnostic. Lee-Carter assumes that k_t captures a single dominant temporal pattern of mortality change, modeled as a random walk with drift. COVID violates this assumption because the pandemic's age profile (encoded in b_x) differs from the age profile of secular mortality improvement. In the pre-COVID data, the first SVD component explains 77.7% of variation because secular improvement is indeed the dominant force. Adding COVID introduces variation along a different age-mortality axis, which dilutes the first component's explanatory power. A two-factor model (Li-Lee or Renshaw-Haberman) might be more appropriate for data spanning a pandemic.

The drift shifted from -1.076 to -0.855 (a difference of +0.222), meaning the model now estimates mortality is improving about 20% more slowly. This is the linear trend being pulled upward by the COVID spike. Interestingly, sigma decreased from 1.789 to 1.516, because the overall variance in k_t innovations is dominated by the secular trend rather than the COVID spike (the spike is a level shift that the linear model absorbs into the drift, not into the volatility).

* **Premium impact of COVID data**

The COVID distortion propagated through the pipeline into insurance premiums. Whole life premiums increased by 3.2-4.3% across all ages, with the largest percentage impact at younger ages (4.28% at age 25 vs. 3.24% at age 60). Term-20 premiums showed larger percentage increases of 5.8-9.9%, again with bigger impacts at younger ages. The reason is that younger policyholders have longer exposure to the shifted mortality trend, so the cumulative effect of a less negative drift compounds over more years.

In absolute terms, the premium increases ranged from +$150/year (term-20, age 25) to +$1,171/year (term-20, age 60), relative to a $1,000,000 MXN sum assured. For a portfolio of policies, these differences would aggregate to material reserve adjustments.

* **Script architecture and reproducibility**

The analysis script (`backend/analysis/mexico_lee_carter.py`) was designed as a self-contained, reproducible pipeline. It imports all 8 engine modules (a01, a02, a04, a06, a07, a08, a09, a10), runs both analyses sequentially, and writes three structured text reports to `backend/analysis/results/`. The random seed is fixed at 42 for all stochastic simulations, ensuring exact reproducibility. The script exercises the full dependency chain documented in `14_architecture_integration_reference.md`: INEGI data -> MortalityData -> GraduatedRates -> LeeCarter -> MortalityProjection -> LifeTable -> CommutationFunctions -> PremiumCalculator, with MortalityComparison cross-referencing against regulatory tables at the end.

---

## Key Technical References

| Topic | Reference Doc |
|:------|:-------------|
| Lee-Carter SVD fitting, k_t re-estimation | `docs/technical/10_lee_carter_implementation_reference.md` |
| RWD projection, stochastic simulation | `docs/technical/13_mortality_projection_reference.md` |
| Whittaker-Henderson graduation | `docs/technical/09_whittaker_henderson_reference.md` |
| System architecture, dependency flow | `docs/technical/14_architecture_integration_reference.md` |
| Lee-Carter mathematical foundations | `docs/technical/07_lee_carter_foundations_reference.md` |
| Life table construction | `docs/technical/11_life_table_foundations_reference.md` |

---

## Status

- **Code changes:** Modified `a08_lee_carter.py` (adaptive bracket search). New analysis script and 3 output reports.
- **Tests:** 137 passing (unchanged). The analysis script is not a test; it runs on real data that is gitignored.
- **Branch:** `7feb`
- **Real data required:** The analysis depends on files in `backend/data/inegi/`, `backend/data/conapo/`, and `backend/data/cnsf/`, which are gitignored. See the DOWNLOAD_GUIDE.md files in each directory.

---

## Next Steps

1. **Sensitivity Analysis** -- Vary interest rates and apply mortality shocks to see how reserves respond
2. **Sex-specific analysis** -- Run Lee-Carter separately for males ("Hombres") and females ("Mujeres") instead of combined
3. **Phase 3: Capital Requirements** -- Map mortality/longevity/interest rate risks, define stress scenarios per CNSF
4. **Phase 4: Web Platform** -- FastAPI backend exposing the engine, interactive frontend
