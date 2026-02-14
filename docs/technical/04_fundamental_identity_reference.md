# The Fundamental Identity - Technical Reference

## Identity Statement

```
A_x + d · ä_x = 1

Where:
  A_x   = M_x / D_x       (whole life insurance APV)
  ä_x   = N_x / D_x       (whole life annuity-due APV)
  d     = i / (1 + i)     (discount rate)
  i     = interest rate
  v     = 1 / (1 + i)     (discount factor)
```

---

## Definitions

| Symbol | Formula | Description |
|--------|---------|-------------|
| d | i / (1+i) = iv | Discount rate; PV of $1 interest at year end |
| v | 1 / (1+i) | Discount factor; PV of $1 due in 1 year |
| A_x | M_x / D_x | APV of $1 paid at death |
| ä_x | N_x / D_x | APV of $1/year annuity-due |

---

## Derivation

### Method 1: From Annuity-Insurance Relationship

```
The standard relationship:
  ä_x = (1 - A_x) / d

Rearranging:
  d · ä_x = 1 - A_x
  A_x + d · ä_x = 1
```

### Method 2: Expectation Proof

```
Let K = curtate future lifetime (integer years until death)

A_x = E[v^K]

ä_x = E[1 + v + v² + ... + v^{K-1}]
    = E[(1 - v^K) / (1 - v)]
    = E[(1 - v^K) / d]

Therefore:
  d · ä_x = E[1 - v^K] = 1 - E[v^K] = 1 - A_x

  A_x + d · ä_x = 1  ∎
```

### Method 3: Commutation Functions

```
A_x + d · ä_x = M_x/D_x + d · N_x/D_x
             = (M_x + d · N_x) / D_x

Using the relationship M_x = D_x - d · N_x:
             = (D_x - d · N_x + d · N_x) / D_x
             = D_x / D_x
             = 1  ∎
```

---

## Economic Interpretation

### Present Value Decomposition

$1 today decomposes into:

| Component | Value | Interpretation |
|-----------|-------|----------------|
| A_x | M_x / D_x | PV of principal returned at death |
| d · ä_x | d · N_x / D_x | PV of interest earned while alive |
| Total | 1 | Original deposit |

### No-Arbitrage Pricing

Fair single premium for $1 death benefit:
```
π = A_x

At this price:
  E[PV(premium income)] = E[PV(benefit outgo)]
  A_x = A_x  ✓
```

If premium π ≠ A_x:
- π > A_x: Insurer profit = π - A_x
- π < A_x: Insurer loss = A_x - π

---

## Related Identities

### Temporary Insurance and Annuity

```
A^1_{x:n|} + d · ä_{x:n|} + ₙE_x = 1

Where:
  A^1_{x:n|} = (M_x - M_{x+n}) / D_x    (term insurance)
  ä_{x:n|}   = (N_x - N_{x+n}) / D_x    (temporary annuity)
  ₙE_x       = D_{x+n} / D_x            (pure endowment)
```

### Endowment Insurance

```
A_{x:n|} + d · ä_{x:n|} = 1

Where:
  A_{x:n|} = A^1_{x:n|} + ₙE_x   (endowment = term + pure endowment)
```

### Annuity-Immediate

```
A_x + d · (1 + a_x) = 1
A_x + d + d · a_x = 1
d · a_x = 1 - A_x - d = (1-d) - A_x = v - A_x

Where:
  a_x = ä_x - 1   (annuity-immediate, first payment at year end)
```

---

## Numerical Example

Using mini table (ages 60-65, i = 5%):

```
i = 0.05
d = 0.05 / 1.05 = 0.047619
v = 1 / 1.05 = 0.952381

At age 60:
  D_60 = 1000.0000
  N_60 = 3372.0219
  M_60 = 839.4275

  A_60 = M_60 / D_60 = 0.839428
  ä_60 = N_60 / D_60 = 3.372022

  d · ä_60 = 0.047619 × 3.372022 = 0.160572

  A_60 + d · ä_60 = 0.839428 + 0.160572 = 1.000000  ✓
```

---

## Code Implementation

### Test (test_premiums_reserves.py)

```python
def test_actuarial_identity(comm, av):
    i = comm.i
    d = i / (1 + i)

    for age in range(60, 66):
        A = av.A_x(age)
        a = av.a_due(age)
        result = A + d * a
        assert result == pytest.approx(1.0, rel=1e-6)
```

### Computation (actuarial_values.py)

```python
def A_x(self, x: int) -> float:
    # Line 72
    return self.comm.get_M(x) / self.comm.get_D(x)

def a_due(self, x: int) -> float:
    # Line 102
    return self.comm.get_N(x) / self.comm.get_D(x)
```

---

## Applications

1. **Premium Calculation**: A_x / ä_x = M_x / N_x = net premium rate
2. **Reserve Validation**: Ensures consistency in prospective calculations
3. **Arbitrage Pricing**: Determines fair value of insurance contracts
4. **Decomposition Analysis**: Separates mortality cost from interest earnings
