# SIMA — Sistema Integral de Modelación Actuarial

SIMA is an end-to-end life-insurance modeling platform for mortality,
pricing, reserves, portfolio BEL, and solvency-capital analysis under a
Mexican LISF/CUSF context.

## Current status

| Capability | Implementation | Status |
|---|---|---|
| Mortality data | HMD and INEGI/CONAPO loaders, versioned schema checks, open-age aggregation | Complete |
| Graduation | Whittaker–Henderson smoothing with diagnostics | Complete |
| Mortality model | Lee–Carter SVD fit, optional `k_t` re-estimation | Complete |
| Projection | Random Walk with Drift, stochastic paths, life-table bridge | Complete |
| Regulatory comparison | CNSF/EMSSA ratios, RMSE, weighted RMSE, bias | Complete |
| Pricing | Whole life, term, endowment, pure endowment, limited-pay products | Complete |
| Reserves | Prospective reserves and trajectories with maturity/expiry handling | Complete |
| Portfolio | Policy validation, BEL breakdown, sex-specific bases, demo state | Complete |
| SCR | Mortality, longevity, interest-rate, catastrophe, aggregation, risk margin | Complete with documented limitations |
| API | FastAPI/Pydantic v2, 24 routes, structured errors, audit logging | Complete |
| Web application | React 19/TypeScript, six bilingual interactive pages | Complete |
| Deployment | Docker and Google Cloud Run configuration | Complete |

The backend-hardening work is tracked in `docs/plan-25julio.md`. Validation
rules are documented in `backend/VALIDATION.md`; SCR assumptions and
limitations are in `docs/technical/18_capital_requirements_reference.md`.

## Architecture

```text
HMD / INEGI / CONAPO
        |
        v
a06 data -> a07 graduation -> a08 Lee-Carter -> a09 projection
        |                                      |
        |                                      v
        +-------------------------------> a01 life table
                                                 |
                              a02 commutation -> a03 values
                                      |          |
                                      v          v
                                a04 premiums  a05 reserves
                                      \          /
                                       a11 portfolio
                                             |
                                           a12 SCR
                                             |
                                      FastAPI services
                                             |
                                      React application
```

The calculation engine is independent of HTTP and UI concerns. API services
convert engine results to typed response models, while routers handle
transport, structured error mapping, and audit logging.

## Technology

| Layer | Technology |
|---|---|
| Engine | Python 3.12, NumPy, SciPy, Pandas |
| API | FastAPI, Pydantic v2, Uvicorn |
| Frontend | React 19, TypeScript 5.9, Vite 7, Plotly.js, i18next |
| Quality | pytest (367 tests), Ruff, strict mypy on hardened core modules, ESLint, TypeScript |
| Delivery | Docker, Google Cloud Run, GitHub Actions |

## API surface

SIMA defines 24 routes: 23 domain routes across five routers plus health.

| Prefix | Count | Responsibility |
|---|---:|---|
| `/api/mortality` | 8 | Data summary, graduation, Lee–Carter, projection, tables, validation |
| `/api/pricing` | 5 | Premiums, reserves, commutations, rate and country sensitivity |
| `/api/portfolio` | 4 | Shared demo portfolio, policies, BEL |
| `/api/scr` | 3 | Custom/default SCR and compliance statement |
| `/api/sensitivity` | 3 | Mortality, country, and COVID comparisons |
| `/api/health` | 1 | Process and data-source health |

The portfolio endpoints currently operate on one locked, process-wide demo
portfolio. They are not per-user persistence.

## Data contract

Real raw data are not required for CI: committed mock INEGI/CONAPO, HMD,
CNSF, and EMSSA-format data exercise the complete pipeline. For real-data
analysis, follow:

- `backend/data/hmd/DOWNLOAD_GUIDE.md`
- `backend/data/inegi/DOWNLOAD_GUIDE.md`
- `backend/data/conapo/DOWNLOAD_GUIDE.md`
- `backend/data/cnsf/DOWNLOAD_GUIDE.md`

Loaders reject malformed schemas, missing/non-positive cells, invalid
age/year ranges, and inconsistent `m_x` versus `d_x/e_x`.

## Actuarial and regulatory scope

SIMA implements transparent, testable actuarial methods:

- Net premiums by the equivalence principle.
- Prospective policy reserves and portfolio BEL.
- Sex-specific mortality bases.
- Illustrative mortality (+15%), longevity (-20%), parallel interest-rate
  (±100 bps), and catastrophe (+35% of base mortality) stresses.
- Positive-semi-definite correlation aggregation.
- Optional Lee–Carter volatility-based shock calibration.
- Portfolio-specific remaining duration for the simplified risk margin.

It is not a complete production RCS/internal model. Missing modules include
credit, spread, lapse, expense, morbidity, operational, concentration, tax,
and full asset-liability/yield-curve modeling. Regulatory use requires
current LISF/CUSF verification, approved data, independent validation, and
insurer governance.

## Development

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest backend/tests/
ruff check .
mypy
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm ci
npm run lint
npm run build
npm run dev
```

## Success criteria

- Domain-invalid inputs fail at explicit boundaries with structured errors.
- Numerical edge cases (`i=0`, terminal ages, expired/matured policies) are
  deterministic and tested.
- BEL/SCR calculations are reproducible and carry documented assumptions.
- CI enforces linting, typing, frontend build, tests, and at least 80% backend
  coverage.
- Documentation distinguishes implemented analytics from filing-ready
  regulatory calculations.
