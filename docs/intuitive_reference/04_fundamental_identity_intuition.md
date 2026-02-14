# The Fundamental Identity: A_x + d*a_x = 1

## The Identity

For any age x:

```
A_x + d * ä_x = 1

Where:
  A_x   = PV of $1 paid at death (whole life insurance value)
  ä_x   = PV of $1/year annuity-due (expected discounted years alive)
  d     = i/(1+i) = discount rate (PV of one year's interest on $1)
```

---

## What Does d Mean?

The discount rate `d` is the **present value of one year's interest** on $1.

```
If you have $1 earning interest rate i:
  - At year end, you earn $i in interest
  - But that $i at year end is worth only $i/(1+i) = d TODAY

Example with i = 5%:
  d = 0.05 / 1.05 = 0.047619

  $1 earns $0.05 at year end
  PV of that $0.05 = $0.0476 today
```

**Key formula:** `d × Capital = PV of one year's interest on that capital`

---

## What Does d * ä_x Mean?

If `d` is PV of one year's interest, then `d * ä_x` is **PV of lifetime interest**.

```
d * ä_x = PV of earning interest on $1 for your entire remaining lifetime

Breakdown:
  Year 0: earn d (PV of this year's interest)
  Year 1: earn d × v × p_x (discounted, if alive)
  Year 2: earn d × v² × ₂p_x (discounted, if alive)
  ...

  Sum = d × (1 + v*p_x + v²*₂p_x + ...) = d × ä_x
```

---

## The Decomposition: Splitting $1 Into Two Streams

The identity says $1 today can be perfectly split into:

| Component | Formula | Meaning |
|-----------|---------|---------|
| Death benefit | A_x | PV of $1 paid when you die |
| Lifetime interest | d * ä_x | PV of interest earned while alive |
| **Total** | **1** | **Original $1** |

### Mental Model: The Bank Account

```
Imagine depositing $1 in a life-contingent account:

WHILE ALIVE:
  - Account earns interest at rate i
  - You withdraw the interest each year (keeping principal)
  - PV of all interest withdrawals = d * ä_x

AT DEATH:
  - The $1 principal goes to your beneficiary
  - PV of this payment = A_x

TOTAL: d * ä_x + A_x = $1 (what you deposited)
```

---

## The No-Arbitrage Interpretation

This identity reveals the **fair price** for life insurance.

### If Insurer Charges $1 for $1 Death Benefit:

```
Insurer receives:     $1.00
Insurer pays out:     A_x = $0.84 (PV of death benefit)
Insurer keeps:        d*ä_x = $0.16 (PV of interest earned)

PROFIT = $0.16 (the interest!)
```

This is **overpriced** - the policyholder is paying too much.

### Fair Price (No Arbitrage):

```
Fair single premium = A_x = $0.84

At this price:
  - Insurer receives A_x
  - Invests and earns interest while policyholder alive
  - Interest exactly funds the gap between A_x and $1 death benefit
  - Expected profit = $0
```

### Arbitrage Summary

| Price Charged | Profit | Status |
|--------------|--------|--------|
| $1.00 | +$0.16 | Overpriced (arbitrage for insurer) |
| A_x = $0.84 | $0.00 | Fair price (no arbitrage) |
| $0.70 | -$0.14 | Underpriced (arbitrage for policyholder) |

---

## Present Value Equivalence: Timing Doesn't Matter

A key insight: **The identity holds regardless of how premiums are paid.**

### Single Premium vs Annual Premiums

```
CASE A: Single Premium of $1
  PV of premiums = $1.00

CASE B: Annual Premium P where P × ä_x = $1
  P = $1 / ä_x = $0.2966 per year
  PV of premiums = $0.2966 × 3.37 = $1.00
```

Both have **the same present value**, so:
- PV of interest earned = d × ä_x = $0.1606 (same for both!)
- PV of death benefit = A_x = $0.8394 (same for both!)

### Why This Works

Present value "collapses" all cash flows to t=0. Once you have PV = $1, the decomposition is:

```
$1 = A_x + d × ä_x
   = (PV of death benefit) + (PV of interest)
```

The **timing** of premium payments is different, but the **present value** is the same.

---

## The Fundamental Equation

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│    PV(Premiums) = PV(Interest) + PV(Death Benefit)    │
│                                                        │
│         $1      =    d*ä_x    +      A_x              │
│                                                        │
│      Premium    =   Insurer   +    Policyholder       │
│                     Keeps          Receives           │
│                                                        │
└────────────────────────────────────────────────────────┘
```

This is a **conservation of value**: nothing is created or destroyed, just split between:
- What the insurer earns (interest while you're alive)
- What the beneficiary receives (death benefit)

---

## Interview Application

### Common Questions This Helps Answer:

1. **"Why is A_x always less than 1?"**
   - Because death is certain but delayed
   - The delay means discounting reduces the PV
   - A_x + d*ä_x = 1 shows exactly where the "missing" value goes (interest)

2. **"What's the fair price for life insurance?"**
   - Fair single premium = A_x (no arbitrage)
   - Fair annual premium = A_x / ä_x = M_x / N_x

3. **"How does the insurer make money?"**
   - If they charge more than fair price: profit = markup
   - At fair price: zero expected profit (competitive market)
   - Real profit comes from: expense loading, investment returns above assumed i, mortality better than assumed

4. **"Why does payment timing not affect PV?"**
   - PV discounts all cash flows to t=0
   - Different timing, same total PV = same economics
   - This is why equivalence principle works for any premium pattern

---

## Mathematical Derivation

For completeness, here's why the identity holds:

```
Start with the annuity-insurance relationship:
  ä_x = (1 - A_x) / d

Rearranging:
  d * ä_x = 1 - A_x
  A_x + d * ä_x = 1  ✓

Alternative proof using expectations:
  A_x = E[v^K]           (K = curtate future lifetime)
  ä_x = E[1 + v + ... + v^{K-1}] = E[(1-v^K)/(1-v)] = E[(1-v^K)/d]

  d * ä_x = E[1 - v^K] = 1 - E[v^K] = 1 - A_x

  Therefore: A_x + d * ä_x = 1  ✓
```

---

## Code Reference

In SIMA, this identity is validated in `backend/tests/test_premiums_reserves.py`:

```python
def test_actuarial_identity(comm, av):
    """
    THEORY: A_x + d * a_due_x = 1
    """
    i = comm.i
    d = i / (1 + i)

    for age in range(60, 66):
        A = av.A_x(age)
        a = av.a_due(age)
        result = A + d * a
        assert result == pytest.approx(1.0, rel=1e-6)
```

The values are computed in `backend/engine/actuarial_values.py`:
- `A_x()` at line 72: `return self.comm.get_M(x) / self.comm.get_D(x)`
- `a_due()` at line 102: `return self.comm.get_N(x) / self.comm.get_D(x)`
