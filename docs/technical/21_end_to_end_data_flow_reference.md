# End-to-End Data Flow: Technical Reference

**Scope:** The complete journey of mortality data from CSV file to Plotly chart, covering all 12 transformation steps across backend engine, REST API, and React frontend.

**Source files cited:** `a06_mortality_data.py`, `a07_graduation.py`, `a08_lee_carter.py`, `a09_projection.py`, `precomputed.py`, `mortality_service.py`, `schemas/mortality.py`, `main.py`, `vite.config.ts`, `client.ts`, `useApi.ts`, `Mortalidad.tsx`, `LineChart.tsx`, `types/index.ts`

---

## 1. The 12-Step Pipeline

| Step | Location | Module / File | Input Format | Output Format | Key Transformation |
|:----:|:---------|:-------------|:-------------|:-------------|:-------------------|
| 1 | CSV on disk | `data/mock/mock_inegi_deaths.csv` | Flat CSV: Anio, Edad, Sexo, Defunciones | pandas DataFrame | `pd.read_csv()` |
| 2 | Engine a06 | `MortalityData.from_inegi()` | Two DataFrames (deaths + population) | Three numpy matrices: `mx`, `dx`, `ex` (101 x 31) | Pivot, cap ages, `m_x = D/P`, validate |
| 3 | Engine a07 | `GraduatedRates.__init__()` | `MortalityData.mx` (numpy 2D) | Smoothed `mx` (same shape) | Whittaker-Henderson per year column in log-space |
| 4 | Engine a08 | `LeeCarter.fit()` | `GraduatedRates` (duck-typed) | Three 1D arrays: `ax`, `bx`, `kt` + scalar `explained_variance` | SVD of residual matrix + identifiability constraints |
| 5 | Engine a09 | `MortalityProjection.__init__()` | `LeeCarter` model | `kt_central`, `kt_simulated`, `projected_years` | Random Walk with Drift extrapolation |
| 6 | Startup | `precomputed.load_all()` | Mock CSV paths | Module-level singletons | Steps 1-5 executed once, cached in memory |
| 7 | Service | `mortality_service.get_lee_carter_params()` | Cached objects via `get_lee_carter()` | Python dict with native types | `[float(v) for v in lc.ax]` -- numpy to Python |
| 8 | Router | `@router.get("/lee-carter")` | Service dict | JSON HTTP response | Pydantic `LeeCaterFitResponse` validates + serializes |
| 9 | Network | Vite proxy + axios | HTTP request to `/api/mortality/lee-carter` | JSON string over TCP | Vite proxies `/api` to `localhost:8000` |
| 10 | Hook | `useGet<LeeCaterFitResponse>()` | JSON response | React state: `{ data, loading, error }` | `axios.get()` -> `setState()` |
| 11 | Page | `Mortalidad.tsx` | `lc.data.ax` (number[]) | Plotly trace: `{ x: ages, y: ax, name: 'a_x' }` | Map data fields to chart props |
| 12 | Chart | `LineChart.tsx` | Trace array + layout | SVG elements in DOM | Plotly.js renders scatter traces to `<Plot>` |

---

## 2. Step-by-Step Trace

### Step 1: CSV Parsing

```
mock_inegi_deaths.csv                      mock_conapo_population.csv
  Anio, Edad, Sexo, Defunciones              Anio, Edad, Sexo, Poblacion
  1990, 0, Total, 4250                       1990, 0, Total, 2850000
  1990, 1, Total, 312                        1990, 1, Total, 2780000
  ...                                        ...
```

`_load_inegi_deaths()` filters by sex string (`"Total"`, `"Hombres"`, `"Mujeres"` -- Spanish values, not English) and year range, then renames columns to `Year`, `Age`, `Value`.

`_load_conapo_population()` does the same for the population file.

### Step 2: Matrix Construction

```python
# a06_mortality_data.py:284
merged["mx"] = merged["Value_dx"] / merged["Value_ex"]
```

The age capping step (`_cap_ages_sum`) aggregates all ages above `age_max` (default 100) into a single group by summing deaths and population. For death rates, this produces the correct exposure-weighted rate, not a naive average of rates.

The pivot operation converts long format to matrices:

```
Before pivot:  Year=1990, Age=60, Value=0.0105
               Year=1991, Age=60, Value=0.0098
               ...

After pivot:   mx[age_idx=60, year_idx=0] = 0.0105
               mx[age_idx=60, year_idx=1] = 0.0098
```

Output: three aligned numpy arrays of shape `(n_ages, n_years)`.

Validation (`_validate`) checks:
- No NaN values
- All death rates positive (required for log transform in step 4)
- All exposures positive
- Recomputed `d/L` matches provided `m_x` within 1%

### Step 3: Graduation

```python
# a07_graduation.py:195-210
log_mx = np.log(self.raw_mx)                    # move to log-space
for j in range(self.n_years):
    graduated_log_mx[:, j] = self._whittaker_henderson_1d(log_col, w)
return np.exp(graduated_log_mx)                  # back to rate-space
```

Each year column is smoothed independently. The linear system solved per column:

```
(W + lambda * D'D) * z = W * m
```

Where `W` = diagonal exposure weights, `D` = second-order sparse difference matrix, `lambda` = 1e5. The log-space approach guarantees all graduated rates are positive after exponentiation.

The `GraduatedRates` object preserves the same interface as `MortalityData` (`.mx`, `.dx`, `.ex`, `.ages`, `.years`), enabling duck typing at step 4.

### Step 4: Lee-Carter SVD

```python
# a08_lee_carter.py:117-140
log_mx = np.log(data.mx)            # (101 x 31) matrix of log-rates
ax = np.mean(log_mx, axis=1)        # row means: 101-vector
residual = log_mx - ax[:, np.newaxis]  # center each row
U, S, Vt = np.linalg.svd(residual, full_matrices=False)
bx = U[:, 0] / sum(U[:, 0])         # first left singular vector, normalized
kt = S[0] * Vt[0, :] * sum(U[:, 0]) # first right sv, scaled
kt = kt - np.mean(kt)               # centered
```

Output dimensions:
- `ax`: (101,) -- one value per age
- `bx`: (101,) -- one value per age, `sum(bx) = 1`
- `kt`: (31,) -- one value per year, `sum(kt) = 0`
- `explained_variance`: scalar in [0, 1]

### Step 5: Projection

```python
# a09_projection.py:128-131
kt_last = self.lee_carter.kt[-1]
h = np.arange(1, self.horizon + 1)
kt_central = kt_last + h * self.drift   # deterministic: 30-vector
```

Stochastic paths (500 simulations, shape 500 x 30):

```python
# a09_projection.py:148-156
innovations = rng.normal(0, 1, size=(500, 30))
kt_simulated = kt_last + h * drift + sigma * np.cumsum(innovations, axis=1)
```

### Step 6: Startup Caching

```python
# precomputed.py:39-75
def load_all():
    _mortality_data = MortalityData.from_inegi(...)   # step 1-2
    _graduated = GraduatedRates(_mortality_data, ...)  # step 3
    _lee_carter = LeeCarter.fit(_graduated, ...)       # step 4
    _projection = MortalityProjection(_lee_carter, ...)# step 5
    _cnsf_lt = LifeTable.from_regulatory_table(...)
    _emssa_lt = LifeTable.from_regulatory_table(...)
```

Called once via FastAPI lifespan context manager at server start. All subsequent requests read from module-level cache variables.

### Step 7: numpy-to-Python Serialization

```python
# mortality_service.py:48-56
return {
    "ages": [int(a) for a in lc.ages],       # np.int64 -> int
    "ax": [float(v) for v in lc.ax],         # np.float64 -> float
    "bx": [float(v) for v in lc.bx],
    "kt": [float(v) for v in lc.kt],
    "explained_variance": lc.explained_variance,  # already float
    ...
}
```

**Why explicit conversion is required:** `np.float64` is not JSON-serializable by Python's standard `json.dumps()`. FastAPI uses `orjson` or `json` under the hood, and both fail on raw numpy types. The list comprehension `[float(v) for v in array]` converts every element from `np.float64` to Python's native `float`.

For 2D matrices (like `log_mx` in the surface endpoint):

```python
# mortality_service.py:150-151
log_mx = [[float(v) for v in row] for row in log_mx]  # nested list comprehension
```

### Step 8: Pydantic Validation and JSON Serialization

```python
# schemas/mortality.py:43-53
class LeeCaterFitResponse(BaseModel):
    ages: List[int]
    years: List[int]
    ax: List[float]
    bx: List[float]
    kt: List[float]
    explained_variance: float
    drift: float
    sigma: float
    validations: Dict[str, bool]
```

FastAPI automatically:
1. Takes the service dict
2. Validates it against the Pydantic model (type checks, required fields)
3. Serializes to JSON via `model.model_dump_json()`
4. Sets `Content-Type: application/json`
5. Returns HTTP 200 with the JSON body

The router endpoint is the glue:

```python
# routers/mortality.py:25-28
@router.get("/lee-carter", response_model=LeeCaterFitResponse)
def get_lee_carter():
    return mortality_service.get_lee_carter_params()
```

### Step 9: Network Transport (Vite Proxy)

Development setup:

```
Browser (port 5173)  --fetch(/api/mortality/lee-carter)-->  Vite Dev Server (port 5173)
                                                               |
                                                               | proxy: /api -> localhost:8000
                                                               v
                                                         FastAPI (port 8000)
```

Configuration:

```typescript
// vite.config.ts:6-9
server: {
    proxy: {
        '/api': 'http://localhost:8000'
    }
}
```

The axios client sets `baseURL: '/api'`, so a call to `/mortality/lee-carter` becomes a request to `/api/mortality/lee-carter`, which Vite proxies to `http://localhost:8000/api/mortality/lee-carter`.

In production, a reverse proxy (nginx) would handle the `/api` routing instead of Vite.

### Step 10: React Hook State Management

```typescript
// useApi.ts:33-54
export function useGet<TRes>(endpoint: string) {
    const [state, setState] = useState<UseApiState<TRes>>({
        data: null, loading: false, error: null,
    });
    const execute = useCallback(async (params?) => {
        setState({ data: null, loading: true, error: null });
        const res = await api.get<TRes>(endpoint, { params });
        setState({ data: res.data, loading: false, error: null });
    }, [endpoint]);
    return { ...state, execute };
}
```

The generic `TRes` parameter provides TypeScript type safety: when the page calls `useGet<LeeCaterFitResponse>('/mortality/lee-carter')`, the returned `data` property is typed as `LeeCaterFitResponse | null`.

### Step 11: Page Data Mapping

```typescript
// Mortalidad.tsx:33,42
const lc = useGet<LeeCaterFitResponse>('/mortality/lee-carter');
useEffect(() => { lc.execute(); }, []);

// Later in JSX (line 166-175):
<LineChart
    traces={[{
        x: lc.data.ages,      // number[] from JSON
        y: lc.data.ax,        // number[] from JSON
        name: 'a_x',
        color: '#000',
    }]}
    xTitle="Edad"
    yTitle="a_x"
    height={300}
/>
```

The page transforms API response fields into Plotly trace objects. No numerical computation happens here -- just structural mapping.

### Step 12: Plotly Rendering

```typescript
// LineChart.tsx:20-39
const data = traces.map((t) => ({
    x: t.x,                          // number[]
    y: t.y,                          // number[]
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: t.name,
    line: { color: t.color, width: 2 },
}));

return <Plot data={data} layout={layout} config={defaultConfig} />;
```

Plotly.js renders the data to SVG path elements inside a `<div>`. The Swiss design defaults (`chartDefaults.ts`) enforce:
- Inter font family
- Transparent paper background
- `#E0E0E0` grid lines
- No Plotly logo, minimal mode bar

---

## 3. Type Mirroring: Pydantic to TypeScript

Every Pydantic model has a corresponding TypeScript interface. The JSON wire format is the contract between them.

### LeeCaterFitResponse

| Field | Pydantic (Python) | JSON Wire | TypeScript |
|:------|:-------------------|:----------|:-----------|
| ages | `List[int]` | `[0, 1, 2, ...]` | `number[]` |
| years | `List[int]` | `[1990, 1991, ...]` | `number[]` |
| ax | `List[float]` | `[-7.32, -9.15, ...]` | `number[]` |
| bx | `List[float]` | `[0.012, 0.008, ...]` | `number[]` |
| kt | `List[float]` | `[14.2, 12.8, ...]` | `number[]` |
| explained_variance | `float` | `0.798` | `number` |
| drift | `float` | `-1.076` | `number` |
| sigma | `float` | `0.45` | `number` |
| validations | `Dict[str, bool]` | `{"bx_sums_to_one": true, ...}` | `Record<string, boolean>` |

### GraduationResponse

| Field | Pydantic | TypeScript |
|:------|:---------|:-----------|
| ages | `List[int]` | `number[]` |
| raw_mx | `List[float]` | `number[]` |
| graduated_mx | `List[float]` | `number[]` |
| residuals | `List[float]` | `number[]` |
| roughness_raw | `float` | `number` |
| roughness_graduated | `float` | `number` |
| roughness_reduction | `float` | `number` |
| lambda_param | `float` | `number` |

### MortalitySurfaceResponse

| Field | Pydantic | TypeScript |
|:------|:---------|:-----------|
| ages | `List[int]` | `number[]` |
| years | `List[int]` | `number[]` |
| log_mx | `List[List[float]]` | `number[][]` |

The 2D `log_mx` is the only nested array in the API. It requires the double list comprehension at step 7.

### ValidationResponse

| Field | Pydantic | TypeScript |
|:------|:---------|:-----------|
| name | `str` | `string` |
| rmse | `float` | `number` |
| max_ratio | `float` | `number` |
| min_ratio | `float` | `number` |
| mean_ratio | `float` | `number` |
| n_ages | `int` | `number` |
| ages | `List[int]` | `number[]` |
| qx_ratios | `List[float]` | `number[]` |
| qx_differences | `List[float]` | `number[]` |

Note: The validation endpoint does not declare a `response_model` in the router (it returns a raw dict), so there is no Pydantic schema. The TypeScript interface `ValidationResponse` is defined purely on the frontend side.

---

## 4. Serialization Boundaries

There are exactly three serialization boundaries in the pipeline:

```
     CSV text  ──(1)──>  pandas DataFrame  ──(2)──>  numpy arrays  ──(3)──>  JSON
       disk                 in-memory                  in-memory              wire
```

| Boundary | From | To | Mechanism | Failure Mode |
|:---------|:-----|:---|:----------|:-------------|
| 1 | CSV text | pandas DataFrame | `pd.read_csv()` | Malformed CSV, wrong column names, encoding issues |
| 2 | DataFrame | numpy matrix | `.pivot().values.astype(float)` | Missing (age, year) pairs -> NaN in matrix |
| 3 | numpy -> JSON | `[float(v) for v in arr]` | Manual list comprehension | `np.float64` not serializable if missed |

Boundary 3 is where most Phase 4 bugs occurred. The pattern `[float(v) for v in array]` must be applied everywhere numpy values exit the engine. Forgetting this produces:

```
TypeError: Object of type float64 is not JSON serializable
```

---

## 5. Error Propagation

What happens when data is bad at each step, and how does the error surface to the user?

| Error Location | Error Type | How It Propagates | What the User Sees |
|:---------------|:-----------|:------------------|:-------------------|
| Step 1: CSV missing | `FileNotFoundError` | `load_all()` fails at startup | FastAPI never starts; uvicorn prints traceback |
| Step 2: Zero population | `ValueError` from `_validate()` | `load_all()` fails at startup | Same: server won't start |
| Step 2: NaN in matrix | `ValueError`: "has N NaN values" | `load_all()` fails at startup | Same: server won't start |
| Step 4: SVD fails | `np.linalg.LinAlgError` | `load_all()` fails | Server won't start |
| Step 7: numpy type leak | `TypeError` during serialization | FastAPI returns HTTP 500 | `useGet` catches -> `error` state -> red error text on page |
| Step 8: Pydantic validation | `ValidationError` | FastAPI returns HTTP 422 | Same: error state in hook |
| Step 10: Network timeout | `AxiosError` | `catch` block in `useGet` | `error` string displayed: "Error desconocido" |

Key design choice: all heavy computation happens at **startup** (step 6), not at request time. This means:
- If the server starts successfully, all data is guaranteed valid
- Request-time errors are limited to parameter validation (e.g., invalid `projection_year`) and serialization bugs
- The most catastrophic failures (bad data files) are caught before any user request

---

## 6. Full Pipeline ASCII Diagram

```
                               DATA FLOW: CSV TO CHART
  ============================================================================

  DISK                 PYTHON ENGINE                 API LAYER
  ────                 ─────────────                 ─────────

  mock_inegi_           ┌──────────────┐
  deaths.csv  ────────> │ a06:         │
  mock_conapo_          │ MortalityData│  mx, dx, ex
  population.csv ────>  │ from_inegi() │  (101 x 31)
                        └──────┬───────┘
                               │
                               v
                        ┌──────────────┐
                        │ a07:         │
                        │ GraduatedRates│  smoothed mx
                        │ (W-H)        │  (101 x 31)
                        └──────┬───────┘
                               │
                               v
                        ┌──────────────┐
                        │ a08:         │
                        │ LeeCarter    │  ax (101), bx (101), kt (31)
                        │ .fit()       │  explained_var: float
                        └──────┬───────┘
                               │
                               v
                        ┌──────────────┐
                        │ a09:         │
                        │ Projection   │  kt_central (30)
                        │ (RWD)        │  kt_simulated (500 x 30)
                        └──────┬───────┘
                               │
                               │  ┌──────────────────┐
                               └─>│ precomputed.py    │ module-level cache
                                  │ load_all()        │ (called once at startup)
                                  └──────┬────────────┘
                                         │
                                         v
                                  ┌──────────────────┐
                                  │ mortality_service │ numpy -> Python native
                                  │ get_lee_carter_   │ [float(v) for v in ...]
                                  │ params()          │
                                  └──────┬────────────┘
                                         │
                                         v
                                  ┌──────────────────┐
                                  │ router:          │ Pydantic validates
                                  │ GET /lee-carter  │ -> JSON response
                                  │ response_model=  │ Content-Type: app/json
                                  │ LeeCaterFitResp  │
                                  └──────┬────────────┘
                                         │
  ============================================================================

  NETWORK                REACT FRONTEND
  ───────                ──────────────

                                         │  HTTP GET /api/mortality/lee-carter
                                         │
                        ┌────────────────┐│
                        │ Vite proxy     ││  /api -> localhost:8000
                        │ vite.config.ts ││
                        └────────┬───────┘│
                                 │        │
                                 v        v
                        ┌──────────────────┐
                        │ axios client     │  baseURL: '/api'
                        │ api.get<T>()     │  TypeScript generic
                        └──────┬───────────┘
                               │
                               v
                        ┌──────────────────┐
                        │ useGet<T> hook   │  { data: T | null,
                        │ useApi.ts        │    loading: boolean,
                        │                  │    error: string | null }
                        └──────┬───────────┘
                               │
                               v
                        ┌──────────────────┐
                        │ Mortalidad.tsx   │  Map data -> trace objects
                        │ lc.data.ax ->   │  { x: ages, y: ax,
                        │ trace           │    name: 'a_x', color: '#000' }
                        └──────┬───────────┘
                               │
                               v
                        ┌──────────────────┐
                        │ LineChart.tsx    │  <Plot data={data}
                        │ Plotly.js       │        layout={layout} />
                        │                 │  -> SVG in DOM
                        └─────────────────┘
```

---

## 7. CORS Configuration

```python
# main.py:50-56
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

In development, requests come from two origins:
1. **Same-origin via Vite proxy**: Browser -> `localhost:5173/api/...` -> Vite -> `localhost:8000`. No CORS needed (same origin from browser's perspective).
2. **Direct to FastAPI**: Browser -> `localhost:8000/api/...`. CORS required because origin is `localhost:5173`.

The CORS middleware is configured for case 2 (direct access, Swagger docs testing, etc.). The Vite proxy handles case 1 transparently.

---

## 8. Router Architecture

All routers are mounted with a `/api` prefix at the app level:

```python
# main.py:59-63
app.include_router(mortality.router, prefix="/api")   # -> /api/mortality/...
app.include_router(pricing.router, prefix="/api")     # -> /api/pricing/...
app.include_router(portfolio.router, prefix="/api")   # -> /api/portfolio/...
app.include_router(scr.router, prefix="/api")         # -> /api/scr/...
app.include_router(sensitivity.router, prefix="/api") # -> /api/sensitivity/...
```

Each router also has its own prefix:

```python
# routers/mortality.py:16
router = APIRouter(prefix="/mortality", tags=["mortality"])
```

The combination yields `/api/mortality/lee-carter`, `/api/mortality/graduation`, etc.

This two-level prefix design separates:
- **`/api`**: distinguishes API calls from frontend asset requests (HTML, JS, CSS)
- **`/mortality`**, `/pricing`, etc.: groups related endpoints by domain

---

## 9. Lifespan Pattern

```python
# main.py:31-35
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all()      # runs BEFORE first request
    yield           # app serves requests
                    # cleanup would go after yield
```

The `load_all()` call in the lifespan context manager ensures:
1. All CSVs are parsed and matrices built (steps 1-2)
2. Graduation is applied (step 3)
3. Lee-Carter is fitted (step 4)
4. Projection is computed (step 5)
5. Regulatory tables are loaded

Total startup time: approximately 2-3 seconds on the project hardware. All subsequent requests are pure dict construction from cached objects.

---

## 10. The `.tolist()` Pattern and When to Use It

There are two approaches to converting numpy arrays to JSON-serializable Python types:

| Approach | Code | When Used |
|:---------|:-----|:----------|
| List comprehension | `[float(v) for v in array]` | Most service functions |
| `.tolist()` method | `array.tolist()` | Would also work, but not used in this codebase |

The list comprehension approach was chosen for explicitness -- it makes the type conversion visible at the call site. Both approaches handle nested arrays differently:

```python
# 1D array
np.array([1.0, 2.0]).tolist()                    # [1.0, 2.0]
[float(v) for v in np.array([1.0, 2.0])]         # [1.0, 2.0]

# 2D array
np.array([[1.0, 2.0], [3.0, 4.0]]).tolist()      # [[1.0, 2.0], [3.0, 4.0]]
[[float(v) for v in row] for row in arr]          # [[1.0, 2.0], [3.0, 4.0]]
```

For `np.int64`, the conversion is `int(v)` rather than `float(v)`:

```python
"ages": [int(a) for a in lc.ages]    # np.int64 -> int
```

---

## 11. Data Volume at Each Step

For the default mock dataset (101 ages, 31 years, 500 simulations):

| Step | Data Size | Format |
|:-----|:----------|:-------|
| CSV files | ~200 KB | Text on disk |
| numpy matrices (3 x 101 x 31) | ~75 KB | In-memory float64 |
| Lee-Carter params (ax + bx + kt) | ~1.9 KB | In-memory float64 |
| Projection (central + 500 sims) | ~125 KB | In-memory float64 |
| JSON response (lee-carter) | ~5 KB | Wire format |
| JSON response (surface) | ~90 KB | Wire format (2D matrix) |
| TypeScript object in memory | ~5 KB | Heap objects |
| Plotly SVG in DOM | ~20 KB | DOM nodes |

The surface endpoint is the largest single response due to the 2D matrix. The graduation and lee-carter endpoints are modest.
