# 11 -- Life Table Foundations: Technical Reference

**Module:** `backend/engine/a01_life_table.py`
**Tests:** `backend/tests/test_life_table.py`

---

## 1. Overview

The life table is the foundational data structure in actuarial science. It tracks the survival and mortality experience of a hypothetical cohort from birth (or any starting age) through the ultimate age $\omega$. Every actuarial calculation -- premiums, reserves, annuities, insurance values -- ultimately depends on a life table.

The `LifeTable` class implements the **complete (single-year) life table**, providing the four fundamental columns: $l_x$, $d_x$, $q_x$, and $p_x$.

---

## 2. Mathematical Definitions

### 2.1 The Survivor Function: $l_x$

$l_x$ is the number of survivors at exact age $x$ from an initial cohort. It is the **sole input**; all other columns are derived from it.

- $l_0$ is called the **radix** (conventionally 100,000 in published tables, though any positive value works)
- $l_x$ is a non-increasing function: $l_{x+1} \leq l_x$ for all $x$
- $l_\omega > 0$ (there must be survivors at the terminal age for the table to be well-defined)

### 2.2 Deaths: $d_x$

$$d_x = l_x - l_{x+1} \quad \text{for } x < \omega$$

$$d_\omega = l_\omega \quad \text{(all remaining survivors die at the terminal age)}$$

$d_x$ represents the number of deaths between exact age $x$ and exact age $x+1$.

### 2.3 Mortality Probability: $q_x$

$$q_x = \frac{d_x}{l_x} = \frac{l_x - l_{x+1}}{l_x} = 1 - \frac{l_{x+1}}{l_x}$$

$q_x$ is the **conditional probability** that a person alive at exact age $x$ dies before reaching age $x+1$. This is the one-year probability of death.

At the terminal age: $q_\omega = 1.0$ (death is certain).

Special case: if $l_x = 0$, then $q_x = 1.0$ by convention (no survivors means certain death).

### 2.4 Survival Probability: $p_x$

$$p_x = 1 - q_x = \frac{l_{x+1}}{l_x}$$

$p_x$ is the probability that a person alive at age $x$ survives to age $x+1$.

At the terminal age: $p_\omega = 0.0$.

---

## 3. Fundamental Identities

### 3.1 Conservation of Lives (Telescoping Sum)

$$\sum_{x=\alpha}^{\omega} d_x = l_\alpha$$

where $\alpha$ is the starting age of the table. This is a **conservation law**: every person alive at age $\alpha$ must eventually die. The proof is immediate by telescoping:

$$\sum_{x=\alpha}^{\omega} d_x = (l_\alpha - l_{\alpha+1}) + (l_{\alpha+1} - l_{\alpha+2}) + \cdots + (l_{\omega-1} - l_\omega) + l_\omega = l_\alpha$$

### 3.2 Terminal Age Condition

$$q_\omega = 1.0, \quad p_\omega = 0.0, \quad d_\omega = l_\omega$$

The table must "close": no one survives past $\omega$.

### 3.3 Multi-Year Survival

$$_np_x = \frac{l_{x+n}}{l_x} = \prod_{k=0}^{n-1} p_{x+k}$$

The probability of surviving $n$ years from age $x$ is the product of successive one-year survival probabilities, or equivalently the ratio of survivors.

### 3.4 Deferred Mortality

$$_{n|}q_x = \frac{l_{x+n} - l_{x+n+1}}{l_x} = \;_np_x \cdot q_{x+n}$$

The probability of surviving $n$ years and then dying in year $n+1$.

---

## 4. The Radix Convention

Published mortality tables typically use $l_0 = 100{,}000$ as the radix. This convention:

1. Makes $l_x$ values easy to interpret (e.g., $l_{65} = 82{,}345$ means 82.3% survive to 65)
2. Keeps $d_x$ as whole numbers (or close to it) for readability
3. Does **not** affect $q_x$ or $p_x$, which are ratios and thus independent of scale

The `LifeTable` class accepts any positive radix. When used with `CommutationFunctions`, the radix cancels in all actuarial value formulas (since both numerator and denominator contain $l_x$-derived terms).

---

## 5. The `LifeTable` Class API

### 5.1 Constructor

```python
LifeTable(ages: List[int], l_x_values: List[float])
```

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `ages` | `List[int]` | Consecutive integer ages |
| `l_x_values` | `List[float]` | Survivors at each age (same length as `ages`) |

**Validations on construction:**
- `ages` and `l_x_values` must have equal length
- At least 2 ages are required (need $l_x$ and $l_{x+1}$ to compute $d_x$)

**Computed on `__init__`:**
- `self.l_x: Dict[int, float]` -- survivor dictionary
- `self.d_x: Dict[int, float]` -- deaths (via `_compute_derivatives()`)
- `self.q_x: Dict[int, float]` -- mortality rates
- `self.p_x: Dict[int, float]` -- survival rates

### 5.2 Class Method: `from_csv`

```python
@classmethod
LifeTable.from_csv(filepath: str) -> LifeTable
```

Loads a life table from a CSV file with the expected format:

```csv
age,l_x
60,1000.00
61,850.00
62,700.00
...
```

Uses Python's `csv.DictReader`, expecting columns named exactly `age` and `l_x`.

### 5.3 Instance Method: `subset`

```python
subset(start_age: int, end_age: int) -> LifeTable
```

Creates a new `LifeTable` restricted to `[start_age, end_age]`. Useful for:
- Analyzing specific age ranges
- Creating tables for products with limited coverage periods
- Validation against reference sub-tables

Raises `ValueError` if the requested range is out of bounds.

### 5.4 Accessor Methods

| Method | Returns | Description |
|:-------|:--------|:------------|
| `get_l(age)` | `float` | Survivors $l_x$ at age $x$ |
| `get_d(age)` | `float` | Deaths $d_x$ at age $x$ |
| `get_q(age)` | `float` | Mortality probability $q_x$ at age $x$ |
| `get_p(age)` | `float` | Survival probability $p_x$ at age $x$ |

All raise `KeyError` if the age is not in the table.

### 5.5 Properties

| Property | Type | Description |
|:---------|:-----|:------------|
| `omega` | `int` | Ultimate (terminal) age $\omega$ |
| `ages` | `List[int]` | All ages in the table as a list |
| `min_age` | `int` | First age in the table |
| `max_age` | `int` | Last age in the table (same as $\omega$) |

### 5.6 Validation Method

```python
validate() -> Dict[str, bool]
```

Returns a dictionary with three checks:

| Key | Validates | Formula |
|:----|:----------|:--------|
| `sum_deaths_equals_l0` | Conservation of lives | $\sum d_x \approx l_{\alpha}$ (tolerance $10^{-6}$) |
| `terminal_mortality_is_one` | Terminal closure | $q_\omega \approx 1.0$ (tolerance $10^{-6}$) |
| `all_rates_valid` | Probability bounds | $0 \leq q_x \leq 1$ for all $x$ |

---

## 6. Internal Computation: `_compute_derivatives()`

The private method `_compute_derivatives()` derives $d_x$, $q_x$, and $p_x$ from $l_x$:

```
FOR age FROM min_age TO max_age - 1:
    d_x[age] = l_x[age] - l_x[age + 1]
    q_x[age] = d_x[age] / l_x[age]       (or 1.0 if l_x[age] == 0)
    p_x[age] = 1.0 - q_x[age]

# Terminal age (omega):
d_x[omega] = l_x[omega]
q_x[omega] = 1.0
p_x[omega] = 0.0
```

The edge case handling (division by zero when $l_x = 0$) sets $q_x = 1.0$, which is actuarially correct: if no one is alive, death is certain in a vacuous sense.

---

## 7. Connection to Commutation Functions

The `LifeTable` is the **input** to `CommutationFunctions`:

```python
lt = LifeTable(ages, l_x_values)
comm = CommutationFunctions(lt, interest_rate=0.05)
```

The commutation functions apply a discount factor $v = 1/(1+i)$ to the life table columns:

$$D_x = v^x \cdot l_x, \qquad C_x = v^{x+1} \cdot d_x$$

From these, all actuarial present values ($A_x$, $\ddot{a}_x$, $_nE_x$) are computed as ratios, making the life table the ultimate source of all pricing and reserving.

---

## 8. Connection to Empirical Data (Lee-Carter Pipeline)

In the SIMA project, life tables can be constructed from empirical mortality data through the Lee-Carter pipeline:

```
MortalityData (m_x) --> Graduation (smooth m_x) --> Lee-Carter (project m_x)
                                                          |
                                                   to_life_table()
                                                          |
                                                      LifeTable
```

The bridge uses the conversion:

$$q_x = 1 - e^{-m_x}$$

where $m_x$ is the central death rate, and then builds $l_x$ recursively:

$$l_0 = 100{,}000, \qquad l_{x+1} = l_x \cdot (1 - q_x) = l_x \cdot p_x$$

---

## 9. Complete vs. Abridged Tables

The `LifeTable` class implements a **complete** (single-year age interval) life table. In contrast:

- **Abridged tables** use wider age groups (0, 1-4, 5-9, ..., 85+)
- **Select tables** condition on both age and duration since policy issue
- **Ultimate tables** apply after the select period ends

The current implementation assumes single-year age intervals and consecutive integer ages.

---

## 10. Notation Summary

| Symbol | Name | Domain | Computed From |
|:-------|:-----|:-------|:--------------|
| $l_x$ | Survivors | $l_x \geq 0$, non-increasing | Input |
| $d_x$ | Deaths | $d_x \geq 0$ | $l_x - l_{x+1}$ |
| $q_x$ | Mortality probability | $0 \leq q_x \leq 1$ | $d_x / l_x$ |
| $p_x$ | Survival probability | $0 \leq p_x \leq 1$ | $1 - q_x$ |
| $\omega$ | Ultimate age | Integer | $\max(\text{ages})$ |
| $l_0$ | Radix | Positive real | Convention (e.g., 100,000) |

---

*Created: February 2026*
