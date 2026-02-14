# 08 -- Lee-Carter Pipeline & Estimation Intuition

## Focus: What a07 and a08 Do and Why

---

## a07_graduation.py -- Smoothing Raw Rates

```
PROBLEM:    Raw m_{x,t} is NOISY.
            Small populations at extreme ages --> wild fluctuations.
            Age 98 has 15 people, 3 die: m = 0.22
            Age 99 has 8 people, 0 die:  m = 0.00
            Age 100 has 5 people, 2 die: m = 0.50

            Biology says mortality rises smoothly with age.
            Data says it jumps around. Data is lying (small samples).

SOLUTION:   Graduation = smoothing.
            Force the m_x curve to be smooth while staying close to data.
            Balance: FIDELITY (stay near data) vs SMOOTHNESS (no jumps).
```

```
METHOD:     Whittaker-Henderson

INPUT:      Raw m_x values (one year at a time, or the whole matrix)
OUTPUT:     Smoothed m_x values -- biologically plausible curve

IDEA:       Minimize:
              FIT     = SUM w_x * (m_x^smooth - m_x^raw)^2
              ROUGH   = SUM (delta^z m_x^smooth)^2

            Total = FIT + lambda * ROUGH

            w_x      = weights (higher for ages with more data)
            delta^z  = z-th order differences (z=2 or z=3 typical)
            lambda   = smoothing parameter (big = smoother, small = closer to data)

ANALOGY:    Like drawing a curve through scattered dots.
            lambda = 0:   curve passes through every dot (overfitting)
            lambda = inf: curve is a straight line (oversmoothing)
            Right lambda: curve follows the trend, ignores the noise.
```

```
WHY BEFORE LEE-CARTER:

  Lee-Carter takes ln(m_x) as input.
  ln(0) = -infinity. If any m_x = 0 (no deaths observed), Lee-Carter breaks.
  Graduation fills these gaps with plausible interpolated values.

  Even without zeros, noisy m_x produces noisy a_x (row means).
  Noisy a_x means the residual matrix Z carries noise that isn't trend.
  SVD might pick up noise patterns instead of real mortality improvement.
  Smoother input --> cleaner SVD --> more reliable b_x and k_t.
```

```
WHAT a07 DOES STEP BY STEP:

  1. Receive raw m_{x,t} matrix (ages x years)
  2. For each year (or for the whole surface):
     - Apply Whittaker-Henderson with chosen lambda and difference order
     - Handle age 0 separately (infant mortality has unique pattern)
     - Handle old ages carefully (small populations, high noise)
  3. Output smoothed m_{x,t} matrix
  4. Pass to a08_lee_carter.py
```

| Decision | Options | Default | Why |
|:---------|:--------|:--------|:----|
| Difference order z | 2 or 3 | 3 | z=3 preserves curvature better |
| Lambda | 1 to 10000 | Cross-validate | Balances fit vs smoothness |
| Weights w_x | 1/variance or exposure-based | L_{x,t} | More data = more trust |
| Age 0 | Separate or include | Separate | Infant mortality is structurally different |
| Cap age | 100, 105, 110 | 100 | Group all 100+ together |

---

## a08_lee_carter.py -- The Estimation Engine

```
ROLE:       The core model. Takes smoothed mortality surface,
            produces three parameter vectors: a_x, b_x, k_t.
            These three vectors compress the entire mortality surface
            into a forecastable structure.

INPUT:      Smoothed m_{x,t} from a07
            Raw d_{x,t} and L_{x,t} for re-estimation step
OUTPUT:     a_x (A values), b_x (A values), k_t (T values)
            Variance explained (rho_1)
```

```
WHAT a08 DOES STEP BY STEP:

  PHASE 1: MATRIX PREPARATION
    1. Y = ln(smoothed_m)              Take log of entire matrix
    2. a_x = row_mean(Y)              Average each age across all years
    3. Z = Y - a_x                     Subtract age means --> residual matrix

  PHASE 2: SVD DECOMPOSITION
    4. SVD(Z) --> U, Sigma, V          Full decomposition
    5. Check sigma_1 >> sigma_2        Verify one-factor is justified
    6. rho_1 = sigma_1^2 / sum        Compute variance explained
    7. b_x^raw = first column of U     Age pattern
    8. k_t^raw = sigma_1 * first col of V    Time pattern

  PHASE 3: NORMALIZATION
    9. s = SUM(b_x^raw)
    10. b_x = b_x^raw / s             Now SUM(b_x) = 1
    11. k_t = k_t^raw * s             Compensate to preserve product
    12. k_bar = mean(k_t)
    13. k_t = k_t - k_bar             Now SUM(k_t) = 0
    14. a_x = a_x + b_x * k_bar       Absorb shift

  PHASE 4: RE-ESTIMATION
    15. For each year t:
        Newton-Raphson to find k_t such that
        SUM_x d_{x,t} = SUM_x L_{x,t} * exp(a_x + b_x * k_t)
    16. Re-apply: k_bar = mean(k_t), shift into a_x
    17. Final a_x, b_x, k_t are ready

  PHASE 5: DIAGNOSTICS
    18. Variance explained percentage
    19. Residual analysis (are leftover patterns random?)
    20. Plot a_x, b_x, k_t for visual sanity check
```

---

## Why a07 Before a08 (The Dependency)

```
Raw m_{x,t}  ---->  a07: Graduate/Smooth  ---->  a08: Lee-Carter
                          |                            |
                    Removes noise               Decomposes signal
                    Fills zeros                 Extracts trend
                    Biological plausibility     Statistical optimality
```

```
WITHOUT a07:
  - Zero m_x values crash the log transform
  - Noisy old ages corrupt SVD (noise looks like signal)
  - b_x might reflect sampling artifacts, not real age sensitivity
  - k_t might be unstable year to year

WITH a07:
  - All m_x > 0 guaranteed (log is safe)
  - SVD sees clean signal
  - b_x reflects genuine biological patterns
  - k_t reflects genuine time trend
```

---

## What Each Parameter Tells You (After a08)

```
a_x:  "What does mortality look like on average across the observation period?"
      - Low at young ages (around -8 in log space)
      - Rises steadily
      - High at old ages (around -1 in log space)
      - THE SHAPE of human mortality

b_x:  "When mortality improves, which ages benefit most?"
      - Typically higher at young/middle ages (they improved faster)
      - Lower at very old ages (harder to improve)
      - SUM = 1 (proportions of total sensitivity)
      - THE SENSITIVITY vector

k_t:  "How much has mortality improved by year t?"
      - Trends downward (mortality improving)
      - Year-to-year noise around the trend
      - SUM = 0 (centered around observation period)
      - THE CLOCK of mortality improvement
```

---

## The Re-estimation: Why It Matters

```
BEFORE RE-ESTIMATION:
  SVD says:    "I minimized squared error on log(m_x)"
  Reality:     Predicted total deaths != Observed total deaths

EXAMPLE:
  Year 2015, observed deaths = 50,000
  SVD-based prediction = 48,200
  Difference: 1,800 deaths unaccounted for

  The error is small in log-rate space but large in body count.
  An insurer who reserved for 48,200 deaths is underfunded.

AFTER RE-ESTIMATION:
  Newton-Raphson adjusts k_2015 slightly
  Now predicted deaths = 50,000 exactly
  The reserve is correct

INTUITION:
  SVD = statistician's answer (best log-rate fit)
  Re-estimation = actuary's correction (match the death count)
  Both are needed. SVD gives structure. Re-estimation gives calibration.
```

---

## Connection to Existing Engine

```
a08 output: a_x, b_x, k_t
     |
     v
a09: forecast k_{T+1}, k_{T+2}, ...
     |
     v
For future year t*:
  ln(m_{x,t*}) = a_x + b_x * k_{t*}
  m_{x,t*} = exp(...)
  q_{x,t*} = 1 - exp(-m_{x,t*})
     |
     v
a01_life_table.py   <-- receives projected q_x
     |
     v
a02_commutation.py  <-- D_x, N_x, C_x, M_x with future mortality
     |
     v
a03 -> a04 -> a05   <-- premiums and reserves reflect mortality improvement
```

```
BEFORE LEE-CARTER:    Static q_x --> fixed premiums forever
AFTER LEE-CARTER:     Projected q_x(t*) --> premiums that account for
                      people living longer in the future

For LIFE INSURANCE:   People die less --> charge less --> lower premiums
For ANNUITIES:        People live longer --> pay longer --> higher cost
```
