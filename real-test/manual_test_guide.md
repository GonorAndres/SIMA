# SIMA Manual Test Guide

Comprehensive validation checklist for the SIMA web application.
Every assertion in this document can be verified against the running API.
Designed for both runtime validation and interview preparation.

**Total assertions: 95+**

---

## Section 0: Setup & Prerequisites

### Starting the Application

```bash
# Terminal 1: Backend (from project root)
/home/andtega349/SIMA/venv/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (from project root)
cd /home/andtega349/SIMA/frontend && npx vite --host 0.0.0.0 --port 5173
```

**API Base URL:** `http://localhost:8000`
**Frontend URL:** `http://localhost:5173`

### Data Sources

| Source | Details |
|--------|---------|
| Mortality data | INEGI deaths + CONAPO population, sex="Total", 1990-2020, ages 0-100 |
| Graduation | Whittaker-Henderson, lambda=1e5, diff_order=2, weight_by_exposure=True |
| Lee-Carter | `LeeCarter.fit(graduated, reestimate_kt=False)` |
| Projection | 30-year horizon, 500 simulations, seed=42 |
| Regulatory tables | CNSF 2000-I (male), EMSSA 2009 (male), ages 0-99 |
| Interest rate | 5% (i=0.05) default for pricing and SCR |

Reference: `backend/api/services/precomputed.py:72-112`

### Default Portfolio (12 Policies)

| ID | Type | Issue Age | SA / Pension | Term | Duration | Attained Age |
|----|------|-----------|-------------|------|----------|-------------|
| WL-01 | whole_life | 25 | $2,000,000 | -- | 10 | 35 |
| WL-02 | whole_life | 35 | $1,500,000 | -- | 5 | 40 |
| WL-03 | whole_life | 45 | $1,000,000 | -- | 5 | 50 |
| WL-04 | whole_life | 55 | $500,000 | -- | 0 | 55 |
| TM-05 | term | 30 | $3,000,000 | 20 | 5 | 35 |
| TM-06 | term | 40 | $2,000,000 | 20 | 10 | 50 |
| TM-07 | term | 50 | $1,000,000 | 20 | 3 | 53 |
| EN-08 | endowment | 30 | $1,500,000 | 20 | 8 | 38 |
| EN-09 | endowment | 40 | $1,000,000 | 20 | 5 | 45 |
| AN-10 | annuity | 60 | $120,000/yr | -- | 0 | 60 |
| AN-11 | annuity | 65 | $150,000/yr | -- | 0 | 65 |
| AN-12 | annuity | 70 | $100,000/yr | -- | 0 | 70 |

Reference: `backend/engine/a11_portfolio.py:288-319`

---

## Section 1: Inicio Page

### 1.1 MetricBlocks

**Source:** Inicio page fetches `/mortality/lee-carter` and `/mortality/projection`

| Metric | Expected Range | Source Field |
|--------|---------------|-------------|
| Explained variance | 70%-85% (~77.7% for Mexican data) | `explained_variance` |
| Drift | -1.5 to -0.5 (~-1.076) | `drift` |
| Projected q_60 (2029) | 0.008 - 0.015 | from `/mortality/projection?projection_year=2029` |

**Assertion 1:** `explained_variance` is in `[0.70, 0.85]`
**Assertion 2:** `drift < 0` (mortality is improving over time)
**Assertion 3:** `drift` value on Inicio matches `/mortality/lee-carter` response exactly

### 1.2 COVID Teaser

**Source:** Inicio page fetches `/sensitivity/covid-comparison`

| Metric | Expected Value |
|--------|---------------|
| Pre-COVID drift | -1.076431 |
| Full-period drift | -0.854812 |
| Drift shift | ~0.22 (pre_covid.drift - full_period.drift is more negative) |
| Premium impact age 40 | ~3.83% |

**Assertion 4:** `pre_covid.drift` is more negative than `full_period.drift`
**Assertion 5:** All `premium_impact[i].pct_change > 0` (COVID increases premiums for all ages)
**Assertion 6:** Premium impact values are between 3% and 5%

### 1.3 Gotcha Questions

> **Q:** "Why is explained_variance only 77.7%? Is that bad?"
>
> **A:** Mexican data has COVID noise, structural breaks (drug violence spikes, healthcare expansion), and the young-adult accident hump that violates the Lee-Carter assumption of time-invariant b_x. Spain gets 94.8% because its data is cleaner. The ~78% is reasonable and consistent with published studies on developing-country mortality data.

> **Q:** "The drift is -1.08. What does that mean in practical terms?"
>
> **A:** k_t decreases by ~1.08 per year, so exp(b_x * (-1.08)) decreases mortality at each age. For an age where b_x ~ 0.01, that is roughly a 1% annual mortality improvement. Over 30 years, mortality at that age would decrease by ~26%.

---

## Section 2: Mortalidad Page

### 2.1 Data Summary Tab

**Endpoint:** `GET /mortality/data/summary`

```bash
curl http://localhost:8000/mortality/data/summary
```

| Field | Expected Value |
|-------|---------------|
| `age_range` | `[0, 100]` |
| `year_range` | `[1990, 2020]` |
| `shape` | `[101, 31]` |
| `mx_min` | > 0 (all mortality rates positive) |
| `mx_max` | < 1.0 (central death rate, not q_x) |

**Assertion 7:** `shape[0] == 101` (ages 0 through 100 inclusive)
**Assertion 8:** `shape[1] == 31` (years 1990 through 2020 inclusive)
**Assertion 9:** `mx_min > 0`
**Assertion 10:** `mx_max < 1.0`

**Gotcha:**

> **Q:** "Why 31 years for 1990-2020?"
>
> **A:** Inclusive endpoints: 2020 - 1990 + 1 = 31 years. This is a common off-by-one confusion.

### 2.2 Graduation Tab

**Endpoint:** `GET /mortality/graduation`

```bash
curl http://localhost:8000/mortality/graduation
```

| Field | Expected |
|-------|----------|
| `roughness_reduction` | > 90% (Whittaker-Henderson smooths heavily at lambda=1e5) |
| `lambda_param` | 100000.0 |
| `graduated_mx` | Smooth curve, no sign reversals in 2nd differences |
| Mean of `residuals` | Near 0 (unbiased smoother) |

**Assertion 11:** `roughness_reduction > 90`
**Assertion 12:** `lambda_param == 100000.0`
**Assertion 13:** `len(ages) == len(raw_mx) == len(graduated_mx) == len(residuals)`
**Assertion 14:** Mean of `residuals` is within `[-0.1, 0.1]` (approximately unbiased)
**Assertion 15:** All `graduated_mx[i] > 0` (no negative mortality rates)

**Gotcha:**

> **Q:** "What happens if lambda is too large?"
>
> **A:** Over-smoothing. The graduated curve approaches a polynomial of degree (diff_order - 1). Since diff_order=2, it would approach a straight line. You lose the Gompertz curvature at old ages and the infant mortality spike. The optimal lambda balances fidelity (fit) vs smoothness (roughness penalty).

> **Q:** "Why Whittaker-Henderson instead of Gompertz-Makeham?"
>
> **A:** Non-parametric. It preserves local features (infant spike, young-adult hump) without forcing a parametric shape. One tuning parameter (lambda) vs fitting multiple parametric coefficients. Better for irregular mortality data like Mexico with structural breaks.

Reference: `backend/engine/a07_graduation.py`, `backend/api/services/mortality_service.py:105-138`

### 2.3 Lee-Carter Parameters Tab

**Endpoint:** `GET /mortality/lee-carter`

```bash
curl http://localhost:8000/mortality/lee-carter
```

**Identifiability Constraints (exact):**

**Assertion 16:** `sum(bx) = 1.0` within `1e-6`
**Assertion 17:** `mean(kt) = 0.0` within `1e-6`
**Assertion 18:** All `bx[i] > 0` (positive mortality sensitivity at every age)

**Model Quality:**

**Assertion 19:** `explained_variance` in `[0.70, 0.85]`
**Assertion 20:** `drift < 0` (mortality improving)
**Assertion 21:** `len(ages) == 101` (ages 0-100)
**Assertion 22:** `len(years) == 31` (years 1990-2020)
**Assertion 23:** `len(ax) == len(ages)` and `len(bx) == len(ages)` and `len(kt) == len(years)`

**SVD Reconstruction Identity:**

For each year j: `mean(ax + bx * kt[j])` should equal `mean(log_mx[:, j])` within `1e-4`.
This verifies the SVD decomposition is correctly reconstructing the observed log-mortality surface.

**Assertion 24:** SVD reconstruction error < 1e-4 for each year

**Gotcha:**

> **Q:** "What does negative drift mean?"
>
> **A:** k_t is decreasing over time. Since ln(m_{x,t}) = a_x + b_x * k_t, a decreasing k_t means ln(m) decreases, so m_x decreases, so mortality improves. Negative drift = mortality improvement = good.

> **Q:** "Why use reestimate_kt=False for graduated data?"
>
> **A:** Graduation can create negative b_x at some ages (77, 78, 85 in Mexican data). When b_x < 0, the death residual function used in k_t re-estimation becomes non-monotone (U-shaped), causing brentq to fail. SVD k_t is mathematically consistent with the log-bilinear formulation even without re-estimation.

Reference: `backend/engine/a08_lee_carter.py`, `backend/api/services/mortality_service.py:42-57`

### 2.4 Surface Tab

**Endpoint:** `GET /mortality/surface`

```bash
curl http://localhost:8000/mortality/surface
```

**Assertion 25:** `len(ages) == 101` and `len(years) == 31`
**Assertion 26:** `len(log_mx) == 101` and `len(log_mx[0]) == 31` (matrix dimensions match)
**Assertion 27:** For ages > 10, `log_mx` increases monotonically with age for each year (Gompertz law)
**Assertion 28:** For most ages, `log_mx` generally decreases with calendar year (mortality improvement)

**Gotcha:**

> **Q:** "Why log-scale for the surface?"
>
> **A:** log(m_x) is approximately linear in age (Gompertz law: ln(m_x) ~ alpha + beta*x) and approximately linear in time (Lee-Carter: ln(m_{x,t}) = a_x + b_x*k_t). The log surface is approximately planar, making patterns easier to see. On the original scale, the exponential growth with age would obscure everything.

Reference: `backend/api/services/mortality_service.py:141-156`

### 2.5 Validation Tab (CNSF/EMSSA)

**Endpoint:** `GET /mortality/validation?projection_year=2040&table_type=cnsf`

```bash
curl "http://localhost:8000/mortality/validation?projection_year=2040&table_type=cnsf"
```

**Assertion 29:** `mean_ratio` between 0.5 and 1.5
**Assertion 30:** `rmse < 0.05` (reasonable agreement)
**Assertion 31:** `n_ages > 0`
**Assertion 32:** `len(qx_ratios) == len(ages)`

Expected for CNSF: `mean_ratio ~ 0.95` (projected slightly below regulatory)

**Gotcha:**

> **Q:** "Why would projected q_x be below the regulatory table?"
>
> **A:** CNSF 2000-I is based on year-2000 mortality experience. Mortality has improved since then (20+ years of improvement). So a Lee-Carter projection to 2040 should project LOWER mortality than a table frozen at year-2000 levels. mean_ratio < 1 means "projected is lower than regulatory" which is correct and expected.

> **Q:** "What about EMSSA 2009?"
>
> **A:** EMSSA 2009 is designed for social security pensioners. At ages 60+, the ratio goes to 1.7-2.9, meaning projected mortality is much HIGHER than EMSSA assumes. This suggests EMSSA is optimistic for current mortality experience at older ages -- a known regulatory concern.

Reference: `backend/api/services/mortality_service.py:188-221`

### 2.6 Diagnostics Tab

**Endpoint:** `GET /mortality/diagnostics`

```bash
curl http://localhost:8000/mortality/diagnostics
```

**Assertion 33:** `explained_variance` matches the value from `/mortality/lee-carter` **exactly**
**Assertion 34:** `rmse > 0` (no perfect fit expected)
**Assertion 35:** `max_abs_error > rmse` (max error always exceeds average)
**Assertion 36:** `mean_abs_error > 0`
**Assertion 37:** Mean of `residuals_sample[i].residual` is near 0 (no systematic bias)

**Gotcha:**

> **Q:** "What would systematic residuals indicate?"
>
> **A:** Model misspecification. If residuals show a pattern by age or year, it means the rank-1 SVD approximation is insufficient. You might need a second component (rank-2 Lee-Carter), or b_x may need to be time-varying (Renshaw-Haberman extension). Mexican COVID years likely show large positive residuals (actual mortality >> fitted).

Reference: `backend/api/services/mortality_service.py:159-185`

---

## Section 3: Precios Page

The most formula-intensive section. All tests use CNSF 2000-I (male), i=0.05 unless stated.

### 3.1 Premium Calculations

**Endpoint:** `POST /pricing/premium`

```bash
# Whole life, age 40, SA=1,000,000, i=0.05
curl -X POST http://localhost:8000/pricing/premium \
  -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"interest_rate":0.05}'
```

#### Test Case 1: Whole Life, Age 40

Formula: `P_WL = SA * M_40 / N_40`

**Assertion 38:** `annual_premium` is in `[$8,000, $15,000]` for SA=1M
**Assertion 39:** `premium_rate` (= premium/SA) is in `[0.008, 0.015]`

#### Test Case 2: Term 20yr, Age 40

Formula: `P_term = SA * (M_40 - M_60) / (N_40 - N_60)`

```bash
curl -X POST http://localhost:8000/pricing/premium \
  -H "Content-Type: application/json" \
  -d '{"product_type":"term","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}'
```

**Assertion 40:** `P_term < P_WL` (term is strictly cheaper than whole life)
**Assertion 41:** `P_term` is roughly 1/3 to 1/2 of `P_WL`

#### Test Case 3: Endowment 20yr, Age 40

Formula: `P_endow = SA * (M_40 - M_60 + D_60) / (N_40 - N_60)`

```bash
curl -X POST http://localhost:8000/pricing/premium \
  -H "Content-Type: application/json" \
  -d '{"product_type":"endowment","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}'
```

**Assertion 42:** `P_endow > P_WL` (endowment most expensive)
**Assertion 43:** `P_endow > P_term` (endowment > term, always)

#### Test Case 4: Pure Endowment 20yr, Age 40

Formula: `P_pure = SA * D_60 / (N_40 - N_60)`

```bash
curl -X POST http://localhost:8000/pricing/premium \
  -H "Content-Type: application/json" \
  -d '{"product_type":"pure_endowment","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}'
```

**Assertion 44:** `P_endow = P_term + P_pure` within $0.01 (exact decomposition)

This is because:
```
(M_40 - M_60 + D_60) / (N_40 - N_60) = (M_40 - M_60)/(N_40 - N_60) + D_60/(N_40 - N_60)
```

#### Product Ordering Invariant

**Assertion 45:** For ANY age in [20, 60] with n=20 and i=0.05:
```
P_term < P_whole_life < P_endowment
P_pure_endowment < P_endowment
```

Test by looping ages 20, 30, 40, 50, 60 and verifying the ordering holds at each.

#### Age Monotonicity

**Assertion 46:** For whole life: `P(age=30) < P(age=40) < P(age=50) < P(age=60)`

Older issue age means fewer years of premium collection to fund the same benefit, so premiums must be higher.

Reference: `backend/engine/a04_premiums.py:61-84` (whole_life), `a04_premiums.py:86-125` (term), `a04_premiums.py:127-171` (endowment), `a04_premiums.py:173-207` (pure_endowment)

### 3.2 Fundamental Identity Check

**Endpoint:** `GET /pricing/commutation?age=40&interest_rate=0.05`

```bash
curl "http://localhost:8000/pricing/commutation?age=40&interest_rate=0.05"
```

Returns: `D_x, N_x, C_x, M_x, A_x, a_due_x`

**THE FUNDAMENTAL IDENTITY:**
```
A_x + d * a_due_x = 1    where d = i/(1+i) = 0.05/1.05 = 0.047619...
```

**Assertion 47:** `|A_x + d * a_due_x - 1.0| < 1e-6` at age 40
**Assertion 48:** Same identity holds at ages 0, 20, 60, 80, 99

Test script:
```bash
for age in 0 20 40 60 80 99; do
  curl -s "http://localhost:8000/pricing/commutation?age=$age&interest_rate=0.05" | \
  python3 -c "
import json,sys; d=json.load(sys.stdin)
result = d['A_x'] + (0.05/1.05) * d['a_due_x']
print(f'Age {d[\"age\"]}: A_x={d[\"A_x\"]:.6f}, a_due_x={d[\"a_due_x\"]:.6f}, A+d*a={result:.10f}, error={abs(result-1.0):.2e}')
"
done
```

**Gotcha:**

> **Q:** "Why does A_x + d * a_x = 1? Prove it."
>
> **A:** A person alive at age x MUST eventually die. A_x is the APV of $1 paid at death. d*a_x is the APV of the "discount earned" by deferring payment while alive. Together they exhaust all probability mass. Algebraically: A_x = 1 - d*a_x because the whole-life insurance is a sequence of one-year deferrals: A_x = v*q_x + v*p_x*A_{x+1}, and a_x = 1 + v*p_x*a_{x+1}. Combining gives the identity.

> **Q:** "Why does this matter for validation?"
>
> **A:** It is a mathematical certainty that must hold for any consistent life table and interest rate. If it fails by more than floating-point error, something is wrong with the commutation function computation. It is the actuarial equivalent of checking that probabilities sum to 1.

### 3.3 Commutation Function Properties

Using the commutation endpoint at multiple ages, verify:

**Assertion 49:** `D_x > 0` for all ages (discounted survivors, never negative)
**Assertion 50:** `D_x` strictly decreasing with age
**Assertion 51:** `N_x > N_{x+1}` for all x (cumulative sum, strictly decreasing)
**Assertion 52:** `C_x >= 0` for all ages (discounted deaths, non-negative)
**Assertion 53:** `M_x >= M_{x+1}` for all x (cumulative, non-increasing)

**Recursion identities** (verify numerically at a few ages):

**Assertion 54:** `N_x = D_x + N_{x+1}` (exact, within floating-point tolerance)
**Assertion 55:** `M_x = C_x + M_{x+1}` (exact, within floating-point tolerance)

To test recursion: fetch commutation at ages 40 and 41, then verify N_40 = D_40 + N_41.

Reference: `backend/engine/a02_commutation.py:117-132` (N backward recursion), `a02_commutation.py:148-163` (M backward recursion)

### 3.4 Reserve Trajectory

**Endpoint:** `POST /pricing/reserve`

#### Whole Life, Age 40

```bash
curl -X POST http://localhost:8000/pricing/reserve \
  -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"interest_rate":0.05}'
```

**Assertion 56:** `trajectory[0].reserve` is within $0.01 of 0 (0V = 0, equivalence principle)
**Assertion 57:** Reserve is strictly increasing with duration (monotone)
**Assertion 58:** Reserve approaches SA ($1,000,000) as attained age approaches omega
**Assertion 59:** `trajectory[t].reserve > 0` for all t > 0

#### Term 20yr, Age 40

```bash
curl -X POST http://localhost:8000/pricing/reserve \
  -H "Content-Type: application/json" \
  -d '{"product_type":"term","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}'
```

**Assertion 60:** `trajectory[0].reserve` ~ 0 (equivalence at issue)
**Assertion 61:** `trajectory[20].reserve` = 0 (policy expired, no liability)
**Assertion 62:** Reserve has a hump shape: rises then falls (NOT monotone)

#### Endowment 20yr, Age 40

```bash
curl -X POST http://localhost:8000/pricing/reserve \
  -H "Content-Type: application/json" \
  -d '{"product_type":"endowment","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}'
```

**Assertion 63:** `trajectory[0].reserve` ~ 0
**Assertion 64:** `trajectory[20].reserve` = SA exactly ($1,000,000)
**Assertion 65:** Reserve is strictly increasing (always, for endowment)

**Gotcha:**

> **Q:** "Why does the term reserve go back to zero?"
>
> **A:** At expiry (t=n), there is no death benefit remaining AND no future premiums. The net liability is zero. The reserve "hump" reflects the insurer accumulating funds mid-term to cover the increasing mortality risk, then releasing them as coverage winds down.

> **Q:** "Why is 0V exactly zero?"
>
> **A:** This IS the equivalence principle. At issue: 0V = SA * A_x - P * a_x. But P was defined so that P * a_x = SA * A_x, so 0V = 0. If you get a nonzero initial reserve, your premium formula is wrong.

Reference: `backend/engine/a05_reserves.py:57-101` (whole_life), `a05_reserves.py:103-142` (term), `a05_reserves.py:144-183` (endowment)

### 3.5 Interest Rate Sensitivity

**Endpoint:** `POST /pricing/sensitivity`

```bash
curl -X POST http://localhost:8000/pricing/sensitivity \
  -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"rates":[0.02,0.03,0.04,0.05,0.06,0.07,0.08]}'
```

**Assertion 66:** Premium is monotonically DECREASING with interest rate
**Assertion 67:** Spread from i=2% to i=8% is at least 80% of the i=5% premium (substantial sensitivity)

Example expected: at i=2% ~$17,910 vs i=8% ~$7,014 = ~155% spread relative to i=5% premium

**Gotcha:**

> **Q:** "Why does higher interest rate mean lower premium?"
>
> **A:** Higher interest rate means the money collected as premiums earns more investment income. The insurer needs fewer premium dollars today because each dollar grows faster. Equivalently, future benefit payments are discounted more heavily, so the present value of benefits (numerator) shrinks faster than the present value of premium income (denominator).

Reference: `backend/api/services/pricing_service.py:131-169`

---

## Section 4: Sensibilidad Page

### 4.1 Mortality Shock Sweep

**Endpoint:** `POST /sensitivity/mortality-shock`

```bash
curl -X POST http://localhost:8000/sensitivity/mortality-shock \
  -H "Content-Type: application/json" \
  -d '{"age":40,"sum_assured":1000000,"product_type":"whole_life"}'
```

Default factors: `[-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30]`

**Assertion 68:** `factor=0` gives `base_premium` exactly (pct_change=0)
**Assertion 69:** Positive factors increase premium, negative factors decrease it
**Assertion 70:** **Asymmetry**: `|pct_change(-30%)| > |pct_change(+30%)|`
  - Expected: -30% shock ~ -18% premium change; +30% shock ~ +16% premium change

**Product Comparison** (run with different product_types):

**Assertion 71:** Term premiums are most proportional to mortality shocks (~30% shock -> ~30% change)
**Assertion 72:** Endowment premiums are least sensitive to mortality (savings component dominates)

**Gotcha:**

> **Q:** "Why the asymmetry in mortality shock response?"
>
> **A:** The premium is M_x/N_x. When q_x changes by a factor (1+f), both the numerator (death benefit APV) and the denominator (annuity-due APV) shift, but not proportionally. This creates actuarial convexity, analogous to bond convexity. Specifically, the denominator (representing survival) changes in the opposite direction to mortality, amplifying downward shocks and dampening upward shocks.

Reference: `backend/api/services/sensitivity_service.py:60-103`

### 4.2 Cross-Country Data

**Endpoint:** `GET /sensitivity/cross-country`

```bash
curl http://localhost:8000/sensitivity/cross-country
```

This returns hardcoded comparison data for Mexico, USA (Estados Unidos), and Spain (Espana).

**Assertion 73:** Drift ordering: Spain (-2.89) < USA (-1.19) < Mexico (-1.08)
  - Spain has fastest mortality improvement
**Assertion 74:** Explained variance ordering: Spain (0.948) > USA (0.867) > Mexico (0.777)
  - Spain has cleanest Lee-Carter fit
**Assertion 75:** Premium ordering at age 40: Spain (8191) < USA (10178) < Mexico (10765)
  - Lower mortality + faster improvement = cheaper premiums
**Assertion 76:** `len(kt_profiles) == 3` (one per country)
**Assertion 77:** `len(ax_profiles) == 3` and `len(bx_profiles) == 3`

**Exact hardcoded values** (from `sensitivity_service.py:108-111`):

| Country | drift | explained_var | sigma | q60 | premium_age40 |
|---------|-------|--------------|-------|-----|--------------|
| Mexico | -1.0764 | 0.7767 | 1.7889 | 0.010545 | 10765 |
| Estados Unidos | -1.1920 | 0.8666 | 1.4576 | 0.010018 | 10178 |
| Espana | -2.8949 | 0.9481 | 2.3622 | 0.006836 | 8191 |

**Gotcha:**

> **Q:** "Why is Mexico's Lee-Carter fit the worst?"
>
> **A:** Mexico had more structural breaks in 1990-2020 that violate the LC assumption of time-invariant b_x: the drug violence spike (2006-2012), rapid healthcare expansion, and COVID-19. These create heterogeneous mortality shocks that a single time factor k_t cannot capture. Spain's mortality decline is smoother and more uniform across ages.

### 4.3 COVID Comparison

**Endpoint:** `GET /sensitivity/covid-comparison`

```bash
curl http://localhost:8000/sensitivity/covid-comparison
```

**Assertion 78:** `pre_covid.drift` (-1.076431) is more negative than `full_period.drift` (-0.854812)
**Assertion 79:** `pre_covid.explained_var` (0.7767) > `full_period.explained_var` (0.5347)
**Assertion 80:** All `premium_impact[i].pct_change > 0` (COVID always increases premiums)
**Assertion 81:** `premium_impact` is sorted by age ascending
**Assertion 82:** Premium impact values are all between 3% and 5%

**Exact hardcoded premium impacts** (from `sensitivity_service.py:159-168`):

| Age | Pre-COVID Premium | Full-Period Premium | % Change |
|-----|------------------|-------------------|----------|
| 25 | 5,375 | 5,605 | 4.28% |
| 30 | 6,707 | 6,982 | 4.09% |
| 35 | 8,441 | 8,771 | 3.92% |
| 40 | 10,736 | 11,148 | 3.83% |
| 45 | 13,758 | 14,252 | 3.59% |
| 50 | 17,745 | 18,340 | 3.35% |
| 55 | 22,926 | 23,676 | 3.27% |
| 60 | 29,829 | 30,796 | 3.24% |

**Gotcha:**

> **Q:** "Why does COVID affect premiums permanently?"
>
> **A:** Lee-Carter is fitted on ALL years in the data window. Adding 2020-2024 with high mortality pulls the drift toward zero (slower improvement). Since k_t is projected forward using this drift, ALL future projected mortality is higher forever. This is not a one-time spike in premium -- it is a structural shift in the trend. The premium increases 3-4% because 30 years of compounded slower improvement is significant.

---

## Section 5: Capital Page (SCR)

### 5.1 Portfolio Summary

**Endpoint:** `GET /portfolio/summary`

```bash
curl http://localhost:8000/portfolio/summary
```

**Assertion 83:** `n_policies == 12`
**Assertion 84:** `n_death == 9` (4 WL + 3 term + 2 endowment)
**Assertion 85:** `n_annuity == 3`
**Assertion 86:** `total_sum_assured == 12,500,000` (2M + 1.5M + 1M + 0.5M + 3M + 2M + 1M + 1.5M + 1M)
**Assertion 87:** `total_annual_pension == 370,000` (120K + 150K + 100K)

### 5.2 BEL Computation

**Endpoint:** `POST /portfolio/bel`

```bash
curl -X POST http://localhost:8000/portfolio/bel \
  -H "Content-Type: application/json" \
  -d '{"interest_rate": 0.05}'
```

**Assertion 88:** `annuity_bel >> death_bel` (annuities dominate because they pay immediately)
**Assertion 89:** `total_bel == death_bel + annuity_bel` exactly
**Assertion 90:** WL-04 (duration=0) has BEL near 0 (equivalence principle: newly issued)
**Assertion 91:** All death policies with duration > 0 have BEL > 0
**Assertion 92:** Total BEL in range $4M - $6M

Expected ranges:
- Annuity BEL: $3.5M - $5M (annuity BEL = pension * a_due(age), and a_due(60) at 5% ~ 13)
- Death BEL: $500K - $1.5M (accumulated reserves on in-force policies)

**Gotcha:**

> **Q:** "Why is annuity BEL so much larger than death BEL?"
>
> **A:** Annuity BEL = pension * a_due(attained_age). For AN-10 at age 60 with $120K/yr pension, a_due(60) at 5% is roughly 13 years of expected payments, so BEL ~ $1.56M for just one policy. Death product BEL is a prospective reserve that builds slowly over time. WL-01 (age 35, 10yr duration) has only accumulated ~10 years of reserve against a $2M SA.

### 5.3 SCR by Risk Module

**Endpoint:** `POST /scr/compute`

```bash
# With defaults
curl -X POST http://localhost:8000/scr/defaults

# Or with custom parameters
curl -X POST http://localhost:8000/scr/compute \
  -H "Content-Type: application/json" \
  -d '{"interest_rate":0.05,"mortality_shock":0.15,"longevity_shock":0.20,"ir_shock_bps":100,"cat_shock_factor":1.35,"coc_rate":0.06,"portfolio_duration":15.0,"available_capital":1000000}'
```

**Default shock parameters:**

| Module | Shock | Standard |
|--------|-------|----------|
| Mortality | +15% q_x permanent | Solvency II standard |
| Longevity | -20% q_x permanent | Solvency II standard |
| Interest Rate | +/- 100 bps | Simplified standard |
| Catastrophe | +35% one-year spike | COVID-calibrated |

**Mortality SCR:**
**Assertion 93:** `mortality.scr > 0`
**Assertion 94:** `mortality.bel_stressed > mortality.bel_base` (higher q_x -> higher death reserves)

**Longevity SCR:**
**Assertion 95:** `longevity.scr > 0`
**Assertion 96:** `longevity.bel_stressed > longevity.bel_base` (lower q_x -> people live longer -> higher annuity BEL)

**Interest Rate SCR:**
**Assertion 97:** `interest_rate.scr > 0`
**Assertion 98:** `interest_rate.bel_down > interest_rate.bel_up` (lower rate -> higher PV of liabilities)
**Assertion 99:** Interest rate SCR is the largest module

**Catastrophe SCR:**
**Assertion 100:** `catastrophe.scr > 0`
**Assertion 101:** Catastrophe SCR is the smallest module

**Module Ordering:**
**Assertion 102:** `SCR_ir > SCR_long > SCR_mort > SCR_cat`

**Gotcha:**

> **Q:** "Why does interest rate risk dominate?"
>
> **A:** Interest rate affects ALL 12 policies simultaneously -- both death products and annuities have future cash flows that are discounted. A 100bps rate change on a $5M+ BEL portfolio creates a large absolute SCR. By contrast, mortality shock only affects 9 death policies, longevity only 3 annuities, and catastrophe only 1 year of excess deaths.

> **Q:** "Why does rate-down produce higher BEL than rate-up?"
>
> **A:** Lower discount rate means future payments have a HIGHER present value. Since BEL is the present value of future obligations, reducing the rate increases every single future cash flow's value. This is the same mechanism as bond prices rising when rates fall.

Reference: `backend/engine/a12_scr.py:121-167` (mortality), `a12_scr.py:174-223` (longevity), `a12_scr.py:230-274` (interest rate), `a12_scr.py:281-347` (catastrophe)

### 5.4 Aggregation

**Life Underwriting Aggregation:**

**Assertion 103:** `life_aggregation.scr_aggregated < life_aggregation.sum_individual` (diversification benefit exists)
**Assertion 104:** `life_aggregation.diversification_pct > 0`
**Assertion 105:** Diversification is between 10% and 20%

The diversification exists because mortality and longevity are negatively correlated (-0.25):
```
LIFE_CORR = [[1.00, -0.25, 0.25],
             [-0.25, 1.00, 0.00],
             [0.25,  0.00, 1.00]]
```

A pandemic increases death claims but DECREASES annuity obligations. An insurer selling both products has a natural hedge.

**Total Aggregation:**

**Assertion 106:** `total_aggregation.scr_aggregated < total_aggregation.sum_individual`
**Assertion 107:** `total_aggregation.sum_individual == life_aggregation.scr_aggregated + interest_rate.scr`

Reference: `backend/engine/a12_scr.py:354-402` (life aggregation), `a12_scr.py:409-445` (total aggregation)

### 5.5 Risk Margin

**Assertion 108:** `risk_margin.risk_margin > 0`

Manual verification formula:
```
annuity_factor = (1 - v^duration) / i
                = (1 - 1.05^(-15)) / 0.05
                = (1 - 0.48102) / 0.05
                = 10.3797

risk_margin = coc_rate * scr_total * annuity_factor
            = 0.06 * scr_total * 10.3797
```

**Assertion 109:** `risk_margin.annuity_factor` is approximately 10.38 (for duration=15, i=5%)
**Assertion 110:** `risk_margin.coc_rate == 0.06`
**Assertion 111:** `risk_margin.duration == 15.0`

**Gotcha:**

> **Q:** "Why is the risk margin computed with a constant SCR?"
>
> **A:** Simplification. The full formula sums SCR(t)/(1+r)^(t+1) for each future year, requiring a separate SCR calculation at each duration. We assume constant SCR, which overestimates (conservative = acceptable to CNSF). This is the standard simplification in practice.

Reference: `backend/engine/a12_scr.py:452-500`

### 5.6 Technical Provisions

**Assertion 112:** `technical_provisions == bel_base + risk_margin.risk_margin` exactly

Expected range: $5M - $7M

### 5.7 Solvency Ratio

When `available_capital = 1,000,000`:

**Assertion 113:** `solvency.ratio = available_capital / scr_total`
**Assertion 114:** `solvency.ratio_pct = ratio * 100`
**Assertion 115:** `solvency.is_solvent = (ratio >= 1.0)`

**Gotcha:**

> **Q:** "What ratio should a well-managed insurer target?"
>
> **A:** 150-200%. Below 100% triggers CNSF intervention (supervisory ladder: plan de regularizacion, revocacion). Above 300% means capital is being "wasted" -- shareholders could earn better returns elsewhere. The sweet spot balances safety with capital efficiency. European insurers typically target 160-180%.

Reference: `backend/engine/a12_scr.py:507-537`

---

## Section 6: Metodologia Page

### 6.1 Formula Consistency

Verify the Metodologia page descriptions match the actual implementation:

**Assertion 116:** Graduation uses `diff_order = 2` (not 3)
**Assertion 117:** Graduation uses `lambda = 1e5`
**Assertion 118:** Lee-Carter equation displayed: `ln(m_{x,t}) = a_x + b_x * k_t`
**Assertion 119:** Constraints displayed: `sum(b_x) = 1`, `mean(k_t) = 0`
**Assertion 120:** All 24 reference doc pairs should be accessible

Reference: `backend/api/services/precomputed.py:90-98` (graduation params)

---

## Section 7: Cross-Page Consistency Checks

These tests verify the same number appears consistently across different pages and endpoints.

**Assertion 121:** `explained_variance` on Inicio == on Mortalidad Lee-Carter tab == on Diagnostics endpoint
```bash
# All three should return identical values:
curl -s http://localhost:8000/mortality/lee-carter | python3 -c "import json,sys; print(json.load(sys.stdin)['explained_variance'])"
curl -s http://localhost:8000/mortality/diagnostics | python3 -c "import json,sys; print(json.load(sys.stdin)['explained_variance'])"
```

**Assertion 122:** `drift` on Inicio == on Mortalidad == on Projection endpoint
```bash
curl -s http://localhost:8000/mortality/lee-carter | python3 -c "import json,sys; print(json.load(sys.stdin)['drift'])"
curl -s http://localhost:8000/mortality/projection | python3 -c "import json,sys; print(json.load(sys.stdin)['drift'])"
```

**Assertion 123:** `diff_order` on Metodologia == `lambda_param` from graduation endpoint == 100000
```bash
curl -s http://localhost:8000/mortality/graduation | python3 -c "import json,sys; print(json.load(sys.stdin)['lambda_param'])"
```

**Assertion 124:** Whole life premium at age 40 on Precios == `base_premium` on Sensibilidad (when factor=0)
```bash
# Premium from pricing endpoint
curl -s -X POST http://localhost:8000/pricing/premium \
  -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"interest_rate":0.05}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['annual_premium'])"

# NOTE: Sensitivity endpoint uses projected life table (2029), not CNSF regulatory table.
# So these will NOT match -- this is expected and correct.
# The Precios page uses CNSF 2000-I, the Sensibilidad page uses Lee-Carter projected table.
```

**Assertion 125:** Total BEL from `/portfolio/bel` == `bel_base` in `/scr/compute` or `/scr/defaults`

---

## Section 8: Interview Challenge Questions

Top 15 questions an examiner might ask, with expected answer summaries.

### Q1: "Walk me through how you compute a net annual premium."

**Expected answer:** Equivalence principle. At issue, APV(premiums) = APV(benefits). For whole life: P * a_x = SA * A_x, so P = SA * A_x / a_x. Using commutation functions: P = SA * M_x / N_x. The D_x cancels in numerator and denominator.

### Q2: "Why is the initial reserve zero?"

**Expected answer:** Direct consequence of the equivalence principle. At t=0: 0V = SA * A_x - P * a_x. Since P was defined to make P * a_x = SA * A_x, the reserve is exactly zero. A nonzero initial reserve would mean the premium was incorrectly calculated.

### Q3: "What happens to your Lee-Carter model if COVID data is included?"

**Expected answer:** Explained variance drops from 77.7% to 53.5%. The drift becomes less negative (-1.076 to -0.855), meaning projected mortality improvement slows. This increases premiums by 3-4% across all ages, permanently, because the trend shift affects all future projections.

### Q4: "How do you handle the identifiability problem in Lee-Carter?"

**Expected answer:** The SVD decomposition ax + bx * kt has a scaling/shifting ambiguity. We impose two constraints: sum(bx) = 1 (fixes the scale of bx vs kt) and mean(kt) = 0 (fixes the shift between ax and bx*kt). These constraints make ax = mean(log_mx) by construction.

### Q5: "Why use Whittaker-Henderson instead of a parametric model?"

**Expected answer:** Non-parametric, preserves local features (infant mortality spike, young-adult hump from accidents). One tuning parameter (lambda) instead of multiple parametric coefficients. Better for irregular mortality data like Mexico's. The penalty matrix D'D ensures smoothness without imposing a functional form.

### Q6: "What is the diversification benefit in your SCR, and why does it exist?"

**Expected answer:** 10-20% reduction from summing individual SCR components. Arises from negative correlation (-0.25) between mortality and longevity risk. A pandemic kills more people (bad for death products) but also reduces annuity obligations (good for annuities). An insurer with both products has a natural hedge.

### Q7: "Why do you normalize D_x with v^(x-min_age)?"

**Expected answer:** Standard v^x computation causes extreme underflow at high ages (v^100 ~ 0.0076 at 5%). Normalizing to v^(x-min_age) keeps values in a manageable range. Since ALL actuarial values are RATIOS of commutation functions (A_x = M_x/D_x), the normalization constant cancels exactly. Absolute D, N values differ from published tables, but all derived quantities are identical.

### Q8: "What regulatory tables are you comparing against?"

**Expected answer:** CNSF 2000-I (Circular Unica de Seguros y Fianzas, year 2000) and EMSSA 2009 (Experiencia Mexicana de Mortalidad del Seguro Social, 2009). CNSF is the general insurance regulatory table; EMSSA is specifically for social security pensioners. Both have separate male/female columns.

### Q9: "Why does your term reserve have a hump shape?"

**Expected answer:** During the first half of the term, premiums are collected and mortality risk is moderate, so the reserve builds up. In the second half, remaining coverage shrinks (fewer years of potential claims) and no benefit is owed at expiry, so the reserve declines. At t=n, there is zero liability (no death benefit, no future premiums) so the reserve returns to zero.

### Q10: "How did you calibrate the catastrophe shock?"

**Expected answer:** From COVID's impact on Mexican mortality data. Pre-COVID k_t was trending at -1.076/year. COVID caused a k_t reversal of ~6.76 units above trend. Converting through b_x, this implies roughly +35% excess mortality at working ages. This is a one-year spike (not permanent), applied only to death products.

### Q11: "What SCR modules are missing, and why?"

**Expected answer:** Lapse risk, disability/morbidity, expense risk, and operational risk. This project focuses on the four most material risks for a death+annuity portfolio. Lapse would require surrender value modeling; disability needs multi-state Markov chains; expense risk needs historical cost data. All four are in the Solvency II standard formula but were excluded for scope.

### Q12: "Why is the risk margin computed with a constant SCR?"

**Expected answer:** Simplification. The full formula sums discounted future SCR: MdR = CoC * sum_t[SCR(t)/(1+r)^(t+1)]. Computing SCR(t) at each future duration requires re-running the entire SCR pipeline. We assume SCR is constant, which overestimates the risk margin (conservative). CNSF accepts this simplification in practice.

### Q13: "What is the fundamental identity A_x + d*a_x = 1 and why does it matter?"

**Expected answer:** A_x = APV of $1 at death. d*a_x = APV of the "interest earned" while alive (d = i/(1+i) is the discount rate). A person alive at x must eventually die (A_x) or keep generating interest on deferred payments (d*a_x). Together they sum to 1 (probability conservation). It serves as a validation check: if this identity fails, the commutation functions are wrong.

### Q14: "Explain the asymmetry in mortality shock sensitivity."

**Expected answer:** Premium = M_x/N_x. When q_x increases, both M_x (death benefit APV) and N_x (premium annuity) change. But they don't change proportionally because N_x represents survival probability, which decreases when mortality increases. This is actuarial convexity: the premium function is convex in q_x, so upward and downward shocks have asymmetric effects, similar to how bond prices have convexity in yields.

### Q15: "Why does interest rate risk dominate your SCR?"

**Expected answer:** Three reasons: (1) It affects ALL 12 policies (mortality only affects 9 death, longevity only 3 annuities). (2) The portfolio has $5M+ in BEL, so even a 1% rate change has a large absolute impact. (3) Annuities have long effective duration (a_due(60) ~ 13 years), amplifying rate sensitivity. By contrast, mortality shocks only change q_x by 15%, affecting only the portion of BEL attributable to mortality risk.

---

## Appendix A: Quick Validation Script

```bash
#!/bin/bash
# Run all critical assertions against running API
API="http://localhost:8000"

echo "=== SIMA Quick Validation ==="

# Data summary
echo -n "Data shape: "
curl -s $API/mortality/data/summary | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d['shape'] == [101, 31], f'FAIL: shape={d[\"shape\"]}'
print(f'PASS {d[\"shape\"]}')"

# Lee-Carter constraints
echo -n "LC constraints: "
curl -s $API/mortality/lee-carter | python3 -c "
import json,sys; d=json.load(sys.stdin)
s = sum(d['bx']); m = sum(d['kt'])/len(d['kt'])
assert abs(s - 1.0) < 1e-6, f'FAIL: sum(bx)={s}'
assert abs(m) < 1e-6, f'FAIL: mean(kt)={m}'
assert all(b > 0 for b in d['bx']), 'FAIL: negative bx'
print(f'PASS sum(bx)={s:.8f}, mean(kt)={m:.8e}')"

# Fundamental identity
echo -n "A_x + d*a_x = 1: "
for age in 0 20 40 60 80 99; do
  curl -s "$API/pricing/commutation?age=$age&interest_rate=0.05" | python3 -c "
import json,sys; d=json.load(sys.stdin)
r = d['A_x'] + (0.05/1.05)*d['a_due_x']
assert abs(r-1.0) < 1e-6, f'FAIL at age {d[\"age\"]}: {r}'
print(f'age {d[\"age\"]}=PASS', end=' ')"
done
echo ""

# Product ordering
echo -n "Product ordering age 40: "
WL=$(curl -s -X POST $API/pricing/premium -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"interest_rate":0.05}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['annual_premium'])")
TM=$(curl -s -X POST $API/pricing/premium -H "Content-Type: application/json" \
  -d '{"product_type":"term","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['annual_premium'])")
EN=$(curl -s -X POST $API/pricing/premium -H "Content-Type: application/json" \
  -d '{"product_type":"endowment","age":40,"sum_assured":1000000,"interest_rate":0.05,"term":20}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['annual_premium'])")
python3 -c "
tm,wl,en = $TM,$WL,$EN
assert tm < wl < en, f'FAIL: {tm} < {wl} < {en}'
print(f'PASS term={tm:.0f} < WL={wl:.0f} < endow={en:.0f}')"

# Reserve 0V = 0
echo -n "0V = 0 (whole life): "
curl -s -X POST $API/pricing/reserve -H "Content-Type: application/json" \
  -d '{"product_type":"whole_life","age":40,"sum_assured":1000000,"interest_rate":0.05}' | python3 -c "
import json,sys; d=json.load(sys.stdin)
v0 = d['trajectory'][0]['reserve']
assert abs(v0) < 0.01, f'FAIL: 0V={v0}'
print(f'PASS 0V={v0:.6f}')"

# Portfolio summary
echo -n "Portfolio: "
curl -s $API/portfolio/summary | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d['n_policies'] == 12, f'FAIL: n={d[\"n_policies\"]}'
assert d['n_death'] == 9
assert d['n_annuity'] == 3
assert d['total_sum_assured'] == 12500000
assert d['total_annual_pension'] == 370000
print(f'PASS 12 policies, SA=12.5M, pension=370K')"

# SCR ordering
echo -n "SCR module ordering: "
curl -s -X POST $API/scr/defaults | python3 -c "
import json,sys; d=json.load(sys.stdin)
ir = d['interest_rate']['scr']
lo = d['longevity']['scr']
mo = d['mortality']['scr']
ca = d['catastrophe']['scr']
assert ir > lo > mo > ca, f'FAIL: ir={ir:.0f} lo={lo:.0f} mo={mo:.0f} ca={ca:.0f}'
print(f'PASS ir={ir:.0f} > long={lo:.0f} > mort={mo:.0f} > cat={ca:.0f}')"

# Diversification
echo -n "Diversification: "
curl -s -X POST $API/scr/defaults | python3 -c "
import json,sys; d=json.load(sys.stdin)
agg = d['life_aggregation']['scr_aggregated']
ind = d['life_aggregation']['sum_individual']
pct = d['life_aggregation']['diversification_pct']
assert agg < ind, f'FAIL: agg={agg:.0f} >= ind={ind:.0f}'
assert 5 < pct < 30, f'FAIL: div_pct={pct:.1f}'
print(f'PASS div={pct:.1f}%, agg={agg:.0f} < sum={ind:.0f}')"

# Technical provisions
echo -n "Tech provisions: "
curl -s -X POST $API/scr/defaults | python3 -c "
import json,sys; d=json.load(sys.stdin)
tp = d['technical_provisions']
bel = d['bel_base']
rm = d['risk_margin']['risk_margin']
assert abs(tp - bel - rm) < 0.01, f'FAIL: TP={tp}, BEL+RM={bel+rm}'
print(f'PASS TP={tp:,.0f} = BEL({bel:,.0f}) + MdR({rm:,.0f})')"

# Cross-page consistency
echo -n "Cross-page explained_var: "
EV1=$(curl -s $API/mortality/lee-carter | python3 -c "import json,sys; print(json.load(sys.stdin)['explained_variance'])")
EV2=$(curl -s $API/mortality/diagnostics | python3 -c "import json,sys; print(json.load(sys.stdin)['explained_variance'])")
python3 -c "
assert abs($EV1 - $EV2) < 1e-10, f'FAIL: {$EV1} != {$EV2}'
print(f'PASS lee-carter={$EV1} == diagnostics={$EV2}')"

echo "=== Done ==="
```

---

## Appendix B: Assertion Count Summary

| Section | Assertions |
|---------|-----------|
| 0: Setup | 0 |
| 1: Inicio | 6 |
| 2: Mortalidad | 31 |
| 3: Precios | 29 |
| 4: Sensibilidad | 15 |
| 5: Capital (SCR) | 30 |
| 6: Metodologia | 5 |
| 7: Cross-Page | 5 |
| **Total** | **121** |
