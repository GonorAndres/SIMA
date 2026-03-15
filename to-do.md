# SIMA -- Final Roadmap to Portfolio-Ready State

**Project:** Sistema Integral de Modelacion Actuarial
**Author:** Andres Gonzalez Ortega
**Created:** 2026-03-15
**Branch:** `main` (merged from 14feb on 2026-03-15)
**Live URL:** https://sima-d3qj5vwxtq-uc.a.run.app
**Tests:** 205 unit + 33 API = 238 total, all passing

---

## Summary

| Priority | Items | Est. Effort |
|----------|-------|-------------|
| P0 Critical | 7 | ~14h |
| P1 High | 10 | ~22h |
| P2 Medium | 11 | ~24h |
| P3 Nice-to-have | 6 | ~14h |
| **Total** | **34** | **~74h (~10 work sessions)** |

---

## Sprint Plan

| Sprint | Theme | Items | Est. |
|--------|-------|-------|------|
| 1 | Git hygiene + README | P0-01, P0-02, P0-03, P0-06 | 4h |
| 2 | LISF compliance view | P0-04, P0-05 | 6h |
| 3 | InsightCard + Inicio storytelling | P0-07, P1-01, P1-02 | 5h |
| 4 | Mortalidad + Tarificacion narrative | P1-03, P1-04 | 5h |
| 5 | SCR + Sensibilidad + Metodologia narrative | P1-05, P1-06, P1-07 | 6h |
| 6 | Form UX + demo tour + deploy | P1-08, P1-09, P1-10 | 5h |
| 7 | CI/CD pipelines + dev deps | P2-01, P2-02, P2-03, P2-04 | 7h |
| 8 | Portfolio alignment + screenshots | P2-05, P2-06, P2-07, P2-08 | 5h |
| 9 | Interview prep + docs update | P2-09, P2-10, P2-11 | 6h |
| 10 | Polish (a11y, perf, mobile, meta) | P3-01 to P3-06 | 6h |

---

## P0 -- Critical

Items that must be done before any external visibility (interviewers, recruiters clicking links).

---

### P0-01: Commit 14feb working tree changes -- DONE

- [x] Stage the 28 modified files (sex-differentiated pipelines, i18n, schemas, tests)
- [x] Commit with descriptive message
- [x] Verify 238 tests still pass

**Why:** 28 uncommitted files = weeks of work at risk. The sex-differentiated pipeline (male/female/unisex) is a major feature that needs to be preserved in git history.

**Effort:** S
**Files:** All 28 files in `git diff --name-only HEAD`

---

### P0-02: Merge 14feb to main -- DONE

- [x] Ensure all tests pass on 14feb
- [x] Merge 14feb into main (fast-forward)
- [x] Push main to origin
- [x] Committed `real-test/` (95-assertion QA guide is a portfolio artifact)

**Why:** GitHub visitors see `main`. A portfolio project with work stuck on a feature branch looks unfinished. The branch name `14feb` is meaningless to reviewers.

**Effort:** S
**Depends on:** P0-01

---

### P0-03: Create root README.md -- DONE

- [x] Project title + one-line description + live demo link
- [x] Architecture diagram (text-based dependency flow)
- [ ] 3-4 screenshots of the running app (deferred to P2-05)
- [x] Feature highlights: 12 engine modules, 238 tests, 22 API endpoints, sex-differentiated analysis
- [x] Tech stack: Python 3.12, FastAPI, React 19, Plotly.js, Vite, Docker, GCP Cloud Run
- [x] Quick start instructions (backend + frontend)
- [x] Docker deployment instructions
- [x] Link to Metodologia page and LaTeX documents
- [x] HMD data attribution (CC BY 4.0 required)
- [x] Author section with UNAM affiliation

**Why:** A GitHub repo without a README is invisible. This is the first thing any interviewer or recruiter sees after clicking through from the portfolio site.

**Effort:** M (1-2h)
**Depends on:** P0-02
**Files:** `README.md` (create), `docs/screenshots/` (create directory)

---

### P0-04: Add LISF/CUSF regulatory context to SCR page -- DONE

- [x] Add narrative intro section at top of SCR.tsx (LISF framework description, bilingual)
- [x] Per-module regulatory cards with CUSF references, standard shocks, descriptions
- [x] InsightCard component created (4 variants: info, insight, warning, regulatory)
- [x] Diversification insight, BEL explanation, risk margin LISF basis
- [x] Coverage and limitations disclosure section
- [x] 22 new i18n keys (ES + EN)

**Why:** CRITICAL gap. The portfolio describes "stress testing under LISF/CUSF" but the SCR page shows numbers without regulatory context. A hiring manager at a Mexican insurer needs to see regulatory awareness, not just computation ability.

**Effort:** L (4-5h)
**Files:**
- `frontend/src/pages/SCR.tsx`
- `frontend/src/pages/SCR.module.css`
- `frontend/src/components/data/RegulatoryCallout.tsx` (create)
- `frontend/src/components/data/RegulatoryCallout.module.css` (create)
- `frontend/src/i18n.ts` (~20 new keys)

---

### P0-05: Add LISF compliance endpoint to API -- DONE

- [x] GET /api/scr/compliance endpoint with 4 risk modules, CUSF references
- [x] LISFComplianceResponse schema + LISFRiskModuleInfo
- [x] get_lisf_compliance() service function with regulatory mapping
- [x] Test: test_lisf_compliance (34 API tests total now)

**Why:** Structured compliance data gives the SCR page (P0-04) concrete regulatory references to display. Also serves as interview-ready documentation.

**Effort:** M (2-3h)
**Files:**
- `backend/api/routers/scr.py`
- `backend/api/schemas/scr.py`
- `backend/api/services/scr_service.py` (create if needed)
- `backend/tests/test_api/test_scr_api.py`

---

### P0-06: Track LaTeX PDFs in git -- DONE

- [x] Update `.gitignore` to stop excluding `docs/latex/*.pdf`
- [x] Stage and commit the 6 LaTeX PDFs
- [x] Consolidated stray .tex sources into `docs/latex/` alongside PDFs

**Why:** The Metodologia page references these PDFs but they are gitignored. GitHub visitors and the deployed app cannot access them. These documents demonstrate mathematical depth -- a major portfolio differentiator.

**Effort:** S (15 min)
**Files:** `.gitignore`, 6 PDF files in `docs/latex/`

---

### P0-07: Fix portfolio site URL -- DONE

- [x] Updated URL in projects.ts (line 21 comment + line 34 url field)
- [x] Also updated tags to include React, TypeScript, SVD, Solvency II (pulled P2-06 forward)

**Why:** Broken link on the portfolio site = visitors click "Live Demo" and get nothing. The most basic portfolio failure.

**Effort:** S (15 min)
**Files:** Portfolio repo: `src/data/projects.ts`

---

## P1 -- High

Do within the first two work sessions after P0. These add the storytelling layer that transforms the app from "technical tool" to "portfolio showcase."

---

### P1-01: Create InsightCard reusable component -- DONE (created with P0-04)

- [x] InsightCard.tsx with 4 variants (info, insight, warning, regulatory)
- [x] InsightCard.module.css with variant-specific border colors and backgrounds
- [x] Already used in SCR page (6 instances) and Inicio page (1 instance)

**Why:** Every page needs contextual narrative boxes. Currently only the COVID teaser on Inicio has this pattern, hardcoded. A reusable component enables consistent storytelling without code duplication.

**Effort:** S (1h)
**Files:**
- `frontend/src/components/data/InsightCard.tsx` (create)
- `frontend/src/components/data/InsightCard.module.css` (create)

---

### P1-02: Inicio page storytelling overhaul -- DONE

- [x] InsightCard elevator pitch: 3 competencies + tech stack summary
- [x] Problem-oriented pipeline cards ("How long?", "What cost?", "Can survive?")
- [x] Skills badges row (9 technologies/frameworks)
- [x] Bilingual i18n keys (ES + EN)

**Why:** The landing page currently speaks to actuaries. The first 10 seconds must communicate: "This person built a full-stack actuarial platform with real data, proper statistical methods, and regulatory awareness."

**Effort:** M (2-3h)
**Depends on:** P1-01
**Files:** `frontend/src/pages/Inicio.tsx`, `Inicio.module.css`, `i18n.ts`

---

### P1-03: Mortalidad page narrative injection -- DONE

- [x] Graduation: "Why graduate" InsightCard (biological signal vs noise)
- [x] Surface: "What to look for" InsightCard (Gompertz, COVID anomaly)
- [x] SVD: "Model quality" InsightCard (77.7% vs Spain 94.8%)
- [x] 6 new i18n keys (ES + EN)

**Why:** Technically complete but reads like a dashboard for experts. For interviews, the narrative around numbers matters more than the numbers themselves.

**Effort:** M (2-3h)
**Depends on:** P1-01
**Files:** `frontend/src/pages/Mortalidad.tsx`, `i18n.ts`

---

### P1-04: Tarificacion page context and narrative -- DONE

- [x] Equivalence principle InsightCard
- [x] Reserve insight: why level premiums create reserves
- [x] Sensitivity: interest rate dominance and convexity
- [x] 6 new i18n keys (ES + EN)

**Why:** Without narrative, the pricing page looks like a calculator. With it, it demonstrates understanding of the actuarial equivalence principle and reserve theory.

**Effort:** M (2h)
**Depends on:** P1-01
**Files:** `frontend/src/pages/Tarificacion.tsx`, `Tarificacion.module.css`, `i18n.ts`

---

### P1-05: SCR page narrative enrichment -- DONE (completed with P0-04)

- [x] Per-module InsightCards with descriptions from compliance endpoint (dynamic, bilingual)
- [x] Diversification InsightCard explaining mortality-longevity natural hedge
- [x] BEL explanation, risk margin LISF basis
- [x] All covered by Sprint 2 compliance implementation

**Why:** The waterfall chart and solvency gauge are visually impactful but intellectually empty without narrative. The diversification insight is one of the most interview-worthy concepts.

**Effort:** M (2h)
**Depends on:** P0-04, P1-01
**Files:** `frontend/src/pages/SCR.tsx`, `i18n.ts`

---

### P1-06: Sensibilidad page narrative per tab -- DONE

- [x] Interest rate: "Key finding" -- rate dominance, 101% spread
- [x] Mortality shock: "Fundamental asymmetry" -- convexity property
- [x] Cross-country: "Competitive pressure" -- Mexico vs Spain structural gap
- [x] COVID: "Real actuarial decision" -- pre-COVID vs full trend
- [x] 8 new i18n keys (ES + EN)

**Why:** Sensibilidad is the most insight-rich page. The findings (rate dominance, asymmetry, cross-country gaps, COVID regime shift) are exactly what hiring managers want to discuss.

**Effort:** M (2h)
**Depends on:** P1-01
**Files:** `frontend/src/pages/Sensibilidad.tsx`, `i18n.ts`

---

### P1-07: Metodologia page interview narrative -- DONE

- [x] Portfolio framing InsightCard: 5 competencies demonstrated
- [x] 2 new i18n keys (ES + EN)
- [ ] Interview Questions collapsible section (deferred -- content exists in demo tour steps)

**Why:** Metodologia is where interviewers dig deep. Should also be a "here's what I know and can defend" showcase.

**Effort:** M (2h)
**Files:** `frontend/src/pages/Metodologia.tsx`, `Metodologia.module.css`, `i18n.ts`

---

### P1-08: Form field tooltips

- [ ] Create `Tooltip.tsx` component (hover/focus-triggered popover)
- [ ] Add to PremiumForm fields:
  - Product type: "Whole life pays on death at any age. Term pays only within n years. Endowment pays on death OR survival."
  - Age: "Issue age. Premiums increase steeply due to Gompertz mortality."
  - Sum assured: "Benefit amount paid to beneficiaries."
  - Interest rate: "Technical discount rate. Lower rates = higher premiums."
  - Term: "Policy duration in years. Only for term and endowment."
- [ ] Add to PolicyForm fields similarly
- [ ] Add i18n keys (ES + EN)

**Why:** Labels like "Sum Assured" and "Interest Rate" assume actuarial literacy. Tooltips make the app accessible to non-specialists while keeping the UI clean.

**Effort:** M (2-3h)
**Files:**
- `frontend/src/components/forms/Tooltip.tsx` (create)
- `frontend/src/components/forms/Tooltip.module.css` (create)
- `frontend/src/components/forms/PremiumForm.tsx`
- `frontend/src/components/forms/PolicyForm.tsx`
- `frontend/src/i18n.ts`

---

### P1-09: Demo tour narrative improvement

- [ ] Review and rewrite demo step texts in `i18n.ts` (12 steps, ES + EN)
- [ ] Rewrite step 1 to include elevator pitch framing
- [ ] Add transition phrases between steps ("Now that we see mortality improving, what does that mean for premiums?")
- [ ] Ensure demo step 8 (SCR) mentions LISF by name
- [ ] Add prominent "Start Demo" CTA on Inicio hero section
- [ ] Consider progress indicator in DemoBar

**Why:** The demo tour is the most powerful portfolio feature. A prominent start button on Inicio ensures visitors discover it.

**Effort:** M (1-2h)
**Files:** `i18n.ts`, `frontend/src/pages/Inicio.tsx`, `frontend/src/components/demo/DemoBar.tsx`

---

### P1-10: Deploy after storytelling changes

- [ ] Build frontend: `cd frontend && npm run build`
- [ ] Test locally with Docker build
- [ ] Deploy to Cloud Run
- [ ] Verify live URL reflects updated content
- [ ] Verify all 6 pages load and API endpoints respond

**Why:** Storytelling changes are useless if not deployed. The live URL is what visitors see.

**Effort:** S (1h)
**Depends on:** P1-02 through P1-09

---

## P2 -- Medium

Complete within a week after P1. Infrastructure, documentation, and alignment tasks.

---

### P2-01: GitHub Actions CI pipeline

- [ ] Create `.github/workflows/ci.yml`:
  - Trigger on push to main and PRs
  - Python 3.12, install requirements
  - Run `pytest backend/tests/ -v`
  - Frontend: `npm ci && npm run build`
- [ ] Add test badge to README.md

**Why:** A portfolio project without CI suggests the candidate doesn't practice CI/CD. The badge on README is immediate credibility.

**Effort:** M (1-2h)
**Files:** `.github/workflows/ci.yml` (create), `README.md`

---

### P2-02: GitHub Actions CD pipeline (Cloud Run auto-deploy)

- [ ] Create `.github/workflows/deploy.yml`:
  - Trigger on push to main (or manual dispatch)
  - Build Docker image, push to Artifact Registry, deploy to Cloud Run
- [ ] Requires GCP service account key as GitHub secret

**Why:** Auto-deploy on merge = production-level workflow. Shows DevOps awareness.

**Effort:** L (3-4h)
**Depends on:** P2-01
**Files:** `.github/workflows/deploy.yml` (create)

---

### P2-03: Add httpx to requirements.txt

- [ ] API tests use `TestClient` which requires `httpx`
- [ ] Currently works in venv but not declared
- [ ] Verify Docker build still works

**Why:** CI pipeline will fail without it. Clean dependency declaration.

**Effort:** S (15 min)
**Files:** `requirements.txt`

---

### P2-04: Create requirements-dev.txt

- [ ] Include pytest, httpx, and any other dev-only dependencies
- [ ] Update CI workflow to install from dev requirements

**Why:** Separating prod and dev deps is basic engineering hygiene.

**Effort:** S (30 min)
**Files:** `requirements-dev.txt` (create), `.github/workflows/ci.yml`

---

### P2-05: Take screenshots for README and portfolio

- [ ] Capture 4-5 screenshots of running app:
  1. Inicio hero with stats sidebar
  2. Mortalidad graduation + Lee-Carter parameters
  3. Tarificacion premium form + results
  4. SCR waterfall chart + solvency gauge
  5. Sensibilidad cross-country comparison
- [ ] Store in `docs/screenshots/`
- [ ] Reference in README.md
- [ ] Optionally update portfolio site with screenshots

**Why:** Screenshots in a README are worth a thousand lines of description. They convert "I'll look later" into "I want to learn more."

**Effort:** S (1h)
**Depends on:** P1-10 (screenshot after storytelling changes are deployed)
**Files:** `docs/screenshots/` (create + images), `README.md`

---

### P2-06: Fix portfolio site description alignment

- [ ] Update SIMA description in portfolio `projects.ts`:
  - Add "sex-differentiated mortality analysis (male/female/unisex)"
  - Change "commutation tables" to "commutation functions for premium calculation"
  - Mention "Lee-Carter with SVD" not just "Lee-Carter"
- [ ] Update tags to include: React, TypeScript, Plotly, Solvency II
- [ ] Update screenshot path if new screenshots available

**Why:** Portfolio description should match actual app experience. "Commutation tables" implies visible tables; the app shows premium calculations.

**Effort:** S (30 min)
**Files:** Portfolio repo: `src/data/projects.ts`

---

### P2-07: Serve LaTeX PDFs from frontend

- [ ] Metodologia references `docs/latex/*.pdf` but they aren't served by the web app
- [ ] Option A: Copy PDFs to `frontend/public/docs/` (simplest)
- [ ] Option B: Add API endpoint to serve from `docs/latex/`
- [ ] Update Metodologia resourceCards with working download links
- [ ] Test that clicking a resource card downloads the PDF

**Why:** Metodologia lists 6 LaTeX documents but none are downloadable. Broken promise to visitors.

**Effort:** M (1-2h)
**Depends on:** P0-06
**Files:** `frontend/src/pages/Metodologia.tsx`, `frontend/public/docs/` or `backend/api/main.py`

---

### P2-08: Add data source indicator to frontend

- [ ] API already has `get_data_source()` returning "real" or "mock"
- [ ] Add subtle indicator in Footer or TopNav:
  - Real data: "INEGI/CONAPO (1990-2019)"
  - Mock data: "Synthetic demo data"

**Why:** Transparency prevents awkward interview moments. If an interviewer asks "is this real data?" the app itself should answer.

**Effort:** S (1h)
**Files:** `frontend/src/components/layout/Footer.tsx`, possibly `hooks/useApi.ts`

---

### P2-09: Commit real-test/ manual test guide

- [ ] Decide: track `real-test/manual_test_guide.md` or gitignore it
- [ ] Recommendation: commit it -- 95 manual assertions show QA rigor
- [ ] Reference in README under "Testing" section

**Why:** An untracked directory looks like forgotten debris. The QA guide is a portfolio artifact worth showing.

**Effort:** S (15 min)
**Files:** `real-test/manual_test_guide.md`, `.gitignore`, `README.md`

---

### P2-10: Interview preparation cheat sheet

- [ ] Create `docs/project/13_interview_preparation.md` with:
  - Top 20 interview questions about SIMA
  - Key numbers to memorize (explained variance, drift, SCR, diversification benefit)
  - Common "gotcha" questions and answers
  - Architecture decisions and tradeoffs
  - "What would you do differently?" prepared answers
- [ ] Organize by topic: mortality, pricing, SCR, architecture, data

**Why:** The ultimate purpose of the project. A prep doc means practicing before interviews instead of recalling months-old details.

**Effort:** M (2-3h)
**Files:** `docs/project/13_interview_preparation.md` (create)

---

### P2-11: Update CLAUDE.md with final project state

- [ ] Update "Project Status" section:
  - 238 tests (205 unit + 33 API)
  - Sex-differentiated pipelines
  - LaTeX PDFs tracked
  - README, CI/CD, LISF compliance endpoint
  - Updated endpoint count (22+)
- [ ] Update API Endpoints table
- [ ] Update Key Files Structure if new files created

**Why:** CLAUDE.md is the instruction manual for future sessions. Stale docs = wrong assumptions.

**Effort:** S (30 min)
**Files:** `.claude/CLAUDE.md`

---

## P3 -- Nice-to-Have

Do if time permits, in any order. Each independently valuable.

---

### P3-01: Accessibility audit

- [ ] Add `aria-label` to all interactive elements
- [ ] Check color contrast (Swiss red #C41E3A on white -> WCAG AA)
- [ ] Keyboard navigation for tab panels
- [ ] Per-page `<title>` tags

**Why:** Accessibility demonstrates professional frontend practice.

**Effort:** M (2h)

---

### P3-02: Lazy load heavy page sections

- [ ] Mortalidad makes 7 API calls on mount -- lazy-load below-fold sections
- [ ] Sensibilidad fetches cross-country/COVID even when those tabs inactive -- move to `onClick`
- [ ] Add skeleton loading states

**Why:** Faster initial load improves demo experience. 2-3s delay on first visit loses attention.

**Effort:** M (2-3h)
**Files:** `Mortalidad.tsx`, `Sensibilidad.tsx`

---

### P3-03: Mobile responsive polish

- [ ] Test all 6 pages at 375px (iPhone SE)
- [ ] 3D surface and heatmap need mobile fallbacks
- [ ] DataTable horizontal scroll
- [ ] TopNav hamburger menu for mobile
- [ ] Form layout on narrow screens

**Why:** If a recruiter opens the link on their phone during a coffee break, it should not look broken.

**Effort:** L (3-4h)

---

### P3-04: OpenGraph meta tags for link previews

- [ ] Add to `frontend/index.html`:
  - `og:title`: "SIMA -- Actuarial Modeling Platform"
  - `og:description`: "Lee-Carter mortality, premium pricing, SCR under Mexican regulation"
  - `og:image`: Screenshot from P2-05
  - `og:url`: Live Cloud Run URL

**Why:** When a recruiter pastes the SIMA link into Slack or LinkedIn, the preview card determines whether anyone clicks.

**Effort:** S (30 min)
**Depends on:** P2-05
**Files:** `frontend/index.html`

---

### P3-05: Error state polish

- [ ] Create `ErrorState` component with retry button + user-friendly message
- [ ] Handle: data not loaded, network error, server timeout
- [ ] Fallback message when running without real data

**Why:** Clean error handling = production-quality thinking. If the app errors during a demo, recovery matters.

**Effort:** M (1-2h)
**Files:** `frontend/src/components/common/ErrorState.tsx` (create), various page files

---

### P3-06: Enhanced guided tour overlay

- [ ] Semi-transparent overlay highlighting current section during demo
- [ ] Animate highlight box transitions
- [ ] "What to look for" subtitle in DemoBar per step
- [ ] Make DemoBar sticky at bottom, not overlapping content

**Why:** A polished guided tour is the strongest possible portfolio demo format.

**Effort:** L (3-4h)
**Files:** `DemoBar.tsx`, `DemoBar.module.css`, `DemoContext.tsx`

---

## Dependency Graph

```
P0-01 (commit) --> P0-02 (merge) --> P0-03 (README)
                                 \-> P2-01 (CI) --> P2-02 (CD)
                                 \-> P2-04 (dev deps)

P0-04 (LISF frontend) <-- P0-05 (LISF endpoint, can be parallel)
P0-06 (track PDFs) --> P2-07 (serve PDFs)

P1-01 (InsightCard) --> P1-02 (Inicio narrative)
                    \-> P1-03 (Mortalidad narrative)
                    \-> P1-04 (Tarificacion narrative)
                    \-> P1-05 (SCR narrative, also needs P0-04)
                    \-> P1-06 (Sensibilidad narrative)

P1-02..P1-09 --> P1-10 (deploy) --> P2-05 (screenshots)
P2-05 (screenshots) --> P3-04 (og:image)
```

---

## Done Criteria

The project is portfolio-ready when ALL of the following are true:

1. [ ] `main` branch is clean -- no uncommitted changes, no stale feature branches
2. [ ] Root `README.md` exists with screenshots, live demo link, architecture overview
3. [ ] Live URL works and matches README
4. [ ] Portfolio site URL points to correct Cloud Run deployment
5. [ ] Every page has at least one narrative element explaining what the visitor sees
6. [ ] SCR page explicitly references LISF/CUSF regulation with article numbers
7. [ ] LaTeX PDFs are downloadable from the web app
8. [ ] CI pipeline runs on push and reports green
9. [ ] Demo tour completes start-to-finish without confusion
10. [ ] A 5-minute live walkthrough can be delivered confidently in an interview
