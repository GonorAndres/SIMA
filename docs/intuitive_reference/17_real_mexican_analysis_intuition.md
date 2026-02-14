# Real Mexican Data Analysis: Intuitive Reference

**Analysis:** Lee-Carter on INEGI/CONAPO mortality data, COVID-19 comparison, regulatory validation

---

## The Two Timelines

The entire analysis rests on a single idea: run the same pipeline twice, on two overlapping windows of Mexican mortality data, and compare what comes out.

```
Timeline A (Pre-COVID):   1990 =========================> 2019  (30 clean years)
Timeline B (Full):        1990 =========================> 2019 ===> 2024  (35 years, includes COVID)

What changed?  These 5 extra years:  2020  2021  2022  2023  2024
                                       ^     ^
                                     COVID spike
```

Pre-COVID gives a clean baseline: how was Mexican mortality improving before the pandemic hit? Full period shows what COVID did to that trend. By comparing the two, we isolate the actuarial cost of the pandemic.

---

## The k_t Story

k_t is the "mortality level dial" -- one number per year that captures whether people are dying more or less than average. When k_t goes down, mortality improves. When it jumps up, something bad happened.

```
k_t trajectory (schematic):

  k_t
   |
 25 +  *
   |     *
 20 +       *
   |
 15 +          *
   |
 10 +             *
   |                *
  5 +                  *
   |                     *        COVID
  0 + - - - - - - - - - - *- - - - -spike- - - -
   |                        *      /\
 -5 +                         * * /  \  *
   |                              /    *
-10 +                                     *
   |_____|_____|_____|_____|_____|_____|_____|___
   1990  1995  2000  2005  2010  2015  2020  2024
```

```
FORMULA:    k_{t+1} = k_t + drift + sigma * Z,    Z ~ N(0,1)

INTUITION:  k_t is a ball rolling downhill (drift < 0 means mortality improving).
            COVID kicked the ball back uphill for two years.
            Including those years makes the hill look less steep.

ROLE:       drift controls ALL future mortality projections.
            A less negative drift means higher future mortality means higher premiums.

USE:        Pre-COVID drift = -1.076 --> "mortality improving fast"
            Full drift = -0.855 --> "mortality improving slower"
            Difference = +0.222 --> "COVID slowed improvement by ~21%"
```

---

## Why Explained Variance Dropped from 77.7% to 53.5%

Lee-Carter assumes mortality change is driven by a SINGLE factor k_t that affects all ages proportionally (each age weighted by its own b_x). This works beautifully when mortality improves smoothly over decades -- the SVD finds one clean signal.

COVID broke this assumption. The pandemic did not affect all ages proportionally to their usual b_x pattern. It was a shock that hit working-age adults (30-60) harder than children, and hit differently than the historical age pattern of improvement.

```
What Lee-Carter expects:       What COVID did:

ln(m_x) change by age          ln(m_x) change by age

  |          /                    |       /\
  |         /                     |      /  \
  |        /                      |     /    \
  |       /                       |    /      \
  |      /                        |   /        \
  |     /                         |  /          \
  |    /                          |_/            \_____
  |___/                           |
  |________________________       |________________________
  0   20   40   60   80          0   20   40   60   80
  age                            age

  Smooth, b_x-shaped             Irregular, NOT b_x-shaped
```

The SVD says: "I can explain 77.7% of this surface with one component." Add COVID and it says: "Now I can only explain 53.5% -- there is a big chunk of variation that does not follow the b_x pattern."

---

## The k_t Re-estimation Contradiction

This is the most subtle technical finding in the analysis. It matters because it determines whether you use `reestimate_kt=True` or `False`.

```
FORMULA:    sum_x D_{x,t} = sum_x L_{x,t} * exp(a_x + b_x * k_t)

INTUITION:  "Find k_t so that the model reproduces the EXACT number of
             deaths observed in year t."

            Left side:  RAW deaths (real data, unsmoothed)
            Right side: exp(a_x + b_x * k_t) where a_x, b_x come from
                        GRADUATED (smoothed) rates

            This is like asking: "Find a tuning parameter so that a SMOOTH
            curve, when summed up, equals a NOISY total."

PROBLEM:    Graduation can make some b_x negative (ages 77, 78, 85 in
            Mexican data). When b_x < 0 at some ages and b_x > 0 at
            others, changing k_t makes some terms go UP and others go DOWN.
            The total is not monotone in k_t -- it is U-shaped.
            brentq needs a monotone function. It fails.

                     death_residual(k)
                        |
                        |  \          /
                        |   \        /
                     0 -+----\------/--------
                        |     \    /
                        |      \  /
                        |       \/   <-- brentq can't find root
                        |            of a U-shaped function
                        |________________________
                               k
```

```
ROLE:       reestimate_kt=False is the correct choice for graduated data.
            SVD k_t minimizes error in LOG-SPACE, which is where Lee-Carter
            is defined: ln(m_{x,t}) = a_x + b_x * k_t.
            Re-estimation minimizes error in REAL-SPACE (matching death counts).
            When graduation has altered the surface, log-space consistency wins.

USE:        LeeCarter.fit(graduated_data, reestimate_kt=False)
```

---

## The EMSSA Insight

EMSSA 2009 is the regulatory mortality table used for pension and insurance pricing in Mexico. Our Lee-Carter projection gives us what mortality SHOULD look like based on actual INEGI/CONAPO data. Comparing the two reveals whether the regulatory table is conservative or optimistic.

```
Ratio = projected_q_x / EMSSA_q_x

Ratio < 1:  EMSSA is more pessimistic (assumes MORE deaths)
            --> conservative, safe for insurers

Ratio > 1:  EMSSA is more optimistic (assumes FEWER deaths)
            --> potentially dangerous, underpricing mortality risk

What we found:

  Ratio
    |
  3 +                                                  *
    |                                             *
  2 +                                        *
    |                                   *
  1 + - - - - - - - - - - - - - -*- - - - - - - - - - - -
    |                        *
    |                   *
  0 +  *    *    *    *
    |__________________________|___________________________
    0   10   20   30   40   50   60   70   80   90
                              age

    Ages 0-40: ratio < 1 (EMSSA is conservative -- good)
    Ages 50+:  ratio > 1 and GROWING (EMSSA underestimates mortality)
    Age 90:    ratio = 2.87 (projected mortality is nearly 3x EMSSA)
```

```
INTUITION:  EMSSA 2009 was calibrated on data available before 2009.
            Mexican mortality at old ages has NOT improved as fast as EMSSA assumed.
            For life insurance (pays on death): EMSSA underpredicts claims at 60+.
            For annuities (pays while alive): EMSSA overpredicts payouts at 60+.

ROLE:       This finding suggests Mexican regulatory mortality tables need updating.
            The gap at old ages is actuarially significant -- it affects reserves,
            capital requirements, and solvency calculations.

USE:        MortalityComparison(projected_lt, emssa_lt).qx_ratio()
            Ratio > 1.5 at ages 60+ is a red flag for any product with
            mortality exposure at those ages.
```

---

## The COVID Premium Impact

Think of drift as a "mortality improvement speed" dial.

```
                    Speed Dial
                    __________
                   /          \
                  /   FASTER   \
                 /  improvement \
    Pre-COVID   |   -1.076 *    |   Full period
    pointer --> |              *| <-- pointer
                 \    SLOWER  /
                  \ improvement/
                   \__________/
                       -0.855

    The dial moved 0.222 toward "slower improvement"
```

Slower improvement means higher future mortality means higher premiums. The effect is not uniform across products:

```
Product          COVID premium increase    Why?
-----------      ----------------------    ----
Whole life       +3.2% to +4.3%           Pays on death at ANY age.
                                           Higher old-age mortality matters
                                           but is discounted heavily.

Term 20          +5.8% to +9.9%           Pays on death within 20 years ONLY.
                                           Very sensitive to near-term mortality.
                                           Young ages see bigger % change because
                                           their base premium is small.

Endowment 20    < +1%                     Mostly a savings product (pays at
                                           maturity OR death). Death benefit
                                           is a small fraction of total premium.
```

```
FORMULA:    P_whole_life = SA * M_x / N_x
            where M_x and N_x encode the projected life table

INTUITION:  Higher mortality -> larger M_x (more expected deaths weighted by discount)
            Higher mortality -> smaller N_x (fewer expected survivors to pay premium)
            Both effects push the premium UP.
            The +3-10% increase is the actuarial cost of COVID's mortality legacy.
```

---

## The Full Pipeline in One Picture

```
    INEGI deaths          CONAPO population
         |                       |
         +----------+------------+
                    |
              MortalityData.from_inegi()
              (101 ages x 30 or 35 years)
                    |
              GraduatedRates
              (Whittaker-Henderson, lambda=1e5)
                    |
              LeeCarter.fit(reestimate_kt=False)
              (a_x: 101 values, b_x: 101 values, k_t: 30 or 35 values)
                    |
              MortalityProjection(horizon=30, nsim=1000)
              (drift, sigma, 1000 simulated k_t paths)
                    |
         +----------+----------+
         |                     |
    to_life_table()      to_life_table_with_ci()
    (central estimate)   (optimistic, central, pessimistic)
         |                     |
    CommutationFunctions       90% confidence bands
    (D_x, N_x, C_x, M_x)     on q_x at each age
         |
    PremiumCalculator
    (whole life, term, endowment)
         |
    MortalityComparison
    (vs CNSF 2000-I, CNSF 2000-G, CNSFM 2013, EMSSA 2009)
```

---

## Confidence Intervals: What They Mean

The 90% CI comes from 1000 simulated k_t paths. Each path uses the same drift and sigma but different random noise. At year 2029, we have 1000 different k_t values, each producing a different life table.

```
FORMULA:    k_t(sim_i) = k_last + drift * h + sigma * sum(Z_1, ..., Z_h)

INTUITION:  1000 possible futures. The 5th percentile path is "optimistic"
            (mortality improved faster than expected). The 95th percentile
            is "pessimistic" (mortality improved slower or worsened).

            Pre-COVID, age 60:
            Optimistic:   q_60 = 0.0100  (fewer people die)
            Central:      q_60 = 0.0105  (expected)
            Pessimistic:  q_60 = 0.0111  (more people die)

            The band is narrow (~11% wide) because we are only 10 years out.
            At 30 years out, the band would be much wider -- uncertainty
            compounds like compound interest.
```

The width of the confidence band matters for capital requirements. If the pessimistic scenario produces significantly higher mortality than central, the insurer needs a bigger capital buffer. This connects directly to Phase 3 (SCR calculations).

---

## Key Numbers to Remember (Interview)

| Fact | Value | Why it matters |
|------|-------|----------------|
| Pre-COVID explained variance | 77.7% | Strong single-factor model for Mexico |
| Full period explained variance | 53.5% | COVID broke the single-factor assumption |
| Drift difference | +0.222 | COVID slowed mortality improvement by ~21% |
| EMSSA ratio at age 60 | 1.74 | EMSSA underestimates old-age mortality |
| EMSSA ratio at age 80 | 2.59 | Gap widens dramatically with age |
| Whole life premium increase (age 40) | +3.83% | Actuarial cost of COVID |
| Term 20 premium increase (age 25) | +9.80% | Term products most sensitive |
| reestimate_kt | False | Required for graduated data (negative b_x issue) |
