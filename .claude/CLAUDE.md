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

---

## Project Status (Updated: 2025-01-27)

### Completed

| Phase | Component | Location |
|-------|-----------|----------|
| Phase 2 | Life Table (l_x, d_x, q_x, p_x) | `backend/engine/a01_life_table.py` |
| Phase 2 | Commutation Functions (D, N, C, M) | `backend/engine/a02_commutation.py` |
| Phase 2 | Actuarial Values (A_x, a_x, nE_x) | `backend/engine/a03_actuarial_values.py` |
| Phase 2 | Net Premiums (whole life, term, endowment) | `backend/engine/a04_premiums.py` |
| Phase 2 | Reserves (prospective method) | `backend/engine/a05_reserves.py` |
| Phase 2 | Integration Tests (38 passing) | `backend/tests/` |

### Next Steps (In Order)

1. **Phase 1: Lee-Carter Mortality Model**
   - Get real Mexican mortality data (INEGI/CONAPO)
   - Graduate raw rates (Whittaker-Henderson smoothing)
   - Implement Lee-Carter (a_x, b_x, k_t parameters)
   - Validate against EMSSA-2009

2. **Phase 2 (continued): Sensitivity Analysis**
   - Interest rate sensitivity on reserves
   - Mortality shock analysis

3. **Phase 3: Capital Requirements**
   - Risk mapping (mortality, longevity, interest rate)
   - Stress scenarios per CNSF specifications
   - SCR aggregation with correlation matrix

4. **Phase 4: Web Platform**
   - FastAPI backend
   - React/Vue frontend
   - Interactive scenarios and reports

### Backend Code Reading Order

Read the engine modules in this order (dependencies build progressively):

| Order | File | Focus Areas | Key Formula |
|:-----:|------|-------------|-------------|
| 01 | `a01_life_table.py` | `__init__`, `_compute_derivatives()`, `@classmethod from_csv()`, `@property` | q_x = d_x / l_x |
| 02 | `a02_commutation.py` | `__init__` receives LifeTable, `_compute_D()` forward loop, `_compute_N()` backward recursion | D_x = v^x * l_x |
| 03 | `a03_actuarial_values.py` | All methods are ratio formulas using `self.comm.get_X()` | A_x = M_x / D_x |
| 04 | `a04_premiums.py` | Creates ActuarialValues inside, D_x cancels in formulas | P = SA * M_x / N_x |
| 05 | `a05_reserves.py` | Creates both `self.av` and `self.pc`, prospective formula | tV = SA*A_{x+t} - P*a_{x+t} |

**Dependency Flow:**
```
a01_life_table --> a02_commutation --> a03_actuarial_values
                                   |-> a04_premiums (uses a03)
                                   |-> a05_reserves (uses a03 + a04)
```

### Key Files Structure

```
backend/
├── engine/
│   ├── a01_life_table.py       # l_x -> d_x, q_x, p_x
│   ├── a02_commutation.py      # D, N, C, M (backward recursion)
│   ├── a03_actuarial_values.py # A_x, a_x, nE_x
│   ├── a04_premiums.py         # Equivalence principle
│   └── a05_reserves.py         # Prospective method
├── data/
│   ├── mini_table.csv          # Validation (ages 60-65)
│   └── sample_mortality.csv    # Full range (ages 20-110)
└── tests/
    └── test_*.py               # 38 tests
```
