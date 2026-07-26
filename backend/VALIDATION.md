# Backend Validation Rules

This document is the validation contract for the SIMA actuarial engine and
API. Engine violations raise structured `ActuarialValidationError` or
`DataQualityError` instances with `field`, `constraint`, and `message`.
FastAPI maps domain/data-quality errors to HTTP 422, unavailable data to 503,
and malformed lookup/value errors to 400.

## Life tables and numeric assumptions

| Input | Rule | Actuarial rationale |
|---|---|---|
| Ages | At least two, sorted, integer, and consecutive | The recurrences for `d_x`, `q_x`, and `l_{x+1}` require every adjacent age |
| Survivors `l_x` | Finite, non-negative, and non-increasing, subject to a small floating-point tolerance | A survivor population cannot grow or become negative |
| Mortality `q_x` | Every value in `[0, 1]`; terminal mortality is 1 | Probabilities outside the unit interval invalidate survival recurrences |
| Lookup age | Within the life-table minimum and maximum | SIMA does not extrapolate actuarial values silently |
| Interest rate | Finite and strictly greater than `-1`; rates above 100% are allowed with a warning where configured | Discount factors require `1 + i > 0`; extreme rates remain mathematically defined but merit audit attention |
| Monetary amounts | Finite and non-negative; API death benefits and annuity pensions are strictly positive when applicable | Negative or non-finite cash flows reverse or destroy the intended liability |

Commutation functions accept `i = 0` explicitly. Their `D_x` exponent is
normalized to the life table's minimum age, which changes scale but not the
ratios used for actuarial values.

## Products, terms, and reserves

Supported death-product types are `whole_life`, `term`, `endowment`, and
`pure_endowment`; the portfolio also supports `annuity` and
`deferred_annuity`.

| Input | Rule | Actuarial rationale |
|---|---|---|
| Term `n` | Integer and non-negative; required for finite-horizon products | A finite contract needs a defined maturity |
| Duration `t` | Integer with `0 <= t <= n` for term/endowment products | Duration beyond maturity is not an active valuation state |
| Issue/attained age | Must remain within the selected life table | Claims and premiums cannot be valued without mortality rates |
| Limited-pay period `m` | Non-negative and within available table years | Premium payments cannot extend beyond the modeled lifetime |
| Matured/expired contracts | Term benefits become zero after expiry; matured endowments are handled explicitly | Prevents claims or reserves being counted after the contractual horizon |
| Portfolio policy IDs | Unique and non-empty | Avoids accidental double counting and enables audit tracing |
| Portfolio | Must be non-empty for BEL/SCR calculations | Capital on an absent exposure is undefined |

Reserve and premium equivalence checks use tolerances scaled to the sum
assured rather than fixed currency-unit tolerances.

## Mortality data

HMD and INEGI/CONAPO loaders validate data before Lee–Carter estimation.

| Area | Rule |
|---|---|
| Files | Expected versioned filenames and source-specific columns must exist |
| HMD schema | `Year`, `Age`, and the requested `Female`, `Male`, or `Total` column |
| INEGI deaths | `Anio`, `Edad`, `Sexo`, `Defunciones` |
| CONAPO population | `Anio`, `Edad`, `Sexo`, `Poblacion` |
| Age/year fields | Numeric integers; requested ranges must be non-empty |
| Missing cells | Rejected by default; optional interpolation is limited to a small proportion of cells |
| Exposures | Strictly positive |
| Central death rates | Strictly positive for log-space graduation |
| Consistency | `m_x` must agree with `d_x / e_x` within 1% by default |
| Open age | HMD `110+` is parsed as 110; ages above `age_max` are exposure-weight aggregated |

`DataQualityReport` records the validated matrix dimensions, age/year ranges,
imputation count, source, and open-age group.

## Graduation, Lee–Carter, and projection

- Whittaker–Henderson `lambda_param >= 0` and `diff_order >= 1`.
- Graduation rejects non-positive rates before applying `log(m_x)`.
- A warning is emitted for an ill-conditioned smoothing system or a graduated
  curve that is not broadly increasing after early childhood.
- Lee–Carter validation uses a configurable explained-variance threshold and
  an adaptive root bracket for `k_t` re-estimation.
- Projection requires at least two observation years, `horizon > 0`, and
  `1 <= n_simulations <= 1,000,000`.
- Projection year and age lookups must be exact members of their modeled
  arrays.
- Requested life-table subsets must satisfy `age_min <= age_max` and contain at
  least one modeled age.

## Portfolio and SCR

- Policy amounts, durations, issue ages, expense loadings, lapse rates, and
  commissions are validated at construction.
- Policy attained age must fit the valuation life table.
- Expired term and paid endowment policies contribute no capital; an
  endowment exactly at maturity carries the benefit immediately due.
- The portfolio is an in-force inventory. Catastrophe exposure is conditional
  on survival to attained age, so historical survival is not applied again.
- Death-policy contractual premiums are stored or resolved once on the base
  issue basis and remain fixed under mortality and interest-rate stresses.
- Interest-rate down shocks use a configurable floor (default 0.5%) and log
  when the floor applies.
- Correlation matrices must be square, symmetric, have unit diagonal, and be
  positive semi-definite.
- Custom shock parameters must be internally consistent; calibrated
  Lee–Carter shocks are optional and reported explicitly.
- BEL/SCR calculations reject empty portfolios.

## API request validation

Pydantic enforces basic types/ranges and the following cross-field rules:

- `term` is required for term and endowment requests.
- Death products require a positive `sum_assured`.
- Annuities require a positive `annual_pension`.
- Portfolio `duration` cannot exceed `term`.
- SCR shock inputs must describe a consistent mortality/longevity/rate
  scenario and use a supported sex.

The demo portfolio is shared process-wide and guarded by a re-entrant lock.
This prevents concurrent mutation corruption, but it is not per-user storage.
