# Analysis Scripts: Technical Reference

**Source files:** `backend/analysis/mexico_lee_carter.py`, `backend/analysis/sensitivity_analysis.py`, `backend/analysis/capital_requirements.py`

---

## 1. Scripts vs Engine: The Consumer Pattern

The three analysis scripts are **consumers** of the engine library (`a01-a12`). They import engine classes, run computations with specific parameters, and produce human-readable text reports.

```
Engine (a01-a12):      Library code. No print statements. Returns objects/dicts.
Analysis scripts:      Consumer code. Prints progress. Writes .txt reports.
API services:          Also consumers. Returns JSON-serializable dicts.
```

| Property | Engine Modules | Analysis Scripts |
|:---------|:---------------|:-----------------|
| Purpose | Reusable computation | One-time analysis |
| Output | Python objects (LifeTable, dict) | Text reports (.txt) |
| Data source | Receives data as arguments | Hardcodes file paths |
| Side effects | None | Writes files, prints progress |
| Tests | 191 tests | No dedicated tests |
| Used by | API, tests, scripts | Standalone execution |

---

## 2. Script Summary

| Script | Lines | Engine Modules Used | Data Required | Output Files |
|:-------|:------|:-------------------|:--------------|:-------------|
| `mexico_lee_carter.py` | 536 | a01, a02, a04, a06-a10 | Real INEGI + CONAPO + CNSF/EMSSA | 3 reports |
| `sensitivity_analysis.py` | 1017 | a01, a02, a04, a05, a06-a09 | Real INEGI + CONAPO + HMD (USA, Spain) | 4 reports |
| `capital_requirements.py` | 463 | a01, a02, a06-a09, a11, a12 | Real INEGI + CONAPO | 1 report |

All scripts require real data files that are not committed to the repository (licensing restrictions). Download guides are in `backend/data/{inegi,conapo,cnsf}/DOWNLOAD_GUIDE.md`.

---

## 3. Script 1: `mexico_lee_carter.py`

### Purpose

Runs the full Lee-Carter pipeline on real Mexican mortality data in two parallel analyses:
- **Pre-COVID (1990-2019):** Clean baseline, no pandemic distortion
- **Full period (1990-2024):** Includes COVID-19 spike

### Pipeline

```
INEGI deaths + CONAPO population
    -> MortalityData.from_inegi()
    -> GraduatedRates(lambda=1e5)
    -> LeeCarter.fit(reestimate_kt=False)
    -> MortalityProjection(horizon=30, n_sim=1000, seed=42)
    -> to_life_table(target_year)
    -> MortalityComparison(vs 7 regulatory tables)
    -> PremiumCalculator (8 ages x 3 products)
    -> confidence intervals (central, optimistic, pessimistic)
```

### Key Design Decision

Uses `reestimate_kt=False` because graduated data cannot satisfy the death-matching equation. The SVD k_t is used, which minimizes log-space reconstruction error.

### Output Files

| File | Content |
|:-----|:--------|
| `results/mexico_pre_covid_2019.txt` | 7-section report: data summary, LC diagnostics, projection, life table, regulatory comparisons, premiums, CIs |
| `results/mexico_full_2024.txt` | Same structure for full period |
| `results/mexico_covid_comparison.txt` | Side-by-side: drift, sigma, premiums, k_t trajectories |

### Key Findings (extracted from reports)

| Metric | Pre-COVID (1990-2019) | Full (1990-2024) |
|:-------|:---------------------|:-----------------|
| Explained variance | 77.7% | 53.5% |
| Drift (annual) | -1.076 | -0.855 |
| Sigma | 1.789 | 1.516 |
| q_60 (projected) | ~0.0105 | ~0.0112 |
| Premium impact (age 40) | baseline | +3.8% higher |

---

## 4. Script 2: `sensitivity_analysis.py`

### Purpose

Three-dimensional sensitivity analysis on the Lee-Carter mortality pipeline:
1. **Interest rate sweep** (i = 2% to 8%) on Mexico
2. **Mortality shock sweep** (q_x x 0.70 to 1.30) on Mexico
3. **Cross-country comparison** (Mexico vs USA vs Spain)

### Pipeline Components

**Interest rate sensitivity:**
```
Mexico projected LifeTable (fixed) x 7 interest rates
    -> CommutationFunctions(lt, rate) for each rate
    -> PremiumCalculator -> premiums at 8 ages x 3 products
    -> ReserveCalculator -> reserve trajectories at age 35
```

**Mortality shock sensitivity:**
```
Mexico projected LifeTable -> build_shocked_life_table(lt, factor) x 7 factors
    -> CommutationFunctions(shocked_lt, i=5%) for each
    -> PremiumCalculator -> premiums at 8 ages x 3 products
```

**Cross-country:**
```
For each country in {Mexico, USA, Spain}:
    -> MortalityData (INEGI for Mexico, HMD for USA/Spain)
    -> GraduatedRates -> LeeCarter -> MortalityProjection
    -> Compare: drift, sigma, explained_var, a_x, b_x, k_t, q_x, premiums
```

### Helper Functions

```python
def build_shocked_life_table(base_lt, shock_factor, radix=100_000.0):
    """Scale q_x by factor, clip at 1.0, rebuild l_x."""

def run_country_pipeline(country, sex="Total", year_start=1990, year_end=2019):
    """Full LC pipeline for one country. Returns dict with all objects."""

def compute_premiums_at_rate(life_table, interest_rate):
    """Premiums for 3 products at 8 ages. Returns dict[age] = {wl, term, endow}."""
```

### Output Files

| File | Content |
|:-----|:--------|
| `results/sensitivity_interest_rate.txt` | Premium tables, % changes vs base, reserve trajectories |
| `results/sensitivity_mortality_shock.txt` | Shocked q_x values, premium tables, % changes |
| `results/sensitivity_cross_country.txt` | Data summary, LC diagnostics, projections, q_x, premiums, a_x, b_x |
| `results/sensitivity_summary.txt` | Executive summary combining key findings from all three |

### Key Findings

| Analysis | Key Result |
|:---------|:-----------|
| Interest rate | i=2%->8% causes 101% spread in whole life premium at age 40 ($17,910 vs $7,014) |
| Mortality shock | +30% q_x -> +16.2% premium, -30% q_x -> -18.2% premium (asymmetric/convex) |
| Cross-country | Spain drift=-2.89 (fastest), USA=-1.19, Mexico=-1.08 (slowest improvement) |

---

## 5. Script 3: `capital_requirements.py`

### Purpose

Computes the full Solvency Capital Requirement (RCS/SCR) for a sample 12-policy Mexican insurance portfolio using the Solvency II standard formula.

### Pipeline

```
Mexico LC pipeline -> projected LifeTable
    +
create_sample_portfolio() -> 12 policies (9 death + 3 annuity)
    |
    v
run_full_scr(portfolio, lt, i=5%, ...)
    |
    +--> compute_scr_mortality   (shock=+15%, death products only)
    +--> compute_scr_longevity   (shock=-20%, annuity products only)
    +--> compute_scr_interest_rate (+-100 bps, all products)
    +--> compute_scr_catastrophe  (factor=1.35, death products only)
    |
    +--> aggregate_scr_life (3x3 correlation matrix)
    +--> aggregate_scr_total (life + market, rho=0.25)
    +--> compute_risk_margin (CoC=6%, duration=15yr)
    +--> Technical Provisions = BEL + MdR
    +--> Solvency ratio at 5 capital levels
```

### Output File

`results/capital_requirements_report.txt` -- 12-section report:

| Section | Content |
|:--------|:--------|
| 1 | Portfolio summary (12 policies with attributes) |
| 2 | Baseline BEL decomposition (per-policy breakdown) |
| 3 | Mortality risk SCR |
| 4 | Longevity risk SCR |
| 5 | Interest rate risk SCR |
| 6 | Catastrophe risk SCR (COVID-calibrated) |
| 7 | Life underwriting aggregation (3x3 correlation) |
| 8 | Total SCR aggregation (life + market) |
| 9 | Risk margin (cost-of-capital method) |
| 10 | Technical provisions (BEL + MdR) |
| 11 | Solvency ratio at $1M, $2M, $3M, $5M, $10M capital |
| 12 | SCR decomposition summary (% of total by component) |

### Key Findings

| Metric | Value | % of SCR Total |
|:-------|:------|:--------------|
| SCR_mortality | $24K | 4.2% |
| SCR_longevity | $252K | 44.4% |
| SCR_interest_rate | $453K | 79.7% |
| SCR_catastrophe | $14K | 2.4% |
| SCR_life (aggregated) | -- | -- |
| SCR_total | $568.7K | 100% |
| Diversification benefit | 14.4% | -- |
| BEL total | $5.16M | -- |
| Risk margin | $354K | -- |
| Technical provisions | $5.51M | -- |

---

## 6. How Hardcoded API Data Was Extracted

The sensitivity service (`sensitivity_service.py`) returns hardcoded data for cross-country and COVID endpoints. This data was extracted from the analysis scripts:

| API Endpoint | Source Script | How Values Were Extracted |
|:-------------|:-------------|:-------------------------|
| `GET /sensitivity/cross-country` | `sensitivity_analysis.py` | Drift, sigma, explained_var, q_60 from `run_country_pipeline()` results; premium_age40 from `compute_premiums_at_rate()` |
| `GET /sensitivity/covid-comparison` | `mexico_lee_carter.py` | Pre-COVID and full-period drift/sigma/explained_var from `run_pipeline()` results; k_t trajectories from `lc.kt`; premiums from `compute_premiums()` |

The k_t profiles, a_x profiles, and b_x profiles in the cross-country endpoint were sampled at 13 representative ages (0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100) from the Lee-Carter model objects.

---

## 7. Running the Scripts

```bash
cd /home/andtega349/SIMA

# Requires real INEGI/CONAPO data in backend/data/inegi/ and backend/data/conapo/
venv/bin/python backend/analysis/mexico_lee_carter.py

# Requires real data + HMD data for USA/Spain
venv/bin/python backend/analysis/sensitivity_analysis.py

# Requires real INEGI/CONAPO data
venv/bin/python backend/analysis/capital_requirements.py
```

---

## 8. Interview-Ready Talking Points

**Q: Why are analysis scripts separate from the engine?**
A: The engine is a library with no side effects -- it returns Python objects. The analysis scripts are one-time consumers that configure the pipeline with specific parameters (country, year range, shock factors), run it, and produce formatted reports. Separating them means the engine stays clean and reusable.

**Q: Why does `sensitivity_analysis.py` use `build_shocked_life_table` instead of the SCR module's version?**
A: Both functions do the same thing (scale q_x, clip at 1.0, rebuild l_x). The sensitivity script was written before the SCR module existed. The SCR module's `build_shocked_life_table` in `a12_scr.py` is the canonical version.

**Q: What was the most surprising finding from the analysis?**
A: That interest rate risk dominates the SCR (79.7% of total) despite the portfolio having more death products than annuities. Interest rate changes affect every discounted cash flow in every product, while mortality/longevity shocks only affect one product type each. This explains why Solvency II separates market risk from underwriting risk.

**Q: How did COVID-19 affect the Lee-Carter model?**
A: Including COVID years (2020-2024) dropped explained variance from 77.7% to 53.5% and made the drift 0.22 less negative (-1.076 to -0.855). The single-factor Lee-Carter model cannot capture a transient spike -- it interprets it as a permanent slowdown in mortality improvement, inflating premiums by 3-4%.
