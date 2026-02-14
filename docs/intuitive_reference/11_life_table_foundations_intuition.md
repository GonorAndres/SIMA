# 11 -- Life Table Foundations: Intuitive Reference

**Module:** `backend/engine/a01_life_table.py`

---

## 1. The Story of 100,000 Newborns

Imagine you gather 100,000 newborns on January 1st of some year. You follow them through their entire lives, recording who dies each year. At the end, you have a complete record:

- **Year 0:** 100,000 alive. 650 die in the first year.
- **Year 1:** 99,350 alive. 45 die.
- **Year 2:** 99,305 alive. 30 die.
- ...
- **Year 85:** 42,100 alive. 4,850 die.
- ...
- **Year 110:** 12 alive. All 12 die.

That record **is** the life table. The column $l_x$ (survivors at age $x$) tells the entire story. Everything else is derived from counting who is left.

---

## 2. Why $l_x$ Is the Foundation

The life table has four columns, but only one is truly independent:

```
l_x (survivors)         <-- THE INPUT. Everything else comes from this.
  |
  +-- d_x = l_x - l_{x+1}    "How many died this year?"
  |
  +-- q_x = d_x / l_x         "What fraction died?"
  |
  +-- p_x = 1 - q_x           "What fraction survived?"
```

Think of $l_x$ as a **tank of water** that drains over time. Each year, some water (people) flows out ($d_x$). The rate of outflow relative to the current level is $q_x$. The fraction that stays is $p_x$.

If you have $l_x$, you can compute everything. If you lose $l_x$, you can rebuild it from any of the others (given the starting value). The columns are different views of the same underlying reality.

---

## 3. $q_x$ vs. $p_x$: Two Sides of a Coin

$q_x$ and $p_x$ are complementary probabilities. They always add to 1:

```
q_x + p_x = 1    (always)

q_x = "risk"      -- probability of death within the year
p_x = "safety"    -- probability of surviving the year
```

**Which one do actuaries focus on?** Both, depending on context:

- **Pricing insurance (death benefits):** Focus on $q_x$. Higher $q_x$ means more claims, higher premiums.
- **Pricing annuities (survival benefits):** Focus on $p_x$. Higher $p_x$ means longer payments, higher cost.
- **Reserves:** Both matter. The reserve balances future death claims against future premium income.

**Mental model:** If you are selling life insurance, $q_x$ is your "cost driver." If you are selling pensions, $p_x$ is your "cost driver." Same data, different perspective.

---

## 4. What Does $q_{40} = 0.002$ Actually Mean?

It means: **out of every 1,000 people who are alive at their 40th birthday, about 2 of them will die before turning 41.**

More precisely, it is a conditional probability:

$$q_{40} = P(\text{die before 41} \mid \text{alive at 40})$$

The "conditional" part matters. This is NOT the probability that a random newborn dies at age 40. It is the probability that someone who has already survived to 40 dies in the next year.

**Real-world calibration:**
- $q_{20} \approx 0.001$ -- very low, healthy young adults
- $q_{40} \approx 0.002$ -- still low, beginning to rise
- $q_{65} \approx 0.015$ -- noticeable, retirement age
- $q_{85} \approx 0.10$ -- high, 1 in 10 die each year
- $q_{100} \approx 0.35$ -- very high, but not 1.0 (some centenarians survive!)

---

## 5. The Radix: Why 100,000?

The radix $l_0$ is the starting population size. Published tables use 100,000 by convention. But here is the key insight: **the radix does not matter for any calculation.**

Why? Because every useful quantity is a **ratio**:

$$q_x = \frac{d_x}{l_x} = \frac{l_x - l_{x+1}}{l_x}$$

If you double $l_0$ (to 200,000), then both $l_x$ and $d_x$ double, and the ratio stays the same. It is like converting a recipe from "serves 4" to "serves 8" -- the proportions do not change.

The radix is a **presentation choice**, not a mathematical one. The LifeTable class accepts any positive radix.

---

## 6. The Conservation Law: Everyone Dies

One of the most important (and obvious) properties of a life table:

$$\sum_{x=0}^{\omega} d_x = l_0$$

**Translation:** If you add up all the deaths from every age, you get back the initial population. No one disappears. No one is immortal. Everyone who starts alive ends up dead.

This is a **telescoping sum**:

```
d_0 + d_1 + d_2 + ... + d_{omega}
= (l_0 - l_1) + (l_1 - l_2) + ... + (l_{omega-1} - l_{omega}) + l_{omega}
= l_0
```

Each intermediate $l_x$ appears once with a + and once with a -, so they all cancel, leaving only $l_0$.

**Why this matters:** This is your first sanity check for any life table. If the deaths do not sum to the initial population, something is wrong with the data.

---

## 7. Terminal Age ($\omega$) and the Closing of the Table

Every life table must have a terminal age $\omega$ where:

$$q_\omega = 1.0, \quad p_\omega = 0.0, \quad d_\omega = l_\omega$$

This says: everyone who reaches age $\omega$ dies. The table "closes."

**Common gotcha:** $q_\omega = 1.0$ does not mean age $\omega$ is the maximum human lifespan. It means the table has been truncated at that point. In practice:

- The EMSSA-2009 table closes at $\omega = 99$
- HMD tables often extend to $\omega = 110$ or $\omega = 110+$
- The choice of $\omega$ affects annuity calculations (longer tables = higher annuity values)

In the codebase, the `LifeTable` class sets $d_\omega = l_\omega$ and $q_\omega = 1.0$ automatically. You do not need to handle this in your input data.

---

## 8. Complete vs. Abridged Life Tables

**Complete table:** One row per year of age (0, 1, 2, 3, ..., 110). This is what the `LifeTable` class implements.

**Abridged table:** Wider age groups (0, 1-4, 5-9, 10-14, ..., 85+). Used when data is sparse or for quick reference.

The complete table is more precise and is what you need for actuarial pricing. Abridged tables are useful for demographic analysis but require interpolation for insurance calculations.

---

## 9. How the Life Table Connects to Everything Else

The life table is the **starting point** for the entire actuarial engine:

```
                    LifeTable (l_x)
                         |
                  + interest rate
                         |
               CommutationFunctions
               (D_x, N_x, C_x, M_x)
                    /    |    \
                   /     |     \
        Actuarial    Premiums   Reserves
         Values     (equivalence  (prospective
      (A_x, a_x)    principle)    method)
```

Without $l_x$, there are no commutation functions. Without commutation functions, there are no premiums or reserves. The life table is truly the foundation.

---

## 10. Interview Elevator Pitch

If someone asks "What is a life table?" in an interview, here is a concise answer:

> "A life table tracks the survival experience of a cohort through time. Starting from a hypothetical group of, say, 100,000 people, it records how many survive to each age ($l_x$), how many die at each age ($d_x$), and the corresponding mortality and survival probabilities ($q_x$ and $p_x$). The key property is that $l_x$ alone is sufficient -- everything else is derived from it. In actuarial practice, the life table is the foundation for all pricing and reserving: it feeds into commutation functions, which produce insurance values, premiums, and reserves."

**Follow-up questions to prepare for:**

1. "How do you handle the terminal age?" -- $q_\omega = 1.0$ by definition; the table must close.
2. "What if $l_x = 0$ at some age before $\omega$?" -- $q_x = 1.0$ by convention; the cohort has been absorbed.
3. "How do you get $l_x$ in practice?" -- From observed mortality rates $m_x$ (central death rates from population data), converted via $q_x = 1 - e^{-m_x}$, then $l_{x+1} = l_x \cdot p_x$.
4. "Does the radix affect premiums?" -- No. All actuarial values are ratios, so the scale of $l_x$ cancels out.

---

## 11. Common Gotchas

1. **$q_x$ at the last age is always 1.0.** If it is not, your table is broken or not properly closed.

2. **$l_x$ must be non-increasing.** If $l_{x+1} > l_x$, you have "negative deaths," which makes no physical sense (people do not un-die).

3. **The table does not start at age 0.** The `LifeTable` class supports any starting age. A table from ages 20-110 is perfectly valid. The conservation law still holds: $\sum d_x = l_{20}$.

4. **$q_x$ is NOT the unconditional probability of dying at age $x$.** It is the conditional probability given survival to $x$. The unconditional probability is $\frac{d_x}{l_0}$.

5. **Mortality rates are NOT constant across the lifespan.** They follow a bathtub curve: high in infancy, low in youth, then exponentially rising after middle age (Gompertz law).

---

## 12. The Code in Action

```python
from backend.engine.a01_life_table import LifeTable

# Create from lists
ages = [60, 61, 62, 63, 64, 65]
l_x  = [1000, 850, 700, 540, 370, 200]
lt = LifeTable(ages, l_x)

# Or load from CSV
lt = LifeTable.from_csv("backend/data/mini_table.csv")

# Query individual values
lt.get_q(60)   # 0.15 -- 15% mortality at age 60
lt.get_p(60)   # 0.85 -- 85% survival at age 60
lt.get_d(60)   # 150  -- 150 deaths between 60 and 61

# Validate consistency
lt.validate()
# {'sum_deaths_equals_l0': True,
#  'terminal_mortality_is_one': True,
#  'all_rates_valid': True}

# Feed into the actuarial engine
from backend.engine.a02_commutation import CommutationFunctions
comm = CommutationFunctions(lt, interest_rate=0.05)
# Now you have D_x, N_x, C_x, M_x for pricing and reserving
```

---

*Created: February 2026*
