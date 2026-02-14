# Lee-Carter Phase 1 Implementation -- Session Report

**Date:** 2026-02-07
**Branch:** `7feb`
**Tests before:** 38 | **Tests after:** 106 (68 new)

---

## Actions

- Created virtual environment and `requirements.txt` (added `scipy`)
- Wrote 15 tests for existing `a06_mortality_data.py` (zero tests -> full coverage)
- Implemented `a07_graduation.py` -- Whittaker-Henderson smoothing via sparse linear algebra
- Wrote 13 tests for `a07_graduation.py`
- Implemented `a08_lee_carter.py` -- SVD decomposition with k_t re-estimation via Brent's method
- Wrote 20 tests for `a08_lee_carter.py` (including synthetic data recovery)
- Implemented `a09_projection.py` -- RWD projection with stochastic simulation and LifeTable bridge
- Wrote 17 tests for `a09_projection.py` (including end-to-end premium calculation)
- Wrote 3 integration tests proving the full pipeline: HMD -> Graduate -> Lee-Carter -> Project -> LifeTable -> Premium
- Updated `backend/engine/__init__.py` to export all 4 new classes

## Outputs

| Artifact | Type | Tests |
|:---------|:-----|------:|
| `backend/engine/a07_graduation.py` | New module | 13 |
| `backend/engine/a08_lee_carter.py` | New module | 20 |
| `backend/engine/a09_projection.py` | New module | 17 |
| `backend/tests/test_mortality_data.py` | New test file | 15 |
| `backend/tests/test_graduation.py` | New test file | 13 |
| `backend/tests/test_lee_carter.py` | New test file | 20 |
| `backend/tests/test_projection.py` | New test file | 17 |
| `backend/tests/test_integration_lee_carter.py` | New test file | 3 |
| `backend/engine/__init__.py` | Modified | -- |
| `requirements.txt` | New file | -- |

---

## Chronology

* **Testing the foundation (a06_mortality_data)**
We started by writing tests for the existing `a06_mortality_data.py` which had zero tests despite being the data input contract for the entire Lee-Carter pipeline. Every new module depends on the shape, content, and behavior of its matrices. We validated matrix dimensions (101 ages x 31 years for the USA 1990-2020 window), confirmed no NaN values, verified all death rates are positive (critical because Lee-Carter takes logarithms), and checked that `m_x ≈ d_x / L_x` within 1% tolerance. We also tested the age capping logic which aggregates ages above `age_max` into a single group using exposure-weighted rates (not naive averaging). All 15 tests passed immediately, confirming the foundation was solid. For detailed look see `10_lee_carter_implementation_reference.md`.

* **Implementing Whittaker-Henderson graduation (a07)**
We built the `GraduatedRates` class to smooth raw mortality rates before Lee-Carter fitting. The core algorithm solves a penalized least squares problem in log-space: `z = (W + lambda * D'D)^{-1} * W * m`, where `W` is a diagonal weight matrix (exposure-weighted), `D` is a sparse second-order difference matrix, and `lambda` controls the smoothness-fidelity tradeoff. We used `scipy.sparse` for efficient matrix construction and `spsolve` for the linear system. Working in log-space guarantees positivity of graduated rates via exponentiation. The 13 tests verified: correct difference matrix construction (shape and values), smoothing reduces roughness, lambda=0 recovers raw data, large lambda gives smoother output, residual mean near zero, and the `from_hmd` convenience method. For detailed look see `10_lee_carter_implementation_reference.md`.

* **Implementing Lee-Carter model fitting (a08)**
We built the `LeeCarter` class implementing the full Lee-Carter (1992) fitting procedure: (1) compute `a_x` as row means of the log-rate matrix, (2) SVD the residual matrix to extract the first component, (3) apply identifiability constraints (`sum(b_x)=1`, `sum(k_t)=0`), and (4) re-estimate `k_t` using Brent's root-finding method to match observed total deaths per year. The re-estimation step is critical because SVD minimizes error in log-space, but actuarial applications need accurate death counts. We also handled the sign convention (b_x should be mostly positive) and provided both `fit()` and `fit_from_hmd()` convenience methods. The 20 tests verified: a_x equals exact row means, both identifiability constraints hold to 1e-6 precision, explained variance exceeds 70% for USA data, k_t is generally decreasing (mortality improving), re-estimated k_t reproduces observed deaths within 0.1%, synthetic data with known parameters is recovered, and USA vs Spain produce distinct parameters. For detailed look see `10_lee_carter_implementation_reference.md`.

* **Implementing mortality projection (a09)**
We built the `MortalityProjection` class that projects `k_t` forward using a Random Walk with Drift, generates stochastic simulation paths, and provides the crucial `to_life_table()` bridge method. The drift is estimated as the average annual change in k_t, sigma as the standard deviation of innovations. The bridge converts `m_x -> q_x` via the exact relationship `q_x = 1 - exp(-m_x)` (constant force assumption), builds `l_x`, and returns a `LifeTable` object that plugs directly into the Phase 2 engine (a02-a05). The 17 tests verified: drift computation for linear k_t, central projection extends trend, stochastic simulations average near central, CI bands widen with horizon, reproducibility with fixed seed, projected LifeTable passes all validations, and the full integration from projection through to premium calculation. For detailed look see `10_lee_carter_implementation_reference.md`.

* **Integration testing**
We wrote 3 integration tests that prove the full pipeline from raw HMD data to actuarially meaningful premiums. The key test `test_mortality_improvement_lowers_premiums` verifies that projecting further into the future (more mortality improvement) produces lower death insurance premiums -- a fundamental sanity check that validates the entire chain of computations. The Spain pipeline test confirms the code generalizes beyond USA data.

* **Architectural decision: dual interface**
A deliberate design choice was to give `GraduatedRates` the same attribute interface as `MortalityData` (`.mx`, `.dx`, `.ex`, `.ages`, `.years`). This means `LeeCarter.fit()` accepts either raw or graduated data without type-checking -- a form of structural subtyping (duck typing) that keeps the code simple while allowing the user to decide whether graduation is appropriate for their data.
