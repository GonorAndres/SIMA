# Lee-Carter Mortality Pipeline -- Intuitive Reference

---

## The Big Picture

```
THE PROBLEM:
  You have 30 years of death rates for 101 ages.
  That's a 101 x 30 matrix of numbers.
  You need to predict the NEXT 30 years.

THE TRICK:
  Mortality doesn't move randomly age-by-age.
  There's ONE dominant trend driving everything.
  Find it, extrapolate it, done.

THE PIPELINE:
  Raw data -> Smooth it -> Decompose it -> Project it -> Use it
     a06   ->    a07     ->     a08      ->    a09     -> a01-a05
```

---

## a07: Graduation (Smoothing)

```
PROBLEM:    Raw death rates are noisy.
            Age 87 has 0.12, age 88 has 0.09, age 89 has 0.15.
            Real mortality doesn't zigzag like that.

SOLUTION:   Whittaker-Henderson -- a tug of war between two goals:
            (1) Stay close to the data  (fidelity)
            (2) Make the curve smooth   (penalty on curvature)

ANALOGY:    Drawing a curve through scattered dots.
            Lambda = how stiff your ruler is.
            Stiff ruler (lambda big) = smooth curve, ignores noise.
            Flexible ruler (lambda small) = follows every bump.

WHY LOG-SPACE: Mortality spans orders of magnitude (0.001 at age 20,
               0.3 at age 90). Smoothing in log-space treats
               proportional changes equally at all ages.
               Also guarantees positivity: exp(anything) > 0.
```

| Lambda | What you get |
|:-------|:-------------|
| 0 | The raw data, untouched |
| 1e5 | The standard -- smooth but faithful |
| huge | A nearly straight line in log-space |

---

## a08: Lee-Carter Decomposition

```
THE MODEL:  ln(m_{x,t}) = a_x + b_x * k_t

INTUITION:  Mortality at any (age, year) is:
            - a_x: the "shape" -- how bad is this age on average?
            - b_x * k_t: the "shift" -- how much has this age improved
              compared to average, given the overall trend k_t?

ANALOGY:    Think of a_x as the PHOTOGRAPH of mortality (fixed shape).
            k_t is the VOLUME KNOB (turns everything up or down).
            b_x is the EQUALIZER (some ages respond more than others).

            When k_t decreases by 1 unit:
            - An age with b_x = 0.02 improves by 2%
            - An age with b_x = 0.005 improves by 0.5%
```

**Why SVD?**

```
FORMULA:    R = U * S * V'  (Singular Value Decomposition)

INTUITION:  SVD finds the BEST rank-1 approximation of the residual
            matrix. "Best" means minimizing squared errors.

            Think of it as: "If I could only describe this entire
            101x30 matrix with ONE pattern, what would it be?"

            That one pattern IS Lee-Carter: b_x * k_t.

            S[0]^2 / sum(S^2) tells you how good the approximation
            is. For USA: ~85%. One number (k_t) captures 85% of all
            the variation in 30 years of death rates across 101 ages.
```

**Why re-estimate k_t?**

```
PROBLEM:    SVD optimizes in log-space (minimizes log-rate errors).
            But actuaries care about DEATH COUNTS, not log-rates.

            A 10% error at age 0 (rate 0.005) = 0.0005 in log-space
            A 10% error at age 80 (rate 0.08) = 0.008 in log-space

            SVD treats both equally. But age 80 has 100x more deaths.

SOLUTION:   For each year, solve:
            "What k_t makes the model predict the right TOTAL deaths?"

            This is one equation in one unknown per year.
            brentq (root-finding) solves it in microseconds.

RESULT:     Model now reproduces observed deaths within 0.1%.
```

---

## a09: Projection (The Bridge)

```
FORECASTING k_t:

  Past k_t:     10, 8, 7, 5, 3, 1, -1, -3  (going down)

  The pattern:  It's roughly a line going down.
                drift = (last - first) / (n - 1)
                sigma = how much it wobbles around that line

  Central:      Just extend the line.  k_{T+h} = k_T + h * drift

  Stochastic:   Extend the line + add random noise.
                1000 paths, each slightly different.
                -> Gives you confidence intervals.

WHY RWD:    k_t differences are roughly i.i.d.
            That's the definition of a random walk.
            The drift captures the secular improvement trend.
            It's simple, interpretable, and standard in practice.
```

**The Bridge (most important method):**

```
FORMULA:    m_x -> q_x -> l_x -> LifeTable

            q_x = 1 - exp(-m_x)     (exact under constant force)
            l_{x+1} = l_x * (1-q_x) (standard recursion)
            q_omega = 1.0            (everyone dies at terminal age)

INTUITION:  This is where EMPIRICAL DATA meets THEORETICAL MACHINERY.

            Before: LifeTable was hand-crafted from a CSV.
            Now:    LifeTable is GENERATED from real mortality data,
                    projected into the future with uncertainty bounds.

            The LifeTable object doesn't know or care where it came from.
            It just has ages and l_x. The downstream engine (commutations,
            premiums, reserves) works identically.

USE:        proj.to_life_table(2035) -> LifeTable -> CommutationFunctions
            -> PremiumCalculator -> "A whole life policy for a 30-year-old
               in 2035 costs $X per year"
```

---

## Key Design Decision: Duck Typing

```
GraduatedRates has the SAME INTERFACE as MortalityData:
  .mx, .dx, .ex, .ages, .years

LeeCarter.fit() accepts EITHER ONE.

WHY:  No type-checking needed. No inheritance hierarchy.
      If it has .mx and .ages, it works.

      User decides: graduate or not?
      Code doesn't care either way.
```

---

## Interview Anchors

| Question | Key Concept |
|:---------|:------------|
| "Why not just average rates to smooth?" | Whittaker-Henderson respects exposure (more data = more weight) and controls smoothness explicitly via lambda |
| "Why SVD and not regression?" | SVD solves for b_x and k_t simultaneously without assuming a functional form for either |
| "Why re-estimate k_t?" | SVD minimizes log-rate errors; re-estimation minimizes death count errors (actuarially relevant) |
| "Why RWD for k_t?" | k_t differences are empirically i.i.d.; simplest model that captures the trend and uncertainty |
| "How does q_x relate to m_x?" | q_x = 1 - exp(-m_x) under constant force assumption; for small m_x they're approximately equal |
| "What does b_x tell you?" | Which ages benefit most from mortality improvement. High b_x = age improves fastest when k_t drops |
