# Equivalence Principle, Premiums & Reserves: Technical Reference

## Key Notation

```
SA = Sum Assured (English) / Suma Asegurada (Spanish)
   = Face Amount (American)
   = Death Benefit

This is the amount paid at death (or maturity for endowments).
Example: SA = $100,000
```

---

## The Equivalence Principle

### Definition

```
At policy issue (t=0):

  APV(Premiums) = APV(Benefits)

  P · ä_{x:n|} = SA · A_{x:n|}

Where:
  P = net annual premium (in currency)
  SA = sum assured (death benefit amount)
  ä_{x:n|} = present value of $1/year premium payments
  A_{x:n|} = present value of $1 benefit
```

### Mathematical Statement

```
For a policy issued at age x:

  E[PV(Premium Income)] = E[PV(Benefit Outgo)]

This ensures:
  · Fair price for policyholder
  · No expected profit or loss at issue for insurer
  · ₀V_x = 0 (initial reserve is zero)
```

---

## Net Premium Formulas

### General Formula

```
         SA · APV(Benefits per $1)
P = ─────────────────────────────────
       APV(Premium Payments per $1)

         SA · A_x
P = ─────────────────
           ä_x
```

### By Product Type (Per Unit, SA = 1)

| Product | Premium Formula | Simplified |
|:--------|:----------------|:-----------|
| Whole Life | (M_x/D_x) / (N_x/D_x) | M_x / N_x |
| Term (n years) | (M_x - M_{x+n}) / (N_x - N_{x+n}) | — |
| Pure Endowment | D_{x+n} / (N_x - N_{x+n}) | — |
| Endowment | (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n}) | — |

### With Sum Assured (SA)

```
WHOLE LIFE:
  P = SA · M_x / N_x

TERM (n years):
  P = SA · (M_x - M_{x+n}) / (N_x - N_{x+n})

ENDOWMENT (n years):
  P = SA · (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})

EXAMPLE:
  SA = $100,000, age 60, whole life
  P = 100,000 × M_60 / N_60 = 100,000 × 0.2592 = $25,920/year
```

### Premium Payment Patterns

```
SINGLE PREMIUM:
  π = SA · A_x  (one payment at issue)

ANNUAL PREMIUM (whole life):
  P = SA · A_x / ä_x = SA · M_x / N_x

ANNUAL PREMIUM (limited pay, m years):
  ₘP_x = SA · A_x / ä_{x:m|} = SA · M_x / (N_x - N_{x+m})

ANNUAL PREMIUM (term n, pay n):
  P = SA · A^1_{x:n|} / ä_{x:n|} = SA · (M_x - M_{x+n}) / (N_x - N_{x+n})
```

---

## Reserve Formulas

### Notation

```
ₜV_x = Reserve at duration t for policy issued at age x

  t = years since issue
  x = age at issue
  x+t = current attained age
```

### Prospective Method

```
ₜV_x = APV(Future Benefits) - APV(Future Premiums)

PER UNIT (SA = 1):
     = A_{x+t} - P · ä_{x+t}
     = (M_{x+t} - P · N_{x+t}) / D_{x+t}

WITH SUM ASSURED:
     = SA · A_{x+t} - P · ä_{x+t}
     = SA · (M_{x+t}/D_{x+t}) - P · (N_{x+t}/D_{x+t})

Where:
  SA = Sum Assured (death benefit)
  P = Annual premium (in currency, already includes SA)

EXAMPLE:
  SA = $100,000, P = $25,920, at duration 3 (age 63)
  ₃V_60 = 100,000 × A_63 - 25,920 × ä_63
```

### Retrospective Method

```
ₜV_x = [APV(Past Premiums) - APV(Past Benefits)] / ₜE_x

     = [P · ä_{x:t|} - A^1_{x:t|}] / ₜE_x

     = [P · (N_x - N_{x+t}) - (M_x - M_{x+t})] / D_{x+t} × D_x

"Accumulated value of past surplus"
```

### Fundamental Identity

```
Prospective Reserve = Retrospective Reserve

This equality holds when:
  · Same mortality basis
  · Same interest rate
  · Premium calculated by equivalence principle
```

### Reserve by Product Type

**Whole Life:**
```
ₜV_x = A_{x+t} - P_x · ä_{x+t}

     = (M_{x+t} - P_x · N_{x+t}) / D_{x+t}

Where P_x = M_x / N_x
```

**Term Insurance (n years):**
```
ₜV^1_{x:n|} = A^1_{x+t:n-t|} - P · ä_{x+t:n-t|}

For t < n:
     = (M_{x+t} - M_{x+n}) / D_{x+t} - P · (N_{x+t} - N_{x+n}) / D_{x+t}

For t ≥ n:
     = 0 (policy expired)
```

**Endowment (n years):**
```
ₜV_{x:n|} = A_{x+t:n-t|} - P · ä_{x+t:n-t|}

     = (M_{x+t} - M_{x+n} + D_{x+n}) / D_{x+t} - P · (N_{x+t} - N_{x+n}) / D_{x+t}
```

---

## Reserve Properties

### Boundary Conditions

```
₀V_x = 0                    Reserve at issue is zero

ₙV_{x:n|} = 1               Endowment reserve at maturity equals sum assured
                            (per unit)

lim ₜV_x = 1                Whole life reserve approaches sum assured
t→ω-x                       as policyholder approaches ultimate age
```

### Recursive Relationship

```
(ₜV + P)(1 + i) = q_{x+t} · 1 + p_{x+t} · ₜ₊₁V

"Reserve at t plus premium, accumulated one year,
 equals expected value of death benefit or next reserve"
```

### Reserve Increment

```
ₜ₊₁V - ₜV = Change in reserve over one year

           = P + i·ₜV - q_{x+t}·(1 - ₜV)

           "Premium + interest - cost of insurance"
```

---

## Company-Level Reserves

### Aggregate Reserve

```
Total Reserve = Σᵢ (SAᵢ × ₜᵢVₓᵢ)

Where:
  i = policy index
  SAᵢ = sum assured for policy i
  ₜᵢ = duration of policy i
  xᵢ = issue age of policy i
```

### LISF Requirements

```
Article 217: Reserves calculated using net premium method

Article 218: Interest rate ≤ regulatory maximum

Article 219: Mortality tables approved by CNSF

Reserve ≥ 0 for all policies
```

---

## Gross Premium

### Components

```
G = P + e + c + m

Where:
  G = gross premium (what policyholder pays)
  P = net premium (covers mortality + interest)
  e = expense loading
  c = contingency margin
  m = profit margin
```

### Expense Loading Types

```
α = percentage of premium (commission)
β = percentage of sum assured (admin)
γ = fixed per-policy expense

G · ä_x = P · ä_x + α·G·ä_x + β·SA + γ·ä_x

Solving for G:
G = (P · ä_x + β·SA + γ·ä_x) / ((1-α) · ä_x)
```

---

## Quick Reference

### Premium Formulas (With SA)

```
Whole life:     P = SA · M_x / N_x
Term n:         P = SA · (M_x - M_{x+n}) / (N_x - N_{x+n})
Endowment n:    P = SA · (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})
```

### Reserve Formula (Prospective, With SA)

```
ₜV = SA · A_{x+t} - P · ä_{x+t}

   = SA · (M_{x+t}/D_{x+t}) - P · (N_{x+t}/D_{x+t})

Where P already incorporates SA.
```

### Key Identities

```
₀V_x = 0                    (equivalence principle)
Prospective = Retrospective (consistency check)
Reserve ≥ 0                 (regulatory requirement)
ₙV_{x:n|} = SA              (endowment at maturity equals SA)
```

### Terminology

```
SA = Sum Assured (British/International)
   = Face Amount (American)
   = Suma Asegurada (Spanish/Mexican)
   = Death Benefit (common usage)
```
