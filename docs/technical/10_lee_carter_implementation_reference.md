# Lee-Carter Mortality Pipeline -- Technical Reference

---

## Pipeline Architecture

```
[HMD Files]  -->  a06_mortality_data.MortalityData
                        |
                  a07_graduation.GraduatedRates
                        |
                  a08_lee_carter.LeeCarter
                        |
                  a09_projection.MortalityProjection
                        |
                  to_life_table() --> a01_life_table.LifeTable
                                          |
                                     a02 -> a03 -> a04 -> a05
```

## Module Interface Contract

| Module | Class | Input | Output Attributes |
|:-------|:------|:------|:------------------|
| a06 | `MortalityData` | HMD text files | `.mx`, `.dx`, `.ex`, `.ages`, `.years` |
| a07 | `GraduatedRates` | `MortalityData` | `.mx`, `.dx`, `.ex`, `.ages`, `.years` (same interface) |
| a08 | `LeeCarter` | `MortalityData` or `GraduatedRates` | `.ax`, `.bx`, `.kt`, `.ages`, `.years` |
| a09 | `MortalityProjection` | `LeeCarter` | `.kt_central`, `.kt_simulated`, `.to_life_table()` |

---

## a06: MortalityData

**Purpose:** Load HMD 1x1 files into aligned matrices (ages x years).

| File Pattern | Content |
|:-------------|:--------|
| `Mx_1x1_{country}.txt` | Central death rates m_{x,t} |
| `Deaths_1x1_{country}.txt` | Death counts d_{x,t} |
| `Exposures_1x1_{country}.txt` | Person-years L_{x,t} |

**Age capping:** Ages above `age_max` are aggregated. Deaths and exposures are **summed**. Rates are **recomputed** as d/L (not averaged).

**Validation checks:**
1. No NaN in any matrix
2. All m_x > 0 (required for log transform)
3. All L_x > 0
4. Recomputed d/L matches provided m_x within 1%

---

## a07: Whittaker-Henderson Graduation

**Problem:** `minimize: sum_x w_x(z_x - m_x)^2 + lambda * sum_x (Delta^h z_x)^2`

**Solution:** `z = (W + lambda * D'D)^{-1} * W * m`

| Symbol | Type | Meaning |
|:-------|:-----|:--------|
| z_x | vector | Graduated log-rates |
| m_x | vector | Observed log-rates |
| W | diagonal matrix | Weights (exposure per age) |
| D | sparse (n-h) x n | h-th order difference matrix |
| lambda | scalar | Smoothing parameter |
| h | int | Difference order (default: 2) |

**Difference matrix construction (order 2, n=5):**

```
D_1 = [ 1 -1  0  0  0 ]     D_2 = D_1[4x4] @ D_1[4x5]
      [ 0  1 -1  0  0 ]
      [ 0  0  1 -1  0 ]     D_2 = [ 1 -2  1  0  0 ]
      [ 0  0  0  1 -1 ]           [ 0  1 -2  1  0 ]
                                   [ 0  0  1 -2  1 ]
```

**Lambda behavior:**

| Lambda | Result |
|:-------|:-------|
| 0 | Raw data (no smoothing) |
| 1e3 | Light smoothing |
| 1e5 | Standard (default) |
| 1e7 | Heavy smoothing (near polynomial of degree h-1) |

**Implementation:** `scipy.sparse.diags` for D, `scipy.sparse.linalg.spsolve` for the system. Each year column smoothed independently. Work in log-space, exponentiate for guaranteed positivity.

---

## a08: Lee-Carter Model

**Model:** `ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}`

| Parameter | Formula | Constraint | Meaning |
|:----------|:--------|:-----------|:--------|
| a_x | mean_t(ln(m_{x,t})) | -- | Average log-mortality shape |
| b_x | U[:,0] / sum(U[:,0]) | sum(b_x) = 1 | Age sensitivity to trend |
| k_t | S[0] * V[0,:] * sum(U[:,0]) | sum(k_t) = 0 | Time index of mortality level |

**Fitting procedure:**

```
1. a_x = row_means(log_mx)              # Age averages
2. R = log_mx - a_x[:, newaxis]         # Residual matrix
3. U, S, Vt = svd(R)                    # Singular value decomposition
4. bx_raw = U[:,0]                      # First left singular vector
5. kt_raw = S[0] * Vt[0,:]             # Scaled first right singular vector
6. Normalize: bx = bx_raw/sum(bx_raw)  # Identifiability
7. Scale: kt = kt_raw * sum(bx_raw)    # Preserve product bx*kt
8. Center: kt = kt - mean(kt)          # sum(k_t) = 0
9. Re-estimate kt via root-finding      # Match observed deaths
```

**k_t re-estimation (step 9):**

For each year t, solve for k_t:

```
sum_x d_{x,t} = sum_x L_{x,t} * exp(a_x + b_x * k_t)
```

Method: `scipy.optimize.brentq` with bracket [-500, 500]. This is a monotone function in k_t (exp is monotone, b_x > 0 for most ages), so brentq converges reliably.

**Explained variance:** `S[0]^2 / sum(S^2)` -- fraction of total variance captured by first SVD component. Typically > 70% for developed countries.

**Sign convention:** If `sum(bx_raw) < 0`, flip both bx and kt (the product is invariant).

---

## a09: Mortality Projection

**k_t model:** Random Walk with Drift

```
k_{T+h} = k_T + h * drift + sqrt(h) * sigma * Z,   Z ~ N(0,1)

drift = (k_T - k_1) / (T - 1)
sigma = std(diff(k_t) - drift, ddof=1)
```

**Simulation:**

```python
innovations = N(0, 1) of shape (n_sims, horizon)
paths = k_T + h * drift + sigma * cumsum(innovations, axis=1)
```

**Bridge method `to_life_table()`:**

| Step | Formula | Purpose |
|:-----|:--------|:--------|
| 1 | m_x = exp(a_x + b_x * k_t) | Projected central death rates |
| 2 | q_x = 1 - exp(-m_x) | Convert force to probability (constant force assumption) |
| 3 | q_omega = 1.0 | Force terminal mortality |
| 4 | l_{x+1} = l_x * (1 - q_x) | Build survivor column |
| 5 | Return LifeTable(ages, l_x) | Feed into a02-a05 |

**Key relationship:** `q_x = 1 - exp(-m_x)` assumes constant force of mortality within each year of age. For m_x < 0.1 this is approximately `q_x ≈ m_x`. For high ages the difference matters.

---

## Test Summary

| Test File | Count | Key Validations |
|:----------|------:|:----------------|
| test_mortality_data.py | 15 | Shape, NaN, positivity, d/L consistency, age capping |
| test_graduation.py | 13 | Difference matrix, roughness reduction, lambda extremes |
| test_lee_carter.py | 20 | Constraints, variance, k_t trend, death matching, synthetic recovery |
| test_projection.py | 17 | Drift, CI widening, LifeTable validity, premium integration |
| test_integration_lee_carter.py | 3 | Full pipeline, mortality improvement lowers premiums |
| **New total** | **68** | |
| **Grand total (with Phase 2)** | **106** | |

---

## Dependency Map

```
requirements.txt: numpy>=1.24, pandas>=2.0, scipy>=1.11, pytest>=7.0

scipy additions:
  - scipy.sparse         (Whittaker-Henderson difference/weight matrices)
  - scipy.sparse.linalg  (spsolve for the graduation system)
  - scipy.optimize       (brentq for k_t re-estimation)
```

## Key Files

```
backend/engine/
├── a06_mortality_data.py  # Input: HMD -> matrices
├── a07_graduation.py      # Smoothing: Whittaker-Henderson
├── a08_lee_carter.py      # Fitting: SVD + re-estimation
├── a09_projection.py      # Forecasting: RWD + bridge to LifeTable
└── __init__.py             # Exports all 9 classes
```
