# SIMA: Sistema Integral de Modelacion Actuarial

## Project Purpose

Portfolio project for a bachelor's actuarial science graduate demonstrating:
- Traditional actuarial methods (commutation functions, reserves, LISF compliance)
- Modern techniques (Lee-Carter, stochastic modeling)
- Production software engineering (APIs, web interface)

**Primary Goal**: Deep understanding for interview proficiency, not just working code.

---

## Automatic Skill Invocation

### Planning Phase (Major Features)
When planning any major feature or methodology:
1. **Invoke `/regulador-mexicano`** - Regulatory compliance perspective first
2. **Invoke `/actuario-vanguardia`** - Challenge methodology with frontier research

### Completion Phase (Major Features)
When completing a major feature:
1. **Invoke `/gran-cuestionador`** - Test understanding through Socratic questioning
2. **Invoke `/regulador-mexicano`** - Final regulatory compliance validation

### Major Features Include
- Mortality graduation and Lee-Carter implementation
- Commutation functions and reserve calculations
- Premium pricing for any product
- Capital requirement components
- Any CNSF/LISF regulatory checkpoint

---

## Project Phases

### Phase 1: Mortality Engine
- Data: INEGI/CONAPO raw mortality
- Graduation: Whittaker-Henderson smoothing
- Model: Lee-Carter (a_x, b_x, k_t parameters)
- Validation: Compare vs EMSSA-2009

### Phase 2: Reserve Valuation
- Commutation functions: D_x, N_x, C_x, M_x
- Products: Term, whole life, endowment
- Premiums: Net premium via equivalence principle
- Reserves: Prospective method, sensitivity analysis

### Phase 3: Capital Requirements
- Risk mapping: Mortality, longevity, interest rate
- Stress scenarios per CNSF specifications
- SCR aggregation with correlation matrix
- Solvency dashboard

### Phase 4: Web Platform
- FastAPI backend with calculation engine
- React/Vue frontend with visualizations
- Interactive scenarios and reports

---

## Interview Preparation Focus

When working on any component, Claude should:
1. Explain the "why" behind each formula and method
2. Connect implementation to regulatory requirements
3. Highlight common interview questions for each topic
4. Challenge understanding with edge cases
5. Document assumptions explicitly

---

## Key Regulatory References

- **LISF**: Ley de Instituciones de Seguros y Fianzas
- **CUSF**: Circular Unica de Seguros y Fianzas
- **CNSF**: Comision Nacional de Seguros y Fianzas
- **EMSSA-2009**: Mexican Experience Mortality Table

---

## Data Licensing: Human Mortality Database (HMD)

HMD data are licensed under **Creative Commons Attribution 4.0 International License (CC BY 4.0)**.

**Required citation in all published work and presentations:**

> HMD. Human Mortality Database. Max Planck Institute for Demographic Research (Germany), University of California, Berkeley (USA), and French Institute for Demographic Studies (France). Available at www.mortality.org.

**Key obligations:**
- Always acknowledge HMD as source or intermediary provider
- Note the download date for future reference
- Do NOT redistribute HMD data copies -- refer users to www.mortality.org to download themselves
- Input data (under "Input Data" on country pages) must NOT be used for commercial gain or re-published without explicit permission from data owners (usually national statistical offices)
- Original HMD estimates (exposure-to-risk, death rates, life tables) are CC BY 4.0; input data remain under each provider's license

**Data stored locally at:** `backend/data/hmd/{COUNTRY_CODE}/`

---

## Development Standards

- Write tests alongside code
- Validate against known/published results
- Document assumptions as you go
- Use Spanish variable names where they match regulatory terminology
- English for code structure and documentation

---

## Documentation Structure

All documentation goes in `docs/` with two subfolders:

```
docs/
├── project/               # Session logs, what was done and why
│   └── ##_topic_project.md
├── technical/              # Formal definitions, formulas, reference material
│   └── ##_topic_reference.md
│
└── intuitive_reference/    # Conceptual explanations, intuition, learning notes
    └── ##_topic_intuition.md
```

### Naming Convention

- **Prefix with number:** `01_`, `02_`, etc. (order of creation/topic sequence)
- **Technical docs:** `##_<topic>_reference.md`
- **Intuitive docs:** `##_<topic>_intuition.md`

### When to Create Docs

1. After completing a learning/discussion session on a topic
2. When building understanding of a new concept
3. Always create BOTH technical AND intuitive versions when possible

### Current Docs

| # | Topic | Technical | Intuitive |
|:--|:------|:----------|:----------|
| 01 | Commutation Functions | `technical/01_commutation_functions_reference.md` | `intuitive_reference/01_commutation_functions_intuition.md` |
| 02 | Equivalence, Premiums & Reserves | `technical/02_equivalence_premiums_reserves_reference.md` | `intuitive_reference/02_equivalence_premiums_reserves_intuition.md` |
| 03 | Observations & Clarifications | `technical/03_observations_clarifications_reference.md` | `intuitive_reference/03_observations_clarifications_intuition.md` |
| 04 | Fundamental Identity (A_x + d*a_x = 1) | `technical/04_fundamental_identity_reference.md` | `intuitive_reference/04_fundamental_identity_intuition.md` |
| 05 | Commutation Deep Insights (N_x/D_x, O(n) recursion) | `technical/05_commutation_deep_insights_reference.md` | `intuitive_reference/05_commutation_deep_insights_intuition.md` |
| 06 | Python Class Mechanics (self, @classmethod, @property, dunder) | `technical/06_python_class_mechanics_reference.md` | `intuitive_reference/06_python_class_mechanics_intuition.md` |
| 07 | Lee-Carter Foundations (model, SVD, identifiability) | `technical/07_lee_carter_foundations_reference.md` | `intuitive_reference/07_lee_carter_foundations_intuition.md` |
| 08 | Lee-Carter Full Pipeline (estimation, diagnostics) | `technical/08_lee_carter_full_pipeline_reference.md` | `intuitive_reference/08_lee_carter_pipeline_estimation_intuition.md` |
| 09 | Whittaker-Henderson Graduation | `technical/09_whittaker_henderson_reference.md` | `intuitive_reference/09_whittaker_henderson_graduation_intuition.md` |
| 10 | Lee-Carter Implementation (code, tests, architecture) | `technical/10_lee_carter_implementation_reference.md` | `intuitive_reference/10_lee_carter_implementation_intuition.md` |
| 11 | Life Table Foundations (l_x, d_x, q_x, radix, LifeTable API) | `technical/11_life_table_foundations_reference.md` | `intuitive_reference/11_life_table_foundations_intuition.md` |
| 12 | Mortality Data & HMD (formats, MortalityData class, matrices) | `technical/12_mortality_data_hmd_reference.md` | `intuitive_reference/12_mortality_data_hmd_intuition.md` |
| 13 | Mortality Projection (RWD, simulation, to_life_table bridge) | `technical/13_mortality_projection_reference.md` | `intuitive_reference/13_mortality_projection_intuition.md` |
| 14 | Architecture & Integration (two pipelines, dependency flow) | `technical/14_architecture_integration_reference.md` | `intuitive_reference/14_architecture_integration_intuition.md` |
| 15 | Sensitivity Analysis (interest rate, mortality shocks, cross-country) | `technical/15_sensitivity_analysis_reference.md` | `intuitive_reference/15_sensitivity_analysis_intuition.md` |
| 16 | Mexican Data Pipeline (INEGI/CONAPO, regulatory, validation) | `technical/16_mexican_data_pipeline_reference.md` | `intuitive_reference/16_mexican_data_pipeline_intuition.md` |
| 17 | Real Mexican Data Analysis (Lee-Carter, COVID, regulatory) | `technical/17_real_mexican_analysis_reference.md` | `intuitive_reference/17_real_mexican_analysis_intuition.md` |
| 18 | Capital Requirements (SCR, risk modules, aggregation) | `technical/18_capital_requirements_reference.md` | `intuitive_reference/18_capital_requirements_intuition.md` |
| 19 | API Architecture (REST design, 3-tier, Pydantic, caching) | `technical/19_api_architecture_reference.md` | `intuitive_reference/19_api_architecture_intuition.md` |
| 20 | Frontend Architecture (React, Swiss design, Plotly, i18n) | `technical/20_frontend_architecture_reference.md` | `intuitive_reference/20_frontend_architecture_intuition.md` |
| 21 | End-to-End Data Flow (CSV to Plotly, 12 steps, serialization) | `technical/21_end_to_end_data_flow_reference.md` | `intuitive_reference/21_end_to_end_data_flow_intuition.md` |
| 22 | Testing Strategy (191 tests, THEORY pattern, API tests) | `technical/22_testing_strategy_reference.md` | `intuitive_reference/22_testing_strategy_intuition.md` |
| 23 | Analysis Scripts (3 scripts, output artifacts, hardcoded data) | `technical/23_analysis_scripts_reference.md` | `intuitive_reference/23_analysis_scripts_intuition.md` |
| 14b | Architecture Update Addendum (a10-a12, API tier, frontend tier) | `technical/14b_architecture_update_reference.md` | `intuitive_reference/14b_architecture_update_intuition.md` |

**Project Docs:**

| # | Topic | Location |
|:--|:------|:---------|
| 01 | Python Class Mechanics Session | `project/01_python_class_mechanics_project.md` |
| 02 | Lee-Carter Foundations Session | `project/02_lee_carter_foundations_project.md` |
| 03 | Lee-Carter Deep Dive Session | `project/03_lee_carter_deep_dive_project.md` |
| 04 | Graduation, Quadratic Forms & HMD Session | `project/04_graduation_quadratic_hmd_project.md` |
| 05 | Lee-Carter Implementation Session (7feb branch) | `project/05_lee_carter_implementation_project.md` |
| 06 | Documentation Catch-up Session (agent teams) | `project/06_documentation_catchup_project.md` |
| 07 | Mexican Data Pipeline (mock data, INEGI loader, validation) | `project/07_mexican_data_pipeline_project.md` |
| 08 | Real Mexican Data Analysis (Lee-Carter on INEGI/CONAPO, COVID) | `project/08_real_mexican_data_analysis_project.md` |
| 09 | Sensitivity Analysis (interest rate, mortality shocks, cross-country) | `project/09_sensitivity_analysis_project.md` |
| 10 | Capital Requirements (SCR, Phase 3) | `project/10_capital_requirements_project.md` |
| 11 | Web Platform Implementation (Phase 4a + 4b) | `project/11_web_platform_implementation_project.md` |

**Additional Docs:**

| Folder | File | Content |
|:-------|:-----|:--------|
| `latex/` | `quadratic_minimization_matrix.md` | Matrix calculus for Whittaker-Henderson |
| `latex/` | `svd_bilinear_identifiability_lee_carter.md` | SVD and identifiability proofs |
| `latex/` | `whittaker_henderson_graduation.md` | Graduation formula derivations |
| root | `portfolio_roadmap.md` | Project roadmap overview |

---

## Project Status (Updated: 2026-02-09, Phase 4b Complete)

### Completed

| Phase | Component | Location |
|-------|-----------|----------|
| Phase 2 | Life Table (l_x, d_x, q_x, p_x) | `backend/engine/a01_life_table.py` |
| Phase 2 | Commutation Functions (D, N, C, M) | `backend/engine/a02_commutation.py` |
| Phase 2 | Actuarial Values (A_x, a_x, nE_x) | `backend/engine/a03_actuarial_values.py` |
| Phase 2 | Net Premiums (whole life, term, endowment) | `backend/engine/a04_premiums.py` |
| Phase 2 | Reserves (prospective method) | `backend/engine/a05_reserves.py` |
| Phase 1 | HMD Data Loading (USA, Spain) | `backend/engine/a06_mortality_data.py` |
| Phase 1 | Whittaker-Henderson Graduation | `backend/engine/a07_graduation.py` |
| Phase 1 | Lee-Carter Model (SVD + k_t re-estimation) | `backend/engine/a08_lee_carter.py` |
| Phase 1 | Mortality Projection (RWD + LifeTable bridge) | `backend/engine/a09_projection.py` |
| Phase 1 | INEGI/CONAPO Data Loading (Mexican mortality) | `backend/engine/a06_mortality_data.py` (`from_inegi()`) |
| Phase 1 | Regulatory Table Loading (CNSF, EMSSA) | `backend/engine/a01_life_table.py` (`from_regulatory_table()`) |
| Phase 1 | Mortality Validation (comparison metrics) | `backend/engine/a10_validation.py` |
| Phase 1 | Real Mexican Data Analysis (Lee-Carter on INEGI/CONAPO) | `backend/analysis/mexico_lee_carter.py` |
| Phase 2 | Sensitivity Analysis (interest rate, mortality, cross-country) | `backend/analysis/sensitivity_analysis.py` |
| Phase 3 | Portfolio Management (Policy, Portfolio, BEL) | `backend/engine/a11_portfolio.py` |
| Phase 3 | SCR Engine (4 risk modules, aggregation, risk margin) | `backend/engine/a12_scr.py` |
| Phase 3 | Capital Requirements Analysis (full report) | `backend/analysis/capital_requirements.py` |
| Phase 4a | FastAPI REST API (15 endpoints, 5 routers) | `backend/api/` |
| Phase 4a | React Frontend (6 pages, Swiss design system) | `frontend/src/` |
| Phase 4b | Graduation/Surface/Diagnostics endpoints | `backend/api/routers/mortality.py` (3 new) |
| Phase 4b | Sensitivity endpoints (shock, cross-country, COVID) | `backend/api/routers/sensitivity.py` (3 new) |
| Phase 4b | Mortalidad page enrichment (graduation, 3D surface, SVD, EMSSA) | `frontend/src/pages/Mortalidad.tsx` |
| Phase 4b | Sensibilidad page enrichment (dynamic shock, API cross-country, COVID tab) | `frontend/src/pages/Sensibilidad.tsx` |
| Phase 4b | Inicio COVID teaser + Metodologia resources section | `frontend/src/pages/Inicio.tsx`, `Metodologia.tsx` |
| All | Tests (191 passing) | `backend/tests/` |

### API Endpoints (21 total)

| Router | Endpoint | Method |
|--------|----------|--------|
| mortality | `/mortality/data/summary` | GET |
| mortality | `/mortality/lee-carter` | GET |
| mortality | `/mortality/projection` | GET |
| mortality | `/mortality/life-table` | GET |
| mortality | `/mortality/validation` | GET |
| mortality | `/mortality/graduation` | GET (NEW 4b) |
| mortality | `/mortality/surface` | GET (NEW 4b) |
| mortality | `/mortality/diagnostics` | GET (NEW 4b) |
| pricing | `/pricing/premium` | POST |
| pricing | `/pricing/reserve` | POST |
| pricing | `/pricing/commutation` | GET |
| pricing | `/pricing/sensitivity` | POST |
| portfolio | `/portfolio/summary` | GET |
| portfolio | `/portfolio/bel` | POST |
| portfolio | `/portfolio/policy` | POST |
| portfolio | `/portfolio/reset` | POST |
| scr | `/scr/compute` | POST |
| scr | `/scr/defaults` | POST |
| sensitivity | `/sensitivity/mortality-shock` | POST (NEW 4b) |
| sensitivity | `/sensitivity/cross-country` | GET (NEW 4b) |
| sensitivity | `/sensitivity/covid-comparison` | GET (NEW 4b) |

### Backend Code Reading Order

Read the engine modules in this order (dependencies build progressively):

| Order | File | Focus Areas | Key Formula |
|:-----:|------|-------------|-------------|
| 01 | `a01_life_table.py` | `__init__`, `_compute_derivatives()`, `@classmethod from_csv()`, `@property` | q_x = d_x / l_x |
| 02 | `a02_commutation.py` | `__init__` receives LifeTable, `_compute_D()` forward loop, `_compute_N()` backward recursion | D_x = v^x * l_x |
| 03 | `a03_actuarial_values.py` | All methods are ratio formulas using `self.comm.get_X()` | A_x = M_x / D_x |
| 04 | `a04_premiums.py` | Creates ActuarialValues inside, D_x cancels in formulas | P = SA * M_x / N_x |
| 05 | `a05_reserves.py` | Creates both `self.av` and `self.pc`, prospective formula | tV = SA*A_{x+t} - P*a_{x+t} |
| 06 | `a06_mortality_data.py` | HMD + INEGI/CONAPO loading, age capping, matrix validation | m_x = d_x / L_x |
| 07 | `a07_graduation.py` | Whittaker-Henderson, sparse matrices, log-space smoothing | z = (W + lambda*D'D)^{-1} * W * m |
| 08 | `a08_lee_carter.py` | SVD decomposition, identifiability constraints, brentq re-estimation | ln(m_{x,t}) = a_x + b_x * k_t |
| 09 | `a09_projection.py` | RWD projection, stochastic simulation, `to_life_table()` bridge | k_{T+h} = k_T + h*drift + sigma*Z |
| 10 | `a10_validation.py` | MortalityComparison: qx_ratio, qx_difference, RMSE | RMSE = sqrt(mean((proj_qx - reg_qx)^2)) |
| 11 | `a11_portfolio.py` | Policy, Portfolio, BEL = prospective reserve, annuity BEL | BEL_death = tV; BEL_annuity = pension * a_due(x) |
| 12 | `a12_scr.py` | 4 risk modules, correlation aggregation, risk margin, solvency | SCR = sqrt(vec' * CORR * vec) |

**Dependency Flow:**
```
a06_mortality_data --> a07_graduation --> a08_lee_carter --> a09_projection
  (from_hmd)                                                    |
  (from_inegi)                                            to_life_table()
                                                                |
a01_life_table --> a02_commutation --> a03_actuarial_values     |
  (from_csv)                       |-> a04_premiums (uses a03)  |
  (from_regulatory_table)          |-> a05_reserves (uses a03 + a04)
                                                                |
                                                      a10_validation
                                                   (MortalityComparison)
                                                                |
a11_portfolio (Policy, Portfolio) --> a12_scr (SCR engine)
  uses: a02, a03, a04, a05            uses: a11, a01, a02, a03
```

### Key Files Structure

```
backend/
├── engine/
│   ├── a01_life_table.py       # l_x -> d_x, q_x, p_x
│   ├── a02_commutation.py      # D, N, C, M (backward recursion)
│   ├── a03_actuarial_values.py # A_x, a_x, nE_x
│   ├── a04_premiums.py         # Equivalence principle
│   ├── a05_reserves.py         # Prospective method
│   ├── a06_mortality_data.py   # HMD + INEGI/CONAPO data loading -> matrices
│   ├── a07_graduation.py       # Whittaker-Henderson smoothing
│   ├── a08_lee_carter.py       # Lee-Carter SVD fitting
│   ├── a09_projection.py       # RWD projection + LifeTable bridge
│   ├── a10_validation.py       # MortalityComparison (projected vs regulatory)
│   ├── a11_portfolio.py        # Policy, Portfolio, BEL computation
│   └── a12_scr.py              # SCR: 4 risk modules, aggregation, risk margin
├── data/
│   ├── mini_table.csv          # Validation (ages 60-65)
│   ├── sample_mortality.csv    # Full range (ages 20-110)
│   ├── hmd/                    # Human Mortality Database files
│   │   ├── usa/                # USA: Mx, Deaths, Exposures (1x1)
│   │   └── spain/              # Spain: Mx, Deaths, Exposures (1x1)
│   ├── mock/                   # Synthetic Mexican data (committed, for tests)
│   │   ├── mock_inegi_deaths.csv
│   │   ├── mock_conapo_population.csv
│   │   ├── mock_cnsf_2000_i.csv
│   │   └── mock_emssa_2009.csv
│   ├── inegi/                  # Real INEGI data (gitignored, see DOWNLOAD_GUIDE.md)
│   ├── conapo/                 # Real CONAPO data (gitignored, see DOWNLOAD_GUIDE.md)
│   └── cnsf/                   # Real CNSF/EMSSA tables (gitignored, see DOWNLOAD_GUIDE.md)
└── tests/
    └── test_*.py               # 169 tests
```

---

## Deployment (GCP VM)

| Field | Value |
|:------|:------|
| VM Name | `claude-dev-20260207-022749` |
| Zone | `us-central1-c` |
| Machine Type | `e2-standard-2` |
| Internal IP | `10.128.0.2` |
| External IP | `34.68.132.245` |
| User | `andtega349` |

### Local Development Deploy

**On the VM** (start both servers):

```bash
# Terminal 1: Backend
/home/andtega349/SIMA/venv/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd /home/andtega349/SIMA/frontend && npx vite --host 0.0.0.0 --port 5173
```

**On your local machine** (SSH tunnel via gcloud):

```bash
gcloud compute ssh andtega349@claude-dev-20260207-022749 --zone=us-central1-c -- -L 5173:localhost:5173 -L 8000:localhost:8000
```

Then open `http://localhost:5173` in your browser.

Note: Raw `ssh` won't work -- GCP uses metadata-based SSH keys managed by `gcloud`.
