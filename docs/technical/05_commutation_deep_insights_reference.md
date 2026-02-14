# Commutation Functions: Technical Reference

## Formula Derivation: ä_x = N_x / D_x

### Definitions

```
D_x = v^x × l_x           (discounted radix at age x)
N_x = Σ D_y  (y = x to ω) (sum of future discounted radix)
```

### Derivation

```
N_x   Σ(y=x to ω) v^y × l_y
─── = ─────────────────────
D_x        v^x × l_x

      Σ(y=x to ω) v^y × l_y
    = ─────────────────────
           v^x × l_x

      Σ(k=0 to ω-x) v^(x+k) × l_(x+k)
    = ─────────────────────────────────
              v^x × l_x

      Σ(k=0 to ω-x) v^k × (l_(x+k) / l_x)
    = ─────────────────────────────────────
                     1

    = Σ(k=0 to ω-x) v^k × ₖp_x

    = ä_x
```

Where ₖp_x = l_{x+k} / l_x is the k-year survival probability from age x.

### Key Transformation

The division by D_x transforms cohort counts into probabilities:

```
l_{x+k}
─────── = ₖp_x
  l_x
```

---

## Computational Complexity

### Forward Summation: O(n²)

```
N_x = Σ(y=x to ω) D_y

Operations for each N_x:
  N_ω:     0 additions
  N_{ω-1}: 1 addition
  ...
  N_x:     (ω - x) additions

Total = Σ(k=0 to n-1) k = n(n-1)/2 ∈ O(n²)
```

### Backward Recursion: O(n)

```
N_ω = D_ω                 (base case)
N_x = D_x + N_{x+1}       (recursive case)

Operations:
  1 addition per age (except ω)

Total = n - 1 ∈ O(n)
```

### Complexity Comparison

| n | Forward O(n²) | Backward O(n) | Speedup |
|---|---------------|---------------|---------|
| 10 | 45 | 9 | 5x |
| 100 | 4,950 | 99 | 50x |
| 1,000 | 499,500 | 999 | 500x |

---

## Mathematical Properties

### Recursion Relations

```
N_x = D_x + N_{x+1}       (backward from ω)
M_x = C_x + M_{x+1}       (backward from ω)
```

### Difference Formulas

```
N_x - N_{x+n} = D_x + D_{x+1} + ... + D_{x+n-1}  (n terms)
M_x - M_{x+n} = C_x + C_{x+1} + ... + C_{x+n-1}  (n terms)
```

### Ratio Formulas

```
ä_x = N_x / D_x           (annuity-due)
A_x = M_x / D_x           (whole life insurance)
ₙE_x = D_{x+n} / D_x      (pure endowment)
```

---

## Code Implementation

### Backward Recursion (commutation.py)

```python
def _compute_N(self) -> None:
    omega = self.life_table.omega

    # Base case
    self.N[omega] = self.D[omega]

    # Recursive case: O(n) operations
    for age in range(omega - 1, self.life_table.min_age - 1, -1):
        self.N[age] = self.D[age] + self.N[age + 1]
```

### Actuarial Value Computation (actuarial_values.py)

```python
def a_due(self, x: int) -> float:
    # ä_x = N_x / D_x
    # Division by D_x converts cohort to per-person
    return self.comm.get_N(x) / self.comm.get_D(x)
```
