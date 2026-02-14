# Phase 4: Web Platform Implementation -- Session Report

**Date:** 2026-02-09
**Branch:** `7feb`
**Tests before:** 169 (engine only) | **Tests after:** 191 (engine + 22 API tests)

---

## Actions: Phase 4a (FastAPI + React Scaffold)

### Backend API (`backend/api/`)

- Built the FastAPI application with lifespan-based startup data loading
- Created `precomputed.py` service that loads mock INEGI/CONAPO data, graduates it, fits Lee-Carter, projects 30 years, and caches results in module-level variables
- Implemented 4 routers with 15 endpoints:
  - `mortality` (5 endpoints): data summary, Lee-Carter params, projection, life table, validation
  - `pricing` (4 endpoints): premium, reserve, commutation values, interest rate sensitivity
  - `portfolio` (4 endpoints): summary, BEL, add policy, reset
  - `scr` (2 endpoints): compute with custom params, compute with Solvency II defaults
- Created Pydantic schemas mirroring engine output types (33 models total across 4 schema files)
- Created service layer (3 service files) bridging router requests to engine modules
- Configured CORS middleware for Vite dev server origin (`localhost:5173`)
- Added `/api/health` health check endpoint
- Wrote 22 API tests verifying actuarial properties (e.g., whole life premium < SA, reserve at t=0 near zero, diversification benefit > 0)

### Frontend Scaffold (`frontend/`)

- Initialized Vite 7.3.1 + React 19 + TypeScript project
- Installed dependencies: react-router-dom, react-i18next, i18next, plotly.js, react-plotly.js, katex, axios
- Configured Vite proxy: `/api` -> `http://localhost:8000`
- Implemented Swiss International Typographic Style design system:
  - Design tokens: black/grey/white palette, accent #C41E3A, Inter + JetBrains Mono fonts
  - Zero border-radius on all elements, no box-shadow, no gradients
  - Uppercase navigation with 0.1em letter-spacing
- Built 19 reusable components:
  - Layout (3): TopNav, PageLayout, Footer
  - Data (4): DataTable, MetricBlock, FormulaBlock, DeepDiveLink
  - Charts (7): LineChart, FanChart, WaterfallChart, HeatmapChart, SolvencyGauge, MortalitySurface, chartDefaults
  - Forms (3): SliderInput, PremiumForm, PolicyForm
  - Common (2): LanguageToggle, LoadingState
- Created axios client with `/api` base URL
- Created `useGet` and `usePost` React hooks wrapping axios with loading/error state management
- Implemented 6 pages connected to API endpoints:
  - Inicio: project overview, key metrics, k_t mini chart, navigation cards
  - Mortalidad: Lee-Carter parameters (a_x, b_x, k_t charts), projection fan chart, validation table
  - Tarificacion: premium calculator form, reserve trajectory chart, interest rate sensitivity
  - SCR: SCR computation, waterfall decomposition chart, solvency gauge
  - Sensibilidad: interest rate tab with hardcoded mortality shock and cross-country data
  - Metodologia: 8 numbered sections explaining the mathematical pipeline
- Set up i18n with Spanish (default) and English, ~80 initial translation keys
- Defined TypeScript interfaces mirroring all Pydantic response models (20+ interfaces in `types/index.ts`)

---

## Actions: Phase 4b (Web Enrichment)

### Backend Enrichment

- Added 3 new endpoints to `routers/mortality.py`:
  - `GET /mortality/graduation`: raw vs graduated mx with roughness metrics
  - `GET /mortality/surface`: 2D log(mx) matrix for 3D visualization
  - `GET /mortality/diagnostics`: Lee-Carter RMSE, residuals sample
- Created new sensitivity router (`routers/sensitivity.py`) with 3 endpoints:
  - `POST /sensitivity/mortality-shock`: dynamic shock sweep (configurable age, product, factors)
  - `GET /sensitivity/cross-country`: Mexico/USA/Spain Lee-Carter comparison (hardcoded from analysis)
  - `GET /sensitivity/covid-comparison`: pre-COVID vs full-period (hardcoded from analysis)
- Added 3 new Pydantic schemas to `schemas/mortality.py`: `GraduationResponse`, `MortalitySurfaceResponse`, `LCDiagnosticsResponse`
- Created `schemas/sensitivity.py` with 8 Pydantic models for the sensitivity endpoints
- Created `services/sensitivity_service.py` with `_build_shocked_lt()` and `_compute_premium()` helper functions
- Added 3 new service functions to `mortality_service.py`: `get_graduation_data()`, `get_surface_data()`, `get_diagnostics_data()`
- Registered sensitivity router in `main.py`

### Frontend Enrichment

- Enriched Mortalidad page with 4 new sections:
  1. Graduation overlay: raw vs graduated log(mx) line chart with roughness metrics
  2. Mortality surface: 3D Plotly surface plot of log(m_{x,t})
  3. SVD diagnostics: RMSE, max/mean absolute error, explained variance metrics
  4. Multi-table validation: CNSF 2000-I / EMSSA 2009 tab switcher
- Enriched Sensibilidad page with 3 changes:
  1. Mortality shock tab: replaced hardcoded arrays with dynamic API call, added age slider + product select
  2. Cross-country tab: replaced hardcoded data with API fetch, added k_t/a_x/b_x profile charts
  3. New COVID tab: drift comparison metrics, k_t overlay chart, premium impact table
- Added COVID impact teaser to Inicio page (drift shift metric, premium impact, DeepDiveLink)
- Added Resources section to Metodologia page (LaTeX document + 18 technical doc pairs)
- Added 13 new TypeScript interfaces to `types/index.ts`
- Added ~40 new i18n translation keys in both Spanish and English

---

## Outputs

### Phase 4a Files Created

| File | Type |
|:-----|:-----|
| `backend/api/__init__.py` | Package init |
| `backend/api/main.py` | FastAPI app with CORS + lifespan |
| `backend/api/routers/__init__.py` | Package init |
| `backend/api/routers/mortality.py` | 5 endpoints |
| `backend/api/routers/pricing.py` | 4 endpoints |
| `backend/api/routers/portfolio.py` | 4 endpoints |
| `backend/api/routers/scr.py` | 2 endpoints |
| `backend/api/schemas/__init__.py` | Package init |
| `backend/api/schemas/mortality.py` | 8 Pydantic models |
| `backend/api/schemas/pricing.py` | 10 Pydantic models |
| `backend/api/schemas/portfolio.py` | 6 Pydantic models |
| `backend/api/schemas/scr.py` | 9 Pydantic models |
| `backend/api/services/__init__.py` | Package init |
| `backend/api/services/precomputed.py` | Startup cache |
| `backend/api/services/mortality_service.py` | Mortality bridge |
| `backend/api/services/pricing_service.py` | Pricing bridge |
| `backend/api/services/scr_service.py` | SCR bridge |
| `backend/tests/test_api/conftest.py` | TestClient fixture |
| `backend/tests/test_api/test_health.py` | 1 test |
| `backend/tests/test_api/test_mortality_api.py` | 6 tests |
| `backend/tests/test_api/test_pricing_api.py` | 7 tests |
| `backend/tests/test_api/test_portfolio_api.py` | 4 tests |
| `backend/tests/test_api/test_scr_api.py` | 4 tests |
| `frontend/` (entire directory) | Vite + React project |
| 19 React components | Charts, layout, forms, data display |
| 6 page components | Inicio through Metodologia |
| `frontend/src/types/index.ts` | 20 TypeScript interfaces |
| `frontend/src/hooks/useApi.ts` | useGet + usePost hooks |
| `frontend/src/api/client.ts` | Axios instance |
| `frontend/src/i18n.ts` | Spanish + English translations |

### Phase 4b Files Created/Modified

| File | Action |
|:-----|:-------|
| `backend/api/routers/sensitivity.py` | Created (3 endpoints) |
| `backend/api/schemas/sensitivity.py` | Created (8 models) |
| `backend/api/services/sensitivity_service.py` | Created (3 services + 2 helpers) |
| `backend/api/routers/mortality.py` | Modified (+3 endpoints) |
| `backend/api/schemas/mortality.py` | Modified (+3 models) |
| `backend/api/services/mortality_service.py` | Modified (+3 service functions) |
| `backend/api/main.py` | Modified (added sensitivity router) |
| `frontend/src/pages/Mortalidad.tsx` | Modified (+4 sections) |
| `frontend/src/pages/Mortalidad.module.css` | Modified (+3 CSS classes) |
| `frontend/src/pages/Sensibilidad.tsx` | Modified (3 tabs rewritten + 1 new tab) |
| `frontend/src/pages/Inicio.tsx` | Modified (+COVID teaser section) |
| `frontend/src/pages/Inicio.module.css` | Modified (+4 CSS classes) |
| `frontend/src/pages/Metodologia.tsx` | Modified (+Resources section) |
| `frontend/src/types/index.ts` | Modified (+13 interfaces) |
| `frontend/src/i18n.ts` | Modified (+40 translation keys) |

---

## Tech Stack Decisions

| Decision | Chosen | Alternative Considered | Rationale |
|:---------|:-------|:----------------------|:----------|
| Backend framework | FastAPI | Django REST | FastAPI has native async, Pydantic validation, auto-generated Swagger docs. Django is heavier than needed for a pure API. |
| Frontend framework | React 19 | Vue 3 | React has the largest ecosystem for data visualization (react-plotly.js, katex). More interview-relevant. |
| Build tool | Vite 7.3 | Create React App | Vite is 10x faster for dev builds, has native TypeScript + proxy support, and CRA is deprecated. |
| Charting library | Plotly.js | D3.js, Recharts | Plotly provides 3D surfaces, fan charts, and waterfall charts out of the box. D3 would require building all of these from scratch. |
| HTTP client | Axios | fetch API | Axios provides interceptors, automatic JSON parsing, and TypeScript generics. Less boilerplate than raw fetch. |
| Design system | Swiss (custom) | Material UI, Tailwind | Swiss design demonstrates visual design sensibility. Component libraries produce generic-looking apps. |
| i18n | react-i18next | Manual | Industry standard, supports dynamic key loading, tiny bundle impact. |
| Math rendering | KaTeX | MathJax | KaTeX is 3x faster than MathJax and works with React rendering lifecycle. |

---

## Challenges and Solutions

### 1. numpy Serialization (Most Common Bug)

**Problem:** `np.float64` values cannot be serialized to JSON by FastAPI's default encoder.

```python
# Fails:
return {"ages": lc.ages}    # numpy int64 array

# Works:
return {"ages": [int(a) for a in lc.ages]}
```

**Solution:** Every service function explicitly converts numpy types to Python native types using list comprehensions. This affects every array returned by the engine.

### 2. CORS in Development

**Problem:** Browser blocks requests from `localhost:5173` to `localhost:8000` due to different origins.

**Solution:** Two layers:
1. Vite proxy (`/api` -> `localhost:8000`) makes most requests same-origin
2. FastAPI CORSMiddleware with `allow_origins=["http://localhost:5173"]` handles direct access

### 3. Pydantic Schema Keys vs Engine Keys

**Problem:** Template code used `summary["lambda_param"]` but the actual engine method returns `summary["lambda"]`.

**Solution:** Read the actual engine code before writing service functions. The template was a starting point, not a specification.

### 4. Residuals Matrix Not in goodness_of_fit()

**Problem:** Assumed `LeeCarter.goodness_of_fit()` returns a residuals matrix, but it only returns scalar metrics.

**Solution:** Manually compute residuals in the service layer:

```python
fitted_log = lc.ax[:, np.newaxis] + np.outer(lc.bx, lc.kt)
residuals_matrix = lc.log_mx - fitted_log
```

### 5. TypeScript Strict Mode

**Problem:** TypeScript's strict null checking requires handling the `data: T | null` state from useGet hooks.

**Solution:** Guard all data access with conditional rendering:

```tsx
{lc.data && (
    <LineChart traces={[{ x: lc.data.ages, y: lc.data.ax, ... }]} />
)}
```

And use non-null assertion (`data!.field`) inside nested callbacks where the parent guard already checks for null.

---

## Agent Team Orchestration

### Phase 4a

Three agents worked in parallel:
1. **Backend engineer**: Built `backend/api/` (main.py, 4 routers, 4 schemas, 3 services, precomputed.py, 22 tests)
2. **Visualizer**: Built `frontend/` scaffold (Vite project, 19 components, 6 pages, design system, i18n, types, hooks)
3. **Actuary/CNSF reviewer**: Validated endpoint designs against regulatory requirements

Coordination: the backend engineer report and visualizer report were written to `subagents_outputs/` for the lead agent to review before integration.

### Phase 4b

Five agents worked in parallel:
1. **Backend mortality agent**: Added 3 endpoints to mortality router (graduation, surface, diagnostics)
2. **Backend sensitivity agent**: Created entire sensitivity router (3 endpoints, schemas, service)
3. **i18n + types agent**: Added 40 translation keys and 13 TypeScript interfaces
4. **Frontend mortalidad agent**: Enriched Mortalidad page with 4 new sections
5. **Frontend pages agent**: Enriched Sensibilidad, Inicio, and Metodologia pages

Coordination: backend agents ran first (their endpoints are dependencies for frontend agents). Frontend agents consumed the new TypeScript types and i18n keys added by the types agent.

---

## API Endpoint Summary (21 Total)

| # | Router | Method | Path | Phase |
|:-:|:-------|:-------|:-----|:------|
| 1 | -- | GET | `/api/health` | 4a |
| 2 | mortality | GET | `/api/mortality/data/summary` | 4a |
| 3 | mortality | GET | `/api/mortality/lee-carter` | 4a |
| 4 | mortality | GET | `/api/mortality/projection` | 4a |
| 5 | mortality | GET | `/api/mortality/life-table` | 4a |
| 6 | mortality | GET | `/api/mortality/validation` | 4a |
| 7 | mortality | GET | `/api/mortality/graduation` | 4b |
| 8 | mortality | GET | `/api/mortality/surface` | 4b |
| 9 | mortality | GET | `/api/mortality/diagnostics` | 4b |
| 10 | pricing | POST | `/api/pricing/premium` | 4a |
| 11 | pricing | POST | `/api/pricing/reserve` | 4a |
| 12 | pricing | GET | `/api/pricing/commutation` | 4a |
| 13 | pricing | POST | `/api/pricing/sensitivity` | 4a |
| 14 | portfolio | GET | `/api/portfolio/summary` | 4a |
| 15 | portfolio | POST | `/api/portfolio/bel` | 4a |
| 16 | portfolio | POST | `/api/portfolio/policy` | 4a |
| 17 | portfolio | POST | `/api/portfolio/reset` | 4a |
| 18 | scr | POST | `/api/scr/compute` | 4a |
| 19 | scr | POST | `/api/scr/defaults` | 4a |
| 20 | sensitivity | POST | `/api/sensitivity/mortality-shock` | 4b |
| 21 | sensitivity | GET | `/api/sensitivity/cross-country` | 4b |
| 22 | sensitivity | GET | `/api/sensitivity/covid-comparison` | 4b |

---

## Forward References

- **Doc 19**: API Architecture Reference (`docs/technical/19_api_architecture_reference.md`) -- detailed Pydantic schemas, service patterns, testing strategy
- **Doc 20**: Frontend Architecture Reference (`docs/technical/20_frontend_architecture_reference.md`) -- component hierarchy, Swiss design system, i18n patterns
- **Doc 21**: End-to-End Data Flow (`docs/technical/21_end_to_end_data_flow_reference.md`) -- 12-step trace from CSV to Plotly chart
