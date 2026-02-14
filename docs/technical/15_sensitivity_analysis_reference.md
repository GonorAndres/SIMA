# Sensitivity Analysis -- Technical Reference

**Module:** `backend/analysis/sensitivity_analysis.py`
**Dependencies:** `a01_life_table`, `a02_commutation`, `a04_premiums`, `a05_reserves`, `a06_mortality_data`, `a07_graduation`, `a08_lee_carter`, `a09_projection`

---

## 1. Interest Rate Sensitivity

### 1.1 Formulas

$$P_{\text{whole life}} = SA \cdot \frac{M_x}{N_x}$$

$$P_{\text{term } n} = SA \cdot \frac{M_x - M_{x+n}}{N_x - N_{x+n}}$$

$$P_{\text{endowment } n} = SA \cdot \frac{M_x - M_{x+n} + D_{x+n}}{N_x - N_{x+n}}$$

Transmission mechanism: $v = \frac{1}{1+i}$, $D_x = v^x \cdot l_x$. Changing $i$ changes $v$, which changes every $D_x$, $N_x$, $C_x$, $M_x$.

### 1.2 Parameters

```python
INTEREST_RATES = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
BASE_RATE = 0.05
SA = 1_000_000
```

### 1.3 Premium Results (Age 40, Whole Life, SA = $1M)

| i | Premium ($) | % vs base (i=5%) |
|---|------------|-------------------|
| 2% | 17,910 | +66.4% |
| 3% | 15,019 | +39.5% |
| 4% | 12,666 | +17.7% |
| 5% | 10,765 | 0.0% (base) |
| 6% | 9,233 | -14.2% |
| 7% | 8,003 | -25.7% |
| 8% | 7,014 | -34.8% |

### 1.4 Product Sensitivity Ranking (Age 40, i = 2% to 8%)

| Product | Spread | Reason |
|---------|--------|--------|
| Whole life | 101% | Long duration, discount compounds over decades |
| Endowment 20 | 37% | Mixed: savings + mortality; savings component is rate-sensitive |
| Term 20 | 11% | Short duration, less discounting effect |

### 1.5 Reserve Trajectory (Whole Life, Age 35, SA = $1M)

| Duration | i=2% | i=5% | i=8% |
|----------|------|------|------|
| 0 | 0 | 0 | 0 |
| 10 | 148,661 | 86,657 | 52,058 |
| 20 | 313,581 | 205,376 | 136,329 |
| 30 | 485,164 | 354,306 | 258,628 |

---

## 2. Mortality Shock Sensitivity

### 2.1 Shock Method

```
shocked_q_x = min(base_q_x * factor, 1.0)
l_{x+1} = l_x * (1 - shocked_q_x)
terminal: q_omega = 1.0
```

### 2.2 Parameters

```python
SHOCK_FACTORS = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]
```

### 2.3 Premium Results (Age 40, i=5%, SA = $1M)

| Factor | Whole Life ($) | % chg | Term 20 ($) | % chg | Endowment 20 ($) | % chg |
|--------|---------------|-------|-------------|-------|-------------------|-------|
| 0.70 | 8,807 | -18.2% | 2,931 | -29.7% | 30,276 | -2.1% |
| 0.80 | 9,490 | -11.8% | 3,346 | -19.8% | 30,487 | -1.4% |
| 0.90 | 10,141 | -5.8% | 3,759 | -9.9% | 30,699 | -0.7% |
| 1.00 | 10,765 | 0.0% | 4,172 | 0.0% | 30,910 | 0.0% |
| 1.10 | 11,365 | +5.6% | 4,583 | +9.9% | 31,122 | +0.7% |
| 1.20 | 11,944 | +11.0% | 4,994 | +19.7% | 31,334 | +1.4% |
| 1.30 | 12,506 | +16.2% | 5,403 | +29.5% | 31,546 | +2.1% |

### 2.4 Key Property: Asymmetry

- +30% shock: whole life +16.2%; -30% shock: -18.2%
- Term is nearly proportional: ~30% shock produces ~30% premium change
- Endowment is nearly insensitive: ~2% change at age 40

---

## 3. Cross-Country Comparison

### 3.1 Data Sources

| Country | Source | Sex | Years | Ages |
|---------|--------|-----|-------|------|
| Mexico | INEGI/CONAPO | Total | 1990-2019 | 0-100 |
| USA | HMD | Male | 1990-2019 | 0-100 |
| Spain | HMD | Male | 1990-2019 | 0-100 |

### 3.2 Lee-Carter Parameters

| Parameter | Mexico | USA | Spain |
|-----------|--------|-----|-------|
| Explained var | 0.7767 | 0.8666 | 0.9481 |
| RMSE (log) | 0.0618 | 0.0558 | 0.0753 |
| Drift | -1.0764 | -1.1920 | -2.8949 |
| Sigma | 1.7889 | 1.4576 | 2.3622 |
| k_t range | 23.3 to -7.9 | 21.7 to -12.8 | 42.6 to -41.3 |

### 3.3 Projected q_x (Year 2029, 1000*q_x)

| Age | Mexico | USA | Spain |
|-----|--------|-----|-------|
| 0 | 8.178 | 5.215 | 1.326 |
| 40 | 2.167 | 1.966 | 0.621 |
| 60 | 10.545 | 10.018 | 6.836 |
| 80 | 54.498 | 50.549 | 42.753 |

### 3.4 Premium Comparison (Whole Life, i=5%, SA = $1M)

| Age | Mexico ($) | USA ($) | Spain ($) |
|-----|-----------|---------|----------|
| 25 | 5,394 | 5,158 | 3,753 |
| 40 | 10,765 | 10,178 | 8,191 |
| 60 | 29,870 | 27,165 | 23,745 |

### 3.5 a_x Profile (Selected Ages)

| Age | Mexico | USA | Spain |
|-----|--------|-----|-------|
| 0 | -4.263 | -4.966 | -5.811 |
| 40 | -5.877 | -5.968 | -6.447 |
| 60 | -4.441 | -4.383 | -4.608 |

### 3.6 b_x Profile (Selected Ages)

| Age | Mexico | USA | Spain |
|-----|--------|-----|-------|
| 0 | 0.0288 | 0.0116 | 0.0116 |
| 30 | 0.0098 | 0.0059 | 0.0205 |
| 70 | 0.0054 | 0.0133 | 0.0068 |

---

## 4. Sanity Checks

| Check | Expected | Verified |
|-------|----------|----------|
| P decreases as i increases | Yes at all ages | PASS |
| Endowment > Term | At all ages/rates | PASS |
| Factor 1.00 = base | 0% change | PASS |
| Higher mortality -> higher P | At all ages/factors | PASS |
| Reserve(t=0) = 0 | Equivalence principle | PASS |
| All countries: explained_var > 50% | Yes | PASS |
| All countries: negative drift | Yes | PASS |
| sum(b_x) = 1, sum(k_t) = 0 | Identifiability | PASS |

---

## 5. API Reference

### 5.1 Functions

```python
build_shocked_life_table(base_lt, shock_factor, radix=100_000.0) -> LifeTable
```
Applies multiplicative shock to all q_x values. Caps at 1.0. Rebuilds l_x from radix.

```python
run_country_pipeline(country, sex="Total", year_start=1990, year_end=2019) -> dict
```
Loads data, graduates, fits Lee-Carter, projects 10 years, builds LifeTable. Returns dict with keys: `life_table`, `lee_carter`, `projection`.

```python
compute_premiums_at_rate(life_table, interest_rate) -> dict[age, dict[product, float]]
```
Builds CommutationFunctions at given rate. Computes whole life, term 20, endowment 20 premiums at each age in `PREMIUM_AGES`.

```python
compute_reserve_trajectory(life_table, interest_rate, age, product, n=None) -> List[Tuple[int, float]]
```
Computes reserve at each policy duration from 0 to max duration.

### 5.2 Constants

```python
INTEREST_RATES = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
SHOCK_FACTORS = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]
PREMIUM_AGES = [25, 30, 35, 40, 45, 50, 55, 60]
SA = 1_000_000
BASE_RATE = 0.05
TARGET_YEAR_OFFSET = 10
```

---

## 6. File Locations

| File | Purpose |
|------|---------|
| `backend/analysis/sensitivity_analysis.py` | Analysis script |
| `backend/analysis/results/sensitivity_interest_rate.txt` | Interest rate report |
| `backend/analysis/results/sensitivity_mortality_shock.txt` | Mortality shock report |
| `backend/analysis/results/sensitivity_cross_country.txt` | Cross-country report |
| `backend/analysis/results/sensitivity_summary.txt` | Executive summary |
