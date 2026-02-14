# Architecture Update Addendum: Intuitive Reference

**Addendum to:** Doc 14 (`14_architecture_integration_intuition.md`)

**Scope:** This document extends Doc 14's "Two Rivers" analogy with the three new engine modules (a10-a12), the API tier, and the frontend tier. Read Doc 14 first.

---

## 1. Where We Left Off: The Two Rivers

Doc 14 described the SIMA engine as two rivers merging:

- **River 1 (Empirical):** Raw data -> graduation -> Lee-Carter -> projection
- **River 2 (Theoretical):** Life table -> commutation -> premiums -> reserves
- **The Bridge:** `to_life_table()` connects the two rivers

That architecture covered 9 modules (a01-a09) with 106 tests. Now the system has grown to 12 engine modules, 21 API endpoints, and a full React frontend. Here is what was added and why.

---

## 2. Three New Engine Modules: The Downstream Extensions

Think of the original two rivers as merging into a lake. The three new modules are infrastructure built ON that lake:

```
THE EXTENDED LANDSCAPE
======================

  River 1 (Empirical)    River 2 (Theoretical)
  a06 -> a07 -> a08 -> a09 -- bridge --> a01 -> a02 -> a03 -> a04 -> a05
                                                                  |
                                                    +-------------+
                                                    |
                              a10 VALIDATION        |
                              "Regulatory checkpoint"
                              Projected vs CNSF/EMSSA
                                                    |
                              a11 PORTFOLIO          |
                              "Insurance company"    |
                              Policies + BEL         |
                                                    |
                              a12 SCR               |
                              "Capital fortress"    |
                              4 risk modules + aggregation
```

### a10: The Regulatory Checkpoint

```
INTUITION
=========
After building a projected life table (Lee-Carter), the regulator asks:
"How does your projection compare to our approved tables?"

a10 (MortalityComparison) puts the two tables side by side:
- projected q_x / regulatory q_x  -> ratio (should be ~1.0)
- RMSE across working ages        -> overall fit metric
- Signed differences               -> where does projection diverge?

ANALOGY: Like comparing your GPS route to the official road map.
Both should show roughly the same terrain. If they diverge dramatically,
either your GPS is miscalibrated or the road map is outdated.
```

### a11: The Insurance Company

```
INTUITION
=========
Until a11, we had premiums and reserves for one policy at a time.
A real insurer holds THOUSANDS of policies -- a portfolio.

a11 introduces:
- Policy: a single insurance contract (age, product, sum assured, duration)
- Portfolio: a collection of policies (12 in the sample)
- BEL: the "Best Estimate Liability" -- what the insurer truly OWES

KEY INSIGHT
===========
BEL for a death product = the prospective reserve (from a05).
No new math. The reserve formula tV = SA*A_{x+t} - P*a_{x+t},
when evaluated with best-estimate assumptions, IS the BEL.

BEL for an annuity = pension * a_due(current_age).
The insurer simply owes annual payments as long as the person lives.
```

### a12: The Capital Fortress

```
INTUITION
=========
Having computed what the insurer OWES (BEL), the regulator asks:
"What if things go wrong? How much capital do you need to survive?"

a12 answers with four stress scenarios:

  1. MORTALITY RISK:    "+15% permanent q_x increase"
     What if more policyholders die than expected?
     -> Death claims increase, BEL for death products rises.

  2. LONGEVITY RISK:    "-20% permanent q_x decrease"
     What if annuitants live longer than expected?
     -> More pension payments, BEL for annuities rises.

  3. INTEREST RATE RISK: "+/- 1% parallel shift"
     What if interest rates change?
     -> All future cash flows are discounted differently. ALL products affected.

  4. CATASTROPHE RISK:   "+35% one-year mortality spike"
     What if a pandemic hits? (Calibrated from COVID-19 Mexico data)
     -> Sudden burst of excess death claims in year 1.

Each stress = "rerun BEL under adverse assumptions, measure the increase."

AGGREGATION
===========
You might think: total risk = sum of 4 risks.
But mortality risk and longevity risk are OPPOSITES (negative correlation = -0.25).
If more people die (bad for death products), annuitants also die (good for annuities).
The portfolio has a NATURAL HEDGE.

The correlation matrix captures this:
  SCR_life = sqrt(vec' * CORR * vec)  <  sum(vec)
  Diversification benefit = 14.4% reduction

Then life risk and interest rate risk are aggregated (rho = 0.25):
  SCR_total = sqrt(SCR_life^2 + SCR_ir^2 + 2*0.25*SCR_life*SCR_ir)
```

---

## 3. The API Tier: Engine Behind Glass

```
ANALOGY
=======
The engine modules (a01-a12) are like a complex machine in a factory.
The API is the glass window and control panel that lets you OPERATE
the machine without TOUCHING it.

REQUEST -> Router -> Service -> Engine -> Response

The 3-layer pattern:
  Router:   Handles HTTP (validates request, returns JSON)
  Service:  Orchestrates engine calls (loads data, calls functions, transforms results)
  Engine:   Pure computation (knows nothing about HTTP or JSON)

This separation means:
- The engine can be used without the API (e.g., in Jupyter notebooks)
- The API can be swapped (e.g., GraphQL) without changing engine code
- Testing is layered: engine tests, service tests, API integration tests
```

```
STARTUP PRECOMPUTATION
======================
Heavy calculations (Lee-Carter fit, graduation, projection) are
computed ONCE at server startup and cached in memory. API requests
read from this cache rather than recomputing.

This is like a restaurant that preps ingredients in the morning.
When orders come in, the kitchen assembles pre-prepped components
rather than starting from raw ingredients each time.
```

---

## 4. The Frontend Tier: The User's Eyes

```
ANALOGY
=======
If the API is the control panel, the frontend is the DASHBOARD.
Six screens, each showing a different aspect of the actuarial pipeline:

  Inicio       -> "Executive summary" (metrics, trend chart, navigation)
  Mortalidad   -> "Microscope" (zoom into mortality data, model, projection)
  Tarificacion -> "Calculator" (input parameters, get premium + reserve)
  SCR          -> "War room" (portfolio, stress scenarios, solvency gauge)
  Sensibilidad -> "Laboratory" (what-if experiments across 4 dimensions)
  Metodologia  -> "Textbook" (formulas and theory reference)

The frontend knows NOTHING about actuarial math.
It sends parameters, receives numbers, and renders them as charts/tables.
All computation happens on the backend.
```

---

## 5. The Full Four-Tier Architecture

```
THE COMPLETE PICTURE
====================

  TIER 4: FRONTEND (React)
  ========================
  User interacts with forms, sliders, buttons
  React renders MetricBlocks, Charts, Tables
  axios sends requests to /api/*
       |
       |  JSON over HTTP (Vite proxy in dev)
       v
  TIER 3: API (FastAPI)
  =====================
  5 routers handle 21 endpoints
  Services orchestrate engine calls
  Pydantic validates request/response schemas
       |
       |  Python function calls
       v
  TIER 2: ENGINE (Python)
  =======================
  12 modules (a01-a12)
  Pure computation, no HTTP awareness
  Can be used directly in scripts or notebooks
       |
       |  File I/O (startup only)
       v
  TIER 1: DATA (CSV/Text Files)
  =============================
  INEGI deaths + CONAPO population (Mexican data)
  HMD text files (USA, Spain)
  CNSF 2000-I, EMSSA 2009 (regulatory tables)
  Mock data for testing (committed to repo)
```

---

## 6. How a11/a12 Connect to the Existing Architecture

```
THE DEPENDENCY CHAIN FOR BEL
=============================
To compute BEL for one whole-life policy at duration t:

  LifeTable (a01)
       |
       v
  CommutationFunctions (a02) -- adds interest rate
       |
       v
  PremiumCalculator (a04) -- computes P (uses a03 internally)
       |
       v
  ReserveCalculator (a05) -- computes tV = SA*A_{x+t} - P*a_{x+t}
       |
       v
  compute_policy_bel (a11) -- calls ReserveCalculator for death products
       |                      calls ActuarialValues for annuities
       v
  Portfolio.compute_bel (a11) -- sums over all policies
       |
       v
  run_full_scr (a12) -- stresses the portfolio under 4 scenarios
```

```
INTUITION
=========
a11 is the "heaviest" importer because BEL computation requires the
ENTIRE theoretical pipeline. Think of it as standing at the end of
the assembly line and touching every preceding machine.

a12 sits on top of a11. It doesn't compute premiums or reserves
directly -- it says "compute BEL under THESE assumptions" and "now
compute BEL under THOSE assumptions" and takes the difference.
The SCR is always: stressed BEL - base BEL.
```

---

## 7. The Natural Hedge: Why Diversification Matters

```
SCENARIO: A PANDEMIC STRIKES
=============================

  DEATH PRODUCTS (whole life, term, endowment):
    More people die -> more claims -> BEL increases -> BAD

  ANNUITY PRODUCTS (life annuity):
    More people die -> fewer pension payments -> BEL decreases -> GOOD

  NET EFFECT: partially offset. The portfolio HEDGES itself.

The correlation matrix encodes this:
  Mortality-Longevity correlation = -0.25

This is why SCR_life (aggregated) < SCR_mort + SCR_long + SCR_cat.
The diversification benefit is 14.4% -- you need 14.4% LESS capital
than if you computed each risk independently and added them up.

INTERVIEW INSIGHT
=================
"The negative correlation between mortality and longevity risk is the
most important diversification benefit in life insurance. It's why
large insurers selling BOTH death products and annuities have a
structural capital advantage."
```

---

## 8. Updated Interview Q&A

**Q: "Your original architecture had 9 modules. How did it grow to 12?"**

A: "The original 9 modules covered two pipelines: empirical (data to model) and theoretical (life table to reserves). Phase 3 added three downstream modules. a10 validates our projections against regulatory tables -- a quality checkpoint. a11 introduces portfolio management and BEL computation -- it connects the 'one policy at a time' reserve calculator to a realistic 'many policies' context. a12 implements SCR by stressing the portfolio under four adverse scenarios and aggregating with a correlation matrix. Crucially, a11 reuses the ENTIRE theoretical pipeline (a01-a05) -- BEL for a death product IS the prospective reserve. No new actuarial math was needed; the architecture just orchestrates existing computations at portfolio scale."

**Q: "How does the API layer fit into the architecture?"**

A: "The API is a THIN layer between the engine and the outside world. It follows a three-layer pattern: Router (HTTP interface) -> Service (orchestration) -> Engine (computation). The engine modules know nothing about HTTP or JSON -- they're pure Python functions. The API precomputes expensive operations (Lee-Carter fit, graduation) at startup and caches them. This means a user's request like 'compute my premium' doesn't trigger a 30-second Lee-Carter fit -- it uses pre-cached results and only runs the fast pricing calculation."

**Q: "What's the role of the frontend?"**

A: "The frontend is a React SPA that visualizes the engine's outputs. It knows nothing about actuarial math -- it sends parameters to the API and renders the JSON response as charts, tables, and metric blocks. Six pages map to the six stages of the actuarial pipeline: mortality analysis, pricing, capital requirements, sensitivity analysis, and a theory reference page. The design uses a Swiss-inspired system with minimal colors, monospace numbers, and zero border-radius -- because in actuarial work, the numbers ARE the design."

**Q: "Could you replace the frontend without changing the backend?"**

A: "Yes, completely. The API's 21 endpoints define a clean contract via Pydantic schemas. You could build a mobile app, a Jupyter dashboard, or an Excel add-in that calls the same endpoints. Similarly, the engine can be used without the API -- you can import a01-a12 directly in a Python script or notebook. Each tier is independently replaceable."
