# 03 -- Lee-Carter Deep Dive: Full Conceptual Foundation

## Actions

- Explored m_x definition, units (deaths/person-year), and why it's the modeling primitive over q_x
- Clarified person-years as the exposure unit with worked examples (partial contributions from deaths)
- Walked through edge case: m_x > 1 (sub-annual observation, 20 deaths from 100 people in 1 month)
- Traced the transformation chain: ln(m_x) -> m_x -> q_x with range guarantees at each step
- Built complete SVD walkthrough with 3-age, 4-year numerical example (ages 40/50/60, years 2010-2013)
- Showed extraction of b_x and k_t from first singular triplet
- Covered identifiability constraints: scale (SUM b_x = 1) and location (SUM k_t = 0) with proofs
- Explained k_t re-estimation via Newton-Raphson to match observed death counts
- Covered k_t forecasting with ARIMA(0,1,0) + drift (random walk with drift)
- Refreshed ARIMA(p,d,q) general structure
- Defined data requirements: d_{x,t} and L_{x,t} from INEGI/CONAPO
- Created LaTeX bridge document (graduate level) on SVD, bilinear forms, identifiability
- Updated intuitive docs for Lee-Carter foundations (07)

## Outputs

- `docs/latex/svd_bilinear_identifiability_lee_carter.tex` -- Graduate-level bridge document
- `docs/latex/svd_bilinear_identifiability_lee_carter.md` -- Obsidian-compatible version
- `docs/intuitive_reference/07_lee_carter_foundations_intuition.md` -- Intuitive reference (m_x, log transform, SVD extraction, constraints, edge cases)
- `docs/project/03_lee_carter_deep_dive_project.md` -- This session log
- `docs/technical/08_lee_carter_full_pipeline_reference.md` -- Full pipeline reference
- `docs/intuitive_reference/08_lee_carter_pipeline_estimation_intuition.md` -- Pipeline intuition with a07/a08 focus

## Chronology

* Conceptual exploration of m_x and its role
We began by establishing why Lee-Carter models m_x (central death rate) rather than q_x (probability). m_x = d_{x,t} / L_{x,t} is the directly observable quantity from death certificates and census data. q_x requires an additional distributional assumption (UDD or constant force). We explored the units (deaths per person-year), typical ranges for Mexico (0.0002 at childhood to 0.4 at extreme old age), and the edge case where m_x exceeds 1 (sub-annual observation of 100 people, 20 deaths in one month, yielding m = 2.667). The conversion q_x = 1 - exp(-m_x) guarantees valid probabilities for any positive m_x. For detailed formulas see 08_lee_carter_full_pipeline_reference.md.

* SVD walkthrough and parameter extraction
We constructed a 3x4 numerical example (ages 40/50/60, years 2010-2013) and traced every step: log transform, row centering to get a_x, SVD on residuals, extraction of b_x from first left singular vector and k_t from sigma_1 * first right singular vector. Sigma_1 = 0.358 vs sigma_2 = 0.006 demonstrated the one-factor dominance (99.9% variance explained). We clarified that SVD produces ALL singular values but Lee-Carter CHOOSES to retain only the first -- a rank-1 approximation, not an equality. For the SVD process itself: build Z'Z, eigendecompose, sqrt for sigmas, multiply back for u's. For formal treatment see `docs/latex/svd_bilinear_identifiability_lee_carter.tex`.

* Identifiability constraints
We proved the two-dimensional equivalence class: scale indeterminacy (multiply b by c, divide k by c) and location indeterminacy (shift constant between a_x and k_t). Two constraints needed: SUM b_x = 1 (fixes scale, b_x become proportions) and SUM k_t = 0 (fixes location, a_x becomes true time-average). Implementation: divide b_x by their sum, multiply k_t by same sum, then recenter k_t and absorb shift into a_x. See 08_lee_carter_full_pipeline_reference.md.

* k_t re-estimation
SVD minimizes error on log-rates (all cells equal weight). But actuarially, death counts matter -- a 1% error at age 60 with millions exposed matters more than 10% at age 105 with hundreds. Newton-Raphson adjusts k_t for each year independently so that SUM_x d_{x,t} = SUM_x L_{x,t} * exp(a_x + b_x * k_t). This requires death counts and exposure separately, not just their ratio. Convergence is fast (3-5 iterations) because the objective is convex in k_t.

* k_t forecasting and ARIMA refresher
Lee-Carter uses ARIMA(0,1,0) with drift: k_{t+1} = k_t + delta + epsilon. Delta = average annual change (negative = improving mortality). Variance grows linearly with horizon h, giving confidence bands proportional to sqrt(h). We refreshed ARIMA(p,d,q): p = autoregressive lags, d = differencing order, q = moving average shocks. Lee-Carter's choice is the simplest non-trivial model, empirically validated against more complex alternatives.

* Data requirements and next steps
Lee-Carter needs d_{x,t} (death counts) and L_{x,t} (mid-year population) by single age and year. For Mexico: INEGI provides deaths, CONAPO provides population estimates. Target matrix: ages 0-100 (capped), 20-30 years of data. Decision: use HMD (Human Mortality Database) data for implementation and validation, single-year ages capped at 100. Implementation will follow: a06 (data loading) -> a07 (graduation/smoothing) -> a08 (Lee-Carter estimation) -> a09 (forecasting).
