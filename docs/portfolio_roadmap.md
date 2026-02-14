# Portfolio Enhancement Roadmap
## Andrés González Ortega — Actuarial Career Development

**Created:** 2026-02-01  
**Status:** Planning  
**Goal:** Add high-value differentiated project to portfolio for competitive positioning

---

## 1. Current Portfolio Assessment

### Existing Strengths
| Skill Area | Evidence | Market Value |
|------------|----------|--------------|
| Python + GCP/BigQuery | CDP systems, Cloud Functions, Firestore | High |
| ML for Insurance | Credit risk model (85% AUC), churn prediction | High |
| Mexican Regulation | LISF/CUSF analysis, CNSF data work | Medium-High |
| Data Engineering | Production email systems, APIs, ETL pipelines | High |
| Traditional Actuarial | Life/damage notes, mortality tables, reserves | Standard |

### Portfolio Gaps
- No forward-looking risk modeling (stochastic)
- No catastrophe/climate risk work
- No international standards (IFRS 17, Solvency II)
- Production engineering experience not showcased
- Heavy academic framing, light industry framing

### Current Projects (gonorandres.github.io)
- GMM Explorer ✓ (strongest piece)
- Monte Carlo Poker ✓
- Bayesian vs Frequentist ✓
- Credit Risk Model ✓
- Traditional actuarial notes ✓

---

## 2. Market Analysis Summary

### High-Demand Areas (2025-2026)

#### Tier 1: Highest Salary Premium
1. **Actuarial + Data Science Hybrid** — 10-15% salary premium
2. **IFRS 17 Implementation** — 28% faster career progression
3. **Catastrophe/Climate Risk Modeling** — Growing rapidly

#### Tier 2: Strong Demand
4. Capital and Risk Modeling (Solvency II style)
5. Reserving with Predictive Techniques
6. Enterprise Risk Management (ERM)

### Key Insight
> Actuaries who can code production systems AND understand actuarial theory are rare. Your CDP/GCP experience is undersold.

---

## 3. Recommended Project: Mexico Earthquake Catastrophe Model

### Why This Project

| Factor | Rationale |
|--------|-----------|
| **Differentiation** | No student-level CAT models exist for Mexico |
| **Skill Fit** | Leverages Monte Carlo, GCP, visualization |
| **Market Demand** | Climate/CAT risk is fastest growing specialty |
| **Mexico Relevance** | Earthquakes are primary peril; local expertise valued |
| **Visual Impact** | Maps + simulations = portfolio standout |
| **Complexity** | Shows depth without requiring proprietary data |

### Project Scope

#### Title
**MexQuake: Modelo Estocástico de Pérdidas por Sismo para el Valle de México**

#### Objective
Build an open-source earthquake loss estimation model for Mexico City metropolitan area using:
- Historical seismic data
- Building stock characteristics
- Probabilistic simulation
- Insurance loss calculation

### Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
├─────────────────────────────────────────────────────────────┤
│  USGS/SSN Seismic Catalog  │  INEGI Building Census         │
│  Historical earthquakes     │  Construction types            │
│  Magnitude, depth, location │  Occupancy, age, stories       │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   HAZARD MODULE                              │
├─────────────────────────────────────────────────────────────┤
│  • Seismic source zones                                      │
│  • Gutenberg-Richter frequency-magnitude relationship        │
│  • Ground Motion Prediction Equations (GMPEs)                │
│  • Site amplification (soil type from INEGI)                 │
│  Output: PGA/PGV at each location for N simulated events     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 VULNERABILITY MODULE                         │
├─────────────────────────────────────────────────────────────┤
│  • Fragility curves by construction type                     │
│  • Damage states (none, slight, moderate, extensive, complete)│
│  • Mean Damage Ratios (MDR)                                  │
│  Output: Expected damage ratio given ground motion           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  FINANCIAL MODULE                            │
├─────────────────────────────────────────────────────────────┤
│  • Replacement cost estimation                               │
│  • Insurance terms (deductible, limit, coinsurance)          │
│  • Loss calculation per event                                │
│  Output: Gross and net loss per simulated event              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT MODULE                              │
├─────────────────────────────────────────────────────────────┤
│  • Exceedance Probability (EP) curves                        │
│  • Average Annual Loss (AAL)                                 │
│  • Probable Maximum Loss (PML) at various return periods     │
│  • Loss maps by zone                                         │
│  • Sensitivity analysis                                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Sources

| Data | Source | Access |
|------|--------|--------|
| Historical earthquakes | SSN (Servicio Sismológico Nacional) | Free API |
| Building characteristics | INEGI Censo 2020 | Free download |
| Soil classification | CENAPRED / Atlas de Riesgos | Free |
| Ground motion models | OpenQuake / Literature | Open source |
| Insurance exposure (synthetic) | Generate based on CNSF aggregates | Synthetic |

### Technology Stack

```yaml
Core:
  - Python 3.11+
  - NumPy/SciPy (simulation)
  - GeoPandas (spatial)
  - OpenQuake Engine (optional, for GMPE validation)

Infrastructure:
  - BigQuery (event storage, analysis)
  - Cloud Run (API if needed)
  - GitHub Actions (CI/CD)

Visualization:
  - Next.js + React (like GMM Explorer)
  - Deck.gl or Mapbox GL (3D maps)
  - Plotly/Recharts (EP curves)

Documentation:
  - Jupyter notebooks (methodology)
  - Technical note (PDF, Spanish)
  - README (English)
```

### Deliverables

1. **Interactive Web App** — MexQuake Explorer
   - Map visualization of simulated losses
   - EP curve explorer
   - Scenario analysis (replay 1985, 2017)
   
2. **Python Package** — `mexquake`
   - Modular, documented, pip-installable
   - Example notebooks
   
3. **Technical Documentation**
   - Methodology paper (Spanish, PDF)
   - README with academic citations
   
4. **Portfolio Integration**
   - Add to gonorandres.github.io
   - LinkedIn post with key visualizations

### Project Phases

#### Phase 1: Research & Data (2 weeks)
- [ ] Literature review on CAT modeling fundamentals
- [ ] Download and clean SSN seismic catalog
- [ ] Obtain INEGI building data for CDMX
- [ ] Study existing GMPEs for Mexico (García et al., Arroyo et al.)
- [ ] Define scope boundaries (geographic, temporal)

#### Phase 2: Hazard Module (2 weeks)
- [ ] Define seismic source zones
- [ ] Fit Gutenberg-Richter parameters
- [ ] Implement GMPE calculations
- [ ] Generate stochastic event set (10,000+ years)
- [ ] Validate against historical catalog

#### Phase 3: Vulnerability Module (2 weeks)
- [ ] Research Mexican building fragility curves
- [ ] Implement damage ratio calculations
- [ ] Map INEGI construction types to vulnerability classes
- [ ] Test with known events (1985, 2017)

#### Phase 4: Financial Module (1 week)
- [ ] Define synthetic insurance portfolio
- [ ] Implement gross/net loss calculations
- [ ] Calculate AAL, EP curves, PML

#### Phase 5: Visualization & Deployment (2 weeks)
- [ ] Build Next.js frontend
- [ ] Implement interactive maps
- [ ] Deploy to Vercel
- [ ] Write documentation

#### Phase 6: Polish & Publication (1 week)
- [ ] Code review and cleanup
- [ ] Write technical note
- [ ] Update portfolio site
- [ ] Create LinkedIn content

**Total Timeline:** ~10 weeks

---

## 4. Alternative Projects

### Option B: Stochastic Reserving with ML

**Scope:** Compare traditional reserving (chain ladder, BF) with ML approaches on CNSF public data.

**Deliverables:**
- Python package for reserving methods
- Comparison study (PDF)
- Interactive dashboard

**Timeline:** 6-8 weeks

**Pros:** Directly applicable to most actuarial roles
**Cons:** Less visually impressive, more crowded space

---

### Option C: IFRS 17 Implementation Demo

**Scope:** Build simplified IFRS 17 calculation engine with CSM, risk adjustment, BBA vs PAA.

**Deliverables:**
- Python/Excel implementation
- Synthetic Mexican life portfolio
- Technical documentation (Spanish)

**Timeline:** 8-10 weeks

**Pros:** High career progression correlation, needed in Mexico soon
**Cons:** Less flashy, requires deep accounting knowledge

---

## 5. Success Metrics

| Metric | Target |
|--------|--------|
| GitHub stars | 50+ |
| Portfolio views (analytics) | 500+ monthly |
| LinkedIn engagement | 100+ reactions on launch post |
| Interview mentions | Project discussed in 3+ interviews |
| Technical depth | Passes review by working actuary |

---

## 6. Resources

### CAT Modeling Fundamentals
- [Catastrophe Modeling 101 - Neuberger Berman](https://www.nb.com/handlers/documents.ashx?id=55b7bbdd-7ae0-4540-8e9d-32f78a34ce99)
- [ASOP 38 - Catastrophe Modeling](https://www.actuarialstandardsboard.org/asops/catastrophe-modeling-practice-areas/)
- [Uses of CAT Model Output - AAA](https://www.actuary.org/sites/default/files/files/publications/Catastrophe_Modeling_Monograph_07.25.2018.pdf)

### Mexico Seismic Data
- [SSN - Servicio Sismológico Nacional](http://www.ssn.unam.mx/)
- [CENAPRED Atlas de Riesgos](http://www.atlasnacionalderiesgos.gob.mx/)
- [OpenQuake Engine](https://github.com/gem/oq-engine)

### Ground Motion Models for Mexico
- García et al. (2005) - GMPEs for Mexican subduction zone
- Arroyo et al. (2010) - Site effects in Mexico City

### IFRS 17 (if pivoting)
- [IFRS 17 Actuarial Best Practices](https://primaconsulting.org/ifrs-17-actuarial-best-practices-guide/)
- [Deloitte IFRS 17 Resources](https://www2.deloitte.com/global/en/pages/financial-services/articles/ifrs-17-insurance-contracts.html)

---

## 7. Notes & Decisions

### 2026-02-01
- Initial roadmap created
- Primary recommendation: Catastrophe Modeling (MexQuake)
- Rationale: Best fit for existing skills, highest differentiation, growing demand

### Next Actions
- [ ] Confirm project choice
- [ ] Set up project repository
- [ ] Begin Phase 1 research

---

## Appendix A: Skills Gap Analysis

| Required Skill | Current Level | Gap | How to Close |
|----------------|---------------|-----|--------------|
| Seismology basics | None | High | Literature review, OpenQuake tutorials |
| GMPEs | None | High | Study García et al., implement from scratch |
| Fragility curves | Conceptual | Medium | HAZUS documentation, academic papers |
| CAT model output (EP, AAL, PML) | Conceptual | Medium | ASOP 38, practice calculations |
| Geospatial Python | Basic | Low | GeoPandas tutorials |
| Next.js | Intermediate | None | Already proficient (GMM Explorer) |

---

## Appendix B: Comparison Matrix

| Factor | CAT Model | Reserving + ML | IFRS 17 |
|--------|-----------|----------------|---------|
| Differentiation | ★★★★★ | ★★★☆☆ | ★★★★☆ |
| Visual Impact | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| Time to Complete | 10 weeks | 6-8 weeks | 8-10 weeks |
| Skill Fit | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| Market Demand | ★★★★☆ | ★★★★☆ | ★★★★★ |
| Mexico Relevance | ★★★★★ | ★★★★☆ | ★★★★☆ |
| Learning Curve | High | Medium | High |
| **Overall Score** | **24/30** | **21/30** | **22/30** |

---

*This document serves as the master reference for portfolio enhancement decisions.*
