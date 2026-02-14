
## The Primitives

| Symbol | Definition           | Intuition                                  |
| :----- | :------------------- | :----------------------------------------- |
| l_x    | Lives at age x       | "How many people are still alive"          |
| d_x    | Deaths at age x      | d_x = l_x - l_{x+1}                        |
| q_x    | Probability of death | q_x = d_x / l_x                            |
| v      | Discount factor      | v = 1/(1+i), "peso today vs peso tomorrow" |

---

## The Four Functions

### D_x — Discounted Survivors

```
FORMULA:    D_x = v^x · l_x

INTUITION:  Present value of survivors at age x.
            "Who is alive to pay or receive at age x"

ROLE:       THE NORMALIZER — always in denominator.
            Converts group totals to per-person values.

            Total obligation / D_x = "obligation per person alive at x"
```

### N_x — Accumulated Survival Stream

```
FORMULA:    N_x = D_x + D_{x+1} + D_{x+2} + ... + D_ω

INTUITION:  Sum of all future survival moments.
            "Stream of payments while alive"

RELATION:   N_x = many D's added together
            D is ONE moment, N is MANY moments

USE:        Annuities (repeated payments to survivors)
```

### C_x — Discounted Deaths

```
FORMULA:    C_x = v^{x+1} · d_x

INTUITION:  Present value of deaths at age x.
            "Death claims for those who die at age x"

NOTE:       v^{x+1} because payment at END of year of death
```

### M_x — Accumulated Death Stream

```
FORMULA:    M_x = C_x + C_{x+1} + C_{x+2} + ... + C_ω

INTUITION:  Sum of all future death moments.
            "Total death claims from age x onward"

RELATION:   M_x = many C's added together
            C is ONE death moment, M is ALL future deaths

USE:        Insurance (payment at death)
```

---

## The Structure

```
SURVIVAL SIDE              DEATH SIDE
─────────────              ──────────
D_x (one moment)     ↔     C_x (one moment)
     │                          │
     │ Σ sum                    │ Σ sum
     ▼                          ▼
N_x (stream)         ↔     M_x (stream)
```

**Recursion (build backwards):**
```
N_x = D_x + N_{x+1}        M_x = C_x + M_{x+1}
```

---

## Why D_x is the Normalizer

```
PROBLEM:  M_x, N_x depend on arbitrary cohort size (l_0 = 1000 or 100,000?)

SOLUTION: Divide by D_x

          M_x / D_x = "death obligation PER PERSON alive at x"

          Both numerator and denominator in present-value terms,
          so units cancel correctly.
```

**Analogy:** Splitting a restaurant bill
- Total bill = M_x
- People sharing = D_x
- Each person pays = M_x / D_x

---

## The Core Insight

```
A_x = M_x / D_x

    = Expected value (probability-weighted)
      × Present value (time-weighted)
      ÷ Fair share (spread equally among survivors)

    = "Fair price today for uncertain future payment"
```

---

## Products and Formulas

### Death Benefits (Insurance)

| Product | Pays When | Formula |
|:--------|:----------|:--------|
| Whole Life | Death (anytime) | M_x / D_x |
| Term (n years) | Death within n years | (M_x - M_{x+n}) / D_x |

### Survival Benefits

| Product | Pays When | Formula |
|:--------|:----------|:--------|
| Pure Endowment | Survive to age x+n | D_{x+n} / D_x |
| Life Annuity | Every year alive | N_x / D_x |
| Temp Annuity (n yrs) | Every year, max n | (N_x - N_{x+n}) / D_x |

### Combined (Endowment)

| Product | Pays When | Formula |
|:--------|:----------|:--------|
| Dotal Mixto | Death OR survive to n | (M_x - M_{x+n} + D_{x+n}) / D_x |

---

## D vs N in Numerator

```
D_{x+n} in numerator:  ONE payment at specific age (lump sum)
                       Example: "Get $500k at age 65"

N_x in numerator:      MANY payments over time (stream)
                       Example: "Get $40k/year for life"
```

---

## Why "Commutation"?

From Latin "commutare" = to exchange/substitute

1. **Historical:** Pre-computed tables to SUBSTITUTE complex sums with simple lookups
2. **Practical:** EXCHANGE between payment types (lump sum ↔ annuity)

---

## Simple Tariff Limitation

```
ONE mortality table = ONE price for same age

40-year-old smoker    }
40-year-old non-smoker}  → Same A_40 (wrong!)

SOLUTION: Multiple tables
  · Smoker vs non-smoker
  · Male vs female
  · Preferred vs standard

Same formulas (D, N, C, M), different mortality input (l_x)
```

---

## The Formula Pattern

**Every product follows:**

```
                (Relevant commutation terms)
Product Value = ─────────────────────────────
                          D_x

Numerator:   WHAT triggers payment (M for death, N for survival stream, D for survival moment)
Denominator: ALWAYS D_x (per person alive at age x)
```

---

## Quick Reference

```
A_x   = M_x / D_x           Whole life insurance
ä_x   = N_x / D_x           Whole life annuity
ₙE_x  = D_{x+n} / D_x       Pure endowment (survive n years)

Term n years:     (M_x - M_{x+n}) / D_x
Temp annuity n:   (N_x - N_{x+n}) / D_x
Endowment n:      (M_x - M_{x+n} + D_{x+n}) / D_x
```

---

*Built through conversation, January 2026*
