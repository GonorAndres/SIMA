# Commutation Functions: Deep Insights

## Insight 1: Why ä_x = N_x / D_x Works

### The Apparent Mystery

At first glance, this formula seems strange:

```
N_x = D_60 + D_61 + D_62 + ... + D_omega  (aggregate cohort value)
D_x = discounted survivors at age x       (aggregate cohort value)

ä_x = N_x / D_x = individual annuity value ???
```

How does dividing two **aggregate cohort values** give us a **per-person** result?

---

### The Key: D_x Contains the Radix

**D_x is the discounted value of the radix (cohort size) at age x.**

When we divide by D_x, we're dividing by a quantity proportional to l_x (the number of people). This converts cohort totals into per-person values.

---

### Expanded Form

Let's write out N_x / D_x explicitly:

```
N_x   D_x + D_{x+1} + D_{x+2} + ... + D_omega
─── = ────────────────────────────────────────
D_x                    D_x

      v^0×l_x + v^1×l_{x+1} + v^2×l_{x+2} + ...
    = ──────────────────────────────────────────
                       l_x

      l_x       l_{x+1}       l_{x+2}
    = ─── + v × ─────── + v² × ─────── + ...
      l_x         l_x           l_x

    = 1 + v × p_x + v² × ₂p_x + v³ × ₃p_x + ...
```

Where:
- l_{x+k} / l_x = ₖp_x = probability of surviving k years from age x
- v^k = discount factor for k years

---

### The Division Converts Counts to Probabilities

| Expression | Meaning |
|------------|---------|
| l_{x+1} | Number of survivors at age x+1 (cohort) |
| l_{x+1} / l_x | Probability of surviving to x+1 (individual) |
| D_{x+1} | Discounted survivors at x+1 (cohort) |
| D_{x+1} / D_x | Discounted survival probability (individual) |

**Dividing by D_x (which contains l_x) converts cohort counts into survival probabilities!**

---

### Numerical Verification

Using mini table (ages 60-65, i = 5%, l_60 = 1000):

**Method 1: Aggregate (N_x / D_x)**
```
N_60 / D_60 = 3372.02 / 1000.00 = 3.372022
```

**Method 2: Individual (sum of discounted survival probabilities)**
```
Year  k    ₖp_60      v^k        v^k × ₖp_60
────────────────────────────────────────────
  60  0   1.0000   1.000000      1.000000
  61  1   0.8500   0.952381      0.809524
  62  2   0.7000   0.907029      0.634921
  63  3   0.5400   0.863838      0.466472
  64  4   0.3700   0.822702      0.304400
  65  5   0.2000   0.783526      0.156705
────────────────────────────────────────────
                          Sum =  3.372022
```

**Both methods give identical results!**

---

### Two Equivalent Views

| View | Formula | Interpretation |
|------|---------|----------------|
| **Aggregate** (insurer) | N_x / D_x | Total payments / Total people |
| **Individual** (policyholder) | Σ v^k × ₖp_x | Expected discounted survival years |

Both views give the same answer because of the **Law of Large Numbers**:
- Individual expected value = Cohort average

---

### The Pizza Analogy

```
Total pizza slices   300 slices
─────────────────── = ────────── = 3 slices per person
Number of people     100 people

Total discounted person-years   N_x
────────────────────────────── = ─── = years per person
Discounted persons at age x     D_x
```

---

### Connection to Equivalence / Fairness

**Aggregate view (insurer):**
- 1000 people buy annuities at age 60
- Total payments = N_60 = 3372 (discounted person-years)
- For break-even: price per person = N_60 / D_60 = 3.37

**Individual view (policyholder):**
- You (one person) expect to receive payments for 3.37 discounted years
- Fair price = 3.37

**Both perspectives agree on the fair price!**

---

## Insight 2: Why Backward Recursion is O(n) vs O(n²)

### The Two Approaches

**Forward approach:** Compute each N_x by summing from x to omega
```
N_60 = D_60 + D_61 + D_62 + D_63 + D_64 + D_65  (5 additions)
N_61 = D_61 + D_62 + D_63 + D_64 + D_65         (4 additions)
N_62 = D_62 + D_63 + D_64 + D_65                (3 additions)
N_63 = D_63 + D_64 + D_65                       (2 additions)
N_64 = D_64 + D_65                              (1 addition)
N_65 = D_65                                     (0 additions)
                                          Total: 15 additions
```

**Backward approach:** Use recursion N_x = D_x + N_{x+1}
```
N_65 = D_65           (0 additions, just assign)
N_64 = D_64 + N_65    (1 addition, reuses N_65)
N_63 = D_63 + N_64    (1 addition, reuses N_64)
N_62 = D_62 + N_63    (1 addition, reuses N_63)
N_61 = D_61 + N_62    (1 addition, reuses N_62)
N_60 = D_60 + N_61    (1 addition, reuses N_61)
                Total: 5 additions
```

---

### Visual Comparison

```
FORWARD (triangle of operations):     BACKWARD (line of operations):

N_60: x x x x x  (5)                  N_65:    (0)
N_61: x x x x    (4)                  N_64: x  (1)
N_62: x x x      (3)                  N_63: x  (1)
N_63: x x        (2)                  N_62: x  (1)
N_64: x          (1)                  N_61: x  (1)
N_65:            (0)                  N_60: x  (1)
─────────────────────                 ───────────────
Total: 15 (triangle)                  Total: 5 (line)
```

---

### Why Forward is O(n²)

The forward approach computes:
```
Total additions = (n-1) + (n-2) + (n-3) + ... + 1 + 0
                = n(n-1)/2
                ≈ n²/2
```

This is the **triangular number formula**. As n grows, operations grow like n².

---

### How It Scales

| n (ages) | Forward | Backward | Ratio |
|----------|---------|----------|-------|
| 6 | 15 | 5 | 3x |
| 10 | 45 | 9 | 5x |
| 50 | 1,225 | 49 | 25x |
| 100 | 4,950 | 99 | 50x |
| 1,000 | 499,500 | 999 | 500x |

For a realistic life table (ages 0-110):
- Forward: 6,105 additions
- Backward: 110 additions
- **Backward is 56x faster!**

---

### The Key Insight: Reuse vs Recomputation

**Forward RE-COMPUTES overlapping sums:**
```
N_60 = D_60 + [D_61 + D_62 + D_63 + D_64 + D_65]
N_61 =        [D_61 + D_62 + D_63 + D_64 + D_65]  <- same work!
```

**Backward REUSES previous results:**
```
N_65 = D_65
N_64 = D_64 + N_65   <- reuses N_65, no recalculation
N_63 = D_63 + N_64   <- reuses N_64, no recalculation
```

This is an example of **dynamic programming** - storing intermediate results to avoid redundant computation.

---

## Code Reference

In SIMA, the backward recursion is implemented in `backend/engine/commutation.py`:

```python
def _compute_N(self) -> None:
    omega = self.life_table.omega

    # Base case: N_omega = D_omega
    self.N[omega] = self.D[omega]

    # Recursive case: work backwards
    for age in range(omega - 1, self.life_table.min_age - 1, -1):
        self.N[age] = self.D[age] + self.N[age + 1]
```

The same pattern applies to M_x = C_x + M_{x+1}.
