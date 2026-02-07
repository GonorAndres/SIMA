# SIMA: Sistema Integral de Modelación Actuarial
## Integrated Actuarial Modeling System

A full-stack life insurance risk management platform demonstrating end-to-end actuarial modeling from mortality projection through capital requirements.

---

## Project Overview

**Purpose**: Build a professional portfolio project that demonstrates:
- Traditional actuarial methods (commutation functions, reserves, LISF compliance)
- Modern techniques (Lee-Carter, stochastic modeling, ML where appropriate)
- Production software engineering (APIs, web interface, documentation)

**Target Audience**: 
- Hiring managers at insurance companies
- CNSF reviewers (regulatory alignment)
- Academic evaluators (methodological rigor)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB INTERFACE                            │
│   Dashboard · Visualizations · Interactive Scenarios · Reports  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CALCULATION ENGINE                         │
├───────────────────┬───────────────────┬─────────────────────────┤
│  PHASE 1          │  PHASE 2          │  PHASE 3                │
│  Mortality Engine │  Reserve Module   │  Capital Module         │
│                   │                   │                         │
│  · Raw data       │  · Commutation    │  · Risk components      │
│  · Graduation     │  · Life products  │  · Stress scenarios     │
│  · Lee-Carter     │  · Reserves       │  · Aggregation          │
│  · Projections    │  · Sensitivity    │  · Solvency metrics     │
└───────────────────┴───────────────────┴─────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
│          Mortality Tables · Policy Portfolio · Assumptions      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Mortality Engine

**Goal**: From raw mortality data to projected mortality rates

### Milestones

| ID | Milestone | Deliverable | Status |
|----|-----------|-------------|--------|
| 1.1 | Data acquisition | INEGI/CONAPO raw mortality data loaded | ⬜ |
| 1.2 | Graduation | Smooth mortality rates (Whittaker-Henderson) | ⬜ |
| 1.3 | Lee-Carter fit | Estimated a_x, b_x, k_t parameters | ⬜ |
| 1.4 | Projection | q_x(t) forecast to 2050 | ⬜ |
| 1.5 | Validation | Comparison vs EMSSA-2009 | ⬜ |

### Key Formulas

```
Lee-Carter Model:
ln(m_{x,t}) = a_x + b_x · k_t + ε_{x,t}

Where:
- a_x = age-specific average log mortality
- b_x = age-specific sensitivity to improvement
- k_t = time-varying mortality index
```

### Output
- `mortality_engine.py` module
- API endpoint: `GET /api/mortality?age={x}&year={t}`
- Visualization: Mortality surface plot, Lee-Carter diagnostics

### Regulatory Checkpoints
- [ ] Compare against EMSSA-2009 (CUSF 7.5 requirement)
- [ ] Document graduation method (CUSF 7.6)
- [ ] Age range 0-110 minimum
- [ ] Extrapolation method documented for ages 85+

---

## Phase 2: Reserve Valuation

**Goal**: From mortality rates to policy reserves

### Milestones

| ID | Milestone | Deliverable | Status |
|----|-----------|-------------|--------|
| 2.1 | Commutation functions | D_x, N_x, C_x, M_x tables | ⬜ |
| 2.2 | Product definitions | Term, whole life, endowment specs | ⬜ |
| 2.3 | Premium calculation | Net premiums via equivalence principle | ⬜ |
| 2.4 | Reserve projection | V_t trajectory for sample policies | ⬜ |
| 2.5 | Sensitivity analysis | Impact of ±Δi, ±Δq_x on reserves | ⬜ |

### Key Formulas

```
Commutation Functions:
D_x = v^x · l_x
N_x = Σ D_y (from y=x to ω)
C_x = v^(x+1) · d_x
M_x = Σ C_y (from y=x to ω)

Prospective Reserve:
V_t = A_{x+t:n-t} - P · ä_{x+t:n-t}

Net Premium (Equivalence Principle):
P = A_{x:n} / ä_{x:n}
```

### Output
- `reserve_module.py` module
- API endpoint: `POST /api/reserves` with policy parameters
- Visualization: Reserve trajectory, sensitivity tornado chart

### Regulatory Checkpoints
- [ ] Net premium method as primary (LISF 217)
- [ ] Interest rate ≤ regulatory maximum (CUSF 7.3)
- [ ] Prospective = Retrospective validation
- [ ] All reserves ≥ 0

---

## Phase 3: Capital Requirements

**Goal**: From reserves to solvency capital

### Milestones

| ID | Milestone | Deliverable | Status |
|----|-----------|-------------|--------|
| 3.1 | Risk identification | Mortality, longevity, interest rate risk mapped | ⬜ |
| 3.2 | Stress scenarios | Shocked mortality/rates per CNSF specs | ⬜ |
| 3.3 | Individual SCR | Capital for each risk component | ⬜ |
| 3.4 | Aggregation | Combined SCR with correlation | ⬜ |
| 3.5 | Solvency dashboard | Ratio, buffer, traffic light status | ⬜ |

### Key Formulas

```
LISF Standard Formula:
RCS = √(C1² + C2² + C3²) + C4 + Concentration

Where:
- C1 = Underwriting risk (mortality/longevity)
- C2 = Market risk (interest rate)
- C3 = Credit risk
- C4 = Operational risk

Stress Scenarios (LISF 236):
- Mortality shock: +15% for life insurance
- Longevity shock: -20% for annuities
- Interest rate: ±100 bps parallel shift
```

### Output
- `capital_module.py` module
- API endpoint: `GET /api/capital`
- Visualization: Capital waterfall, solvency ratio gauge

### Regulatory Checkpoints
- [ ] Map to LISF risk categories (Articles 232-236)
- [ ] Stress scenarios match CNSF specifications
- [ ] Correlation matrix documented
- [ ] 99.5% VaR confidence level

---

## Phase 4: Web Platform

**Goal**: Professional presentation layer

### Sections

| Section | Purpose | Key Elements |
|---------|---------|--------------|
| Landing | Project overview | Hero, value proposition, your profile |
| Methodology | Technical documentation | Math explained clearly, assumptions listed |
| Interactive Demo | User exploration | Input assumptions → see outputs in real-time |
| Visualizations | Data storytelling | Mortality surface, reserve trajectories, capital waterfall |
| Technical Report | Downloadable documentation | CNSF-style PDF format |
| Code Repository | GitHub showcase | Clean code, README, docstrings |

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python + FastAPI |
| Calculation | NumPy, SciPy, Pandas |
| Frontend | React or Vue |
| Visualization | Plotly / D3.js |
| Styling | Tailwind CSS |
| Hosting | Vercel / Railway / GCP |

---

## Development Workflow

### Before Each Phase
1. Invoke **El Regulador** to validate approach is CNSF-compliant
2. Invoke **El Vanguardia** to confirm method selection is appropriate
3. Document assumptions and approach

### During Implementation
- Write tests alongside code
- Validate against known results
- Document as you go

### After Each Phase
1. Invoke **El Gran Cuestionador** for understanding check
2. Complete regulatory checkpoint list
3. Update this document with status

---

## Success Criteria

A reviewer should be able to:

- [ ] Understand the system in 30 seconds (landing page)
- [ ] Verify traditional methods are correct (commutation functions, reserves)
- [ ] See modern techniques applied (Lee-Carter, stochastic elements)
- [ ] Validate calculations independently (worked examples)
- [ ] Run their own scenarios (interactive demo)
- [ ] Review production-quality code (GitHub)
- [ ] Download technical documentation (PDF report)

---

## Timeline

| Week | Focus | Checkpoint |
|------|-------|------------|
| 1-2 | Phase 1: Mortality | Lee-Carter working, validated vs EMSSA |
| 3-4 | Phase 2: Reserves | Reserve calculations for 3 products |
| 5-6 | Phase 3: Capital | SCR aggregation complete |
| 7-8 | Phase 4: Web | Full platform deployed |
| 9 | Polish | Documentation, edge cases, presentation |

---

## File Structure (Target)

```
sima/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── mortality.py
│   │   │   ├── reserves.py
│   │   │   └── capital.py
│   │   └── main.py
│   ├── engine/
│   │   ├── mortality_engine.py
│   │   ├── reserve_module.py
│   │   └── capital_module.py
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── tables/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
│   └── public/
├── docs/
│   ├── technical_note.tex
│   ├── methodology.md
│   └── api_reference.md
├── notebooks/
│   ├── 01_mortality_exploration.ipynb
│   ├── 02_reserve_validation.ipynb
│   └── 03_capital_scenarios.ipynb
└── README.md
```

---

## Progress Log

| Date | Milestone | Notes |
|------|-----------|-------|
| | | |

---

## Notes

*Use this section for ongoing observations, questions, and learnings.*
