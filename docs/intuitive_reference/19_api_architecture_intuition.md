# API Architecture: Intuitive Reference

**Source files:** `backend/api/` (main.py, 5 routers, 4 services, 5 schemas, precomputed.py)

---

## The Big Picture

The SIMA API is a **translation layer** between the web world (JSON, HTTP, React) and the actuarial engine world (numpy arrays, LifeTables, CommutationFunctions). It adds no actuarial logic of its own.

```
ANALOGY
  Engine modules = the kitchen (where food is made)
  Service layer  = the waiters (translate orders, carry plates)
  Routers        = the menu (what you can order and how)
  Schemas        = the order forms (structured expectations)
```

---

## Why Three Tiers?

```
INTUITION
  Router:  "What can you order?" -- defines the menu
  Service: "How do we make it?"  -- orchestrates the kitchen
  Engine:  "The actual recipe"   -- pure actuarial math

  The restaurant analogy is exact: the chef (engine) never sees
  customers. The waiter (service) translates between the two worlds.
  The menu (router) is what the customer interacts with.
```

The key insight is that engine modules never import FastAPI, Pydantic, or anything HTTP-related. They are pure Python/numpy code. This means:
- You can test the engine with pytest alone (no web server needed)
- You can use the engine from a Jupyter notebook, a CLI script, or the API
- Changing the API framework (e.g., FastAPI to Flask) requires zero engine changes

---

## The Precomputed Cache: Why Compute at Startup?

```
INTUITION
  Running Lee-Carter takes several seconds:
    - Parse 4 CSV files
    - Build mortality matrices (101 ages x 31 years)
    - Whittaker-Henderson graduation (sparse linear solve)
    - SVD decomposition (rank-1 approximation)
    - RWD projection (500 Monte Carlo paths)

  If we did this on EVERY request, the API would take 3-5 seconds
  per response. Instead, we do it ONCE at startup and cache
  the results as module-level variables.

  Trade-off: cold start is slower (~3s), but every request after
  that is instant (<50ms).
```

### What Gets Cached

```
MortalityData  (mock INEGI deaths + CONAPO population)
    |
    v
GraduatedRates (Whittaker-Henderson, lambda=1e5)
    |
    v
LeeCarter      (SVD fit, reestimate_kt=False)
    |
    v
MortalityProjection  (30-year RWD, 500 sims, seed=42)

Also: CNSF and EMSSA regulatory LifeTables
```

Each of these has a getter function (`get_mortality_data()`, `get_graduated()`, etc.) that raises `RuntimeError` if called before startup. This is a safety net -- it prevents cryptic `NoneType` errors.

---

## The numpy Serialization Challenge

```
ROLE
  numpy types (int64, float64, ndarray) are NOT JSON-serializable.
  The service layer's primary engineering job is converting them.

USE
  Every service function ends with explicit type conversion:
    ages = [int(a) for a in lc.ages]     # np.int64 -> int
    ax   = [float(v) for v in lc.ax]     # np.float64 -> float
    log_mx = [[float(v) for v in row] for row in matrix]  # 2D array
```

This is tedious but necessary. Without it, FastAPI would raise `TypeError: Object of type int64 is not JSON serializable` on every response.

---

## Dynamic vs Hardcoded Endpoints

```
INTUITION
  Some endpoints compute fresh results from cached data:
    POST /api/pricing/premium     -> builds CommutationFunctions, calls PremiumCalculator
    POST /api/sensitivity/mortality-shock  -> builds shocked LifeTable, recomputes premiums

  Other endpoints return pre-baked data:
    GET /api/sensitivity/cross-country    -> returns a hardcoded dict
    GET /api/sensitivity/covid-comparison -> returns a hardcoded dict

  WHY? The cross-country and COVID endpoints need real HMD data
  (USA, Spain) that isn't distributed with the app. The values
  were extracted by running analysis scripts on real data, then
  pasted into the service code.
```

---

## The Portfolio: Stateful In-Memory

```
INTUITION
  The portfolio router is the only STATEFUL part of the API.
  It maintains a list of 12 policies in memory that you can:
    - View   (GET /summary)
    - Add to (POST /policy)
    - Reset  (POST /reset)
    - Price  (POST /bel, POST /scr/compute)

  This is NOT persisted to disk. Restarting the server resets
  everything to the default 12-policy sample portfolio.

  Think of it like a shopping cart that lives in server memory.
```

---

## Endpoint Organization

The 22 endpoints are organized into 5 functional groups:

```
/api/mortality/    (8 GET endpoints)
  Data loading, Lee-Carter, projection, graduation, surface, diagnostics, validation

/api/pricing/      (2 POST + 2 GET endpoints)
  Premium calculation, reserve trajectory, commutation lookup, interest rate sensitivity

/api/portfolio/    (2 POST + 1 GET endpoints + 1 POST)
  Portfolio summary, BEL computation, add policy, reset

/api/scr/          (2 POST endpoints)
  Full SCR pipeline with custom or default parameters

/api/sensitivity/  (1 POST + 2 GET endpoints)
  Mortality shock sweep (dynamic), cross-country and COVID (hardcoded)
```

---

## Error Flow

```
FORMULA
  Invalid JSON structure -> Pydantic returns 422 automatically
  Invalid domain logic   -> Service raises ValueError -> Router catches -> HTTP 400
  Missing precomputed    -> getter raises RuntimeError -> HTTP 500

USE
  The router's try/except block is the ONLY place where domain
  errors become HTTP errors. This keeps error handling centralized
  and prevents the service layer from knowing about HTTP status codes.
```

---

## Interview Q&A

**Q: Walk me through what happens when a user requests a whole life premium.**

A: The React frontend sends `POST /api/pricing/premium` with `{product_type: "whole_life", age: 40, sum_assured: 1000000, interest_rate: 0.05}`. Pydantic validates the body against `PremiumRequest`. The router calls `pricing_service.calculate_premium()`. The service loads the precomputed CNSF regulatory table, builds `CommutationFunctions(lt, 0.05)`, creates a `PremiumCalculator`, calls `pc.whole_life(SA=1_000_000, x=40)`, and returns the result as a dict. The router validates it against `PremiumResponse` and returns JSON.

**Q: What would break if you removed the service layer and called the engine directly from routers?**

A: Two things. First, numpy serialization would fail -- FastAPI cannot serialize `np.float64` to JSON. Second, you'd have engine import paths and type conversions scattered across every endpoint, making the routers unreadable. The service layer acts as an anti-corruption layer.

**Q: How would you add a new endpoint, say for computing annuity factors?**

A: Three steps. (1) Add a Pydantic response model to `schemas/pricing.py`. (2) Add a service function in `pricing_service.py` that calls `ActuarialValues(comm).a_due(age)` and converts the result. (3) Add a route in `routers/pricing.py` that calls the service function. No engine changes needed.

**Q: Why does the API use mock data instead of real INEGI/CONAPO data?**

A: Real INEGI mortality data is copyrighted and cannot be distributed. The mock data follows the same CSV format with synthetic Gompertz-Makeham mortality patterns. It produces realistic-looking results for demonstration. Users with real data can substitute the files via the download guides in `backend/data/`.
