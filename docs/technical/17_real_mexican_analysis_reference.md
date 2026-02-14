# Real Mexican Data Analysis: Technical Reference

**Analysis:** Lee-Carter on INEGI/CONAPO mortality data, COVID-19 comparison, regulatory validation

**Script:** `backend/analysis/mexico_lee_carter.py`

---

## 1. Analysis Configuration

| Parameter | Pre-COVID | Full Period |
|-----------|-----------|-------------|
| Source | INEGI deaths + CONAPO population | INEGI deaths + CONAPO population |
| Sex | Total (both sexes combined) | Total (both sexes combined) |
| Years | 1990-2019 (30 years) | 1990-2024 (35 years) |
| Ages | 0-100 (101 ages) | 0-100 (101 ages) |
| Matrix shape | (101, 30) | (101, 35) |
| Graduation | Whittaker-Henderson, lambda=1e5 | Whittaker-Henderson, lambda=1e5 |
| Lee-Carter | SVD, `reestimate_kt=False` | SVD, `reestimate_kt=False` |
| Projection | RWD, horizon=30, nsim=1000, seed=42 | RWD, horizon=30, nsim=1000, seed=42 |
| Projection range | 2020-2049 | 2025-2054 |
| Target year | 2029 (10 years after last observed) | 2034 (10 years after last observed) |

---

## 2. Lee-Carter Model Diagnostics

| Metric | Pre-COVID (1990-2019) | Full (1990-2024) | Difference |
|--------|----------------------|-------------------|------------|
| Explained variance | 0.7767 (77.7%) | 0.5347 (53.5%) | -0.2420 |
| RMSE (log-space) | 0.061758 | 0.105164 | +0.043406 |
| Max abs error | 0.330075 | 0.539983 | +0.209908 |
| Mean abs error | 0.046627 | 0.070154 | +0.023527 |
| Drift (annual) | -1.076431 | -0.854812 | +0.221619 |
| Sigma | 1.788860 | 1.516261 | -0.272599 |
| k_t last observed | -7.9481 (year 2019) | -8.5895 (year 2024) | -0.6414 |
| k_t central end | -40.2410 (year 2049) | -34.2338 (year 2054) | -- |

All identifiability constraints satisfied in both models:
- `sum(b_x) = 1`: PASS
- `sum(k_t) = 0`: PASS
- No NaN values: PASS
- Explained variance > 50%: PASS

---

## 3. k_t Re-estimation Issue with Graduated Data

### Problem

Whittaker-Henderson graduation changes the mortality surface. The re-estimation equation:

```
sum_x D_{x,t} = sum_x L_{x,t} * exp(a_x + b_x * k_t)
```

uses raw deaths `D_{x,t}` and exposures `L_{x,t}`, but `a_x` and `b_x` come from GRADUATED rates. With graduation, some `b_x` values become negative (observed at ages 77, 78, 85 in Mexican data), making the `death_residual(k)` function non-monotone (U-shaped). `brentq` requires a monotone function and fails.

### Why b_x becomes negative

Graduation smooths the log-mortality surface. If a particular age had unusually HIGH mortality improvement in the raw data (noise), smoothing reduces that improvement. The SVD sees the smoothed residual as having the opposite sign at that age, producing `b_x < 0`.

### Solution

Use `reestimate_kt=False`. SVD k_t minimizes log-space error, which is internally consistent with the Lee-Carter log-bilinear formulation:

```
ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}
```

SVD minimizes `sum_{x,t} epsilon_{x,t}^2`. Re-estimation minimizes a different objective (matching death counts in real space). When the rates feeding `a_x` and `b_x` have been graduated, the log-space objective is the correct one.

### Adaptive bracket search (fallback in a08)

The code in `a08_lee_carter.py` implements an adaptive bracket search that widens the brentq interval progressively. Even with this, re-estimation can still fail on graduated Mexican data because the non-monotonicity is structural, not a bracket issue.

---

## 4. k_t Trajectory Comparison

### Overlapping years (1990-2017)

| Year | k_t (Pre-COVID) | k_t (Full) | Difference |
|------|-----------------|------------|------------|
| 1990 | 23.2685 | 20.4741 | -2.7943 |
| 1993 | 11.4446 | 10.1520 | -1.2926 |
| 1996 | 8.1656 | 7.8707 | -0.2949 |
| 1999 | 2.5670 | 3.4024 | +0.8354 |
| 2002 | -1.7796 | 0.0085 | +1.7881 |
| 2005 | -3.5722 | -1.3816 | +2.1905 |
| 2008 | -4.7985 | -2.7871 | +2.0114 |
| 2011 | -4.7730 | -3.1624 | +1.6106 |
| 2014 | -8.9684 | -6.4379 | +2.5305 |
| 2017 | -7.3837 | -5.7836 | +1.6001 |

### COVID-era years (full model only)

| Year | k_t (Full) |
|------|------------|
| 2020 | -4.7170 |
| 2021 | -3.3353 |
| 2022 | -5.8466 |
| 2023 | -7.3517 |
| 2024 | -8.5895 |

Note: k_t jumps upward (mortality worsens) in 2020-2021, then resumes declining.

---

## 5. Projected Life Tables

### Pre-COVID projection, year 2029

| Age | l_x | q_x | 1000*q_x |
|-----|-----|-----|----------|
| 0 | 100,000.0 | 0.007929 | 7.9292 |
| 1 | 99,207.1 | 0.000705 | 0.7049 |
| 5 | 99,059.4 | 0.000181 | 0.1814 |
| 10 | 98,977.4 | 0.000176 | 0.1761 |
| 20 | 98,531.1 | 0.000947 | 0.9469 |
| 30 | 97,429.9 | 0.001422 | 1.4224 |
| 40 | 95,850.1 | 0.002136 | 2.1358 |
| 50 | 93,005.3 | 0.004642 | 4.6417 |
| 60 | 86,649.1 | 0.010481 | 10.4810 |
| 70 | 74,099.7 | 0.022289 | 22.2886 |
| 80 | 51,473.8 | 0.054359 | 54.3593 |
| 90 | 14,480.4 | 0.130659 | 130.6589 |
| 100 | 1,859.4 | 1.000000 | 1000.0000 |

### Full period projection, year 2034

| Age | l_x | q_x | 1000*q_x |
|-----|-----|-----|----------|
| 0 | 100,000.0 | 0.006468 | 6.4679 |
| 1 | 99,353.2 | 0.000581 | 0.5806 |
| 5 | 99,228.5 | 0.000163 | 0.1632 |
| 10 | 99,153.7 | 0.000163 | 0.1627 |
| 20 | 98,696.4 | 0.001015 | 1.0152 |
| 30 | 97,497.7 | 0.001557 | 1.5568 |
| 40 | 95,773.1 | 0.002345 | 2.3448 |
| 50 | 92,637.2 | 0.005031 | 5.0314 |
| 60 | 85,905.9 | 0.011148 | 11.1481 |
| 70 | 72,605.4 | 0.023925 | 23.9249 |
| 80 | 49,533.4 | 0.055964 | 55.9638 |
| 90 | 13,390.0 | 0.132010 | 132.0104 |
| 100 | 2,006.2 | 1.000000 | 1000.0000 |

---

## 6. Regulatory Table Comparisons

### Pre-COVID (projected year 2029)

| Table | Ages | RMSE | Mean Ratio | Min Ratio | Max Ratio |
|-------|------|------|------------|-----------|-----------|
| CNSF 2000-I (M) | 89 | 0.002940 | 0.9469 | 0.5448 | 2.8126 |
| CNSF 2000-I (F) | 89 | 0.002940 | 0.9469 | 0.5448 | 2.8126 |
| CNSF 2000-G (M) | 89 | 0.011335 | 0.7584 | 0.2738 | 1.3087 |
| CNSF 2000-G (F) | 89 | 0.011335 | 0.7584 | 0.2738 | 1.3087 |
| CNSFM 2013 | 101 | 0.009415 | 2.0014 | 0.3482 | 18.3123 |
| EMSSA 2009 (M) | 101 | 0.010397 | 1.6788 | 0.1952 | 10.8620 |
| EMSSA 2009 (F) | 101 | 0.015320 | 4.5376 | 0.3762 | 19.3396 |

### Full period (projected year 2034)

| Table | Ages | RMSE | Mean Ratio | Min Ratio | Max Ratio |
|-------|------|------|------------|-----------|-----------|
| CNSF 2000-I (M) | 89 | 0.002083 | 0.9903 | 0.5189 | 3.0539 |
| CNSF 2000-I (F) | 89 | 0.002083 | 0.9903 | 0.5189 | 3.0539 |
| CNSF 2000-G (M) | 89 | 0.010622 | 0.8066 | 0.2607 | 1.4209 |
| CNSF 2000-G (F) | 89 | 0.010622 | 0.8066 | 0.2607 | 1.4209 |
| CNSFM 2013 | 101 | 0.010299 | 2.0708 | 0.3185 | 14.9373 |
| EMSSA 2009 (M) | 101 | 0.011225 | 1.7225 | 0.1786 | 8.8601 |
| EMSSA 2009 (F) | 101 | 0.016188 | 4.7692 | 0.3442 | 15.7752 |

### Detailed q_x ratios vs EMSSA 2009 (M), Pre-COVID

Ratio = projected_q_x / regulatory_q_x. Ratio > 1 means projected mortality exceeds EMSSA.

| Age | Projected q_x | EMSSA q_x | Ratio |
|-----|---------------|-----------|-------|
| 0 | 0.007929 | 0.000730 | 10.8620 |
| 1 | 0.000705 | 0.000730 | 0.9656 |
| 10 | 0.000176 | 0.000820 | 0.2147 |
| 20 | 0.000947 | 0.001040 | 0.9105 |
| 30 | 0.001422 | 0.001450 | 0.9810 |
| 40 | 0.002136 | 0.002180 | 0.9797 |
| 50 | 0.004642 | 0.003520 | 1.3187 |
| 60 | 0.010481 | 0.006040 | 1.7353 |
| 70 | 0.022289 | 0.010960 | 2.0336 |
| 80 | 0.054359 | 0.020950 | 2.5947 |
| 90 | 0.130659 | 0.045600 | 2.8653 |

---

## 7. COVID Impact on Premiums

SA = $1,000,000 MXN, i = 5%.

### Whole Life Annual Premiums

| Age | Pre-COVID ($) | Full ($) | Diff ($) | % Change |
|-----|--------------|----------|----------|----------|
| 25 | 5,374.89 | 5,605.12 | +230.23 | +4.28% |
| 30 | 6,707.29 | 6,981.78 | +274.50 | +4.09% |
| 35 | 8,440.71 | 8,771.23 | +330.51 | +3.92% |
| 40 | 10,736.41 | 11,147.56 | +411.15 | +3.83% |
| 45 | 13,757.57 | 14,251.92 | +494.35 | +3.59% |
| 50 | 17,745.18 | 18,340.39 | +595.21 | +3.35% |
| 55 | 22,926.22 | 23,676.16 | +749.94 | +3.27% |
| 60 | 29,829.25 | 30,796.41 | +967.16 | +3.24% |

### Term 20 Annual Premiums

| Age | Pre-COVID ($) | Full ($) | Diff ($) | % Change |
|-----|--------------|----------|----------|----------|
| 25 | 1,532.57 | 1,682.80 | +150.23 | +9.80% |
| 30 | 1,998.82 | 2,196.06 | +197.24 | +9.87% |
| 35 | 2,807.65 | 3,059.60 | +251.95 | +8.97% |
| 40 | 4,142.06 | 4,480.36 | +338.31 | +8.17% |
| 45 | 6,213.91 | 6,665.57 | +451.67 | +7.27% |
| 50 | 9,232.20 | 9,862.95 | +630.75 | +6.83% |
| 55 | 13,572.26 | 14,472.47 | +900.21 | +6.63% |
| 60 | 20,070.27 | 21,241.02 | +1,170.76 | +5.83% |

### Endowment 20 Annual Premiums

| Age | Pre-COVID ($) | Full ($) |
|-----|--------------|----------|
| 25 | 29,665.46 | 29,748.46 |
| 30 | 29,881.45 | 29,986.77 |
| 35 | 30,241.01 | 30,380.19 |
| 40 | 30,891.40 | 31,088.09 |
| 45 | 31,960.28 | 32,211.97 |
| 50 | 33,629.27 | 33,960.97 |
| 55 | 36,009.90 | 36,512.50 |
| 60 | 39,597.17 | 40,360.19 |

---

## 8. Confidence Intervals (90% CI, 1000 simulations)

### Pre-COVID, year 2029

| Age | Optimistic q_x | Central q_x | Pessimistic q_x |
|-----|---------------|-------------|-----------------|
| 30 | 0.001313 | 0.001438 | 0.001581 |
| 40 | 0.001911 | 0.002167 | 0.002474 |
| 50 | 0.004358 | 0.004680 | 0.005045 |
| 60 | 0.010012 | 0.010544 | 0.011134 |
| 70 | 0.021342 | 0.022416 | 0.023602 |
| 80 | 0.053322 | 0.054498 | 0.055759 |

### Full period, year 2034

| Age | Optimistic q_x | Central q_x | Pessimistic q_x |
|-----|---------------|-------------|-----------------|
| 30 | 0.001481 | 0.001566 | 0.001661 |
| 40 | 0.002167 | 0.002368 | 0.002598 |
| 50 | 0.004840 | 0.005055 | 0.005292 |
| 60 | 0.010838 | 0.011187 | 0.011566 |
| 70 | 0.023367 | 0.023994 | 0.024670 |
| 80 | 0.055306 | 0.056045 | 0.056831 |

---

## 9. Pipeline Code

```python
# Full pipeline call sequence
data = MortalityData.from_inegi(
    deaths_filepath="backend/data/inegi/inegi_deaths.csv",
    population_filepath="backend/data/conapo/conapo_population.csv",
    sex="Total", year_start=1990, year_end=2019, age_max=100
)

graduated = GraduatedRates(data, lambda_param=1e5)
lc = LeeCarter.fit(graduated, reestimate_kt=False)
projection = MortalityProjection(lc, horizon=30, n_simulations=1000, random_seed=42)

# Bridge to actuarial engine
projected_lt = projection.to_life_table(year=2029)
comm = CommutationFunctions(projected_lt, interest_rate=0.05)
pc = PremiumCalculator(comm)
premium = pc.whole_life(SA=1_000_000, x=40)

# Regulatory validation
reg_lt = LifeTable.from_regulatory_table("backend/data/cnsf/emssa_2009.csv", sex="male")
comp = MortalityComparison(projected_lt, reg_lt, name="EMSSA 2009")
print(comp.summary())
```

---

## 10. File Locations

| File | Purpose |
|------|---------|
| `backend/analysis/mexico_lee_carter.py` | Analysis script (both periods + comparison) |
| `backend/analysis/results/mexico_pre_covid_2019.txt` | Pre-COVID full report |
| `backend/analysis/results/mexico_full_2024.txt` | Full period report |
| `backend/analysis/results/mexico_covid_comparison.txt` | Side-by-side COVID comparison |
| `backend/data/inegi/inegi_deaths.csv` | INEGI death counts (gitignored, real data) |
| `backend/data/conapo/conapo_population.csv` | CONAPO population (gitignored, real data) |
| `backend/data/cnsf/cnsf_2000_i.csv` | CNSF 2000-I regulatory table (gitignored) |
| `backend/data/cnsf/cnsf_2000_g.csv` | CNSF 2000-G regulatory table (gitignored) |
| `backend/data/cnsf/cnsf_2013.csv` | CNSFM 2013 regulatory table (gitignored) |
| `backend/data/cnsf/emssa_2009.csv` | EMSSA 2009 regulatory table (gitignored) |
