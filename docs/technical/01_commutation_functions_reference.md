## Primitives (Inputs)

| Symbol | Name | Definition | Source |
|:-------|:-----|:-----------|:-------|
| ω | Ultimate age | Maximum lifespan | Assumption (110) |
| l_x | Lives at age x | Survivors from cohort | Mortality table |
| d_x | Deaths at age x | Deaths between x and x+1 | d_x = l_x - l_{x+1} |
| q_x | Mortality rate | Prob. of death at age x | q_x = d_x / l_x |
| p_x | Survival rate | Prob. of survival at age x | p_x = 1 - q_x |
| i | Interest rate | Annual rate | Assumption |
| v | Discount factor | PV of 1 peso in 1 year | v = 1/(1+i) |

## Commutation Functions

| Symbol | Formula | Meaning |
|:-------|:--------|:--------|
| D_x | v^x · l_x | Discounted survivors at age x |
| N_x | Σ D_y (y=x to ω) | Sum of future discounted survivors |
| C_x | v^{x+1} · d_x | Discounted deaths at age x |
| M_x | Σ C_y (y=x to ω) | Sum of future discounted deaths |

## Recursion Formulas (compute backwards from ω)

```
N_x = D_x + N_{x+1}     with N_ω = D_ω
M_x = C_x + M_{x+1}     with M_ω = C_ω
```

## Standard Actuarial Values

### Insurance (Death Benefits)

| Product | Symbol | Formula |
|:--------|:-------|:--------|
| Whole life | A_x | M_x / D_x |
| Term (n years) | A^1_{x:n\|} | (M_x - M_{x+n}) / D_x |

### Annuities (Survival Benefits)

| Product | Symbol | Formula |
|:--------|:-------|:--------|
| Whole life annuity-due | ä_x | N_x / D_x |
| Temporary annuity-due | ä_{x:n\|} | (N_x - N_{x+n}) / D_x |

### Endowments (Survival + Death)

| Product | Symbol | Formula |
|:--------|:-------|:--------|
| Pure endowment | ₙE_x | D_{x+n} / D_x |
| Endowment insurance | A_{x:n\|} | (M_x - M_{x+n} + D_{x+n}) / D_x |

## Net Premium (Equivalence Principle)

```
P = Benefit APV / Annuity APV

For whole life:     P = A_x / ä_x = M_x / N_x
For term n years:   P = A^1_{x:n|} / ä_{x:n|} = (M_x - M_{x+n}) / (N_x - N_{x+n})
For endowment:      P = A_{x:n|} / ä_{x:n|} = (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})
```

## Key Identities

```
D_x in denominator = "per person alive at age x"
N_x - N_{x+n} = D_x + D_{x+1} + ... + D_{x+n-1}  (n terms)
M_x - M_{x+n} = C_x + C_{x+1} + ... + C_{x+n-1}  (n terms)
```
