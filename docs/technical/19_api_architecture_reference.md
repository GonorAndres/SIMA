# API Architecture: Technical Reference

**Source files:** `backend/api/main.py`, `backend/api/routers/*.py`, `backend/api/services/*.py`, `backend/api/schemas/*.py`

---

## 1. Three-Tier Architecture

The SIMA REST API follows a strict three-tier pattern: **Router -> Service -> Engine**. Each tier has a single responsibility.

```
HTTP Request
    |
    v
[Router]  ----  Defines endpoints, validates input (Pydantic), returns HTTP errors
    |
    v
[Service] ----  Bridges API types to engine types, calls engine modules, serializes numpy
    |
    v
[Engine]  ----  Pure actuarial computation (a01-a12), no HTTP awareness
```

| Tier | Files | Responsibility | Knows About |
|:-----|:------|:---------------|:------------|
| Router | `routers/{mortality,pricing,portfolio,scr,sensitivity}.py` | HTTP verbs, path params, query params, status codes | Pydantic schemas, service functions |
| Service | `services/{mortality_service,pricing_service,scr_service,sensitivity_service}.py` | Type conversion (numpy->list), engine orchestration | Engine modules a01-a12, precomputed cache |
| Engine | `engine/a01_life_table.py` through `engine/a12_scr.py` | Actuarial math | Nothing about HTTP or API |

**Why this matters:** The engine modules are testable without any HTTP infrastructure. The API is a thin wrapper that adds web access without polluting the actuarial code.

---

## 2. Application Lifecycle and Caching

### Startup: `precomputed.py`

The API loads all data-intensive objects **once at startup** via FastAPI's lifespan context manager. This avoids re-parsing CSV files and re-fitting Lee-Carter on every request.

```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all()   # <-- runs ONCE before first request
    yield        # <-- app serves requests here
```

**What `load_all()` creates (6 module-level singletons):**

| Variable | Type | Source | Used By |
|:---------|:-----|:-------|:--------|
| `_mortality_data` | `MortalityData` | `from_inegi(mock_deaths, mock_pop)` | mortality_service |
| `_graduated` | `GraduatedRates` | `GraduatedRates(_mortality_data, lambda=1e5)` | mortality_service |
| `_lee_carter` | `LeeCarter` | `LeeCarter.fit(_graduated, reestimate_kt=False)` | mortality_service |
| `_projection` | `MortalityProjection` | `MortalityProjection(_lee_carter, horizon=30, n_sim=500)` | mortality_service |
| `_cnsf_lt` | `LifeTable` | `from_regulatory_table(mock_cnsf, sex="male")` | pricing_service, scr_service |
| `_emssa_lt` | `LifeTable` | `from_regulatory_table(mock_emssa, sex="male")` | mortality_service |

**Key design decision:** `reestimate_kt=False` because Whittaker-Henderson graduation changes the mortality surface, making the death-matching re-estimation equation unsatisfiable. The SVD k_t minimizes log-space error, which is consistent with the Lee-Carter log-bilinear formulation.

### Accessor Pattern

Each singleton has a getter that raises `RuntimeError` if called before `load_all()`:

```python
def get_mortality_data() -> MortalityData:
    if _mortality_data is None:
        raise RuntimeError("Precomputed data not loaded. Call load_all() first.")
    return _mortality_data
```

This prevents silent None-propagation -- a request that arrives before startup completion gets a clear error.

---

## 3. Complete Endpoint Table (22 endpoints)

| Router | Method | Path | Description | Params |
|:-------|:-------|:-----|:------------|:-------|
| -- | GET | `/api/health` | Health check (status, version, module count) | -- |
| mortality | GET | `/api/mortality/data/summary` | Loaded mock data summary | -- |
| mortality | GET | `/api/mortality/lee-carter` | Lee-Carter parameters (a_x, b_x, k_t) | -- |
| mortality | GET | `/api/mortality/projection` | RWD projection + optional life table | `horizon`, `projection_year` |
| mortality | GET | `/api/mortality/life-table` | Regulatory table (CNSF/EMSSA) | `table_type`, `sex` |
| mortality | GET | `/api/mortality/validation` | Projected vs regulatory comparison | `projection_year`, `table_type` |
| mortality | GET | `/api/mortality/graduation` | Raw vs graduated rates + diagnostics | -- |
| mortality | GET | `/api/mortality/surface` | 2D log(mx) matrix for 3D viz | -- |
| mortality | GET | `/api/mortality/diagnostics` | Lee-Carter goodness-of-fit metrics | -- |
| pricing | POST | `/api/pricing/premium` | Net annual premium | body: product, age, SA, i, term |
| pricing | POST | `/api/pricing/reserve` | Reserve trajectory | body: product, age, SA, i, term |
| pricing | GET | `/api/pricing/commutation` | D, N, C, M, A_x, a_due at one age | `age`, `interest_rate` |
| pricing | POST | `/api/pricing/sensitivity` | Premium at multiple interest rates | body: product, age, SA, rates |
| portfolio | GET | `/api/portfolio/summary` | Portfolio policies and counts | -- |
| portfolio | POST | `/api/portfolio/bel` | Best Estimate Liability computation | body: interest_rate |
| portfolio | POST | `/api/portfolio/policy` | Add policy to portfolio | body: PolicyCreate |
| portfolio | POST | `/api/portfolio/reset` | Reset to 12-policy sample | -- |
| scr | POST | `/api/scr/compute` | Full SCR with configurable shocks | body: SCRRequest (8 params) |
| scr | POST | `/api/scr/defaults` | SCR with Solvency II defaults | -- |
| sensitivity | POST | `/api/sensitivity/mortality-shock` | Dynamic mortality shock sweep | body: age, SA, product, factors |
| sensitivity | GET | `/api/sensitivity/cross-country` | Hardcoded Mexico/USA/Spain comparison | -- |
| sensitivity | GET | `/api/sensitivity/covid-comparison` | Hardcoded pre-COVID vs full period | -- |

---

## 4. Pydantic Schema Overview

The API defines ~35 Pydantic models across 5 schema files. Every endpoint has an explicit request and/or response model.

### Schema Files

| File | Models | Purpose |
|:-----|:-------|:--------|
| `schemas/mortality.py` | 12 models | Data summary, LC params, projection, graduation, surface, diagnostics |
| `schemas/pricing.py` | 8 models | Premium req/resp, reserve req/resp, commutation, sensitivity |
| `schemas/portfolio.py` | 7 models | Policy CRUD, BEL breakdown, portfolio summary |
| `schemas/scr.py` | 8 models | SCR request, per-module results, aggregation, risk margin, solvency |
| `schemas/sensitivity.py` | 8 models | Mortality shock, cross-country entries/profiles, COVID comparison |

### Key Schema Patterns

**Request models** use `Field()` with validation constraints:

```python
class PremiumRequest(BaseModel):
    product_type: str = Field(description="'whole_life', 'term', 'endowment', or 'pure_endowment'")
    age: int = Field(ge=0, le=100)
    sum_assured: float = Field(gt=0)
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)
    term: Optional[int] = Field(default=None, ge=1)
```

**Response models** for complex computations use nested models:

```python
class SCRResponse(BaseModel):
    bel_base: float
    mortality: SCRComponentResult      # nested
    longevity: SCRComponentResult      # nested
    interest_rate: SCRInterestRateResult  # nested
    catastrophe: SCRCatastropheResult  # nested
    life_aggregation: SCRAggregationResult  # nested
    total_aggregation: SCRAggregationResult  # nested
    risk_margin: RiskMarginResult      # nested
    solvency: Optional[SolvencyResult] = None  # optional
```

---

## 5. Service Layer Design Patterns

### numpy Serialization

The biggest engineering challenge in the service layer is converting numpy types to JSON-serializable Python types. Every service function does this explicitly:

```python
# mortality_service.py -- converting LC params
return {
    "ages": [int(a) for a in lc.ages],          # np.int64 -> int
    "ax": [float(v) for v in lc.ax],            # np.float64 -> float
    "explained_variance": lc.explained_variance,  # already Python float
}
```

For 2D arrays (mortality surface), nested list comprehension is used:

```python
log_mx = np.log(grad.mx + 1e-10)
log_mx = [[float(v) for v in row] for row in log_mx]  # shape (101, 31) -> List[List[float]]
```

### Dynamic vs Hardcoded Endpoints

The sensitivity service uses two distinct patterns:

| Pattern | Endpoints | How It Works |
|:--------|:----------|:-------------|
| **Dynamic** | `mortality-shock` | Receives parameters, calls engine modules live, computes fresh results |
| **Hardcoded** | `cross-country`, `covid-comparison` | Returns pre-extracted data dictionaries from analysis script results |

The hardcoded endpoints exist because cross-country and COVID analyses require HMD data (USA/Spain) and real INEGI data that are not bundled with the API. The data was extracted from running `sensitivity_analysis.py` and `mexico_lee_carter.py` on real data.

### Stateful Portfolio Service

The `scr_service` maintains a module-level `_portfolio` singleton that can be modified via the API:

```python
_portfolio: Portfolio | None = None

def _ensure_portfolio() -> Portfolio:
    global _portfolio
    if _portfolio is None:
        _portfolio = create_sample_portfolio()  # 12 default policies
    return _portfolio

def add_policy(...) -> Policy:  # mutates _portfolio
def reset_portfolio() -> Portfolio:  # replaces _portfolio
```

This is in-memory state -- restarting the server resets the portfolio. There is no database persistence.

---

## 6. CORS and Frontend Integration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

All routers are mounted under `/api` prefix:

```python
app.include_router(mortality.router, prefix="/api")  # -> /api/mortality/...
```

---

## 7. Error Handling Pattern

All routers follow the same pattern: catch domain exceptions from the engine and convert to HTTP 400:

```python
@router.post("/premium", response_model=PremiumResponse)
def calculate_premium(request: PremiumRequest):
    try:
        result = pricing_service.calculate_premium(...)
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Pydantic handles input validation automatically (returns 422 for invalid schemas). The only custom error handling is for domain logic errors (unknown product types, out-of-range years, etc).

---

## 8. Interview-Ready Talking Points

**Q: Why separate routers, services, and schemas instead of putting everything in the router?**
A: Separation of concerns. The service layer handles numpy-to-JSON conversion and engine orchestration. The router only handles HTTP concerns. The schemas provide contract documentation. This makes the engine independently testable.

**Q: Why use precomputed singletons instead of computing on each request?**
A: Lee-Carter fitting involves SVD decomposition and 500-simulation Monte Carlo. This takes seconds. Caching at startup makes every subsequent request instant. The tradeoff is a slower cold start.

**Q: Why `reestimate_kt=False` for the API?**
A: The API uses graduated (smoothed) data. Graduation changes the mortality surface, so the re-estimation equation `sum(E * exp(a + b*k)) = sum(D)` becomes unsatisfiable. The SVD-estimated k_t is self-consistent with the log-bilinear model.

**Q: Why are cross-country and COVID endpoints hardcoded?**
A: They require HMD data (USA, Spain) and real INEGI data that are not distributed with the application (licensing restrictions). The values were extracted from running analysis scripts on the author's machine with real data.
