# 04 -- Graduation, Quadratic Minimization, and HMD Data Loading

## Actions

- Explored HMD (Human Mortality Database) structure: file formats, columns, age/year conventions
- Built `a06_mortality_data.py` -- loads HMD data for any country into aligned matrices (mx, dx, ex)
- Successfully loaded USA and Spain (Male, 1990-2023, ages 0-100) with validation passing
- Deep-dived Whittaker-Henderson graduation: why smooth, finite differences, spring-and-rod analogy
- Built finite differences intuition from scratch: first = slope, second = curvature, third = jerk
- Explored the WH objective function and its matrix form: (W + lambda*D'D)g = Wm
- Explained w_x as exposure-based weights (not a tuning parameter -- comes from data)
- Showed the smoother matrix H = (W + lambda*D'D)^{-1}W and its role as a linear filter
- Unified four methods (scalar, OLS, Ridge, WH) as the same quadratic minimization template
- Created LaTeX bridge documents for both WH graduation and quadratic minimization
- Reviewed m_x to q_x conversion under UDD: q_x = m_x / (1 + 0.5*m_x)
- Refreshed ARIMA(p,d,q) structure for k_t forecasting context

## Outputs

- `backend/engine/a06_mortality_data.py` -- HMD data loader with MortalityData class
- `docs/latex/whittaker_henderson_graduation.tex` -- Bridge doc (undergraduate, geometric focus)
- `docs/latex/whittaker_henderson_graduation.md` -- Obsidian companion
- `docs/latex/quadratic_minimization_matrix.tex` -- Bridge doc (scalar-to-matrix progression)
- `docs/latex/quadratic_minimization_matrix.md` -- Obsidian companion
- `docs/intuitive_reference/07_lee_carter_foundations_intuition.md` -- Updated with m_x, log transform, edge cases
- `docs/intuitive_reference/08_lee_carter_pipeline_estimation_intuition.md` -- a07/a08 focus
- `docs/technical/08_lee_carter_full_pipeline_reference.md` -- Complete pipeline reference
- `docs/project/03_lee_carter_deep_dive_project.md` -- Prior session log
- HMD licensing added to `.claude/CLAUDE.md`

## Chronology

* Loading HMD data and building a06_mortality_data.py
We explored the Human Mortality Database structure: three files per country (Mx_1x1, Deaths_1x1, Exposures_1x1), tab-separated with 2 header lines, columns Year/Age/Female/Male/Total. Ages run 0 to 110+ where "110+" is an open interval. We built a06_mortality_data.py following the project's existing code patterns (type hints, docstrings, Dict-based lookups). The module loads HMD files, filters by sex/year range, caps ages at 100 (aggregating 100-110+ deaths and exposure, recomputing m_x as d/L for the group), pivots from long to matrix format, and validates consistency (no NaN, no zeros, d/L matches m_x within 1%). Successfully loaded USA (1933-2023 available, subset to 1990-2023) and Spain (1908-2023, subset to 1990-2023). Both produced (101 x 34) matrices with no zeros. Spain's minimum m_x is lower than USA's (0.00004 vs 0.0001) reflecting lower child mortality. HMD licensing was added to CLAUDE.md per the CC BY 4.0 agreement. See 09_whittaker_henderson_reference.md for the graduation method that processes this data next.

* Conceptual exploration of Whittaker-Henderson graduation
We built the graduation concept from first principles. Started with why smoothing is needed (zeros crash ln(), noise corrupts SVD even without zeros). Introduced finite differences through pure numerical examples: [2,4,6,8,10,12] has constant first differences and zero second differences (straight line); [1,4,9,16,25,36] has constant second differences (parabola); [1,4,7,5,9,11] has large second differences at the dip (noise). The formula delta^2 g_x = g_{x+2} - 2g_{x+1} + g_x was derived naturally as "take differences of differences." Three physical analogies were developed: (1) spring-and-rod -- lambda is stiffness, w_x is spring strength; (2) audio filter -- graduation removes high-frequency noise; (3) nonparametric smoother -- unlike polynomial fitting, WH doesn't assume a functional form, just penalizes roughness. The difference between WH and Taylor/polynomial fitting was clarified: Taylor assumes a global formula, WH constrains local behavior without global assumptions. See 09_whittaker_henderson_reference.md.

* Quadratic minimization unification
We showed that four methods (scalar parabola, OLS, Ridge, WH graduation) follow identical steps: (1) write objective as quadratic in unknowns, (2) expand into x'Ax + b'x + constant form, (3) take gradient using d/dx(x'Ax) = 2Ax, (4) set to zero, (5) solve Ax = b. The only variation is what goes into A: scalar a, X'X for OLS, X'X + lambda*I for Ridge, W + lambda*D'D for WH. Three matrix calculus rules were shown to be scalar rules "with bold letters." The smoother matrix H = (W + lambda*D'D)^{-1}W was identified as a linear filter where each row is a weighted average centered at that age. LaTeX bridge documents were created for both WH graduation (geometric focus) and quadratic minimization (process focus). See docs/latex/ for both .tex and .md versions.

* Clarification of w_x and the objective structure
We clarified that w_x is not a tuning parameter -- it comes directly from exposure L_x in the data. Higher exposure means more reliable rates, encoded as stronger springs pulling the rod toward the data. Lambda is the only knob. The implicit formula g = (W + lambda*D'D)^{-1}Wm means each graduated value depends on ALL observed values through the matrix inverse, with nearby ages contributing most. This was connected to the concept of a smoother/hat matrix from regression theory.
