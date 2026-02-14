# End-to-End Data Flow -- Intuitive Reference

## Follow the Data: One Number's Journey

Let's trace a single mortality rate -- m(60, 2020), the central death rate for 60-year-olds in the year 2020 -- from a CSV file on disk all the way to a pixel on a Plotly chart.

```
WHERE IT STARTS:
    A line in mock_inegi_deaths.csv:     "2020, 60, Total, 8500"
    A line in mock_conapo_population.csv: "2020, 60, Total, 850000"

WHAT HAPPENS:
    m(60, 2020) = 8500 / 850000 = 0.01   (1% of 60-year-olds die per year)

WHERE IT ENDS:
    A point on a Plotly line chart at coordinates (60, ln(0.01)) = (60, -4.6)
    Rendered as an SVG path segment in the browser DOM
```

Between those two points, the data passes through **12 transformation steps**, **3 programming languages** (Python, JSON, TypeScript), and **2 network hops** (Vite proxy, HTTP response).

---

## The Assembly Line

Think of the full pipeline as an assembly line with 12 stations. Raw materials (CSV rows) enter at station 1. A finished product (interactive chart) exits at station 12.

```
STATION    WHAT HAPPENS                            ANALOGY
───────    ────────────                            ───────

  1        CSV file read from disk                 Raw ore from the mine
  2        Pivot to matrix, validate               Smelting: refine into uniform ingots
  3        Whittaker-Henderson smoothing            Polishing: remove surface noise
  4        SVD decomposition (Lee-Carter)           X-ray analysis: reveal internal structure
  5        RWD projection                           Crystal ball: forecast the future
  6        Cache at startup                         Load the warehouse once
  7        Convert numpy to Python native           Translate the label to ship overseas
  8        Pydantic validates, FastAPI serializes   Quality inspection + packaging
  9        HTTP over network (Vite proxy)           Freight shipping
 10        React hook receives and stores           Unpack at the warehouse
 11        Map data fields to chart props           Arrange on the display shelf
 12        Plotly renders to SVG                    Customer sees the product
```

---

## Translation Layers

The data passes through five "languages":

```
CSV text  -->  pandas DataFrame  -->  numpy array  -->  JSON string  -->  TypeScript object
  "8500"        8500 (int64)         0.01 (float64)     "0.01"           0.01 (number)
```

Each translation carries risk. Like translating a book through five languages -- meaning can be lost or corrupted at each boundary:

| Translation | Risk | Mitigation |
|:------------|:-----|:-----------|
| CSV -> pandas | Wrong column names, encoding | Explicit column mapping, `.rename()` |
| pandas -> numpy | Missing cells become NaN | `_validate()` checks for NaN before proceeding |
| numpy -> JSON | `np.float64` not serializable | Explicit `float(v)` conversion in every service function |
| JSON -> TypeScript | Type mismatch (string vs number) | TypeScript interfaces mirror Pydantic models |

The numpy-to-JSON boundary (step 7) was the most common source of bugs during Phase 4 development. The error is:

```
TypeError: Object of type float64 is not JSON serializable
```

The fix is always the same pattern: `[float(v) for v in numpy_array]`.

---

## The Proxy Dance

```
                  BROWSER                            SERVERS
                  ───────                            ───────

  User visits localhost:5173              Vite dev server (port 5173)
                                                     |
  Page loads, React mounts                           |
  useEffect fires                                    |
  axios.get('/api/mortality/lee-carter')              |
                                                     |
  Browser sends to localhost:5173/api/... ──────>    |
  (same origin, no CORS!)                            |
                                                     |
                              Vite sees /api prefix  |
                              Proxies to port 8000   |
                                                     v
                                          FastAPI (port 8000)
                                          router matches
                                          service builds dict
                                          Pydantic validates
                                          JSON response back
                                                     |
                              Vite relays response   |
                                    <────────────────|

  axios receives JSON
  React setState({ data: parsed })
  Component re-renders with data
  Plotly draws the chart
```

Why the proxy? Without it, the browser would send a request from `localhost:5173` to `localhost:8000` -- a different origin. The browser's Same-Origin Policy would block it unless CORS headers are present. The Vite proxy makes the API appear to be on the same origin as the frontend.

---

## The Cache: Why Startup Matters

All the expensive computation (CSV parsing, matrix algebra, SVD, simulation) happens once, at server startup:

```
SERVER START (2-3 seconds)
─────────────────────────

    load_all() runs steps 1-5 completely
    Results stored in module-level Python variables

    _mortality_data = [computed]
    _graduated = [computed]
    _lee_carter = [computed]
    _projection = [computed]
    _cnsf_lt = [computed]
    _emssa_lt = [computed]

EVERY REQUEST (< 1 ms)
─────────────────────

    get_lee_carter_params() just reads from _lee_carter
    Converts numpy -> Python dict
    No recomputation, no file I/O
```

This is like pre-cooking all meals in the morning vs cooking each one when a customer orders. The tradeoff: startup takes a few seconds, but every request is instant.

If the data files are missing or corrupted, the server won't start at all. This is a feature, not a bug -- it catches data problems immediately, not after a user clicks something.

---

## Interview Answer: "How Does Raw Data Become a Chart?"

60-second version:

```
RAW DATA:    INEGI CSV files (deaths + population)
             Loaded by MortalityData.from_inegi() into numpy matrices

ENGINE:      Graduated via Whittaker-Henderson (removes noise)
             Decomposed by Lee-Carter SVD (extracts age/time components)
             Projected forward via Random Walk with Drift

CACHE:       All computed at FastAPI startup, held in module variables

API:         Service layer converts numpy arrays to Python lists
             Pydantic models validate the shape
             FastAPI serializes to JSON and returns HTTP response

NETWORK:     Vite dev proxy forwards /api requests to FastAPI
             Axios client in React receives the JSON

FRONTEND:    Custom useGet hook stores data in React state
             Page component maps data fields to Plotly trace objects
             LineChart component renders <Plot> which draws SVG

KEY INSIGHT: The only computation at request time is dict construction.
             Everything else happens once at startup.
```

---

## The Three Contracts

The system enforces correctness at three levels:

```
CONTRACT 1: Engine validation
─────────────────────────────
    _validate() in a06: no NaN, positive rates, d/L matches m_x
    WHEN: at CSV load time (startup)
    IF BROKEN: ValueError, server won't start

CONTRACT 2: Pydantic schema
────────────────────────────
    LeeCaterFitResponse enforces: ages is List[int], ax is List[float], etc.
    WHEN: at response time
    IF BROKEN: HTTP 422 Unprocessable Entity

CONTRACT 3: TypeScript interface
─────────────────────────────────
    LeeCaterFitResponse interface mirrors Pydantic model
    WHEN: at compile time
    IF BROKEN: tsc compilation error (caught in development)
```

Contract 1 catches data problems. Contract 2 catches serialization problems. Contract 3 catches structural problems. Together, they form a three-layer safety net that makes runtime errors rare.

---

## What Gets Lost in Translation

Even with all these safeguards, there are things the frontend cannot know:

```
KNOWN TO ENGINE, LOST TO FRONTEND:
    - numpy dtypes (float64 vs float32) -- JSON only has "number"
    - Matrix orientation (ages as rows, years as columns) -- flattened to lists
    - Identifiability constraints (sum(bx)=1, sum(kt)=0) -- just numbers by the time they arrive
    - Computational provenance (which step produced which array)

WHAT THE FRONTEND ADDS:
    - Visual encoding (color, position, axis labels)
    - Interactivity (hover tooltips, zoom, pan)
    - Responsive layout (adapts to window size)
    - i18n (Spanish/English labels)
```

The engine is the brain (computation). The API is the voice (communication). The frontend is the face (presentation). Each layer has different responsibilities and different loss characteristics.

---

## A Note on Scale

The SIMA pipeline processes modest data volumes:

```
101 ages  x  31 years  =  3,131 data points per matrix
3 matrices (mx, dx, ex) =  9,393 total cells
Lee-Carter output:         233 parameters (101 + 101 + 31)
JSON response:             ~5 KB for lee-carter endpoint
```

This is small enough that:
- No pagination needed
- No streaming needed
- No WebSocket needed
- Full matrices can be sent in a single HTTP response
- The 3D surface endpoint (101 x 31 = 3,131 cells) is the largest response at ~90 KB

For a production system with millions of policies, you would need pagination, caching layers, and possibly a database. For a portfolio demonstration project, the current architecture is right-sized.
