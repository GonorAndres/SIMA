# Lee-Carter Foundations -- Intuitive Reference

## Why m_x, Not q_x

```
OBSERVABLE:   Deaths (certificates) + Population (census) --> m_x = deaths / person-years
DERIVED:      m_x + assumption (UDD or constant force)    --> q_x

PRINCIPLE:    Model what you observe. Derive what you need.
              m_x is the raw material. q_x is the product.
```

| What | q_x | m_x |
|:-----|:----|:----|
| Nature | Probability | Rate |
| Range | [0, 1] | (0, +inf) |
| Observed directly? | No | Yes |
| Needs assumptions? | Yes (death distribution) | No |
| Can exceed 1? | Never | Yes (extreme cases) |

---

## Person-Years: The Fair Denominator

```
INTUITION:    A budget of risk-time.
              Each person deposits their observed time into a shared pool.
              Deaths are measured against that pool.

ANALOGY:      Like man-hours on a construction project.
              10 workers for 2 days = 20 man-days.
              5 workers for 4 days = 20 man-days.
              Same exposure, comparable injury rates.

WHY IT MATTERS:
              Insurance portfolios are messy -- entries, exits, deaths
              at different times. Person-years handles all of it.
              One person for 12 months = two people for 6 months = same exposure.
```

---

## The Log Transformation

```
PROBLEM 1:    m_x spans 0.0002 to 0.4 (factor of 2000x)
              Young ages crushed near zero on any plot.
SOLUTION:     Log compresses: -8.5 to -0.9. Everything visible.

PROBLEM 2:    10% improvement at age 40: 0.003 -> 0.0027 (delta = 0.0003)
              10% improvement at age 80: 0.08 -> 0.072 (delta = 0.008)
              Look different on original scale.
SOLUTION:     In log space both shift by -0.105. Same improvement = same number.

PROBLEM 3:    A linear model could predict negative m_x.
SOLUTION:     Model ln(m_x) instead. Exponentiate back: always positive.

SUMMARY:      Log makes proportional changes additive,
              equalizes scale across ages,
              guarantees positive rates.
```

---

## Lee-Carter: The Model

```
ln(m_{x,t}) = a_x + b_x * k_t

PIECE         WHAT IT IS                    ANALOGY
─────         ──────────                    ───────
a_x           Average mortality shape       The photograph (static snapshot)
k_t           Time index                    The clock (one dial for all ages)
b_x           Age sensitivity               The volume knob per age
                                            (how loud each age hears the clock)

ONE FACTOR:   All ages share k_t. They just respond differently via b_x.
              Like an economy: one GDP growth rate, different industries
              respond differently.
```

---

## Why SVD, Not Regression

```
REGRESSION:   y = X * beta
              X is known (observed data)
              beta is unknown (estimate it)
              --> Normal equations, OLS

LEE-CARTER:   Z = b * k'
              b is unknown
              k is unknown
              BOTH sides are unknown --> OLS impossible

SVD:          Finds the rank-1 matrix (b * k') that is closest to Z
              in a least-squares sense.
              Same goal as OLS (minimize squared error),
              different tool (because different problem structure).

ECKART-YOUNG: Guarantees SVD rank-1 is THE BEST rank-1 approximation.
              Not "a" solution. THE optimal one.
```

---

## SVD Extraction -- Mental Model

```
INPUT:    Residual matrix Z (log-mortality minus row means)

          Each ROW    = one age's deviation pattern across years
          Each COLUMN = one year's deviation pattern across ages

SVD:      Z = U * S * V'

          sigma_1 >> sigma_2 >> sigma_3   (first value dominates)

          u_1 (first column of U) --> becomes b_x (age loadings)
          v_1 (first column of V) --> becomes k_t (time pattern), scaled by sigma_1

VARIANCE: sigma_1^2 / sum(sigma_i^2) = typically 90-95%
          ONE factor explains almost everything.

WHY:      Mortality improvement is driven by broad forces
          (medicine, sanitation, nutrition) that affect all ages.
          Not random age-by-age noise.
          One underlying process --> one dominant singular value.
```

---

## The Transformation Chain

```
ln(m_x)  ──exp()──>  m_x  ──1-exp(-m)──>  q_x  ──engine──>  premiums
   |                  |                      |
(-inf,+inf)        (0,+inf)              (0, 1)
   |                  |                      |
free space        positive only         valid probability
for modeling      guaranteed            guaranteed
```

```
INTUITION:    Work in the freest space (log).
              Let math do anything it wants.
              Transform back through gates that enforce validity.
              Each gate narrows the range and guarantees correctness.
```

---

## Edge Case: m_x > 1

```
SCENARIO:     100 people, 1 month, 20 die
              Exposure ≈ 7.5 person-years
              m_x = 20 / 7.5 = 2.667

CONVERT:      q_x = 1 - exp(-2.667) = 0.93

LESSON:       m_x > 1 is mathematically fine.
              It means: at this death intensity, you'd burn through
              more than one full person-year of life per person per year.
              The exp() bridge to q_x handles any positive m_x.

WHEN IT HAPPENS:
              - Sub-annual observations, annualized
              - Extreme old ages (110+)
              - Catastrophic events (pandemic months)
              - Small portfolios with unlucky months
```

---

## Remaining Topics (Next Sessions)

```
[ ] Identifiability constraints deep dive
[ ] k_t re-estimation (matching observed vs predicted deaths)
[ ] Forecasting k_t (random walk with drift)
[ ] Data requirements (INEGI/CONAPO matrix structure)
[ ] Whittaker-Henderson graduation (smoothing before Lee-Carter)
```
