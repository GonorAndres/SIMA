# Observations & Clarifications: Technical Reference

## Annuity Relationships

### Life Annuities (Contingent on Survival)

```
ä_x = 1 + a_x

Where:
  ä_x = annuity-due (payments at beginning of period)
  a_x = annuity-immediate (payments at end of period)
```

**Commutation Form:**
```
ä_x = N_x / D_x

a_x = N_{x+1} / D_x
```

**Proof:**
```
ä_x = N_x / D_x
    = (D_x + N_{x+1}) / D_x
    = 1 + N_{x+1}/D_x
    = 1 + a_x  ✓
```

**Why "+1":** Both series continue until death (infinite). The only difference is one payment at time 0.

---

### Certain Annuities (Fixed n Payments, No Mortality)

```
ä_{n|} = (1+i) · a_{n|}

Where:
  ä_{n|} = certain annuity-due for n periods
  a_{n|} = certain annuity-immediate for n periods
```

**Formulas:**
```
ä_{n|} = (1 - v^n) / d      where d = i/(1+i)

a_{n|} = (1 - v^n) / i
```

**Proof:**
```
ä_{n|} = 1 + v + v² + ... + v^{n-1}    (payments at 0,1,...,n-1)
a_{n|} = v + v² + ... + v^n            (payments at 1,2,...,n)

a_{n|} = v · ä_{n|}

Therefore: ä_{n|} = a_{n|} / v = (1+i) · a_{n|}  ✓
```

**Why "(1+i)":** Series have different END points (ä ends at n-1, a ends at n).

---

### Summary Table

| Annuity Type | Relationship | Reason |
|:-------------|:-------------|:-------|
| Life (contingent) | ä_x = 1 + a_x | Same infinite series, shifted |
| Certain (fixed n) | ä_{n\|} = (1+i) · a_{n\|} | Different end points |

---

## Annuity Usage Conventions

### Annuity-Due (ä)

```
Formula: ä_x = N_x / D_x

Payment timing: Beginning of each period

Primary use: PREMIUM payments
  - Policyholder pays at start of year
  - P × ä_x = present value of premium income
```

### Annuity-Immediate (a)

```
Formula: a_x = N_{x+1} / D_x = ä_x - 1

Payment timing: End of each period

Primary use: PENSION/ANNUITY PRODUCT payments
  - Company pays at end of period
  - Benefit × a_x = present value of pension outgo
```

---

## Reserve Calculation: Rounding Considerations

### The ₀V = 0 Principle

```
BY DEFINITION (not by calculation):

₀V_x = 0

This is guaranteed by the equivalence principle:
  P × ä_x = SA × A_x

Therefore:
  ₀V = SA × A_x - P × ä_x = 0
```

### Rounding Error Example

```
ROUNDED PREMIUM:
  P = 25,920 (rounded from 25,921.30)

CALCULATED ₀V:
  ₀V = 100,000 × (844.78/1000) - 25,920 × (3259.31/1000)
     = 84,478 - 84,543.31
     = -65.31  ← ROUNDING ERROR

EXACT PREMIUM:
  P = 100,000 × 844.78 / 3259.31 = 25,921.2996...

EXACT ₀V:
  ₀V = 0 (exactly)
```

### Best Practices

```
1. VALIDATION: If ₀V ≠ 0, check for rounding errors

2. PRECISION: Keep intermediate calculations to 6+ decimals

3. FINAL ROUNDING: Round only final results for display

4. EXAM/INTERVIEW: State ₀V = 0 by definition, don't calculate

5. ALGEBRAIC CHECK:
   ₀V = SA × A_x - P × ä_x
      = SA × A_x - (SA × A_x / ä_x) × ä_x
      = SA × A_x - SA × A_x
      = 0  ✓
```

---

## Terminology Precision

### "Annuity" Has Multiple Meanings

| Context | Term | Meaning |
|:--------|:-----|:--------|
| Mathematical | ä_x, a_x | Present value factors |
| Premium valuation | "annuity factor" | Tool for PV of premiums |
| Product | "life annuity" / "renta vitalicia" | Pension product |

### Recommended Vocabulary

```
PRECISE:
  "The annuity factor ä_60 = 3.259"
  "Present value of premiums is P × ä_x"
  "Life annuity benefit of $50,000/year"

IMPRECISE (avoid):
  "The annuity is 3.259" (factor? product? PV?)
```

### Annuity-Due vs Immediate Notation

```
ä_x  (double-dot) = annuity-DUE (beginning of period)
a_x  (no dot)     = annuity-IMMEDIATE (end of period)

Always specify which one you mean.
```

---

## Quick Reference

```
LIFE ANNUITIES:
  ä_x = N_x / D_x
  a_x = N_{x+1} / D_x
  ä_x = 1 + a_x

CERTAIN ANNUITIES:
  ä_{n|} = (1 - v^n) / d
  a_{n|} = (1 - v^n) / i
  ä_{n|} = (1+i) · a_{n|}

RESERVE VALIDATION:
  ₀V = 0 (by definition)
  If ₀V ≠ 0, check rounding
```
