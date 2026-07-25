# SIMA Backend Robustness Plan — `25julio`

**Date:** 2026-07-25  
**Target branch:** `25julio`  
**Status:** In progress  
**Author:** OpenCode audit session

## Progress Log

- **Phase 1 — Engine validation layer (a01–a05, exceptions, validators):** ✅ done (`4ee7b02`).
- **Phase 5.1 — pyproject.toml + ruff + strict mypy on core 7 files; ActuarialValidationError→422:** ✅ done (`954c68b`).
- **Phase 2 — Portfolio & SCR correctness (a11, a12):** ✅ done — Policy/Portfolio boundary validation, no-op expense/lapse/commission hooks, expired-term skip + `t_p_x` survival in catastrophe SCR, portfolio-specific risk-margin duration (replaces hardcoded 15), configurable IR floor with warning, `LIFE_CORR` PSD validation (import + custom), Lee-Carter shock calibration (`calibrate_shocks_from_lee_carter`), 20 new Phase-2 tests. a11/a12 added to strict mypy `files`.
- **Phase 5.2 — CI fixes:** ✅ done — rewrote `.github/workflows/ci.yml` into 4 jobs (backend-lint, backend-typecheck, backend-tests with coverage ≥80%, frontend lint+tsc+build); removed duplicate `pytest backend/tests/test_api/` line; added pip/npm caching and concurrency cancellation; added `ruff`, `mypy`, `pytest-cov` to `requirements-dev.txt`; updated `.dockerignore` to exclude `backend/analysis/` and `backend/tests_proposed/`.
- **Phase 4 — API hardening:** ✅ done — Pydantic cross-field validators (`PolicyCreate`, `PremiumRequest`, `ReserveRequest`, `SCRRequest` shock-consistency); removed unused `LeeCarterFitRequest` / `ProjectionRequest` schemas; centralized exception handling in `backend/api/exception_handlers.py` (`safe_route` decorator mapping `ActuarialValidationError`/`DataQualityError`→422, `DataNotAvailableError`/`FileNotFoundError`→503, `ValueError`/`KeyError`→400, others→500 with `logger.exception`); added global FastAPI handlers for the same set in `main.py`; request-logging/timing middleware; audit-grade INFO logs on every SCR/BEL computation (rate, shocks, sex, portfolio size, capital, LC-calibration flag); `RLock`-guarded global portfolio with duplicate-`policy_id` check at add time; API docs note about shared demo portfolio. 16 new Phase-4 tests (400/422, 503 path, concurrency smoke, audit-log assertions). mypy strict on the new `exception_handlers` module.
- **Next:** Phase 3 — Data pipeline robustness (a06–a10) OR Phase 6 — Documentation.

---

## Context

The `25julio` branch now contains the latest local work plus the latest `origin/main` fixes (Artifact Registry + PostHog routing). Before it is merged into `main`, the backend needs to move from a well-documented prototype to a robust, regulator-auditable actuarial engine.

Three read-only audits were completed on this branch:

- Backend engine audit (modules `a01`–`a12`)
- API & tests audit
- Documentation & structure audit

The full findings are summarized here. This document is the canonical implementation plan for the next development sessions.

---

## Goal

Make the SIMA backend **actuarially robust and production-ready** while preserving the existing engine pipeline and API contract wherever possible.

Key outcomes:

1. Strict, domain-aware input validation at every engine boundary.
2. Clear, actuarial error semantics (no raw `KeyError` leaking to users).
3. Numerically safe implementations (extreme ages, `i=0`, terminal age, expired policies).
4. Correct SCR/portfolio logic (no double-counting, portfolio-specific risk margin).
5. Stronger test coverage at unit, API, and CI levels.
6. Up-to-date documentation of assumptions, limitations, and regulatory mapping.

---

## Phase 1 — Engine Validation Layer (Highest ROI)

### 1.1 New files

- `backend/engine/exceptions.py`  
  Central `ActuarialValidationError` with structured fields:
  - `field` (optional): the input that failed
  - `constraint`: human-readable rule that was violated
  - `message`: user-facing message

- `backend/engine/validators.py`  
  Reusable domain validators:
  - `validate_consecutive_ages(ages)`
  - `validate_lx_monotonic(l_x)`
  - `validate_probabilities(q_x)`
  - `validate_age_in_table(age, min_age, max_age)`
  - `validate_term_bounds(n, t, product_type)`
  - `validate_non_negative_amount(value, name)`

### 1.2 Harden `a01_life_table.py`

- Validate that `ages` are consecutive and sorted in `__init__`.
- Validate that `l_x` is non-negative and monotonic non-increasing.
- Replace `KeyError` in `get_*` methods with `ActuarialValidationError`.
- Fix `from_regulatory_table` fragile exact float comparison (`float(row[col]) == float(row[other_col])`). Use a small tolerance or compare raw strings.
- Ensure `validate()` returns deterministic tolerance-based checks.

### 1.3 Harden `a02_commutation.py`

- Handle `interest_rate == 0` explicitly (use undiscounted sums instead of `v=1`).
- Validate the life table is non-empty.
- Allow `interest_rate > 1` with a warning rather than a hard error, or make the bound configurable.
- Document why `D_x` is normalized by `min_age`.

### 1.4 Harden `a03_actuarial_values.py`

- Validate `x`, `n`, `t` against life table bounds.
- Validate `n >= 0` and `t <= n` for temporary products.
- Clamp/warn when `a_immediate` becomes negative at very old ages.

### 1.5 Harden `a04_premiums.py`

- Validate `SA >= 0`, `n >= 0`, issue age within table bounds.
- Make `verify_equivalence` tolerance relative to `SA` or configurable.
- Expand `single_premium()` to all supported products, or document why it is limited.
- Add explicit handling for limited-pay whole life beyond omega.

### 1.6 Harden `a05_reserves.py`

- Validate `t <= n` for term/endowment; return `0` with a warning for expired policies.
- Include `pure_endowment` in `validate_zero_reserve`.
- Make `reserve_trajectory` tolerance relative to the sum assured.
- Add explicit handling for `matured` endowment policies.

### 1.7 Tests

- Add error-case tests for each invalid input.
- Add golden-value tests for edge cases:
  - `i = 0`
  - terminal age `omega`
  - expired term policy
  - single-premium equivalence

---

## Phase 2 — Portfolio & SCR Correctness

### 2.1 Harden `a11_portfolio.py`

- `Policy` validation:
  - `attained_age <= max_age` of the life table
  - `duration <= n` for term/endowment (or mark as expired)
  - `SA >= 0`, `annual_pension >= 0`
  - unique `policy_id` within a portfolio
- `Portfolio` validation:
  - no duplicate `policy_id`s
  - at least one policy if a BEL/SCR computation is requested
- Optimize `compute_bel`, `compute_bel_breakdown`, `compute_bel_by_type` to reuse a single `CommutationFunctions` instance.
- Add optional hooks for `expense_loading`, `lapse_rate`, and `commission` as no-op defaults (to enable future gross-premium work without breaking the API).

### 2.2 Fix `a12_scr.py`

- **Catastrophe risk:**
  - Skip expired term policies (`duration >= n`).
  - For active policies, multiply `extra_claim` by `t_p_x` (probability of survival to the start of the shock year) instead of assuming the policy is in-force with certainty.
  - Document the one-year shock convention clearly.

- **Risk margin:**
  - Replace hardcoded `portfolio_duration = 15` with a portfolio-specific weighted average remaining duration.
  - For each policy, compute a remaining horizon (term for term/endowment, life expectancy for whole life/annuity).
  - Add a helper `portfolio_remaining_duration(portfolio, life_table, interest_rate)`.
  - Keep the simple constant-SCR approximation, but make the duration realistic.

- **Interest rate shock:**
  - Make the `0.5%` floor configurable.
  - Log a warning when the floor is applied.
  - Document the choice.

- **Correlation matrix:**
  - Validate `LIFE_CORR` is positive semi-definite on import.
  - Raise a clear error if a custom matrix is not PSD.

- **Shock documentation:**
  - Document that default shocks (`+15%` mortality, `-20%` longevity, `±100` bps, `+35%` catastrophe) are Solvency II illustrative standard values unless calibrated from the Lee-Carter volatility.

### 2.3 Tests

- Regression test that `sex=female` produces materially different BEL/SCR than `sex=male`.
- Test that expired term policies contribute zero to catastrophe SCR.
- Test that risk margin increases with portfolio duration.
- Test that invalid correlation matrices raise a domain error.

---

## Phase 3 — Data Pipeline Robustness

### 3.1 New files

- `backend/engine/data_validation.py`  
  Schema validators for HMD/INEGI/CONAPO loaders:
  - required columns
  - expected age/year formats
  - missing-value detection
  - `mx ≈ dx/ex` tolerance check

### 3.2 Harden `a06_mortality_data.py`

- Validate expected filenames and `skiprows` against a versioned schema.
- Produce a structured `DataQualityReport` object when loading.
- Add optional missing-value imputation strategy (or fail with a detailed report).
- Add explicit handling for open-age groups (`110+`).

### 3.3 Harden `a07_graduation.py`

- Validate `lambda_param > 0` to avoid singular matrices.
- Add a post-graduation monotonicity check (mortality should be broadly increasing by age).
- Make `residual_mean_near_zero` threshold configurable.
- Return a warning if the Whittaker-Henderson system is ill-conditioned.

### 3.4 Harden `a08_lee_carter.py`

- Validate `brentq` bracket adaptively or switch to a bounded search with fallback.
- Make `explained_variance` threshold configurable.
- Fix lazy import annotation to be consistent.

### 3.5 Harden `a09_projection.py`

- Validate `horizon > 0` and `n_simulations` within a reasonable bound.
- Add bounds checking for `np.searchsorted` calls.
- Validate `age_min`/`age_max` produce a non-empty range.

### 3.6 Harden `a10_validation.py`

- Handle `NaN` in `summary()` when `reg_qx = 0`.
- Add weighted RMSE and bias statistics.
- Make the default comparison age range configurable.

### 3.7 Tests

- Loader tests with malformed/mock files.
- Graduation monotonicity test for pathological lambda.
- Projection bounds tests.

---

## Phase 4 — API Hardening

### 4.1 Pydantic schema improvements

- `PolicyCreate`:
  - Add conditional validator: `term` required when `product_type` is `term` or `endowment`.
  - `sum_assured` must be `> 0` for death products.
  - `annual_pension` must be `> 0` for annuities.
  - `duration` must be `<= term` for term/endowment.

- `SCRRequest`:
  - Add `sex` validation to match supported regulatory tables.
  - Add `model_validator` for shock consistency.

- Remove or wire unused request schemas (`LeeCarterFitRequest`, `ProjectionRequest`, etc.).
- Consolidate duplicate `cross-country` endpoints or rename to remove ambiguity.

### 4.2 Exception handling

- Add a FastAPI exception handler for `ActuarialValidationError` → `422`.
- Add a handler for `FileNotFoundError` from data loaders → `503` with a clear message.
- Replace bare `except Exception` in routers with specific catches and `logger.exception`.
- Return sanitized error messages; never expose internal stack traces in production.

### 4.3 Observability

- Add request-logging/timing middleware.
- Log all SCR/BEL computations with key inputs (rate, shocks, sex, portfolio size) for auditability.

### 4.4 State (global portfolio)

- For this phase, keep the module-level portfolio but add a thread lock around mutations.
- Add a clear warning in the API docs that the demo portfolio is shared across requests.
- Leave per-user/session portfolio storage as a future Phase 7.

### 4.5 Tests

- API 400/422 tests for invalid payloads.
- API golden-value tests for a known mini-table.
- Concurrency smoke test for the global portfolio.

---

## Phase 5 — Tooling & CI

### 5.1 Python project metadata

- Add `pyproject.toml` with:
  - `[tool.pytest.ini_options]` default paths
  - `[tool.ruff]` lint/format rules
  - `[tool.mypy]` strict-but-pragmatic settings
  - `[project]` name/version (optional)

### 5.2 CI fixes

- Run backend tests once (remove the duplicate `pytest backend/tests/test_api/` line).
- Add backend lint and type-check jobs.
- Add frontend lint job.
- Add a coverage threshold job.
- Decide whether to run `backend/tests_proposed/` in CI or delete it.

### 5.3 Docker

- Update `.dockerignore` to exclude `backend/tests_proposed/` and `backend/analysis/`.

### 5.4 Tests

- Add property-based tests (e.g., with Hypothesis) for actuarial invariants:
  - premiums increase with age
  - reserves are non-negative for standard products
  - BEL increases when interest rates decrease

---

## Phase 6 — Documentation

### 6.1 Spec & docs

- Update `SIMA-PROJECT-SPEC.md`:
  - mark implemented phases complete
  - update file structure and test counts
  - update tech stack
- Add `backend/VALIDATION.md` documenting every validation rule and its actuarial rationale.
- Update `docs/technical/18_capital_requirements_reference.md` with SCR limitations and calibration notes.
- Fix endpoint-count inconsistency (README says 23, docs say 22, actual is 24).
- Add `frontend/README.md` project-specific quick-start.
- Add missing download guides for HMD/INEGI/CONAPO, or remove references if data is not included.

### 6.2 `AGENTS.md`

- Keep `AGENTS.md` pointing to this plan so future sessions can resume from the same state.

---

## Suggested Execution Order

1. **Phase 1** — Engine validation layer (biggest safety improvement).
2. **Phase 2** — Portfolio & SCR correctness (fixes real actuarial bugs).
3. **Phase 5** — Tooling & CI (so later code is linted and type-checked).
4. **Phase 4** — API hardening (wire engine validators into the API).
5. **Phase 3** — Data pipeline robustness (lower priority, mostly affects real-data runs).
6. **Phase 6** — Documentation (last, once behavior is stable).

---

## Open Decisions

Answer these before starting implementation:

1. **API contract:** Can validation become stricter (e.g., require `term` for term/endowment, reject `sum_assured=0`), or must requests stay backward-compatible?
2. **SCR scope:** Fix obvious bugs only (catastrophe double-counting, portfolio-specific risk margin), or also calibrate shocks from the Lee-Carter volatility?
3. **Expenses/lapses:** Keep net-premium only, or add optional expense/lapse assumptions?
4. **Tooling:** Add `pyproject.toml` + `ruff` + `mypy`, even if it surfaces many existing type issues?
5. **tests_proposed:** Merge into `backend/tests/`, or delete from this branch?

---

## How to Resume This Plan

1. Read this file: `docs/plan-25julio.md`.
2. Ensure you are on branch `25julio` and `git status` is clean.
3. Run the test suite to establish a baseline:
   ```bash
   pytest backend/tests/
   ```
4. Start with the next unfinished phase.
5. Commit each phase separately with a clear message:
   ```
   feat(engine): add validation layer and harden a01-a05
   fix(scr): correct catastrophe exposure and portfolio-specific risk margin
   chore(ci): add pyproject.toml, ruff, mypy and fix CI jobs
   ```
