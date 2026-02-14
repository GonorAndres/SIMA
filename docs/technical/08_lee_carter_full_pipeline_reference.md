# 08 -- Lee-Carter Full Pipeline Reference

## Core Model

| Symbol | Formula | Domain | Meaning |
|:-------|:--------|:-------|:--------|
| m_{x,t} | d_{x,t} / L_{x,t} | (0, +inf) | Central death rate, age x, year t |
| ln(m_{x,t}) | a_x + b_x * k_t + epsilon | (-inf, +inf) | Lee-Carter model equation |
| a_x | (1/T) SUM_t ln(m_{x,t}) | R | Average log-mortality shape by age |
| b_x | u_{1,x} / SUM u_{1,x} | R, SUM=1 | Age sensitivity to time trend |
| k_t | sigma_1 * v_{1,t} * SUM u_{1,x} | R, SUM=0 | Mortality time index |

## Conversion Formulas

| From | To | Formula | Assumption |
|:-----|:---|:--------|:-----------|
| m_x | q_x | 1 - exp(-m_x) | Constant force |
| m_x | q_x | m_x / (1 + 0.5*m_x) | UDD |
| q_x | m_x | -ln(1 - q_x) | Constant force |
| ln(m_x) | m_x | exp(ln(m_x)) | None |

## SVD Estimation

```
INPUT:    m_{x,t} matrix  (A ages x T years)

STEP 1:   Y_{x,t} = ln(m_{x,t})
STEP 2:   a_x = (1/T) SUM_t Y_{x,t}
STEP 3:   Z_{x,t} = Y_{x,t} - a_x
STEP 4:   SVD:  Z = U * Sigma * V'
STEP 5:   b_x^raw = u_{1,x}
           k_t^raw = sigma_1 * v_{1,t}
```

## SVD Computation (via eigendecomposition)

```
STEP A:   Compute Z'Z                    (T x T, symmetric)
STEP B:   Eigendecompose Z'Z = V * Lambda * V'
STEP C:   sigma_i = sqrt(lambda_i)
STEP D:   u_i = Z * v_i / sigma_i        (for each sigma_i > 0)
```

## Identifiability Constraints

| Constraint | Formula | Fixes | Effect |
|:-----------|:--------|:------|:-------|
| C1 (scale) | SUM_x b_x = 1 | Reciprocal scaling | b_x become proportions |
| C2 (location) | SUM_t k_t = 0 | Constant shift a<->k | a_x becomes time-average |

```
ENFORCEMENT:
  s = SUM b_x^raw
  b_x = b_x^raw / s
  k_t = k_t^raw * s           --> C1 satisfied

  k_bar = mean(k_t)
  k_t <- k_t - k_bar
  a_x <- a_x + b_x * k_bar   --> C2 satisfied
```

## Equivalence Class (Indeterminacy Proof)

```
For any c != 0, d in R:
  a_x* = a_x + d*c*b_x
  b_x* = c * b_x
  k_t* = k_t/c - d

Verify:  a_x* + b_x* * k_t* = a_x + b_x * k_t    (always)

Degrees of freedom: 2 (c, d)
Constraints needed: 2 (C1, C2)
```

## k_t Re-estimation (Newton-Raphson)

```
OBJECTIVE:  For each year t, find k_t such that:
            SUM_x d_{x,t} = SUM_x L_{x,t} * exp(a_x + b_x * k_t)

DEFINE:
  g(k_t)  = SUM_x d_{x,t} - SUM_x L_{x,t} * exp(a_x + b_x * k_t)
  g'(k_t) = -SUM_x L_{x,t} * b_x * exp(a_x + b_x * k_t)

UPDATE:
  k_t^{new} = k_t^{old} - g(k_t^{old}) / g'(k_t^{old})

CONVERGENCE:  3-5 iterations typical. Convex in k_t.
REQUIRES:     d_{x,t} and L_{x,t} separately (not just m_{x,t})
POST-STEP:    Re-apply C2 (SUM k_t = 0, adjust a_x)
```

## Forecasting k_t

```
MODEL:       k_{t+1} = k_t + delta + epsilon_t      ARIMA(0,1,0) + drift
             epsilon_t ~ N(0, sigma_eps^2)

ESTIMATE:
  delta = (k_T - k_1) / (T - 1)
  sigma_eps^2 = (1/(T-2)) SUM_{t=2}^{T} (k_t - k_{t-1} - delta)^2

POINT FORECAST:
  k_{T+h} = k_T + h * delta

INTERVAL (95%):
  k_{T+h} +/- 1.96 * sigma_eps * sqrt(h)

PROJECTION:
  ln(m_{x,t*}) = a_x + b_x * k_{t*}
  m_{x,t*} = exp(a_x + b_x * k_{t*})
  q_{x,t*} = 1 - exp(-m_{x,t*})
```

## Variance Decomposition

```
||Z||_F^2 = SUM sigma_i^2            (total variance)
rho_1 = sigma_1^2 / SUM sigma_i^2   (proportion explained by factor 1)

Typical:  rho_1 >= 0.90 for national populations
```

## Complete Pipeline

```
ESTIMATION
  1.  Y = ln(M)                          log transform
  2.  a_x = row_mean(Y)                  age profile
  3.  Z = Y - a_x                        center
  4.  SVD(Z) -> U, Sigma, V              decompose
  5.  b_x, k_t from first triplet        extract
  6.  Normalize (C1, C2)                 identify
  7.  Newton-Raphson on k_t              match deaths
  8.  Re-normalize (C2)                  re-identify

FORECAST
  9.  Fit RW+drift to k_t                time series
  10. Project k_{T+1}, ..., k_{T+h}      extrapolate
  11. Confidence bands via sqrt(h)        uncertainty
  12. q_{x,t*} = 1 - exp(-exp(a_x + b_x*k_{t*}))

APPLICATION
  13. Feed q_x into LifeTable (a01)
  14. Commutation -> Premiums -> Reserves (a02-a05)
```

## Data Requirements

| Source | Provides | Variable | Granularity |
|:-------|:---------|:---------|:-----------|
| INEGI / HMD | Death counts | d_{x,t} | Single age, single year |
| CONAPO / HMD | Mid-year population | L_{x,t} | Single age, single year |
| Computed | Central death rate | m_{x,t} = d/L | Single age, single year |

```
Matrix shape:  ages 0-100 (A=101) x years (T=20-30)
Sex:           Separate models for males and females
Cap:           Ages 100+ grouped into single category
```

## Implementation Map (SIMA)

| Module | Input | Output | Key Operation |
|:-------|:------|:-------|:-------------|
| a06_mortality_data.py | HMD/INEGI files | m_{x,t}, d_{x,t}, L_{x,t} matrices | Load, align, validate |
| a07_graduation.py | Raw m_{x,t} | Smoothed m_{x,t} | Whittaker-Henderson |
| a08_lee_carter.py | Smoothed m_{x,t}, d_{x,t}, L_{x,t} | a_x, b_x, k_t | SVD + re-estimation |
| a09_mortality_forecast.py | k_t series | Projected q_{x,t*} | ARIMA + conversion |

## ARIMA(p,d,q) Reference

| Parameter | Controls | Lee-Carter value | Meaning |
|:----------|:---------|:-----------------|:--------|
| p | AR lags (momentum) | 0 | No dependence on past changes |
| d | Differencing (trend) | 1 | Model changes, not levels |
| q | MA shocks (memory) | 0 | No lingering surprise effects |
| drift | Constant shift | delta < 0 | Steady mortality improvement |

## Key Identities

```
1.  Z = SUM sigma_i * u_i * v_i'           (SVD outer product form)
2.  A_k = argmin_{rank(B)<=k} ||A-B||_F    (Eckart-Young)
3.  ||A||_F^2 = SUM sigma_i^2              (Frobenius via singular values)
4.  b*k' = (c*b)*(k/c)'   for all c!=0    (scale indeterminacy)
5.  q = 1 - exp(-m)  maps (0,inf) -> (0,1) (positivity guarantee)
6.  Var(k_{T+h}) = h * sigma_eps^2          (RW variance growth)
```
