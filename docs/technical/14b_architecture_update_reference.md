# Architecture Update Addendum: Technical Reference

**Addendum to:** Doc 14 (`14_architecture_integration_reference.md`)

**Scope:** This document extends Doc 14 (which covers modules a01-a09) with the three engine modules added in Phase 3 (a10-a12), the API tier (Phase 4a), and the frontend tier (Phase 4b). It does NOT replace Doc 14 -- read Doc 14 first for the foundational two-pipeline architecture.

---

## 1. What Changed Since Doc 14

Doc 14 documented a 9-module engine with 106 tests. The system has since grown:

| Metric | Doc 14 (Phase 1-2) | Current (Phase 4b) | Change |
|:-------|:-------------------|:-------------------|:-------|
| Engine modules | 9 (a01-a09) | 12 (a01-a12) | +3 modules |
| Tests | 106 | 191 | +85 tests |
| Total files | ~30 | ~120 | +API, frontend, analysis |
| Architectural tiers | 1 (engine) | 4 (engine, analysis, API, frontend) | +3 tiers |
| API endpoints | 0 | 21 | +21 endpoints |
| Frontend pages | 0 | 6 | +6 pages |

---

## 2. New Engine Modules (Phase 3)

### a10_validation.py -- MortalityComparison

**Purpose:** Compare a projected life table against a regulatory benchmark.

| Method | Signature | Returns | Formula |
|:-------|:----------|:--------|:--------|
| `qx_ratio()` | `() -> np.ndarray` | Array of q_x ratios for overlap ages | `proj_qx / reg_qx` |
| `qx_difference()` | `() -> np.ndarray` | Array of signed differences | `proj_qx - reg_qx` |
| `rmse()` | `(age_start=20, age_end=80) -> float` | RMSE over age range | `sqrt(mean((proj - reg)^2))` |
| `summary()` | `() -> dict` | Dict with rmse, max/min/mean ratio, n_ages | Combines above |

**Constructor:** `MortalityComparison(projected: LifeTable, regulatory: LifeTable, name: str)`

**Design:** Automatically finds overlapping ages between two life tables. Excludes terminal age (where q_x = 1.0 in both). Raises `ValueError` if overlap < 2 ages.

**Imports:** `a01_life_table.LifeTable`

### a11_portfolio.py -- Policy, Portfolio, BEL

**Purpose:** Model insurance portfolios and compute Best Estimate Liabilities (BEL).

#### Policy Class

| Attribute | Type | Description |
|:----------|:-----|:------------|
| `policy_id` | `str` | Unique identifier |
| `product_type` | `str` | "whole_life", "term", "endowment", or "annuity" |
| `issue_age` | `int` | Age at policy issue |
| `SA` | `float` | Sum assured (death products) |
| `annual_pension` | `float` | Annual payment (annuity products) |
| `n` | `Optional[int]` | Term length (term/endowment only) |
| `duration` | `int` | Years since issue |

| Property | Returns | Formula |
|:---------|:--------|:--------|
| `is_death_product` | `bool` | `product_type in {"whole_life", "term", "endowment"}` |
| `is_annuity` | `bool` | `product_type == "annuity"` |
| `attained_age` | `int` | `issue_age + duration` |

#### compute_policy_bel Function

```python
def compute_policy_bel(policy, life_table, interest_rate) -> float:
    # Death products: BEL = prospective reserve at current duration
    #   Uses ReserveCalculator internally
    # Annuity: BEL = annual_pension * a_due(attained_age)
    #   Uses ActuarialValues internally
```

Key insight: **BEL for death products IS the prospective reserve.** No new math is needed for Solvency II -- the classical reserve formula, evaluated with best-estimate assumptions, gives the BEL directly.

#### Portfolio Class

| Method | Returns | Description |
|:-------|:--------|:------------|
| `compute_bel(lt, i)` | `float` | Total BEL (sum of individual policy BELs) |
| `compute_bel_breakdown(lt, i)` | `List[Dict]` | Per-policy BEL with metadata |
| `compute_bel_by_type(lt, i)` | `Dict` | Split: `death_bel`, `annuity_bel`, `total_bel` |
| `death_products` | `List[Policy]` | Filter for death-benefit policies |
| `annuity_products` | `List[Policy]` | Filter for annuity policies |
| `summary()` | `str` | Formatted portfolio summary |

**Imports:** `a01_life_table`, `a02_commutation`, `a03_actuarial_values`, `a04_premiums`, `a05_reserves`

### a12_scr.py -- SCR Risk Modules and Aggregation

**Purpose:** Compute Solvency Capital Requirements under the Solvency II / CNSF standard formula.

#### Risk Module Functions

| Function | Shock | Affected Products | Formula |
|:---------|:------|:-----------------|:--------|
| `compute_scr_mortality(portfolio, lt, i, shock=0.15)` | +15% q_x permanent | Death only | `SCR = BEL_stressed - BEL_base` |
| `compute_scr_longevity(portfolio, lt, i, shock=0.20)` | -20% q_x permanent | Annuity only | `SCR = BEL_stressed - BEL_base` |
| `compute_scr_interest_rate(portfolio, lt, i, shock_bps=100)` | +/- 1% parallel | All products | `SCR = max(BEL_up, BEL_down) - BEL_base` |
| `compute_scr_catastrophe(portfolio, lt, i, cat=1.35)` | +35% one-year spike | Death only | `SCR = sum(SA * delta_q * v)` |

#### Helper: build_shocked_life_table

```python
def build_shocked_life_table(base_lt, shock_factor, radix=100_000) -> LifeTable:
    # 1. Scale q_x: shocked_q = min(base_q * factor, 1.0)
    # 2. Rebuild l_x from shocked q_x
    # 3. Return new LifeTable
```

#### Aggregation Functions

| Function | Formula | Inputs |
|:---------|:--------|:-------|
| `aggregate_scr_life(mort, long, cat)` | `SCR_life = sqrt(vec' * CORR * vec)` | 3x3 correlation matrix (LIFE_CORR) |
| `aggregate_scr_total(scr_life, scr_ir)` | `SCR_total = sqrt(life^2 + ir^2 + 2*rho*life*ir)` | rho = 0.25 |
| `compute_risk_margin(scr, duration, coc=0.06)` | `MdR = CoC * SCR * annuity_factor` | annuity_factor = (1 - v^n) / i |
| `compute_solvency_ratio(capital, scr)` | `ratio = capital / scr` | >100% = solvent |

#### Correlation Matrix (LIFE_CORR)

```
          Mort   Long    Cat
Mort    [ 1.00  -0.25   0.25 ]
Long    [-0.25   1.00   0.00 ]
Cat     [ 0.25   0.00   1.00 ]
```

#### Full Pipeline: run_full_scr

```python
def run_full_scr(portfolio, base_lt, interest_rate, ...) -> Dict:
    # Step 1: Base BEL for portfolio
    # Step 2: 4 individual SCR components
    # Step 3: Life underwriting aggregation (correlation matrix)
    # Step 4: Total aggregation (life + market)
    # Step 5: Risk margin (CoC method)
    # Step 6: Technical provisions = BEL + MdR
    # Step 7: Solvency ratio (optional, if capital provided)
```

**Imports:** `a01_life_table`, `a02_commutation`, `a03_actuarial_values`, `a11_portfolio`

---

## 3. API Tier (Phase 4a/4b)

### Architecture: Router -> Service -> Engine

The API follows a 3-layer pattern:

```
REQUEST
   |
   v
Router (routers/*.py)         FastAPI route definitions, HTTP interface
   |
   v
Service (services/*.py)       Orchestrates engine calls, transforms results
   |
   v
Engine (engine/a01-a12.py)    Pure computation, no HTTP awareness
   |
   v
RESPONSE (Pydantic schema)
```

### Routers

| Router | Prefix | Endpoints | Engine Modules Used |
|:-------|:-------|:---------:|:--------------------|
| `mortality` | `/api/mortality` | 8 | a06, a07, a08, a09, a10 |
| `pricing` | `/api/pricing` | 4 | a01, a02, a03, a04, a05 |
| `portfolio` | `/api/portfolio` | 4 | a11 |
| `scr` | `/api/scr` | 2 | a12, a11, a01-a05 |
| `sensitivity` | `/api/sensitivity` | 3 | a06, a07, a08, a09, a01-a05, a12 |

### Application Setup (`main.py`)

```python
# FastAPI with lifespan: precompute data at startup
@asynccontextmanager
async def lifespan(app):
    load_all()   # Precompute Lee-Carter fit, graduated rates, etc.
    yield

app = FastAPI(title="SIMA", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])

# 5 routers, all under /api prefix
app.include_router(mortality.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(scr.router, prefix="/api")
app.include_router(sensitivity.router, prefix="/api")
```

### Precomputed Data

The API precomputes heavy calculations at startup via `services/precomputed.py`. This includes the Lee-Carter fit, graduated rates, and mortality projection -- shared across all request handlers to avoid recomputation.

---

## 4. Frontend Tier (Phase 4a/4b)

### Architecture Overview

```
React 19 SPA  ->  axios (/api)  ->  Vite proxy  ->  FastAPI (:8000)
```

The frontend is a React 19 application with TypeScript, Vite, and Plotly.js for charting. See Doc 20 for full details. Key characteristics:

- 6 pages, 18 components, 2 custom hooks
- 31 TypeScript interfaces mirroring backend Pydantic schemas
- Swiss design system (8 colors, zero border-radius, Major Third type scale)
- i18n: Spanish/English (~130 keys each)
- State management: local hooks only, no global store

---

## 5. Updated Dependency Diagram

```
                        FULL SIMA ARCHITECTURE (a01-a12 + API + Frontend)
                        =================================================

                 EMPIRICAL PIPELINE                THEORETICAL PIPELINE
                 ==================                ====================

  INEGI Deaths + CONAPO Population         a01_life_table  <-- from_csv()
  HMD Text Files (Mx, Deaths, Exposures)        |                from_regulatory_table()
        |                                        v  + interest_rate
        v                                  a02_commutation
  a06_mortality_data                             |
  (from_hmd, from_inegi)                         +----+----+
        |                                        |         |
        v  (optional)                            v         v
  a07_graduation                           a03_actuarial  a04_premiums
  (Whittaker-Henderson)                    (A_x, a_x)     (P = SA*M/N)
        |                                                      |
        v                                                      v
  a08_lee_carter                                         a05_reserves
  (SVD fitting)                                          (tV = SA*A - P*a)
        |                                                      |
        v                                                      |
  a09_projection                                               |
  (RWD forecast)                                               |
        |                                                      |
        |  to_life_table()  ----------->  a01_life_table       |
        |                                                      |
        |                                                      v
        |                                  a10_validation  <---+--- regulatory LifeTable
        |                                  (MortalityComparison)
        |
        |                                  a11_portfolio
        |                                  (Policy, Portfolio, BEL)
        |                                  uses: a01, a02, a03, a04, a05
        |                                        |
        |                                        v
        |                                  a12_scr
        |                                  (4 risk modules, aggregation)
        |                                  uses: a01, a02, a03, a11
        |
        v
  ================================================================
                          API TIER (FastAPI)
  ================================================================
        |
  main.py (lifespan: precompute at startup)
        |
        +--- routers/mortality.py   (8 endpoints -> a06-a10)
        +--- routers/pricing.py     (4 endpoints -> a01-a05)
        +--- routers/portfolio.py   (4 endpoints -> a11)
        +--- routers/scr.py         (2 endpoints -> a12)
        +--- routers/sensitivity.py (3 endpoints -> a06-a12)
        |
        v  (JSON over HTTP)
  ================================================================
                       FRONTEND TIER (React)
  ================================================================
        |
  6 Pages:
    Inicio        -> /mortality/lee-carter, /scr/compute
    Mortalidad    -> 7 /mortality/* endpoints
    Tarificacion  -> 3 /pricing/* endpoints
    SCR           -> /portfolio/*, /scr/compute, /portfolio/bel
    Sensibilidad  -> /pricing/sensitivity, /sensitivity/*
    Metodologia   -> (static, no API calls)
```

---

## 6. Updated Import Dependencies

Extension of Doc 14's import table with the new modules:

| Module | Imports From |
|:-------|:-------------|
| a01_life_table | (none) |
| a02_commutation | a01 |
| a03_actuarial_values | a02 |
| a04_premiums | a02, a03 |
| a05_reserves | a02, a03, a04 |
| a06_mortality_data | (none -- numpy, pandas) |
| a07_graduation | a06 |
| a08_lee_carter | a06 (type hint), a07 (lazy) |
| a09_projection | a08, a01 |
| **a10_validation** | **a01** |
| **a11_portfolio** | **a01, a02, a03, a04, a05** |
| **a12_scr** | **a01, a02, a03, a11** |

Key observations:
- **a11 has the most imports** (5 modules) because BEL computation requires the entire theoretical pipeline
- **a12 imports a11** (portfolios) but NOT a04/a05 directly -- it accesses reserves through `compute_policy_bel()`
- **a10 is a leaf** that only needs LifeTable -- it compares two tables without any pricing machinery

---

## 7. Updated Test Count

| Test File | Module(s) | Test Count |
|:----------|:----------|:----------:|
| test_life_table.py | a01 | ~10 |
| test_commutation.py | a02 | ~10 |
| test_actuarial_values.py | a03 | ~5 |
| test_premiums.py | a04 | ~5 |
| test_reserves.py | a05 | ~8 |
| test_mortality_data.py | a06 | 15 |
| test_graduation.py | a07 | 13 |
| test_lee_carter.py | a08 | 20 |
| test_projection.py | a09 | 17 |
| test_integration_lee_carter.py | a06-a09 + a01-a04 | 3 |
| **test_validation.py** | **a10** | **10** |
| **test_regulatory_tables.py** | **a01 (from_regulatory_table)** | **8** |
| **test_inegi_data.py** | **a06 (from_inegi)** | **10** |
| **test_integration_mexican.py** | **a06-a10 + a01-a05** | **12** |
| **test_portfolio.py** | **a11** | **15** |
| **test_scr.py** | **a12** | **18** |
| **test_api/** | **API routers** | **12** |
| **Total** | | **~191** |

---

## 8. Cross-References

| Topic | Document |
|:------|:---------|
| Original architecture (a01-a09) | Doc 14: `14_architecture_integration_reference.md` |
| API tier details (21 endpoints) | Doc 19: `19_api_architecture_reference.md` |
| Frontend tier details (React) | Doc 20: `20_frontend_architecture_reference.md` |
| Sensitivity analysis engine | Doc 15: `15_sensitivity_analysis_reference.md` |
| Capital requirements engine | Doc 18: `18_capital_requirements_reference.md` |
| Mexican data pipeline | Doc 16: `16_mexican_data_pipeline_reference.md` |
