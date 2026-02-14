# Lee-Carter Foundations -- Technical Reference

## Core Definitions

| Symbol | Formula | Definition | Unit |
|:-------|:--------|:-----------|:-----|
| d_{x,t} | observed | Deaths at age x in year t | count |
| L_{x,t} | observed | Person-years of exposure at age x in year t | person-years |
| m_{x,t} | d_{x,t} / L_{x,t} | Central death rate | deaths / person-year |
| q_{x,t} | 1 - exp(-m_{x,t}) | Probability of death (constant force assumption) | probability [0,1] |

## Person-Years Calculation

```
L_{x,t} = SUM over all individuals i of (time_observed_i)

For complete year observation:
  survivor contributes:  1 person-year
  death at time s:       s person-years  (0 < s < 1)

Under UDD assumption (deaths uniform within year):
  L_{x,t} ≈ l_{x,t} - 0.5 * d_{x,t}
```

## m_x to q_x Conversion

```
Exact (constant force):     q_x = 1 - exp(-m_x)
Linear approximation (UDD): q_x ≈ m_x / (1 + 0.5 * m_x)

For small m_x:  q_x ≈ m_x
```

| m_x range | Typical ages | q_x approximation error |
|:----------|:-------------|:------------------------|
| 0.0001 - 0.001 | 1-20 | < 0.05% |
| 0.001 - 0.01 | 20-50 | < 0.5% |
| 0.01 - 0.1 | 50-80 | < 5% |
| 0.1 - 1.0 | 80-110 | significant |

## Lee-Carter Model

```
ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}

Parameters:
  a_x  :  one per age       (average log-mortality profile)
  b_x  :  one per age       (sensitivity to time trend)
  k_t  :  one per year      (mortality time index)
```

## Estimation Procedure (SVD Method)

**Input:** Matrix of observed ln(m_{x,t}), dimensions A ages x T years.

```
STEP 1 — Compute a_x
  a_x = (1/T) * SUM_t ln(m_{x,t})        for each age x

STEP 2 — Center the matrix
  Z_{x,t} = ln(m_{x,t}) - a_x            residual matrix (A x T)

STEP 3 — Singular Value Decomposition
  Z = U * S * V'
  U:  A x A   (left singular vectors, columns = age patterns)
  S:  A x T   (diagonal singular values, sigma_1 >= sigma_2 >= ...)
  V:  T x T   (right singular vectors, columns = time patterns)

STEP 4 — Rank-1 approximation
  Z ≈ sigma_1 * u_1 * v_1'

  Raw estimates:
    b_x^raw = u_1(x)                     first left singular vector
    k_t^raw = sigma_1 * v_1(t)           first right singular vector, scaled

STEP 5 — Normalize (identifiability constraints)
  c = SUM_x b_x^raw
  b_x = b_x^raw / c                      so that SUM_x b_x = 1
  k_t = k_t^raw * c                      preserves b_x * k_t product

  Adjust k_t so SUM_t k_t = 0            (centering)
```

## Variance Explained

```
Proportion = sigma_1^2 / SUM_i sigma_i^2

Typical empirical result: 90-95% for national populations
```

## Identifiability Constraints

| Constraint | Purpose |
|:-----------|:--------|
| SUM_x b_x = 1 | Fixes scale: b_x and k_t cannot be rescaled arbitrarily |
| SUM_t k_t = 0 | Fixes location: a_x truly represents the mean log-mortality |

```
Without constraints:  b_x * k_t = (c * b_x) * (k_t / c)  for any c ≠ 0
                      Infinitely many solutions, same product
With constraints:     unique solution
```

## Transformation Chain (Lee-Carter to Actuarial Engine)

```
Lee-Carter:     ln(m_{x,t}) = a_x + b_x * k_t          real line (-inf, +inf)
      |
      |  exp()
      v
Rate:           m_{x,t} = exp(a_x + b_x * k_t)         positive reals (0, +inf)
      |
      |  q = 1 - exp(-m)
      v
Probability:    q_{x,t}                                  bounded (0, 1)
      |
      |  life table construction
      v
Engine:         l_x -> d_x -> D_x -> N_x -> premiums -> reserves
```

## Equivalent Multiplicative Form

```
m_{x,t} = exp(a_x) * exp(b_x * k_t)

Interpretation: baseline mortality exp(a_x) scaled by time factor exp(b_x * k_t)
When k_t decreases: exp(b_x * k_t) < 1, mortality improves
```

## Numerical Example (3 ages x 4 years)

```
Input m_x:
              2010     2011     2012     2013
age 40:      0.0020   0.0018   0.0016   0.0015
age 50:      0.0060   0.0054   0.0049   0.0045
age 60:      0.0200   0.0182   0.0165   0.0150

a_x:   a_40 = -6.369    a_50 = -5.265    a_60 = -4.056

SVD of residual matrix:
  sigma_1 = 0.358    sigma_2 = 0.006    sigma_3 = 0.002
  Variance explained by first factor: 99.9%

After normalization:
  b_40 = 0.334    b_50 = 0.330    b_60 = 0.337
  k_2010 = +0.267  k_2011 = +0.085  k_2012 = -0.104  k_2013 = -0.249
```
