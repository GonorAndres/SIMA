# Testing Strategy: Technical Reference

**Source files:** `backend/tests/test_*.py` (15 files), `backend/tests/test_api/` (6 files)

---

## 1. Test Suite Overview

191 tests across 19 test files, organized by engine module. Every test has a `THEORY` docstring explaining the actuarial property being verified.

```
backend/tests/
├── test_life_table.py            # a01: l_x, d_x, q_x, p_x derivations
├── test_commutation.py           # a02: D, N, C, M recursion
├── test_premiums_reserves.py     # a03-a05: equivalence principle, reserves
├── test_mortality_data.py        # a06: HMD loading, matrix validation
├── test_graduation.py            # a07: Whittaker-Henderson smoothing
├── test_lee_carter.py            # a08: SVD, identifiability, k_t re-estimation
├── test_projection.py            # a09: RWD, CI bands, bridge to LifeTable
├── test_integration_lee_carter.py # a06-a09: full empirical pipeline
├── test_regulatory_tables.py     # a01: from_regulatory_table() (CNSF/EMSSA)
├── test_validation.py            # a10: MortalityComparison metrics
├── test_inegi_data.py            # a06: from_inegi() (Mexican format)
├── test_integration_mexican.py   # a06-a10: full Mexican pipeline
├── test_portfolio.py             # a11: Policy, Portfolio, BEL
├── test_scr.py                   # a12: 4 risk modules, aggregation, solvency
└── test_api/
    ├── conftest.py               # TestClient fixture with lifespan
    ├── test_health.py            # Health endpoint
    ├── test_mortality_api.py     # 6 mortality endpoint tests
    ├── test_pricing_api.py       # 7 pricing endpoint tests
    ├── test_portfolio_api.py     # 4 portfolio endpoint tests
    └── test_scr_api.py           # 4 SCR endpoint tests
```

---

## 2. Test File to Engine Module Mapping

| Test File | Engine Module(s) | Test Count | Data Source |
|:----------|:-----------------|:-----------|:------------|
| `test_life_table.py` | a01 | 9 | `mini_table.csv`, `sample_mortality.csv` |
| `test_commutation.py` | a01, a02 | 12 | `mini_table.csv` |
| `test_premiums_reserves.py` | a01-a05 | 14 | `mini_table.csv` |
| `test_mortality_data.py` | a06 | 13 | HMD (USA, Spain) |
| `test_graduation.py` | a06, a07 | 12 | HMD (USA) |
| `test_lee_carter.py` | a06-a08 | 17 | HMD (USA, Spain) + synthetic |
| `test_projection.py` | a06-a09, a01, a02, a04 | 14 | HMD (USA) |
| `test_integration_lee_carter.py` | a06-a09, a02, a04 | 3 | HMD (USA, Spain) |
| `test_regulatory_tables.py` | a01, a02 | 10 | Mock CNSF/EMSSA |
| `test_validation.py` | a01, a10 | 7 | Synthetic (Gompertz) |
| `test_inegi_data.py` | a06, a07 | 10 | Mock INEGI/CONAPO |
| `test_integration_mexican.py` | a01-a10 | 4 | Mock INEGI/CONAPO + Mock CNSF/EMSSA |
| `test_portfolio.py` | a01, a11 | 10 | Synthetic (Gompertz) |
| `test_scr.py` | a01, a11, a12 | 19 | Synthetic (Gompertz) |
| `test_api/test_health.py` | main.py | 1 | -- |
| `test_api/test_mortality_api.py` | mortality router/service | 6 | Mock (via precomputed) |
| `test_api/test_pricing_api.py` | pricing router/service | 7 | Mock CNSF (via precomputed) |
| `test_api/test_portfolio_api.py` | portfolio router/service | 4 | Sample portfolio |
| `test_api/test_scr_api.py` | scr router/service | 4 | Sample portfolio + mock CNSF |

---

## 3. Data Conventions

### HMD Data (`DATA_DIR`)

```python
DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")
```

Used by: `test_mortality_data.py`, `test_graduation.py`, `test_lee_carter.py`, `test_projection.py`, `test_integration_lee_carter.py`

Loads real HMD mortality data for USA and Spain (1990-2020, ages 0-100). These tests **require HMD files to be present** -- they will be skipped/fail in environments without the data.

### Mock Data (`MOCK_DIR`)

```python
MOCK_DIR = str(Path(__file__).parent.parent / "data" / "mock")
```

Used by: `test_regulatory_tables.py`, `test_inegi_data.py`, `test_integration_mexican.py`, API tests (via precomputed.py)

Four committed CSV files with synthetic but realistic Mexican demographic patterns:

| File | Format | Content |
|:-----|:-------|:--------|
| `mock_inegi_deaths.csv` | Anio, Edad, Sexo, Defunciones | INEGI-format deaths |
| `mock_conapo_population.csv` | Anio, Edad, Sexo, Poblacion | CONAPO-format population |
| `mock_cnsf_2000_i.csv` | age, qx_male, qx_female | CNSF regulatory table |
| `mock_emssa_2009.csv` | age, qx_male, qx_female | EMSSA regulatory table |

### Synthetic Data (In-Test)

Tests in `test_validation.py`, `test_portfolio.py`, and `test_scr.py` build life tables programmatically using Gompertz mortality:

```python
def build_gompertz_life_table(ages=None, radix=100_000):
    qx = min(0.0005 * math.exp(0.07 * ages[i]), 0.99)
    ...
    return LifeTable(ages, l_x)
```

### Static CSV Files

Tests in `test_life_table.py`, `test_commutation.py`, and `test_premiums_reserves.py` use two small CSV files:

| File | Ages | Purpose |
|:-----|:-----|:--------|
| `mini_table.csv` | 60-65 | Hand-verifiable calculations (6 ages, known l_x) |
| `sample_mortality.csv` | 20-110 | Full-range testing |

---

## 4. The THEORY Docstring Pattern

Every test function includes a docstring starting with `THEORY:` that explains the actuarial property being tested. This serves three purposes:

1. **Documentation** -- readers understand what the test proves
2. **Learning** -- the test suite doubles as a study guide
3. **Traceability** -- each test maps to a specific formula or invariant

Example:

```python
def test_actuarial_identity(comm, av):
    """
    THEORY: A_x + d * a_due_x = 1

    Where d = i/(1+i) = iv (the discount rate).

    This identity says: the PV of $1 at death (A_x) plus the
    PV of interest earned on $1/year annuity (d * a_x) equals $1.
    """
```

---

## 5. Fixture Hierarchy

### Engine Tests: Chain of Fixtures

```
mini_table (LifeTable)
    |
    v
comm (CommutationFunctions, i=5%)
    |
    +--> av (ActuarialValues)
    +--> pc (PremiumCalculator)
    +--> rc (ReserveCalculator)
```

### HMD Pipeline Tests: Full Pipeline Fixture

```
usa_data (MortalityData.from_hmd)
    |
    +--> usa_lc (LeeCarter.fit, reestimate_kt=True)
    +--> usa_lc_no_reest (LeeCarter.fit, reestimate_kt=False)
    |
    +--> graduated (GraduatedRates)
    |
    +--> projection (MortalityProjection)
```

### API Tests: Module-Scoped Client

```python
@pytest.fixture(scope="module")
def client():
    """Create a test client with startup event (loads precomputed data)."""
    with TestClient(app) as c:
        yield c
```

The `scope="module"` means the client (and its startup data) is created once per test file, not once per test function. This avoids re-loading mock data for every individual test.

---

## 6. Test Categories and Coverage

### Unit Tests (Per-Module)

| Category | What It Tests | Example |
|:---------|:-------------|:--------|
| Structure | Output shapes, types, age ranges | `test_matrix_shape_matches_expected` |
| Formulas | Exact formula verification | `test_premium_formula_directly` (P = SA * M_x / N_x) |
| Identities | Actuarial identities that must hold | `test_actuarial_identity` (A_x + d*a_x = 1) |
| Invariants | Properties that must be true | `test_sum_of_deaths_equals_l0`, `test_bx_sums_to_one` |
| Ordering | Monotonicity, magnitude relationships | `test_term_premium_less_than_whole_life` |
| Edge cases | Terminal age, boundary conditions | `test_terminal_mortality_is_one`, `test_term_reserve_zero_at_expiry` |
| Error handling | Invalid inputs raise correct exceptions | `test_invalid_sex_raises_error`, `test_policy_invalid_product` |

### Integration Tests

| File | Pipeline Tested | Key Assertion |
|:-----|:----------------|:-------------|
| `test_integration_lee_carter.py` | HMD -> Graduate -> LC -> Project -> Premiums | Premium positive and < SA |
| `test_integration_mexican.py` | INEGI -> Graduate -> LC -> Project -> Validation | RMSE finite, ratios in [0.1, 10] |
| API tests | HTTP -> Router -> Service -> Engine -> JSON | Status codes + actuarial properties |

### Property-Based Assertions

Tests verify actuarial properties rather than exact numerical values:

```python
# Not: assert premium == 12345.67  (brittle)
# But: assert premium > 0 and premium < sum_assured  (robust)

# Not: assert reserve == 50000.0  (depends on exact data)
# But: assert reserves[i] > reserves[i-1] for all i  (monotonic growth)
```

---

## 7. API Test Infrastructure

### conftest.py

```python
from fastapi.testclient import TestClient
from backend.api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
```

The `TestClient` context manager triggers the lifespan event, which calls `load_all()`. This means API tests exercise the full stack: HTTP parsing -> Pydantic validation -> service logic -> engine computation -> JSON serialization.

### Test Patterns

API tests follow a consistent pattern:

```python
def test_whole_life_premium(client):
    """THEORY: Whole life premium should be positive and less than SA."""
    response = client.post("/api/pricing/premium", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["annual_premium"] > 0
    assert data["annual_premium"] < 1_000_000
```

Key pattern: assert the **status code**, then assert **actuarial properties** of the response data.

### Stateful Portfolio Tests

Portfolio tests reset state between operations:

```python
def test_add_policy(client):
    client.post("/api/portfolio/reset")        # clean state
    initial = client.get("/api/portfolio/summary").json()
    client.post("/api/portfolio/policy", json={...})  # mutate
    updated = client.get("/api/portfolio/summary").json()
    assert updated["n_policies"] == initial["n_policies"] + 1
```

---

## 8. What Is NOT Tested

| Area | Status | Reason |
|:-----|:-------|:-------|
| Frontend (React) | No tests | Development convenience; visual testing done manually |
| Performance benchmarks | No tests | Not a production system; no SLA requirements |
| Concurrent access | No tests | Single-user portfolio project |
| Real INEGI/CONAPO data | Only via analysis scripts | Data not distributed (licensing) |
| Sensitivity service hardcoded data | Partially tested | Cross-country/COVID return hardcoded values, so tests just check structure |
| Deployment (Docker, systemd) | No tests | Local development only |

---

## 9. Running Tests

```bash
# All tests
cd /home/andtega349/SIMA
venv/bin/pytest backend/tests/ -v

# Engine tests only (no API, faster)
venv/bin/pytest backend/tests/test_life_table.py backend/tests/test_commutation.py -v

# API tests only
venv/bin/pytest backend/tests/test_api/ -v

# Tests that don't require HMD data
venv/bin/pytest backend/tests/test_regulatory_tables.py backend/tests/test_validation.py \
    backend/tests/test_inegi_data.py backend/tests/test_portfolio.py backend/tests/test_scr.py -v
```

---

## 10. Interview-Ready Talking Points

**Q: Why do tests verify actuarial properties instead of exact numbers?**
A: Exact values depend on the data, which can change. Properties like "reserve increases with duration" or "term premium < whole life premium" are universal actuarial truths that hold regardless of the specific mortality table or interest rate. This makes tests robust to data changes.

**Q: What is the most important test in the suite?**
A: `test_full_scr_pipeline` in `test_scr.py`. It exercises all 12 engine modules in a single test: builds a portfolio, computes BEL for all products, applies 4 stress scenarios, aggregates with correlation matrices, computes risk margin, and checks that Technical Provisions = BEL + MdR. If this passes, the entire engine is consistent.

**Q: How does `test_reestimated_kt_matches_deaths` work?**
A: It verifies the k_t re-estimation contract: for each year t, the model-implied total deaths `sum(E_{x,t} * exp(a_x + b_x * k_t))` must match observed deaths `sum(D_{x,t})` within 0.1%. This is the Newton-Raphson / Brent root-finding convergence check.

**Q: Why use `scope="module"` for the API test client?**
A: Creating a `TestClient` triggers the lifespan event, which loads all precomputed data (CSV parsing, graduation, SVD, Monte Carlo). Doing this per-function would make the test suite slow. Module scope means it happens once per file.
