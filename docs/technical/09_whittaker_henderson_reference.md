# 09 -- Whittaker-Henderson Graduation Reference

## Core Model

| Symbol | Formula | Domain | Meaning |
|:-------|:--------|:-------|:--------|
| m_x | d_x / L_x | (0, +inf) | Observed central death rate |
| g_x | solved from linear system | (0, +inf) | Graduated (smoothed) rate |
| w_x | L_x (exposure) | [0, +inf) | Weight = trust per age |
| lambda | user-chosen | (0, +inf) | Smoothing parameter |
| z | 2 or 3 (integer) | {1,2,3,...} | Difference order |
| D | difference matrix | R^{(n-z) x n} | Computes z-th differences |

## Finite Differences

```
ORDER 1:  delta^1 g_x = g_{x+1} - g_x
          Coefficients: [1, -1]
          Measures: slope

ORDER 2:  delta^2 g_x = g_{x+2} - 2*g_{x+1} + g_x
          Coefficients: [1, -2, 1]
          Measures: curvature

ORDER 3:  delta^3 g_x = g_{x+3} - 3*g_{x+2} + 3*g_{x+1} - g_x
          Coefficients: [1, -3, 3, -1]
          Measures: rate of change of curvature

GENERAL:  delta^z g_x = SUM_{j=0}^{z} (-1)^{z-j} * C(z,j) * g_{x+j}
          Coefficients: Pascal's triangle with alternating signs
```

## Zero-Difference Implications

| delta^z = 0 everywhere | Curve is |
|:-----------------------|:---------|
| z = 1 | Constant (horizontal line) |
| z = 2 | Linear (straight line) |
| z = 3 | Quadratic (parabola) |

## Objective Function

```
Minimize:  F + lambda * S

F = SUM_x w_x * (g_x - m_x)^2           (fidelity)
S = SUM_x (delta^z g_x)^2                 (smoothness)

F = (g - m)' W (g - m)                    (matrix form)
S = g' D'D g                               (matrix form)

Total = (g - m)'W(g - m) + lambda * g'D'Dg
```

## Difference Matrix D

```
z=2, n=5:
D = [ 1  -2   1   0   0 ]    shape: (n-z) x n = 3 x 5
    [ 0   1  -2   1   0 ]
    [ 0   0   1  -2   1 ]

z=3, n=6:
D = [ 1  -3   3  -1   0   0 ]    shape: (n-z) x n = 3 x 6
    [ 0   1  -3   3  -1   0 ]
    [ 0   0   1  -3   3  -1 ]

Row i: binomial coefficients C(z,j) with alternating signs, starting at column i
```

## Closed-Form Solution

```
Gradient = 2(W + lambda*D'D)g - 2Wm = 0

(W + lambda*D'D) g = Wm

g* = (W + lambda*D'D)^{-1} * W * m
```

## Smoother Matrix

```
H = (W + lambda*D'D)^{-1} * W

g = H * m

Each row of H: weighted average centered at that age
```

## Dimension Trace

```
m, g:           n x 1
W:              n x n  (diagonal)
D:              (n-z) x n
D'D:            n x n  (symmetric, banded, bandwidth 2z+1)
W + lambda*D'D: n x n  (symmetric, positive definite, banded)
Wm:             n x 1
```

## Lambda Behavior

| lambda | Effect | g approaches |
|:-------|:-------|:-------------|
| 0 | No smoothing | g = m (raw data) |
| Small (1-10) | Slight smoothing | Near data, some noise removed |
| Medium (100-1000) | Moderate smoothing | Follows trend, ignores bumps |
| Large (10000+) | Heavy smoothing | Nearly polynomial of degree z-1 |
| infinity | Maximum smoothing | WLS polynomial fit of degree z-1 |

## Weight Choices

| Choice | Formula | When |
|:-------|:--------|:-----|
| Exposure | w_x = L_x | Standard (more people = more trust) |
| Inverse variance | w_x = L_x / m_x | More precise statistically |
| Equal | w_x = 1 | No exposure data available |
| Zero | w_x = 0 | Missing/unreliable ages (filled by smoothness) |

## Quadratic Minimization Unification

| Method | A matrix | RHS | Solution |
|:-------|:---------|:----|:---------|
| Scalar | a | -b/2 | -b/(2a) |
| OLS | X'X | X'y | (X'X)^{-1}X'y |
| Ridge | X'X + lambda*I | X'y | (X'X+lambda*I)^{-1}X'y |
| WH Graduation | W + lambda*D'D | Wm | (W+lambda*D'D)^{-1}Wm |

## Matrix Calculus Rules

```
Rule 1:  d/dx (a'x) = a
Rule 2:  d/dx (x'Ax) = 2Ax          (A symmetric)
Rule 3:  d/dx (x'Ax + b'x) = 2Ax + b
```

## Key Identities

```
1. delta^z coefficients = (-1)^{z-j} * C(z,j)
2. (W + lambda*D'D) is symmetric positive definite
3. lambda = 0  -->  g = m
4. lambda -> inf  -->  g = WLS polynomial of degree z-1
5. D'D is banded (bandwidth 2z+1) --> O(n) solve
6. WH with z=2 = Hodrick-Prescott filter
7. WH ≈ P-splines of degree 0 (Eilers & Marx, 1996)
```

## Conversion Reference (m_x to q_x)

| Assumption | Formula | Use |
|:-----------|:--------|:----|
| Constant force | q_x = 1 - exp(-m_x) | Standard for Lee-Carter |
| UDD | q_x = m_x / (1 + 0.5*m_x) | Traditional actuarial |
| Approximation | q_x ≈ m_x for small m_x | Quick check (m_x < 0.1) |

## HMD Data Reference

```
Files per country:
  Mx_1x1_{country}.txt       death rates
  Deaths_1x1_{country}.txt   death counts
  Exposures_1x1_{country}.txt person-years

Format: 2 header lines, whitespace-separated
Columns: Year  Age  Female  Male  Total
Age range: 0 to 110+ (110+ is open interval)
Load: pd.read_csv(file, sep=r"\s+", skiprows=2, na_values=".")
```
