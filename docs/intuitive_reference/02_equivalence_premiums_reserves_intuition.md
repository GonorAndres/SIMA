# Equivalence Principle, Premiums & Reserves: Intuition

## Key Term: Sum Assured (SA)

```
SA = Sum Assured (British/International)
   = Face Amount (American)
   = Suma Asegurada (Spanish/Mexican)
   = Death Benefit

"The amount the insurance company pays when you die."

Example: SA = $100,000 means your beneficiaries get $100,000.
```

---

## The Equivalence Principle

### The Core Idea

```
"Fair price means no one is cheated at the start."

  What you pay (premiums) = What you get (benefits)

  In present value terms, accounting for:
    · Time value of money (interest)
    · Probability of payment (mortality)
```

### Why It Works

```
POLICYHOLDER PERSPECTIVE:
─────────────────────────────────────────────────────────────────
"I pay premiums while alive, I receive benefit when I die.
 The expected value of what I pay should equal
 the expected value of what I receive."
─────────────────────────────────────────────────────────────────

INSURER PERSPECTIVE:
─────────────────────────────────────────────────────────────────
"If I price fairly, I expect to break even.
 No expected profit, no expected loss at issue.
 Profit comes from expenses, investment, and experience."
─────────────────────────────────────────────────────────────────
```

### The Balance

```
AT ISSUE (t=0):

    ┌─────────────────┐         ┌─────────────────┐
    │   PV of what    │    =    │   PV of what    │
    │   I will PAY    │         │   I will GET    │
    │                 │         │                 │
    │  P × ä_x        │         │  Benefit × A_x  │
    └─────────────────┘         └─────────────────┘

    BALANCED → Initial reserve = 0
```

---

## Premiums

### What is a Premium?

```
PREMIUM = "Your fair share of the group's expected cost"

Every person in the group:
  · Faces the same mortality risk (by age class)
  · Pays the same amount
  · Some will die early (receive benefit)
  · Some will die late (subsidize others)

POOLING makes individual uncertainty manageable.
```

### The Premium Formula Intuition

```
            What company expects to pay out
Premium = ─────────────────────────────────────
            How long company expects to collect


            A_x (death benefit value)
      P = ─────────────────────────────
            ä_x (years of payment)


SIMPLIFIED (D_x cancels):

            M_x (total death obligations)
      P = ─────────────────────────────────
            N_x (total premium-years)
```

### Why D_x Cancels

```
Both benefit and premium are "per person at age x"

When you divide one by the other:

  (M_x / D_x)       M_x   D_x     M_x
  ───────────  =  ───── × ─── = ─────
  (N_x / D_x)       D_x   N_x     N_x

The "per person" normalizer cancels out.
```

### Premium Comparisons

```
PRODUCT          │  WHAT YOU GET           │  PREMIUM IS...
─────────────────┼─────────────────────────┼────────────────────
Whole Life       │  $1 whenever you die    │  Highest (certain pay)
Endowment        │  $1 at death OR at n    │  High (guaranteed)
Term (n years)   │  $1 only if die in n    │  Low (might not pay)
Pure Endowment   │  $1 only if survive n   │  Lowest (might not pay)
```

---

## Reserves

### What is a Reserve?

```
RESERVE = "Money we can't spend because we'll need it later"

It exists because:
  · We charge LEVEL premiums (same every year)
  · But mortality INCREASES with age
  · Early years: premium > real cost → surplus
  · Later years: premium < real cost → deficit

The reserve is the accumulated surplus to cover future deficits.
```

### The Two Perspectives

```
PROSPECTIVE ("look forward"):
─────────────────────────────────────────────────────────────────
"What do I OWE minus what I'll RECEIVE?"

  Future benefits I must pay:     SA × A_{x+t}
  Future premiums I'll receive:   P × ä_{x+t}
  The gap I must cover:           RESERVE

  ₜV = SA × A_{x+t} - P × ä_{x+t}

Where SA = Sum Assured (death benefit amount)
─────────────────────────────────────────────────────────────────


RETROSPECTIVE ("look backward"):
─────────────────────────────────────────────────────────────────
"What did I COLLECT minus what did I PAY, accumulated?"

  Past premiums received:   P × ä_{x:t|}
  Past claims paid:         A^1_{x:t|}
  Accumulated to today:     ÷ ₜE_x

  "The savings account balance"
─────────────────────────────────────────────────────────────────


BOTH METHODS GIVE SAME ANSWER (validation check)
```

### Reserve Over Time

```
$
│
│                          ╭────╮
│                       ╭──╯    ╰──╮
│     RESERVE        ╭──╯          ╰──╮
│                 ╭──╯                ╰──╮
│              ╭──╯                      ╰──╮
│           ╭──╯                            ╰─→ 0
│        ╭──╯                                 (at death)
│     ╭──╯
│  ╭──╯
│──╯
└────────────────────────────────────────────────→ Age
   60    62    64    66    68    70    ...

   ↑                        ↑
Start = 0              Peak, then drops
(equivalence)          (approaching death)
```

### Key Properties

```
₀V = 0      "At issue, fair price means no debt"

ₜV ≥ 0      "Reserve is never negative" (LISF requirement)

ₜV → SA     "Near death, reserve approaches the benefit amount"
```

---

## Premium vs Reserve: The Fundamental Difference

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   PREMIUM                            RESERVE                          ║
║   ────────                           ───────                          ║
║                                                                       ║
║   GROUP perspective                  INDIVIDUAL perspective           ║
║   "Share the risk evenly"            "Track each policy's liability"  ║
║                                                                       ║
║   Set ONCE at issue                  Changes EVERY period             ║
║   Same for all same-age              Different by duration            ║
║                                                                       ║
║   Answers: "How much to CHARGE?"     Answers: "How much to HOLD?"     ║
║   PRICING                            ACCOUNTING                       ║
║                                                                       ║
║   Uses expected mortality            Uses expected mortality          ║
║   BEFORE uncertainty resolves        AFTER some uncertainty resolves  ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Why Level Premiums Create Reserves

```
REAL COST OF INSURANCE BY AGE:

Age 30: Low risk   → Real cost $200/year
Age 40: Low risk   → Real cost $400/year
Age 50: Medium     → Real cost $1,000/year
Age 60: Higher     → Real cost $3,000/year
Age 70: High       → Real cost $8,000/year
Age 80: Very high  → Real cost $20,000/year

BUT WE CHARGE LEVEL: $2,500/year (same every year)

─────────────────────────────────────────────────────────────────

EARLY YEARS (age 30-50):
  Premium:    $2,500
  Real cost:  $200-1,000
  SURPLUS:    Goes to reserve

LATER YEARS (age 70+):
  Premium:    $2,500
  Real cost:  $8,000-20,000
  DEFICIT:    Paid from reserve

─────────────────────────────────────────────────────────────────
```

---

## Reserves Don't Cover Everything

```
RESERVES ARE FOR:
  · Expected future liabilities
  · Normal mortality following q_x
  · Predictable obligations

RESERVES ARE NOT FOR:
  · Mortality WORSE than expected
  · Catastrophes (pandemic, earthquake)
  · Model errors

THAT'S WHY CAPITAL EXISTS:

  ┌─────────────────┐
  │    CAPITAL      │  ← Buffer for unexpected
  ├─────────────────┤
  │    RESERVES     │  ← Cover expected liabilities
  └─────────────────┘
```

---

## Company vs Policy Level

```
POLICY RESERVE:  ₜV_x for ONE policy

COMPANY RESERVE: Sum of ALL policy reserves

─────────────────────────────────────────────────────────────────
 Policy │ Issue Age │ Duration │ Sum Assured │  Reserve
────────┼───────────┼──────────┼─────────────┼────────────
   A    │    60     │    3     │  $100,000   │  $51,000
   B    │    45     │   10     │  $200,000   │  $38,000
   C    │    30     │   20     │   $50,000   │  $12,000
────────┴───────────┴──────────┴─────────────┴────────────

COMPANY TOTAL = $51k + $38k + $12k = $101,000
─────────────────────────────────────────────────────────────────

Each policy has DIFFERENT reserve because:
  · Different issue age
  · Different duration
  · Different sum assured
  · Different product type
```

---

## Summary: The Flow

```
EQUIVALENCE PRINCIPLE
  "Fair price at issue"
         │
         ▼
      PREMIUM
  "What to charge"
  (GROUP perspective)
         │
         │ policy issued
         │ time passes
         ▼
      RESERVE
  "What to hold"
  (INDIVIDUAL perspective)
         │
         │ if shock occurs
         ▼
      CAPITAL
  "Buffer for unexpected"
  (COMPANY perspective)
```

---

## Interview Questions This Answers

```
Q: "How do you calculate premiums?"
A: Equivalence principle — PV of premiums equals PV of benefits.
   For whole life: P = M_x / N_x

Q: "What is a reserve?"
A: Money held to cover future liabilities net of future premiums.
   Exists because level premiums don't match increasing mortality.

Q: "Why are reserves different for each policy?"
A: Each policy has different issue age, duration, and sum assured.
   Company reserve is sum of individual policy reserves.

Q: "What happens if mortality is worse than expected?"
A: Reserves assume expected mortality. Capital absorbs deviations.
   This is why LISF requires capital above reserves.
```

---

*Built through conversation, January 2026*
