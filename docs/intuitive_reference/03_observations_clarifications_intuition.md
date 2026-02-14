# Observations & Clarifications: Intuition

## Annuity-Due vs Annuity-Immediate

### The Two Relationships (Don't Confuse Them!)

```
╔═══════════════════════════════════════════════════════════════════════╗
║  LIFE ANNUITIES (with mortality)                                      ║
║                                                                       ║
║     ä_x = 1 + a_x                                                    ║
║                                                                       ║
║  "Same series, just add 1 for the first payment"                     ║
╚═══════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════╗
║  CERTAIN ANNUITIES (no mortality, fixed payments)                    ║
║                                                                       ║
║     ä_{n|} = (1+i) · a_{n|}                                          ║
║                                                                       ║
║  "Different end points, multiply by (1+i)"                           ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

### Why Different?

```
LIFE ANNUITY:
─────────────────────────────────────────────────────────────────
Payments continue until death (unknown end).

ä_x:  ●───●───●───●───●───●───●─── ... ───† (death)
      0   1   2   3   4   5   6

a_x:      ●───●───●───●───●───●─── ... ───† (death)
          1   2   3   4   5   6

SAME series, just shifted. Difference = 1 payment at time 0.

─────────────────────────────────────────────────────────────────

CERTAIN ANNUITY:
─────────────────────────────────────────────────────────────────
Fixed n payments (known end).

ä_{n|}:  ●───●───●───●───●
         0   1   2   3   4   (ends at n-1)

a_{n|}:      ●───●───●───●───●
             1   2   3   4   5  (ends at n)

DIFFERENT end points! Not just shifted.

─────────────────────────────────────────────────────────────────
```

---

### Mental Model

```
LIFE:    "Both go until death, due just starts earlier"
         → Add 1

CERTAIN: "Due ends earlier, immediate ends later"
         → Multiply by (1+i)
```

---

## Practical Usage

### When to Use Annuity-Due (ä)

```
PREMIUMS — paid at START of period

"I pay my premium January 1st, then I'm covered for the year."

Timeline:
  Pay ──→ Coverage ──→ Pay ──→ Coverage ──→ ...
   │        year 1      │        year 2
   0                    1

Use: P × ä_x for present value of premium income
```

### When to Use Annuity-Immediate (a)

```
PENSIONS — often paid at END of period

"I work all month, then receive my pension payment."

Timeline:
  Work ──→ Receive ──→ Work ──→ Receive ──→ ...
  year 1     │        year 2      │
             1                    2

Use: Pension × a_x for present value of pension outgo
```

### Simple Rule

```
Premium payments → ä (due)      — pay first, then covered
Pension payments → a (immediate) — work/wait first, then paid

(Though some pensions pay at the beginning too!)
```

---

## The ₀V = 0 Mystery

### Why Initial Reserve Must Be Zero

```
EQUIVALENCE PRINCIPLE:

At issue, we set premium so that:

  What we RECEIVE = What we OWE
  P × ä_x = SA × A_x

RESERVE FORMULA:

  ₀V = SA × A_x - P × ä_x
     = (what we owe) - (what we receive)
     = BALANCED
     = 0

If premium is set fairly, there's no initial "gap" to cover.
```

---

### Rounding Error Trap

```
WHAT HAPPENS:

  1. Calculate P = SA × M_x / N_x = 25,921.2996...

  2. Round to P = 25,920 (for display)

  3. Calculate ₀V using rounded P

  4. Get ₀V = -65.31 (NOT zero!)

  5. Panic: "Did I do something wrong?"

ANSWER: No, it's rounding error.
```

---

### How to Avoid

```
OPTION 1: Don't calculate ₀V
  "By the equivalence principle, ₀V = 0"
  (Best for exams/interviews)

OPTION 2: Keep full precision
  Store P = 25921.2996... (many decimals)
  Only round for final display

OPTION 3: Use algebraic cancellation
  ₀V = SA × A_x - (SA × A_x / ä_x) × ä_x
     = SA × A_x - SA × A_x
     = 0  (exactly, no rounding)
```

---

### Validation Check

```
IN YOUR CODE:

  if abs(reserve_at_0) > 0.01:
      print("WARNING: ₀V should be 0, check rounding!")

This catches errors in premium or commutation calculations.
```

---

## Vocabulary Precision

### The Word "Annuity" is Overloaded

```
CONTEXT 1: Mathematical function
  "The annuity factor ä_60 is 3.259"

CONTEXT 2: Premium valuation
  "Present value of premiums = P × ä_x"

CONTEXT 3: Product (pension)
  "She bought a life annuity paying $30,000/year"

ALWAYS clarify which meaning you intend!
```

---

### Interview Tip

```
IF ASKED: "What is an annuity?"

GOOD ANSWER:
"The term has multiple meanings. Mathematically, ä_x is the
present value of $1 per year payments contingent on survival.
As a product, a life annuity is a contract where the insurer
pays periodic income until the annuitant dies.

For life annuities, ä_x = 1 + a_x.
For certain annuities, ä_{n|} = (1+i) × a_{n|}."
```

---

## Summary Card

```
┌─────────────────────────────────────────────────────────────┐
│  ANNUITY RELATIONSHIPS                                      │
├─────────────────────────────────────────────────────────────┤
│  Life (contingent):    ä_x = 1 + a_x                       │
│  Certain (fixed n):    ä_{n|} = (1+i) · a_{n|}             │
├─────────────────────────────────────────────────────────────┤
│  USAGE                                                      │
├─────────────────────────────────────────────────────────────┤
│  Premiums:  use ä (due) — pay at start                     │
│  Pensions:  use a (immediate) — pay at end                 │
├─────────────────────────────────────────────────────────────┤
│  RESERVE CHECK                                              │
├─────────────────────────────────────────────────────────────┤
│  ₀V = 0 by definition (equivalence principle)              │
│  If ₀V ≠ 0, you have a rounding error                      │
└─────────────────────────────────────────────────────────────┘
```

---

*Built through conversation, January 2026*
