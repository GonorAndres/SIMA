# 15 -- Sensitivity Analysis: Intuitive Reference

**Module:** `backend/analysis/sensitivity_analysis.py`
**Data:** `backend/analysis/results/sensitivity_*.txt`

---

## 1. The Three Knobs on the Actuarial Machine

The entire SIMA engine takes two fundamental inputs and produces premiums and reserves. Sensitivity analysis asks: **what happens when we turn the knobs?**

```
    KNOB 1: Interest rate (i)          KNOB 2: Mortality level (q_x)
    "How much is the future             "How fast do people die?"
     worth today?"
         |                                    |
         v                                    v
    ┌────────────────────────────────────────────────┐
    │                                                │
    │   LifeTable + CommutationFunctions + Premiums  │
    │                                                │
    └──────────────────────┬─────────────────────────┘
                           |
                           v
                    Premium & Reserve
                    (the output we measure)
```

There is also a KNOB 3 hiding in the background: **which country's mortality** you use (the shape and trend of the death rates). This is the cross-country dimension.

Turning each knob independently, holding the others fixed, tells you which risks matter most and by how much. This is the foundation of regulatory stress testing.

---

## 2. Interest Rate Sensitivity: The Time Lens

### The Core Idea

The interest rate is a **time lens** -- it controls how much the future is worth today.

Think of it physically: if you can earn 8% per year on your investments, then a dollar you need to pay in 40 years only costs you $0.046 today (you invest 4.6 cents and it grows to $1.00 by then). But at 2%, that same future dollar costs you $0.453 today. The interest rate compresses or stretches the present value of future cash flows.

```
FORMULA:    P = SA * A_x / a_x   where A_x and a_x both depend on v = 1/(1+i)

INTUITION:  Higher i => discount factor v^n shrinks faster
            The death benefit PV (A_x) drops -- it is a single payment far in the future
            The annuity PV (a_x) also drops -- it is a stream of near-term payments
            But the benefit drops FASTER (concentrated in the distant future)
            while the annuity drops SLOWER (spread across near-term payments)
            Net effect: premium DECREASES as i increases.

ROLE:       Interest rate is the single most powerful lever on long-duration products.
            It determines the "exchange rate" between future obligations and today's money.

USE:        CNSF stress testing: what happens to reserves if rates drop 200bps?
            Product design: how sensitive is our pricing to investment returns?
```

### Why Whole Life Is Most Sensitive

The death benefit on a whole life policy could be 40+ years away for a young policyholder. The discount factor compounds over those decades:

```
    v^40 at different interest rates:
    ───────────────────────────────────
    i = 2%:   v^40 = (1/1.02)^40 = 0.453      ─┐
    i = 3%:   v^40 = (1/1.03)^40 = 0.307       │  10x difference!
    i = 5%:   v^40 = (1/1.05)^40 = 0.142       │
    i = 8%:   v^40 = (1/1.08)^40 = 0.046      ─┘
```

A 6-percentage-point shift in interest rates creates a **10x** difference in the present value of a payment 40 years away. That is why whole life premiums at age 25 range from $2,993 (i=8%) to $11,306 (i=2%) -- a factor of 3.8x.

### Why Term 20 Is Least Sensitive

A 20-year term policy has at most 20 years of discounting. The discount factor range is much narrower:

```
    v^20 at different interest rates:
    ───────────────────────────────────
    i = 2%:   v^20 = 0.673      ─┐
    i = 8%:   v^20 = 0.215      ─┘  only 3x difference
```

Plus, the term premium is dominated by the mortality risk (who dies in the next 20 years), not by the time value of money. The interest rate shifts term premiums by only 7-11%, compared to 100%+ for whole life.

### The Product Sensitivity Hierarchy (Real Numbers)

All numbers are age 40, Mexico projected 2029, SA = $1,000,000 MXN:

```
    Product          i=2%        i=5%        i=8%       Spread
    ──────────────  ──────────  ──────────  ──────────  ────────
    Whole Life      $17,910     $10,765     $ 7,014     155.4%
    Endowment 20    $42,261     $30,910     $22,476      88.0%
    Term 20         $ 4,646     $ 4,172     $ 3,762      23.5%
```

**Mental model:** The longer the product's cash flows extend into the future, the more the interest rate matters. Whole life has the longest horizon. Term has the shortest. Endowment sits in between because it combines a death benefit (sensitive) with a savings element (also sensitive, but in a partially offsetting way).

### Reserve Impact

Reserves are the liability side of the equation. Higher interest rates shrink reserves because the insurer's future obligations are worth less in today's money:

```
    Reserve at duration 20, whole life, age 35:
    ───────────────────────────────────────────
    i = 2%:   $313,581
    i = 5%:   $205,376
    i = 8%:   $136,329

    A 3% drop from 5% to 2% INCREASES reserves by 53%.
    That is money the insurer must find to remain solvent.
```

This is why central bank rate decisions shake the insurance industry. A sustained low-rate environment forces insurers to hold dramatically more reserves.

---

## 3. Mortality Shock Sensitivity: The Volume Knob

### The Core Idea

A mortality shock scales every death probability up or down by a constant factor. It is a "volume knob" on death rates.

```
FORMULA:    shocked_q_x = min(base_q_x * factor, 1.0)

INTUITION:  factor = 1.30 is a "pandemic scenario" -- 30% more people die at every age
            factor = 0.70 is a "medical breakthrough" -- 30% fewer people die
            Then rebuild l_x from the shocked q_x to get a new life table.

ROLE:       Measures the insurer's exposure to mortality risk.
            How much does the premium/reserve move if death rates are wrong?

USE:        CNSF requires stress tests with mortality shocks of +15% to +30%.
            This tells the regulator: "We can absorb a pandemic."
```

### The Asymmetry: Why Bad News Hurts More Than Good News Helps

At age 40 (whole life, i=5%):

```
    Shock Factor    Premium      % Change
    ────────────    ──────────   ──────────
    0.70x           $ 8,807      -18.2%
    1.00x (base)    $10,765        0.0%
    1.30x           $12,506      +16.2%
```

Wait -- the same 30% magnitude produces -18.2% downward but only +16.2% upward? The relationship between mortality and premiums is **convex**: the curve bends upward like a bowl.

Why does this happen geometrically? Think about what a mortality shock does to q_x:

```
    If base q_60 = 0.0105:
        0.70x shock:  q_60 = 0.00735    (decrease of 0.00315 absolute)
        1.30x shock:  q_60 = 0.01365    (increase of 0.00315 absolute)

    But for the PREMIUM, the effect is NOT symmetric because:
    - Higher mortality -> people die sooner -> fewer premium payments collected
    - This "shorter payment period" partially OFFSETS the higher death cost
    - Lower mortality -> people live longer -> more premium payments collected
    - This "longer payment period" partially OFFSETS the lower death cost
    - The offset is STRONGER for mortality improvements (more years of offset)
      than for mortality deterioration (fewer years to offset)
```

The practical takeaway: **downside mortality risk is larger than upside benefit**. An insurer cannot assume symmetric exposure. This is exactly why regulators require one-sided stress tests (shock mortality UP, not down).

### Product Sensitivity: Pure Protection vs. Savings

```
FORMULA:    Term premium ~ proportional to sum of discounted q_x
            Whole life premium = SA * A_x / a_x  (A_x depends on q_x, a_x also depends)
            Endowment premium dominated by pure endowment nE_x = D_{x+n}/D_x

INTUITION:  Term is PURE PROTECTION -- its premium scales almost linearly with mortality.
            Whole life has a PAYMENT DURATION buffer -- a_x absorbs some of the shock.
            Endowment is MOSTLY SAVINGS -- the D_{x+n} term barely cares about mortality.
```

Real numbers at age 40, i=5%, for a +30% mortality shock:

```
    Product          Base         Shocked (1.3x)    % Change    Why?
    ──────────────  ──────────   ──────────────    ──────────  ──────────────────────────
    Term 20         $ 4,172      $ 5,403           +29.5%      Nearly LINEAR. Pure risk.
    Whole Life      $10,765      $12,506           +16.2%      MODERATE. a_x offsets.
    Endowment 20    $30,910      $31,546           + 2.1%      INSENSITIVE. Savings dominates.
```

The endowment is remarkable: a 30% mortality shock barely moves the premium by 2%. The savings component (the pure endowment nE_x = D_{x+n}/D_x) dominates the price, and that component depends primarily on the interest rate, not on mortality.

This is why endowment products are sometimes called "interest rate products dressed in insurance clothing."

---

## 4. Cross-Country Comparison: Three Mortality Landscapes

### The Drift as a Speedometer

The Lee-Carter drift measures how fast a country's mortality is improving, in units of "k_t change per year." A more negative drift means faster improvement.

```
                   Mortality Improvement Speed (drift)
    slow                                                          fast
    ────────────────────────────────────────────────────────────────►
    Mexico (-1.08)       USA (-1.19)                Spain (-2.89)
    ■■■■■■               ■■■■■■■                    ■■■■■■■■■■■■■■■■

    Spain improves at 2.7x Mexico's rate.
```

What this means economically:

- **Spain (drift = -2.89):** Mortality has been improving fast over 1990-2019 -- Mediterranean diet, universal healthcare, high life expectancy. Future death rates will be markedly lower than today.
- **USA (drift = -1.19):** Moderate improvement, but the opioid crisis and COVID created headwinds that slow the trend relative to Spain.
- **Mexico (drift = -1.08):** Slowest improvement. The epidemiological transition is still ongoing -- infant mortality dropped dramatically, but adult mortality (especially ages 20-40 from violence/accidents) has not followed the same downward curve.

### Explained Variance as a "Signal Cleanliness" Measure

```
    Country    Explained Var    Interpretation
    ─────────  ─────────────    ────────────────────────────────────────────
    Spain      94.8%            Lee-Carter captures almost everything.
                                k_t trend is clean, nearly linear.

    USA        86.7%            Good fit. Some age-heterogeneous improvement
                                (opioid crisis affected ages 25-50 differently).

    Mexico     77.7%            More "noise." Mortality improvement not
                                uniform across ages. Infant mortality improved
                                dramatically, but adult violence/accident humps
                                do not follow the same trend.
```

**Mental model:** Explained variance tells you how much of the mortality surface is captured by a single time index k_t. If 95% of variation is explained, mortality moves in a very coherent way -- all ages improve together. If only 78% is explained, there are age-specific patterns that k_t misses (some ages improve, others stagnate or worsen).

### Premium Implications

Whole life premium at age 40, i=5%, SA=$1,000,000:

```
    Country    Premium      q_40 (per 1000)    Why?
    ─────────  ──────────   ───────────────    ──────────────────────────
    Mexico     $10,765      2.167              Highest base mortality +
                                                slowest improvement

    USA        $10,178      1.966              Similar base, slightly
                                                faster improvement

    Spain      $ 8,191      0.621              Much lower base mortality +
                                                fastest improvement
```

Spain's whole life premium is 24% lower than Mexico's. This reflects BOTH the lower base mortality (a_x) AND the faster improvement trend (drift). A Spanish 40-year-old is projected to have q_40 = 0.62 per thousand in 2029, versus 2.17 per thousand for Mexico -- nearly 3.5x the mortality risk.

### The a_x Profile: Three Different Countries, Three Different Mortality Shapes

```
    a_x = average log-mortality at each age (lower = healthier)

    Age     Mexico    USA       Spain     What's happening?
    ────    ──────    ──────    ──────    ──────────────────────────────
      0     -4.26     -4.97     -5.81     Infant mortality: MX >> US > ES
      1     -6.44     -7.37     -7.46     Post-infant: big MX gap
     20     -6.82     -6.63     -7.41     Young adults: MX~US (violence/accidents)
     40     -5.88     -5.97     -6.45     Middle age: Spain clearly healthier
     60     -4.44     -4.38     -4.61     Old age: differences narrow
     80     -2.84     -2.66     -2.70     Very old age: nearly converged
```

At young-adult ages (20), Mexico and the USA have surprisingly similar a_x values (-6.82 vs -6.63), while Spain is much lower (-7.41). This reflects the "accident hump" that afflicts both countries -- Mexico from violence, the USA from a combination of gun violence, traffic accidents, and substance abuse.

At old ages (80+), the three countries nearly converge. Biology takes over: once you reach 80, the Gompertz force of mortality dominates regardless of nationality.

---

## 5. Combining the Knobs: Why Joint Stress Matters

The three sensitivity dimensions are not independent in the real world. Economic crises can bring:

```
    ┌─────────────────────────────────────────────────────────┐
    │  Economic Crisis Scenario:                              │
    │                                                         │
    │    Interest rates DROP  (central bank cuts to stimulate) │
    │         +                                               │
    │    Mortality RISES  (poverty, reduced healthcare access) │
    │         =                                               │
    │    DOUBLE HIT on insurer solvency                       │
    │      - Reserves increase (lower discount rate)          │
    │      - Claims increase (higher mortality)               │
    └─────────────────────────────────────────────────────────┘
```

This is why Phase 3 (capital requirements) will combine these shocks using a correlation matrix:

```
FORMULA:    SCR = sqrt( IR^2 + MR^2 + 2 * rho * IR * MR )

INTUITION:  If rho = 0 (independent risks), SCR = sqrt(IR^2 + MR^2)
            This is LESS than IR + MR (diversification benefit).

            If rho = 1 (perfectly correlated), SCR = IR + MR
            No diversification. Both hit simultaneously.

            CNSF calibrates rho based on historical Mexican data.
            Typical values: rho ~ 0.25 to 0.50 for interest/mortality.

ROLE:       The SCR tells the regulator: "This is the capital buffer the insurer
            needs to survive a 1-in-200 year event."

USE:        Directly determines the minimum capital the insurer must hold.
            Too little capital -> regulatory intervention, possible liquidation.
```

---

## 6. Magnitude Comparison: Which Risk Dominates?

Let us put all three sensitivity dimensions on the same scale, using whole life at age 40 as the benchmark:

```
    Risk Factor                       Premium Range      % Spread
    ──────────────────────────────    ──────────────     ──────────
    Interest rate (2% to 8%)          $7,014 - $17,910   +155%
    Mortality shock (0.70x to 1.30x)  $8,807 - $12,506    +42%
    Cross-country (Spain to Mexico)   $8,191 - $10,765    +31%
```

**Interest rate dominates.** For long-duration products, the discount rate matters more than mortality assumptions. This has a practical consequence: the chief actuary worries more about the investment department than about the mortality research team.

For short-duration products (term 20), the picture reverses:

```
    Risk Factor                       Premium Range      % Spread
    ──────────────────────────────    ──────────────     ──────────
    Mortality shock (0.70x to 1.30x)  $2,931 - $5,403    +84%
    Interest rate (2% to 8%)          $4,646 - $3,762     +24%
```

Term insurance is a mortality product. The interest rate barely matters. This is why term life pricing focuses obsessively on underwriting (getting the mortality right) while whole life pricing focuses on asset-liability matching (getting the interest rate right).

---

## 7. The build_shocked_life_table Function: What It Does

The sensitivity analysis code needs a way to create "what if" life tables. The function is simple but worth understanding step by step:

```
FORMULA:    For each age x (except terminal):
                shocked_q_x = min(base_q_x * factor, 1.0)
            Terminal age: shocked_q_omega = 1.0 (always)
            Then: l_0 = 100,000
                  l_{x+1} = l_x * (1 - shocked_q_x)

INTUITION:  The min(..., 1.0) cap prevents nonsensical probabilities > 100%.
            At very old ages, base q_x might be 0.85. A 1.3x shock would
            give 1.105, which is impossible. Capping at 1.0 means "everyone
            at that age dies" -- a reasonable extreme.

ROLE:       Creates a new, self-consistent life table from a single shock parameter.
            The shocked table passes all validation checks (sum of deaths = radix,
            terminal q = 1.0, all rates in [0,1]).

USE:        Feed the shocked life table into CommutationFunctions -> Premiums
            to measure premium sensitivity. Feed it into ReserveCalculator
            to measure reserve sensitivity.
```

---

## 8. Interview-Ready Explanations

**Q: "What is the most important risk factor for a whole life product?"**

> "Interest rate, by a wide margin. In our analysis, varying the discount rate from 2% to 8% creates a 155% spread in whole life premiums at age 40. By comparison, a 30% mortality shock only produces a 34% spread. This is because whole life benefits are paid far in the future, and the present value of distant cash flows is exponentially sensitive to the discount rate. A term product would give the opposite answer -- mortality dominates because the time horizon is short."

**Q: "Why is the mortality-premium relationship asymmetric?"**

> "Because premiums depend on the ratio A_x / a_x, and both numerator and denominator are affected by mortality. When mortality increases, A_x rises (more death claims) but a_x falls (shorter payment period). The denominator partially offsets the numerator, but not symmetrically. The offset is weaker when mortality rises (fewer years of offset) and stronger when mortality falls (more years of offset). The net effect is that a 30% mortality increase raises premiums by about 16%, while a 30% decrease reduces them by about 18%. The convexity means downside risk exceeds upside benefit."

**Q: "Why does Spain have lower premiums than Mexico?"**

> "Two reasons compounding each other. First, Spain has lower base mortality at every age -- better healthcare, lower violence, Mediterranean lifestyle. Second, Spain's mortality improvement is 2.7 times faster than Mexico's (drift of -2.89 vs -1.08). When you project 10 years forward, these compounding differences translate into markedly lower projected death rates. At age 40, Spain's projected q_x in 2029 is 0.62 per thousand versus Mexico's 2.17 -- a 3.5x difference. Lower mortality and faster improvement together reduce the whole life premium by 24%."

**Q: "How would you stress test an insurance portfolio for CNSF?"**

> "Three dimensions. First, interest rate stress: shift the discount rate down by 200-300 basis points to simulate a low-rate environment. This tests reserve adequacy. Second, mortality stress: scale all q_x up by 15-30% to simulate a pandemic or population health deterioration. This tests claims adequacy. Third, and most importantly, combine them: an economic crisis can bring both low rates and high mortality simultaneously. The SCR formula uses a correlation matrix to capture joint stress, and the combined capital requirement is less than the sum of individual requirements due to diversification, but more than either one alone."

---

## 9. The Regulatory Connection: From Sensitivity to Solvency

CNSF/LISF stress testing is not an academic exercise. It determines real capital requirements:

```
    Sensitivity Analysis (Phase 2 -- you are here)
         |
         |  "How much does premium/reserve move per unit of risk?"
         |
         v
    Risk Quantification (Phase 3 -- next)
         |
         |  "What is the 1-in-200 year adverse scenario?"
         |
         v
    Capital Requirement (SCR)
         |
         |  "How much capital must the insurer hold?"
         |
         v
    Solvency Dashboard (Phase 4)
         |
         |  "Are we solvent? By how much? Under which scenarios do we fail?"
         |
         v
    Regulatory Reporting to CNSF
```

The sensitivity analysis we just completed gives us the **gradients** -- how fast outputs move per unit of input change. Phase 3 will multiply those gradients by the **size of the stress scenario** (calibrated from historical data or regulatory prescription) to get the actual capital charge.

In mathematical terms, if f(i, q) is the reserve function:

```
    Capital charge ~ |df/di| * Delta_i  +  |df/dq| * Delta_q  +  cross term

    We just measured df/di (interest rate sensitivity)
    We just measured df/dq (mortality shock sensitivity)
    Phase 3 will calibrate Delta_i and Delta_q from CNSF specifications
```

---

## 10. Key Numbers to Remember

These are the numbers that anchor your intuition. Memorize the order of magnitude, not the exact digits.

```
    INTEREST RATE (age 40, whole life):
        i=2% -> P = $17,910
        i=5% -> P = $10,765  (base)
        i=8% -> P = $7,014
        Spread: ~155%. Interest rate is the DOMINANT driver.

    MORTALITY SHOCK (age 40, whole life, i=5%):
        0.70x -> P = $8,807  (-18.2%)
        1.30x -> P = $12,506 (+16.2%)
        Asymmetric: downside > upside. Convexity.

    CROSS-COUNTRY (age 40, whole life, i=5%):
        Mexico: $10,765    drift = -1.08   explained_var = 77.7%
        USA:    $10,178    drift = -1.19   explained_var = 86.7%
        Spain:  $ 8,191    drift = -2.89   explained_var = 94.8%

    PRODUCT SENSITIVITY TO MORTALITY (30% shock, age 40):
        Term 20:      +29.5%  (nearly linear)
        Whole Life:   +16.2%  (moderate, a_x offset)
        Endowment 20: + 2.1%  (nearly insensitive, savings dominates)
```

---

*Created: February 2026*
