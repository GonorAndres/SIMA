# Capital Requirements (SCR): Technical Reference

**Modules:** `backend/engine/a11_portfolio.py`, `backend/engine/a12_scr.py`
**Dependencies:** `a01_life_table`, `a02_commutation`, `a03_actuarial_values`, `a04_premiums`, `a05_reserves`

---

## 1. Solvency II / CNSF Framework

### 1.1 Overview

The Solvency Capital Requirement (SCR) is the amount of capital an insurer must hold to survive a 1-in-200-year adverse event (99.5% VaR over one year). In Mexico, the equivalent concept is the **Requerimiento de Capital de Solvencia (RCS)**, governed by the **LISF** (Ley de Instituciones de Seguros y Fianzas) and operationalized through the **CUSF** (Circular Unica de Seguros y Fianzas) issued by the **CNSF** (Comision Nacional de Seguros y Fianzas).

### 1.2 Key Definitions

| Symbol | Name | Definition |
|--------|------|------------|
| BEL | Best Estimate of Liabilities | Present value of expected future cash flows (claims minus premiums), using best-estimate assumptions |
| MdR | Margen de Riesgo (Risk Margin) | Additional provision ensuring liabilities could be transferred to a third party |
| PT | Provisiones Tecnicas (Technical Provisions) | PT = BEL + MdR |
| RCS / SCR | Requerimiento de Capital de Solvencia | Capital needed to absorb a 1-in-200 shock |
| FP | Fondos Propios (Own Funds) | Available capital = Assets - PT |
| IS | Indice de Solvencia (Solvency Ratio) | IS = FP / RCS; CNSF minimum = 100% |

### 1.3 Balance Sheet Structure

```
Assets
  = Technical Provisions + Own Funds
  = (BEL + MdR) + FP

Solvency condition:
  FP >= RCS
  equivalently: IS = FP / RCS >= 1.0
```

---

## 2. Best Estimate of Liabilities (BEL)

### 2.1 BEL for Death Products (Term, Whole Life, Endowment)

The BEL for a death product at policy duration $t$ is the **prospective reserve**:

$$\text{BEL}_{\text{death}}(t) = SA \cdot A_{x+t} - P \cdot \ddot{a}_{x+t}$$

where:
- $SA$ is the sum assured
- $A_{x+t}$ is the whole life insurance actuarial present value at attained age $x+t$
- $P$ is the annual net premium (computed at issue via equivalence principle)
- $\ddot{a}_{x+t}$ is the life annuity-due at attained age $x+t$

For term and endowment products, the appropriate temporary versions apply:

$$\text{BEL}_{\text{term}}(t) = SA \cdot A^1_{x+t:\overline{n-t}|} - P \cdot \ddot{a}_{x+t:\overline{n-t}|}$$

$$\text{BEL}_{\text{endow}}(t) = SA \cdot A_{x+t:\overline{n-t}|} - P \cdot \ddot{a}_{x+t:\overline{n-t}|}$$

### 2.2 BEL for Annuity Products

For a life annuity-immediate paying annual pension $R$:

$$\text{BEL}_{\text{annuity}} = R \cdot \ddot{a}_{x}$$

For a deferred annuity (deferral period $n$):

$$\text{BEL}_{\text{deferred}} = R \cdot {}_n|\ddot{a}_{x} = R \cdot \frac{N_{x+n}}{D_x}$$

### 2.3 BEL Computation via Commutation Functions

All BEL components reduce to ratios of commutation functions:

| Component | Formula |
|-----------|---------|
| $A_x$ | $M_x / D_x$ |
| $\ddot{a}_x$ | $N_x / D_x$ |
| $A^1_{x:\overline{n}\|}$ | $(M_x - M_{x+n}) / D_x$ |
| $\ddot{a}_{x:\overline{n}\|}$ | $(N_x - N_{x+n}) / D_x$ |
| ${}_nE_x$ | $D_{x+n} / D_x$ |

When assumptions change (shocked $q_x$ or shifted $i$), a new `LifeTable` and `CommutationFunctions` are built, and BEL is recomputed entirely from the shocked commutation functions.

### 2.4 Portfolio-Level BEL

For a portfolio of $K$ policies:

$$\text{BEL}_{\text{portfolio}} = \sum_{k=1}^{K} \text{BEL}_k(t_k)$$

where $t_k$ is the current policy duration for policy $k$.

---

## 3. Risk Modules

### 3.1 Solvency II Standard Formula Shock Magnitudes

| Risk | Shock | Applies to | Direction |
|------|-------|------------|-----------|
| Mortality | $q_x \times 1.15$ (+15%) | Death products (term, whole life, endowment) | Adverse = higher mortality |
| Longevity | $q_x \times 0.80$ (-20%) | Annuity products | Adverse = lower mortality (longer lives) |
| Interest rate up | $i + 1\%$ | All products | Adverse depends on product |
| Interest rate down | $i - 1\%$ | All products | Adverse depends on product |
| Catastrophe | Instantaneous mortality spike | Death products | One-time event |

### 3.2 Mortality Risk: SCR_mort

**Applicable products:** Term life, whole life, endowment (any product where the insurer pays on death).

**Shock:** Permanent +15% increase in all $q_x$ values.

$$\text{SCR}_{\text{mort}} = \text{BEL}(q_x \times 1.15) - \text{BEL}(q_x)$$

**Computation steps:**

1. Build base `LifeTable` with current best-estimate $q_x$.
2. Build shocked `LifeTable` by applying `build_shocked_life_table(base_lt, factor=1.15)`:
   ```
   shocked_q_x = min(base_q_x * 1.15, 1.0)
   l_{x+1} = l_x * (1 - shocked_q_x)
   ```
3. Compute `CommutationFunctions` at same interest rate $i$ for both tables.
4. Compute `BEL_base` and `BEL_shocked` for each death policy in the portfolio.
5. $\text{SCR}_{\text{mort}} = \sum_k \text{BEL}_{\text{shocked},k} - \sum_k \text{BEL}_{\text{base},k}$

**Sign convention:** For death products, higher $q_x$ increases $A_{x+t}$ (more death claims expected) and decreases $\ddot{a}_{x+t}$ (shorter expected premium payment period), so BEL increases. Thus $\text{SCR}_{\text{mort}} > 0$.

### 3.3 Longevity Risk: SCR_long

**Applicable products:** Life annuities, deferred annuities, pension obligations.

**Shock:** Permanent -20% decrease in all $q_x$ values.

$$\text{SCR}_{\text{long}} = \text{BEL}(q_x \times 0.80) - \text{BEL}(q_x)$$

**Computation steps:**

1. Build base `LifeTable`.
2. Build shocked `LifeTable` with `build_shocked_life_table(base_lt, factor=0.80)`.
3. Compute `CommutationFunctions` at same $i$ for both.
4. For each annuity policy: $\text{BEL}_k = R_k \cdot \ddot{a}_{x_k}$.
5. $\text{SCR}_{\text{long}} = \sum_k \text{BEL}_{\text{shocked},k} - \sum_k \text{BEL}_{\text{base},k}$

**Sign convention:** Lower $q_x$ means longer survival, so $\ddot{a}_x$ increases, BEL for annuities increases. Thus $\text{SCR}_{\text{long}} > 0$.

### 3.4 Interest Rate Risk: SCR_ir

**Applicable products:** All (death products and annuity products).

**Shock:** Parallel shift of +1% and -1% in the interest rate.

$$\text{SCR}_{\text{ir}} = \max\!\Big(\text{BEL}(i + 1\%) - \text{BEL}(i),\;\; \text{BEL}(i - 1\%) - \text{BEL}(i),\;\; 0\Big)$$

**Computation steps:**

1. Compute $\text{BEL}_{\text{base}}$ at interest rate $i$.
2. Compute $\text{BEL}_{\text{up}}$ at interest rate $i + 0.01$ (rebuild `CommutationFunctions`, same `LifeTable`).
3. Compute $\text{BEL}_{\text{down}}$ at interest rate $i - 0.01$ (rebuild `CommutationFunctions`, same `LifeTable`).
4. Take the maximum of the two stress increments and zero.

**Direction depends on product:**
- Death products: BEL typically decreases when $i$ increases (higher discount reduces PV of future claims). So the **down** shock is usually adverse.
- Annuity products: BEL also typically decreases when $i$ increases. So the **down** shock is usually adverse.
- Mixed portfolios: both directions are tested; the formula takes the worst case.

**Note:** The floor at zero ensures that if both shocks reduce BEL (theoretically possible in edge cases), no capital is required for interest rate risk.

### 3.5 Catastrophe Risk: SCR_cat

**Applicable products:** Death products only.

**Shock:** Instantaneous one-time spike in mortality, not a permanent level change.

$$\text{SCR}_{\text{cat}} = \sum_{k=1}^{K} SA_k \cdot \Delta q_{x_k} \cdot v^{1}$$

where:
- $SA_k$ is the sum assured for policy $k$
- $\Delta q_{x_k}$ is the additional probability of death due to the catastrophe
- $v^1 = 1/(1+i)$ discounts the one-year-ahead payment

#### 3.5.1 COVID-19 Calibration for Mexico

The catastrophe shock is calibrated using observed Mexican COVID-19 mortality deviation from the Lee-Carter trend.

**Derivation from Lee-Carter $k_t$ deviation:**

The Lee-Carter model fitted on pre-COVID data (1990-2019) gives:
- Last observed $k_t$: $k_{2019} = -7.9481$
- Projected $k_{2020}$: $k_{2019} + \text{drift} = -7.9481 + (-1.0764) = -9.0245$

The full-period model (1990-2024) gives:
- Observed $k_{2020} = -4.7170$ (from section 4 of doc 17)

However, to calibrate the catastrophe shock directly, we use the k_t deviation observed during COVID:

**Step 1:** Expected $k_{2020}$ from pre-COVID trend: $\hat{k}_{2020} = -9.0245$

**Step 2:** Under the full-period model, the equivalent position of 2020 shows a reversal. The k_t jump from the pre-COVID model's perspective:
- Pre-COVID trend predicted $k_{2020} \approx -9.02$
- Actual mortality level in 2020 corresponded to $k_t \approx -2.27$ in the pre-COVID model's scale (mortality reverted to approximately year 2000 levels)

**Step 3:** The $k_t$ deviation:

$$\Delta k_t = k_{2020,\text{actual}} - k_{2020,\text{predicted}} \approx 6.76 \text{ units}$$

**Step 4:** Translate to $q_x$ shock. The Lee-Carter model gives:

$$\ln(m_{x,t}) = a_x + b_x \cdot k_t$$

A deviation of $\Delta k_t$ produces a multiplicative change in $m_x$:

$$\frac{m_{x,\text{shocked}}}{m_{x,\text{base}}} = \exp(b_x \cdot \Delta k_t)$$

For a representative age (e.g., $x = 50$, where $b_x \approx 0.045$):

$$\text{ratio} = \exp(0.045 \times 6.76) \approx \exp(0.304) \approx 1.355$$

This yields approximately a **+35% spike** in mortality rates, which we adopt as $\Delta q_x$:

$$\Delta q_x = 0.35 \cdot q_x^{\text{base}}$$

**Step 5:** Catastrophe SCR with COVID calibration:

$$\text{SCR}_{\text{cat}} = \sum_{k=1}^{K} SA_k \cdot (0.35 \cdot q_{x_k}) \cdot v$$

#### 3.5.2 Solvency II Standard vs COVID-Calibrated

| Calibration | delta_q | Basis |
|-------------|---------|-------|
| Solvency II standard | 1.5 per mille (0.0015) flat | European-calibrated, all ages |
| CNSF / COVID-calibrated | 35% of base $q_x$ | Age-dependent, Mexican experience |

The COVID-calibrated approach is more appropriate for Mexican portfolios because:
1. It is age-dependent (older ages receive larger absolute shocks, matching observed COVID patterns).
2. It reflects actual Mexican pandemic experience rather than European calibration.
3. It naturally scales with the base mortality level of the portfolio.

---

## 4. Life Underwriting Risk Aggregation

### 4.1 Correlation Matrix (LIFE_CORR)

The three life underwriting sub-risks are aggregated using a correlation matrix. This reflects the fact that mortality, longevity, and catastrophe risks are not fully independent.

$$\text{LIFE\_CORR} = \begin{pmatrix} 1.00 & -0.25 & 0.25 \\ -0.25 & 1.00 & 0.00 \\ 0.25 & 0.00 & 1.00 \end{pmatrix}$$

Row/column order: (Mortality, Longevity, Catastrophe).

| Pair | Correlation | Rationale |
|------|:-----------:|-----------|
| Mortality -- Longevity | -0.25 | Natural hedge: if mortality rises, longevity risk falls (shorter lives reduce annuity BEL) |
| Mortality -- Catastrophe | +0.25 | Catastrophes cause excess deaths, positively correlated with mortality trend risk |
| Longevity -- Catastrophe | 0.00 | Catastrophes (acute events) are independent of long-term longevity improvements |

### 4.2 Positive Semi-Definiteness (PSD)

A valid correlation matrix must be positive semi-definite (all eigenvalues $\geq 0$). For the 3x3 LIFE_CORR:

$$\text{det}(\text{LIFE\_CORR}) = 1.0 \cdot (1.0 \cdot 1.0 - 0.0 \cdot 0.0) - (-0.25)((-0.25)(1.0) - (0.25)(0.0)) + 0.25((-0.25)(0.0) - (0.25)(1.0))$$

$$= 1.0 - (-0.25)(-0.25) + 0.25(-0.25) = 1.0 - 0.0625 - 0.0625 = 0.875$$

Since the determinant is positive and all 2x2 leading principal minors are also positive (1.0 and 0.9375), the matrix is positive definite (strictly stronger than PSD).

**Eigenvalues:** $\lambda_1 \approx 1.25$, $\lambda_2 \approx 1.00$, $\lambda_3 \approx 0.75$. All positive.

### 4.3 Aggregation Formula

Let $\vec{S} = (\text{SCR}_{\text{mort}},\; \text{SCR}_{\text{long}},\; \text{SCR}_{\text{cat}})^\top$.

$$\text{SCR}_{\text{life}} = \sqrt{\vec{S}^\top \cdot \text{LIFE\_CORR} \cdot \vec{S}}$$

Expanded:

$$\text{SCR}_{\text{life}} = \sqrt{S_1^2 + S_2^2 + S_3^2 + 2(-0.25)S_1 S_2 + 2(0.25)S_1 S_3 + 2(0.0)S_2 S_3}$$

$$= \sqrt{S_1^2 + S_2^2 + S_3^2 - 0.5\, S_1 S_2 + 0.5\, S_1 S_3}$$

### 4.4 Diversification Benefit

The diversification benefit measures how much capital is saved by holding a diversified portfolio compared to summing risks independently:

$$\text{Diversification Benefit} = \frac{\sum_i S_i - \text{SCR}_{\text{life}}}{\sum_i S_i}$$

Due to the negative mortality-longevity correlation, a mixed portfolio (death products + annuities) achieves meaningful diversification. Pure death-only portfolios see limited benefit (only between mortality and catastrophe sub-risks).

---

## 5. Top-Level SCR Aggregation

### 5.1 Two-Risk Aggregation

Interest rate risk is a market risk, separate from life underwriting risk. The top-level SCR aggregates these two categories:

$$\text{SCR}_{\text{total}} = \sqrt{\text{SCR}_{\text{life}}^2 + \text{SCR}_{\text{ir}}^2 + 2 \cdot \rho \cdot \text{SCR}_{\text{life}} \cdot \text{SCR}_{\text{ir}}}$$

where $\rho = 0.25$ is the Solvency II inter-module correlation between life underwriting and market risk.

### 5.2 Expanded Formula

$$\text{SCR}_{\text{total}} = \sqrt{\text{SCR}_{\text{life}}^2 + \text{SCR}_{\text{ir}}^2 + 0.5 \cdot \text{SCR}_{\text{life}} \cdot \text{SCR}_{\text{ir}}}$$

### 5.3 Full Correlation Structure

```
Top-Level:    CORR_top = [[1.0,  0.25],
                          [0.25, 1.0 ]]

              Row/col: (SCR_life, SCR_ir)

Life Module:  LIFE_CORR = [[1.0,  -0.25, 0.25],
                           [-0.25, 1.0,  0.0 ],
                           [0.25,  0.0,  1.0 ]]

              Row/col: (Mortality, Longevity, Catastrophe)
```

---

## 6. Risk Margin (MdR)

### 6.1 Definition

The Risk Margin ensures that Technical Provisions are sufficient for a third party to take over the insurance obligations. It is computed using the **Cost of Capital (CoC)** method:

$$\text{MdR} = \text{CoC} \cdot \sum_{t=0}^{T} \frac{\text{SCR}(t)}{(1+i)^{t+1}}$$

where:
- CoC = 6% (regulatory fixed rate, per Solvency II and CNSF)
- $\text{SCR}(t)$ is the projected SCR at future time $t$
- $T$ is the maximum remaining duration of all obligations
- $i$ is the risk-free rate

### 6.2 Simplified Approximation

When projecting future SCR is computationally prohibitive, a common simplification assumes SCR declines proportionally with BEL:

$$\text{MdR} \approx \text{CoC} \cdot \text{SCR}_{\text{current}} \cdot \ddot{a}_{\bar{x}}$$

where $\ddot{a}_{\bar{x}}$ is an annuity factor at the portfolio's average attained age $\bar{x}$, serving as a duration proxy.

### 6.3 Rationale for CoC = 6%

The 6% cost of capital rate represents the excess return above the risk-free rate that a rational third party would demand for holding the required SCR. It is prescribed by regulation (EIOPA for Solvency II, CNSF for Mexican market) and is not calibrated per insurer.

---

## 7. Technical Provisions (PT)

### 7.1 Formula

$$\text{PT} = \text{BEL} + \text{MdR}$$

### 7.2 Components Breakdown

| Component | Death Products | Annuity Products |
|-----------|---------------|------------------|
| BEL | $\sum_k (SA_k \cdot A_{x_k+t_k} - P_k \cdot \ddot{a}_{x_k+t_k})$ | $\sum_k R_k \cdot \ddot{a}_{x_k}$ |
| MdR | CoC $\times$ SCR $\times$ duration proxy | CoC $\times$ SCR $\times$ duration proxy |

### 7.3 Interpretation

- BEL is market-consistent: uses best-estimate mortality and risk-free discounting.
- MdR is a regulatory add-on: ensures transferability of obligations.
- Together, PT represents the minimum assets an insurer must hold against its insurance liabilities before any solvency buffer.

---

## 8. Solvency Ratio

### 8.1 Definition

$$\text{IS} = \frac{\text{FP}}{\text{RCS}} = \frac{\text{Assets} - \text{PT}}{\text{SCR}_{\text{total}}}$$

### 8.2 Regulatory Thresholds (CNSF)

| Ratio | Status | Regulatory Action |
|-------|--------|-------------------|
| IS >= 150% | Comfortable | Normal supervision |
| 100% <= IS < 150% | Adequate | Enhanced monitoring |
| IS < 100% | Insufficient | Recovery plan required (plan de regularizacion) |
| IS < 50% | Critical | Potential license revocation |

### 8.3 Interpretation

A solvency ratio of 120% means the insurer holds 20% more capital than the SCR. This buffer absorbs moderate adverse experience beyond the 1-in-200 calibration of the SCR itself.

---

## 9. Shock Magnitudes Summary Table

| Risk Module | Shock Type | Magnitude | Affected $q_x$ | Affected Products | Sign of SCR |
|-------------|-----------|-----------|-----------------|-------------------|-------------|
| Mortality | Permanent level | $q_x \times 1.15$ | All ages | Death (term, whole, endow) | Positive |
| Longevity | Permanent level | $q_x \times 0.80$ | All ages | Annuity | Positive |
| Interest up | Parallel shift | $i + 1\%$ | N/A (rates only) | All | Non-negative |
| Interest down | Parallel shift | $i - 1\%$ | N/A (rates only) | All | Non-negative |
| Catastrophe | One-time spike | $+35\% \cdot q_x$ (COVID) | All ages | Death | Positive |

---

## 10. API Reference

### 10.1 Portfolio Module (`a11_portfolio.py`)

```python
@dataclass
class Policy:
    policy_id: str
    product_type: str        # "whole_life", "term", "endowment", "annuity"
    age_at_issue: int        # x
    current_duration: int    # t (years since issue)
    sum_assured: float       # SA (death products) or annual pension (annuities)
    term: Optional[int]      # n (None for whole life and lifetime annuities)
```

```python
class Portfolio:
    def __init__(self, policies: List[Policy]):
        ...

    def death_policies(self) -> List[Policy]:
        """Return all policies where product_type in ('whole_life', 'term', 'endowment')."""

    def annuity_policies(self) -> List[Policy]:
        """Return all policies where product_type == 'annuity'."""

    def compute_bel(self, life_table: LifeTable, interest_rate: float) -> float:
        """Compute total portfolio BEL = sum of individual policy BELs."""

    def compute_policy_bel(self, policy: Policy, comm: CommutationFunctions) -> float:
        """Compute BEL for a single policy using its product type and duration."""

    def summary(self) -> dict:
        """Return portfolio composition: count by product type, total SA, average age."""
```

### 10.2 SCR Module (`a12_scr.py`)

```python
# Correlation matrices (module-level constants)
LIFE_CORR = np.array([
    [1.00, -0.25, 0.25],
    [-0.25, 1.00, 0.00],
    [0.25,  0.00, 1.00],
])  # (Mortality, Longevity, Catastrophe)

TOP_CORR = np.array([
    [1.00, 0.25],
    [0.25, 1.00],
])  # (SCR_life, SCR_ir)

COC_RATE = 0.06         # Cost of Capital rate
MORT_SHOCK = 1.15       # +15% mortality shock
LONG_SHOCK = 0.80       # -20% longevity shock
IR_SHOCK = 0.01         # +/- 1% interest rate shift
CAT_SHOCK = 0.35        # +35% catastrophe spike (COVID-calibrated)
```

```python
class SCRCalculator:
    def __init__(self, portfolio: Portfolio, life_table: LifeTable, interest_rate: float):
        ...

    def scr_mortality(self) -> float:
        """BEL(q_x * 1.15) - BEL(q_x) for death policies only."""

    def scr_longevity(self) -> float:
        """BEL(q_x * 0.80) - BEL(q_x) for annuity policies only."""

    def scr_interest_rate(self) -> float:
        """max(BEL(i+1%) - BEL(i), BEL(i-1%) - BEL(i), 0) for all policies."""

    def scr_catastrophe(self) -> float:
        """sum(SA_k * 0.35 * q_{x_k} * v) for death policies only."""

    def scr_life(self) -> float:
        """sqrt(vec' * LIFE_CORR * vec) where vec = (scr_mort, scr_long, scr_cat)."""

    def scr_total(self) -> float:
        """sqrt(scr_life^2 + scr_ir^2 + 2*0.25*scr_life*scr_ir)."""

    def risk_margin(self, avg_annuity_factor: Optional[float] = None) -> float:
        """CoC * SCR_total * annuity_factor. Uses simplified approximation."""

    def technical_provisions(self) -> float:
        """BEL + MdR."""

    def solvency_ratio(self, available_capital: float) -> float:
        """available_capital / scr_total."""

    def diversification_benefit(self) -> float:
        """(sum of individual SCRs - aggregated SCR) / sum of individual SCRs."""

    def full_report(self, available_capital: float) -> dict:
        """Complete breakdown: all sub-SCRs, aggregated SCR, BEL, MdR, PT, solvency ratio."""
```

### 10.3 Helper Function

```python
build_shocked_life_table(base_lt: LifeTable, shock_factor: float, radix: float = 100_000.0) -> LifeTable
```

From `backend/analysis/sensitivity_analysis.py`. Applies multiplicative shock to all $q_x$ values, caps at 1.0, rebuilds $l_x$ from radix. Used by `scr_mortality()` (factor=1.15) and `scr_longevity()` (factor=0.80).

---

## 11. Worked Example

### 11.1 Setup

Consider a simplified portfolio with two policies:

| Policy | Product | Age at Issue | Duration | SA / Pension | Term |
|--------|---------|:------------:|:--------:|:------------:|:----:|
| P001 | Whole life | 40 | 5 | $1,000,000 | -- |
| P002 | Annuity | 65 | 0 | $120,000/yr | -- |

Base assumptions: $i = 5\%$, Mexican projected mortality (pre-COVID).

### 11.2 BEL Computation

**Policy P001 (whole life, attained age 45):**

$$\text{BEL}_1 = SA \cdot A_{45} - P_{40} \cdot \ddot{a}_{45}$$

where $P_{40} = SA \cdot M_{40} / N_{40}$ was the premium set at issue.

**Policy P002 (annuity, age 65):**

$$\text{BEL}_2 = 120{,}000 \cdot \ddot{a}_{65}$$

**Portfolio BEL:**

$$\text{BEL} = \text{BEL}_1 + \text{BEL}_2$$

### 11.3 SCR Components

**Mortality (death policies only, P001):**

$$\text{SCR}_{\text{mort}} = \text{BEL}_1(q_x \times 1.15) - \text{BEL}_1(q_x)$$

**Longevity (annuity policies only, P002):**

$$\text{SCR}_{\text{long}} = \text{BEL}_2(q_x \times 0.80) - \text{BEL}_2(q_x)$$

**Interest rate (all policies):**

$$\text{SCR}_{\text{ir}} = \max\!\big(\text{BEL}(6\%) - \text{BEL}(5\%),\; \text{BEL}(4\%) - \text{BEL}(5\%),\; 0\big)$$

**Catastrophe (death policies only, P001):**

$$\text{SCR}_{\text{cat}} = 1{,}000{,}000 \times 0.35 \times q_{45} \times v$$

### 11.4 Aggregation

$$\text{SCR}_{\text{life}} = \sqrt{S_{\text{mort}}^2 + S_{\text{long}}^2 + S_{\text{cat}}^2 - 0.5 \cdot S_{\text{mort}} \cdot S_{\text{long}} + 0.5 \cdot S_{\text{mort}} \cdot S_{\text{cat}}}$$

$$\text{SCR}_{\text{total}} = \sqrt{\text{SCR}_{\text{life}}^2 + \text{SCR}_{\text{ir}}^2 + 0.5 \cdot \text{SCR}_{\text{life}} \cdot \text{SCR}_{\text{ir}}}$$

### 11.5 Risk Margin and Technical Provisions

$$\text{MdR} = 0.06 \times \text{SCR}_{\text{total}} \times \ddot{a}_{\bar{x}}$$

$$\text{PT} = \text{BEL} + \text{MdR}$$

### 11.6 Solvency Ratio

$$\text{IS} = \frac{\text{Assets} - \text{PT}}{\text{SCR}_{\text{total}}}$$

---

## 12. Connection to Existing SIMA Modules

### 12.1 Dependency Flow

```
a01_life_table ──> a02_commutation ──> a03_actuarial_values
                                    |──> a04_premiums
                                    |──> a05_reserves
                                           |
                   a11_portfolio ──────────>|
                        |                  |
                   a12_scr <───────────────┘
                        |
                   Uses: build_shocked_life_table (from sensitivity_analysis)
```

### 12.2 Module Interaction

| SCR Computation | Calls |
|-----------------|-------|
| `scr_mortality()` | `build_shocked_life_table(lt, 1.15)` -> `CommutationFunctions` -> `ReserveCalculator` for each death policy |
| `scr_longevity()` | `build_shocked_life_table(lt, 0.80)` -> `CommutationFunctions` -> `ActuarialValues.a_x_due()` for each annuity |
| `scr_interest_rate()` | `CommutationFunctions(lt, i+0.01)` and `CommutationFunctions(lt, i-0.01)` -> recompute all BELs |
| `scr_catastrophe()` | Direct computation: $SA \times 0.35 \times q_x \times v$, no new `LifeTable` needed |

### 12.3 Reuse of Existing Code

| Existing Module | How SCR Uses It |
|-----------------|-----------------|
| `a01_life_table.LifeTable` | Base and shocked life tables |
| `a02_commutation.CommutationFunctions` | BEL computation via $M_x/D_x$, $N_x/D_x$ |
| `a03_actuarial_values.ActuarialValues` | $A_x$, $\ddot{a}_x$, ${}_nE_x$ for BEL formulas |
| `a04_premiums.PremiumCalculator` | Net premiums $P$ needed for prospective reserve BEL |
| `a05_reserves.ReserveCalculator` | Prospective reserve = BEL for death products |
| `build_shocked_life_table()` | Mortality and longevity shocks |

---

## 13. Regulatory Mapping: LISF / CUSF to Implementation

| LISF/CUSF Concept | SIMA Implementation | Module |
|--------------------|---------------------|--------|
| RCS (Art. 232 LISF) | `SCRCalculator.scr_total()` | `a12_scr.py` |
| BEL (Art. 218 LISF) | `Portfolio.compute_bel()` | `a11_portfolio.py` |
| MdR (Art. 219 LISF) | `SCRCalculator.risk_margin()` | `a12_scr.py` |
| PT (Art. 216 LISF) | `SCRCalculator.technical_provisions()` | `a12_scr.py` |
| Riesgo de mortalidad | `SCRCalculator.scr_mortality()` | `a12_scr.py` |
| Riesgo de longevidad | `SCRCalculator.scr_longevity()` | `a12_scr.py` |
| Riesgo de tasa de interes | `SCRCalculator.scr_interest_rate()` | `a12_scr.py` |
| Riesgo catastrofico | `SCRCalculator.scr_catastrophe()` | `a12_scr.py` |
| Indice de solvencia (Art. 242 LISF) | `SCRCalculator.solvency_ratio()` | `a12_scr.py` |
| Fondos Propios (Art. 233 LISF) | `available_capital` parameter | User input |

---

## 14. Sanity Checks

| Check | Expected | Formula |
|-------|----------|---------|
| SCR_mort > 0 for death portfolio | Higher q_x increases death claims | BEL(1.15) > BEL(1.00) |
| SCR_long > 0 for annuity portfolio | Lower q_x increases annuity duration | BEL(0.80) > BEL(1.00) |
| SCR_ir >= 0 always | max(..., 0) floor | By construction |
| SCR_cat > 0 for death portfolio | SA * delta_q * v > 0 | All terms positive |
| SCR_life <= SCR_mort + SCR_long + SCR_cat | Correlation <= 1 gives sub-additivity | sqrt(quadratic) <= sum |
| SCR_total <= SCR_life + SCR_ir | Same sub-additivity | sqrt(quadratic) <= sum |
| Diversification benefit in [0, 1) | Cannot exceed sum; zero only if perfectly correlated | By PSD property |
| LIFE_CORR is PSD | All eigenvalues >= 0 | det > 0, all minors > 0 |
| MdR > 0 | CoC > 0, SCR > 0, annuity_factor > 0 | All terms positive |
| Solvency ratio = 1.0 when FP = SCR | Definition | FP/SCR = 1 |

---

## 15. File Locations

| File | Purpose |
|------|---------|
| `backend/engine/a11_portfolio.py` | Policy and Portfolio classes, BEL computation |
| `backend/engine/a12_scr.py` | SCRCalculator, correlation matrices, aggregation |
| `backend/analysis/sensitivity_analysis.py` | `build_shocked_life_table()` helper |
| `backend/tests/test_scr.py` | SCR unit tests (planned) |
| `backend/tests/test_portfolio.py` | Portfolio unit tests (planned) |
