# Analysis Scripts: Intuitive Reference

**Source files:** `backend/analysis/{mexico_lee_carter.py, sensitivity_analysis.py, capital_requirements.py}`

---

## What Are Analysis Scripts?

```
ANALOGY
  Engine modules = a kitchen with tools (oven, mixer, knives)
  Analysis scripts = recipes that use those tools
  API services = a restaurant menu built from the same kitchen

  The kitchen doesn't decide what to cook. Recipes tell it
  "use the oven at 350F for 30 minutes with these ingredients."
  Analysis scripts tell the engine "use Mexico 1990-2019 data
  with lambda=1e5 and project 30 years forward."
```

The scripts import engine classes, configure them with specific parameters, run computations, and write formatted text reports. They are meant to be run once on real data, not called repeatedly.

---

## Script 1: `mexico_lee_carter.py` -- The Core Analysis

```
ROLE
  This is the FLAGSHIP analysis. It runs the full mortality modeling
  pipeline on real Mexican data and produces the project's main results.

USE
  Two parallel runs:
    A. Pre-COVID (1990-2019): Clean mortality signal
    B. Full period (1990-2024): COVID noise included

  Then compares them side by side to quantify COVID's impact.
```

### What It Does

```
Step 1: Load INEGI deaths + CONAPO population  (a06)
Step 2: Graduate with Whittaker-Henderson       (a07)
Step 3: Fit Lee-Carter via SVD                   (a08)
Step 4: Project 30 years forward (RWD)           (a09)
Step 5: Compare vs 7 regulatory tables           (a10)
Step 6: Price insurance products                 (a01-a04)
Step 7: Compute confidence intervals             (a09)
```

### Key Insight: Why `reestimate_kt=False`?

```
INTUITION
  Whittaker-Henderson CHANGES the mortality surface (smooths it).
  The re-estimation equation says:
    sum(Exposure_x * exp(a_x + b_x * k_t)) = sum(Deaths_x)

  But graduated rates don't reproduce raw deaths -- that's the
  whole point of graduation! So the equation has no solution.

  Solution: use SVD k_t directly. It minimizes log-space error,
  which is consistent with the Lee-Carter log-bilinear model.
```

### COVID Impact (the punchline)

```
                Pre-COVID    Full Period    Impact
  Drift:        -1.076       -0.855        +0.22 (slower improvement)
  Explained:     77.7%        53.5%        -24.2% (noise dominates)
  Premium:      $10,736      $11,148       +3.8% higher

  COVID makes mortality appear to STOP improving. The single-factor
  Lee-Carter model can't separate "transient spike" from "trend shift."
  This is a known limitation documented in the LaTeX bridge paper.
```

---

## Script 2: `sensitivity_analysis.py` -- Three Dimensions of Risk

```
ROLE
  Answers three questions that any insurer must understand:
  1. How much do premiums change when interest rates move?
  2. How much do premiums change when mortality is worse/better?
  3. How does Mexico compare to USA and Spain?
```

### Analysis 1: Interest Rate Sweep

```
INTUITION
  Hold mortality FIXED. Vary interest rate from 2% to 8%.
  Watch what happens to premiums and reserves.

  Result: Interest rate is the DOMINANT factor.
  At age 40, whole life premium:
    i=2%: $17,910
    i=5%: $10,765  (base)
    i=8%: $7,014

  That's a 155% spread! Moving from 2% to 8% more than halves
  the premium. This is because higher rates mean future death
  benefits are "cheaper" in present value terms.
```

### Analysis 2: Mortality Shock

```
INTUITION
  Hold interest rate FIXED at 5%. Scale q_x by 0.70 to 1.30.
  Watch what happens to premiums.

  Key finding: the effect is ASYMMETRIC (convex).
    -30% mortality (better): premium drops 18.2%
    +30% mortality (worse):  premium rises 16.2%

  Why asymmetric? Because q_x -> premium is a convex function.
  Making mortality worse hurts more than making it better helps.
  This is why regulators require capital buffers.
```

### Analysis 3: Cross-Country

```
INTUITION
  Run the EXACT SAME pipeline on Mexico, USA, and Spain.
  Same years (1990-2019), same age range (0-100), same lambda.

  What differs:
    Spain: drift = -2.89 (fastest improvement, best LC fit 94.8%)
    USA:   drift = -1.19 (moderate improvement)
    Mexico: drift = -1.08 (slowest improvement, worst LC fit 77.7%)

  Mexico's premiums are ~30% higher than Spain at all ages.
  This reflects both higher base mortality AND slower improvement.
```

### The `build_shocked_life_table` Helper

```
FORMULA
  For each age:
    shocked_q_x = min(base_q_x * factor, 1.0)

  Then rebuild l_x from scratched:
    l_0 = radix
    l_{x+1} = l_x * (1 - shocked_q_x)

INTUITION
  This is the simplest possible mortality stress test.
  Multiply all death rates by a constant factor.
  The clip at 1.0 ensures probabilities stay valid.
  Then feed the new LifeTable into the pricing engine.
```

---

## Script 3: `capital_requirements.py` -- Solvency II in Action

```
ROLE
  Computes how much capital an insurer needs to survive
  a 1-in-200-year event. This is the Solvency Capital
  Requirement (RCS in Spanish, SCR in English).

USE
  Applies 4 stress scenarios to a 12-policy portfolio,
  aggregates with correlation matrices, and checks if
  the insurer is solvent.
```

### The Four Risk Modules

```
INTUITION
  Each module asks: "What if ONE bad thing happens?"

  1. Mortality:   +15% q_x permanently (more people die)
     -> Death BEL increases (pay claims sooner)
     -> Only affects death products (WL, term, endowment)

  2. Longevity:   -20% q_x permanently (people live longer)
     -> Annuity BEL increases (pay pensions for more years)
     -> Only affects annuity products

  3. Interest Rate: +-100 bps shift (lower discount rate)
     -> ALL BEL increases (future payments worth more today)
     -> Affects EVERY product -- this is why it dominates

  4. Catastrophe:  +35% one-year spike (pandemic, earthquake)
     -> Extra death claims in year 1 only
     -> Calibrated to COVID-19 Mexican mortality data
```

### Why Diversification Reduces SCR

```
INTUITION
  Mortality risk and longevity risk are NEGATIVELY correlated
  (rho = -0.25 in the Solvency II standard formula).

  If a pandemic hits:
    - Death claims INCREASE (mortality risk materializes)
    - Pension obligations DECREASE (fewer survivors to pay)

  These partially cancel out. An insurer writing BOTH death
  products and annuities is naturally hedged. The correlation
  matrix captures this:

        Mort   Long    Cat
  Mort  1.00  -0.25   0.25
  Long -0.25   1.00   0.00
  Cat   0.25   0.00   1.00

  Result: SCR_total < sum of individual SCRs
  Diversification benefit: 14.4% saved
```

### The Dominant Risk

```
  Component          SCR        % of Total
  Mortality          $24K        4.2%
  Longevity         $252K       44.4%
  Interest Rate     $453K       79.7%    <-- DOMINANT
  Catastrophe        $14K        2.4%

  Interest rate risk is 79.7% of total because it affects
  EVERY product. Even a 1% rate change shifts the present
  value of ALL future cash flows. A portfolio with $5.16M
  of BEL is extremely sensitive to discount rate changes.
```

---

## How Scripts Feed the API

```
INTUITION
  The analysis scripts produce numerical findings from real data.
  Some of these findings are then HARDCODED into the API for
  the frontend to display.

  Script: sensitivity_analysis.py
    -> Computes cross-country drift, sigma, q_60, premiums
    -> These values are pasted into sensitivity_service.py
       as the cross_country_data() function

  Script: mexico_lee_carter.py
    -> Computes pre-COVID vs full-period k_t, drift, premiums
    -> These values are pasted into sensitivity_service.py
       as the covid_comparison() function

  WHY NOT compute live? Because the cross-country endpoint
  needs HMD data (USA, Spain) that isn't distributed with
  the app. And COVID comparison needs real INEGI data through 2024.
```

---

## Interview Q&A

**Q: If you were to extend the capital requirements analysis, what would you add?**

A: Two things. First, a lapse risk module -- policyholders surrendering their policies early changes the cash flow profile and BEL. Second, a joint stress test combining interest rate AND mortality shocks simultaneously, since economic crises often coincide with health crises (as COVID showed).

**Q: Why use text reports instead of a database or structured output?**

A: The reports are designed for human review and regulatory documentation. An insurer presenting results to the CNSF would submit formatted reports, not JSON blobs. The reports include interpretation sections that explain what the numbers mean, which is essential for regulatory compliance. For programmatic use, the engine functions return structured dicts.

**Q: What's the relationship between BEL and reserves?**

A: BEL IS the prospective reserve. For death products, BEL = SA * A_{x+t} - P * a_due_{x+t}, which is exactly the prospective reserve formula. For annuities, BEL = pension * a_due(attained_age). No new actuarial math was needed for Solvency II -- the existing `ReserveCalculator` and `ActuarialValues` classes compute BEL directly. The `a11_portfolio.py` module just wraps them with per-product dispatching.

**Q: How would results change with real data vs mock data?**

A: The mock data uses Gompertz-Makeham mortality calibrated to approximate Mexican patterns. Real data would show more irregular features: the infant mortality spike would be sharper, the young-adult hump (ages 15-30) from homicides would be more pronounced, and the COVID spike in 2020-2021 would be visible in the k_t trajectory. The qualitative findings (interest rate dominance, diversification benefit, convex mortality sensitivity) would remain the same.
