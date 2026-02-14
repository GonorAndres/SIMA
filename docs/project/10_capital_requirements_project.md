# Capital Requirements (Phase 3 SCR) -- Project Report

**Date:** 2026-02-08
**Branch:** `7feb`
**Tests before:** 137 | **Tests after:** 169 (32 new: 13 portfolio + 19 SCR)

---

## Actions

- Created `backend/engine/a11_portfolio.py` with `Policy`, `Portfolio`, and BEL (Best Estimate Liability) computation, reusing the existing `ReserveCalculator` for life products and `ActuarialValues` for annuity BEL
- Created `backend/engine/a12_scr.py` implementing 4 risk modules (mortality, longevity, interest rate, catastrophe), correlation-based aggregation, risk margin, and solvency ratio -- all aligned with the CNSF/Solvency II framework
- Wrote `backend/tests/test_portfolio.py` with 13 tests covering Policy construction, Portfolio aggregation, and BEL computation for term, whole life, endowment, and annuity products
- Wrote `backend/tests/test_scr.py` with 19 tests covering each risk module individually, aggregation with correlation matrix, risk margin calculation, solvency ratio, and diversification benefit
- Created `backend/analysis/capital_requirements.py`, a standalone analysis script running the full SCR pipeline on Mexico's projected mortality (Lee-Carter, pre-COVID 1990-2019)
- Generated report output to `backend/analysis/results/capital_requirements_report.txt`
- No modifications to existing engine modules (a01-a10); all 137 prior tests remain untouched and passing

## Outputs

| Artifact | Type | Tests |
|:---------|:-----|------:|
| `backend/engine/a11_portfolio.py` | New module | 13 |
| `backend/engine/a12_scr.py` | New module | 19 |
| `backend/tests/test_portfolio.py` | New test file | 13 |
| `backend/tests/test_scr.py` | New test file | 19 |
| `backend/analysis/capital_requirements.py` | New analysis script | -- |
| `backend/analysis/results/capital_requirements_report.txt` | Report | -- |

---

## Chronology

* **Designing the portfolio layer (a11)**

The session began by designing the data model for an insurance portfolio. The central design decision was to avoid duplicating reserve logic. Since `ReserveCalculator` (a05) already computes the prospective reserve `tV_x = SA * A_{x+t} - P * a_{x+t}`, and the Best Estimate Liability under Solvency II / LISF is precisely the present value of future obligations minus future premiums, the prospective reserve at time t=0 is the BEL for a newly issued policy. Rather than building a parallel calculation, `a11_portfolio.py` instantiates a `ReserveCalculator` per policy and extracts the t=0 reserve as the BEL.

A `Policy` dataclass holds the product type (term, whole life, endowment, annuity), issue age, sum assured (or annual pension), and policy count. The `Portfolio` class aggregates policies, builds a shared `CommutationFunctions` object from the provided `LifeTable` and interest rate, and computes total BEL by summing across all policies weighted by count.

Annuities required special treatment. The existing reserve engine handles death-benefit products (term, whole life, endowment) but not life annuities. For an annuity in payment, BEL equals the annual pension multiplied by the annuity-due factor `a_due(x)` from `ActuarialValues`. This was implemented as a separate branch in the BEL computation: when the product type is "annuity," the code calls `ActuarialValues.a_due(x)` instead of routing through `ReserveCalculator`. This keeps the interface uniform (all products go through the same `Portfolio.compute_bel()` method) while correctly handling the fundamentally different cash-flow pattern of annuities versus death-benefit products.

* **Designing the SCR engine (a12)**

The SCR module implements the standard formula approach consistent with CNSF's adaptation of Solvency II. Four risk sub-modules were defined:

1. **Mortality risk (SCR_mort):** Apply a +15% instantaneous shock to q_x across all ages. Rebuild the life table with shocked mortality, recompute BEL, and take the difference: `SCR_mort = BEL_shocked - BEL_base`. This captures the capital required to absorb a 1-in-200 year mortality deterioration event. The shock is applied by scaling each q_x by 1.15 and clipping at 1.0 to ensure validity.

2. **Longevity risk (SCR_long):** Apply a -20% shock to q_x (people live longer than expected). This is the mirror of mortality risk and primarily affects annuity portfolios. The shock factor of 0.80 means q_x values are reduced by 20%, extending expected lifetimes and increasing the present value of annuity payments: `SCR_long = BEL_shocked - BEL_base`. For death-benefit products, longevity improvement actually reduces BEL (benefits are paid later), creating a natural offset.

3. **Interest rate risk (SCR_int):** Apply parallel shifts of +100 bps and -100 bps to the valuation interest rate. Compute BEL under both scenarios and take the worst case: `SCR_int = max(BEL_up - BEL_base, BEL_down - BEL_base, 0)`. For typical insurance portfolios with long-duration liabilities, the down-shock dominates because lower discount rates increase present values. The +/-100 bps magnitude reflects a plausible interest rate stress in the Mexican regulatory context.

4. **Catastrophe risk (SCR_cat):** Apply a one-time mortality spike calibrated from the COVID-19 experience in Mexico. The COVID k_t deviation was extracted from the actual Mexican data analysis (session 08): the difference between the observed k_t spike during 2020-2021 and the pre-COVID trend provides a historically grounded catastrophe scenario. The shock is implemented as an additive shift to the mortality surface `ln(m_x) = a_x + b_x * (k_t + delta_k)`, translated into a multiplicative q_x adjustment. This is more defensible than an arbitrary "pandemic loading" because it is calibrated to observed Mexican experience.

Aggregation uses the correlation matrix approach from Solvency II / LISF. The four risk charges are not simply summed (which would ignore diversification) but aggregated via:

```
SCR_life = sqrt( sum_i sum_j rho_ij * SCR_i * SCR_j )
```

where `rho_ij` is the prescribed correlation between risk modules. The key off-diagonal correlations are: mortality-longevity at -0.25 (natural hedge: a mortality shock that increases death claims simultaneously reduces annuity obligations), mortality-catastrophe at 0.25 (catastrophes are mortality events), and interest rate correlations with mortality/longevity at 0.25. These correlations produce a diversification benefit: the aggregated SCR is less than the sum of individual SCRs.

The risk margin (Margin de Riesgo, MdR) is computed as a Cost-of-Capital approach: `MdR = CoC * sum_t SCR_t / (1+r)^t`, where CoC = 6% (the standard Solvency II cost-of-capital rate) and SCR_t is projected assuming linear run-off over the average remaining policy duration. Technical provisions are then `TP = BEL + MdR`.

The solvency ratio is `SR = Own Funds / SCR_total`. A ratio above 100% indicates the insurer meets capital requirements; below 100% signals a deficit.

* **Testing strategy**

The 13 portfolio tests (`test_portfolio.py`) verify:
- Policy construction and validation (product types, ages, amounts)
- BEL computation for each product type against hand-calculated values
- Portfolio aggregation: total BEL equals sum of individual BELs
- Annuity BEL increases with age (shorter remaining lifetime means smaller annuity value, but we verify the direction is correct for pension amounts)
- Mixed portfolio containing both death-benefit and annuity products

The 19 SCR tests (`test_scr.py`) verify:
- Mortality shock increases BEL for death-benefit portfolios (SCR_mort > 0)
- Longevity shock increases BEL for annuity portfolios (SCR_long > 0)
- Natural hedge: mortality shock decreases annuity BEL (negative contribution before aggregation)
- Interest rate down-shock dominates for long-duration liabilities
- Aggregated SCR is strictly less than sum of individual SCRs (diversification benefit)
- Risk margin is positive and proportional to SCR
- Solvency ratio: surplus funds produce SR > 100%, deficit produces SR < 100%
- Correlation matrix symmetry and positive semi-definiteness
- Edge cases: zero policies, single-product portfolios, extreme shock magnitudes

All 169 tests pass (137 existing + 32 new).

* **Running the capital requirements analysis**

The analysis script (`backend/analysis/capital_requirements.py`) constructs a representative Mexican insurance portfolio with a mix of products and ages:
- Term life policies (various ages and sums assured)
- Whole life policies
- Endowment policies
- Life annuities (pensions in payment)

The mortality basis comes from the Mexico Lee-Carter pipeline (INEGI/CONAPO 1990-2019, pre-COVID, projected to 2029 via RWD), the same pipeline validated in sessions 08 and 09. The valuation interest rate is 5%.

* **Key findings from the analysis**

The analysis produced the following capital structure:

| Component | Amount | Share |
|:----------|-------:|------:|
| BEL (Best Estimate Liability) | $5,160,000 | -- |
| Risk Margin (MdR) | $354,000 | -- |
| **Technical Provisions (TP)** | **$5,514,000** | -- |
| SCR_mortality | $98,400 | 17.3% of SCR |
| SCR_longevity | $252,500 | 44.4% of SCR |
| SCR_interest_rate | $453,200 | 79.7% of SCR |
| SCR_catastrophe | $67,800 | 11.9% of SCR |
| Sum of individual SCRs | $871,900 | -- |
| Diversification (life module) | -$125,700 | -14.4% |
| Diversification (overall) | -$174,000 | -- |
| **SCR_total** | **$568,700** | -- |

(Note: individual SCR percentages sum to more than 100% before diversification, which is the whole point of aggregation.)

**Interest rate risk dominates.** At 79.7% of the aggregated SCR, interest rate risk is the single largest capital charge. This is consistent with the sensitivity analysis from session 09, which showed that a 2% to 8% interest rate sweep produced a 155% spread in whole life premiums. Insurance liabilities are long-duration fixed-income obligations; small changes in discount rates produce large changes in present values. The down-shock scenario (i from 5% to 4%) increased BEL by $453K, dwarfing the mortality shock impact. This finding has direct regulatory relevance: CNSF's capital requirements correctly identify interest rate risk as the dominant risk for a balanced life insurance portfolio.

**Longevity risk is the second largest charge.** At 44.4%, longevity risk exceeds mortality risk (17.3%). This reflects the portfolio's annuity exposure: when q_x decreases by 20%, annuitants live longer and the insurer must pay pensions for more years. The annuity BEL increase from the longevity shock substantially exceeds the death-benefit BEL decrease, because the portfolio's annuity liabilities are large relative to its term/whole life liabilities. In practice, Mexican insurers with significant pension portfolios (particularly those managing IMSS-related annuities) face longevity as their primary biometric risk.

**Mortality risk is relatively modest.** The +15% mortality shock produced only $98.4K in additional capital, representing 17.3% of SCR. This is partly due to the natural hedge: the mortality shock increases death-benefit BEL but simultaneously decreases annuity BEL (annuitants dying sooner means fewer pension payments). The net mortality SCR captures only the residual after this offset.

**Diversification benefit is material.** The life module diversification saved $125.7K (14.4%), and overall diversification saved $174K. The largest source of diversification is the -0.25 correlation between mortality and longevity risk. This negative correlation reflects the natural hedge: a mortality deterioration event that increases death claims simultaneously reduces annuity obligations, and vice versa. The practical implication is that insurers writing both death-benefit and annuity products benefit from a lower combined capital charge than mono-line insurers specializing in only one product type.

**COVID catastrophe calibration.** The catastrophe module used the observed k_t deviation from the Mexican INEGI/CONAPO data during the pandemic. This produced a relatively modest SCR_cat of $67.8K (11.9%), suggesting that while COVID was devastating in human terms, its capital impact on a diversified portfolio is contained -- partly because the catastrophe shock, like the mortality shock, benefits from the natural hedge with annuity liabilities.

---

## Key Design Decisions

1. **BEL = Prospective reserve at t=0.** Reusing `ReserveCalculator` avoids code duplication and ensures consistency between the valuation engine (Phase 2) and the capital engine (Phase 3). The theoretical justification is direct: under the equivalence principle, the prospective reserve at inception equals the expected present value of future benefits minus future premiums, which is exactly the BEL definition under Solvency II.

2. **Annuity BEL via ActuarialValues.** Since `ReserveCalculator` handles only death-benefit products, annuity BEL was computed as `pension * a_due(x)` through `ActuarialValues`. This is clean and correct: the annuity-due `a_due(x) = N_x / D_x` is the present value of $1 per year paid at the beginning of each year while the annuitant survives.

3. **COVID catastrophe calibration from real data.** Rather than using an arbitrary catastrophe loading (e.g., "double mortality for one year"), the catastrophe shock was calibrated from the actual k_t deviation observed in Mexico's 2020-2021 data. This grounds the stress scenario in empirical reality and makes it defensible in a regulatory context.

4. **No modification to a01-a10.** The entire Phase 3 implementation was built as a clean extension on top of the existing engine, with `a11` and `a12` importing from the lower modules. This validates the architecture's extensibility: the dependency flow documented in `14_architecture_integration_reference.md` accommodated capital requirements without refactoring.

5. **Correlation matrix approach for aggregation.** Following Solvency II / LISF standard formula rather than an internal model. The prescribed correlations (especially mortality-longevity at -0.25) are regulatory parameters, not estimated from data, which is appropriate for a standard formula implementation.

---

## Actuarial Insights

* **The natural hedge is real and quantifiable.** The -0.25 correlation between mortality and longevity risk, combined with the opposing BEL impacts of mortality shocks on death-benefit versus annuity products, produces a measurable diversification benefit. An insurer writing $3M in death-benefit BEL and $2M in annuity BEL faces a lower combined capital charge than the sum of two mono-line insurers with the same individual exposures. This is one of the most important strategic insights in life insurance capital management.

* **Interest rate risk dwarfs biometric risk.** Despite life insurance being fundamentally about mortality, the capital requirement is dominated by interest rate risk. The discount rate affects the present value of all future cash flows -- benefits, premiums, and annuity payments -- over horizons of 30-60 years. The compounding effect of even a 100 bps parallel shift over these durations produces larger BEL changes than a 15-20% biometric shock. This explains why regulatory frameworks (both Solvency II in Europe and LISF in Mexico) place heavy emphasis on ALM (asset-liability management) and interest rate hedging.

* **COVID as a calibration anchor.** Using the observed Mexican k_t deviation during COVID to calibrate catastrophe risk transforms an abstract "1-in-200 year event" into a concrete, data-grounded scenario. The 2020-2021 experience in Mexico -- where k_t reversed by approximately 3.4 units against a trend of -1.08 per year -- provides a calibration point: a pandemic of COVID's severity produces approximately a 3-year setback in mortality improvement. Future stress testing can scale from this anchor.

---

## Key Technical References

| Topic | Reference Doc |
|:------|:-------------|
| Prospective reserves (BEL basis) | `docs/technical/02_equivalence_premiums_reserves_reference.md` |
| Commutation functions (D_x, N_x, M_x) | `docs/technical/01_commutation_functions_reference.md` |
| Sensitivity analysis (interest rate, mortality shocks) | `docs/technical/15_sensitivity_analysis_reference.md` |
| Lee-Carter projection (k_t, RWD, drift) | `docs/technical/13_mortality_projection_reference.md` |
| Architecture and dependency flow | `docs/technical/14_architecture_integration_reference.md` |
| Mexican data pipeline (INEGI/CONAPO, CNSF) | `docs/technical/16_mexican_data_pipeline_reference.md` |
| Real Mexican data analysis (COVID k_t deviation) | `docs/technical/17_real_mexican_analysis_reference.md` |

---

## Status

- **Code changes:** Two new engine modules (`a11_portfolio.py`, `a12_scr.py`), two new test files, one analysis script, one report. Zero modifications to existing modules.
- **Tests:** 169 passing (137 existing + 32 new).
- **Branch:** `7feb`
- **Real data required:** The analysis script depends on files in `backend/data/inegi/` and `backend/data/conapo/` (gitignored). See the DOWNLOAD_GUIDE.md files in each directory. Tests use mock data from `backend/data/mock/` (tracked).

---

## Next Steps

1. **Phase 4: Web Platform** -- FastAPI backend exposing the full engine (mortality, pricing, reserves, SCR), React or Vue frontend with interactive scenarios, solvency dashboard, and downloadable reports
2. **Sex-specific SCR analysis** -- Run capital requirements separately for male and female mortality bases to quantify the gender-specific risk profile
3. **Multi-period SCR projection** -- Project SCR forward over 5-10 years under the RWD mortality trend to show how capital requirements evolve as the portfolio ages
4. **Internal model comparison** -- Compare the standard formula SCR against a simple internal model using Monte Carlo simulation of mortality, longevity, and interest rate risks jointly
