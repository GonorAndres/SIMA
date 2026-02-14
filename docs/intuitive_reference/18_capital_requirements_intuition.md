# 18 -- Capital Requirements (SCR): Intuitive Reference

**Phase:** Phase 3 -- Capital Requirements
**Regulatory Framework:** LISF / CUSF / CNSF (Mexico), Solvency II (Europe, conceptual parallel)

---

## 1. What Is SCR? The Emergency Fund Analogy

Every person with a bit of financial literacy knows you should keep an "emergency fund" -- typically 3 to 6 months of living expenses in a savings account, untouched, in case something terrible happens (job loss, medical emergency, car breaks down). You hope you never need it, but if the worst day of your life arrives, that money is the difference between survival and ruin.

The Solvency Capital Requirement (SCR) is exactly this, but for an insurance company. The regulator says:

```
"You collect premiums and promise to pay claims. Your reserves (BEL) cover
 the expected claims. But what if things go worse than expected? You need
 extra capital -- a buffer -- to absorb the shock."
```

How big should the buffer be? Not calibrated to "a bad month" like a personal emergency fund, but to a **1-in-200-year disaster**. In statistical language, the SCR covers the 99.5th percentile adverse scenario over a one-year horizon. That means:

```
    Probability of ruin in one year  <=  0.5%

    In other words: if you ran 200 independent copies of this insurer
    through next year, at most 1 of them would go bankrupt.
```

This is the fundamental contract between an insurer and society: we accept your premium today and promise to pay your claim tomorrow, and to make that promise credible, we hold enough capital that even a once-in-two-centuries catastrophe would not break us.

---

## 2. Why BEL = Reserve? The "What You Owe" Calculation

BEL stands for Best Estimate Liability. Despite the jargon, it is conceptually simple: **it is the present value of what you expect to pay out, minus what you expect to collect**.

For a death benefit product (term life, whole life), BEL is the prospective reserve:

```
FORMULA:    BEL = SA * A_{x+t} - P * a_{x+t}

INTUITION:  "How much do I owe in future benefits, minus how much will I
             still collect in future premiums?"

            At policy issue (t=0), BEL = 0 because that is how we set P.
            Over time, BEL grows as the insured ages and fewer premiums remain.
```

For an annuity-in-payment (pensioner already receiving monthly checks), BEL is even simpler:

```
FORMULA:    BEL = R * a_{x+t}

INTUITION:  "How much money do I need TODAY to keep paying this retiree
             their pension for the rest of their life?"

            If the retiree is 70, and life expectancy suggests another 15 years,
            and you discount at 5%, a_70 is roughly 10. So for a $100,000/year
            pension, BEL ~ $1,000,000.
```

The BEL is **not** the SCR. The BEL is what you owe on a normal day. The SCR is the extra buffer in case the normal day turns into the worst day of the century.

---

## 3. The Four Risks: Mental Models

An insurance company faces many risks, but the CNSF (following Solvency II principles) organizes the life insurance risks into four main categories. Each one asks: "What could go wrong, and how much extra money would we need?"

### 3.1 Mortality Risk -- "What If a Pandemic Hits?"

```
    SCENARIO:   A virus, a war, or a systemic health deterioration
                causes death rates to spike.

    WHO HURTS:  Insurers selling death benefit products (term, whole life).
                More people die --> more claims --> need more money NOW.

    SHOCK:      q_x increases by 15% at all ages (Solvency II standard).

    EXAMPLE:    If your portfolio has 10,000 whole life policies with
                average reserve of $50,000, and a 15% mortality spike
                causes $12M in excess claims, then the mortality SCR
                component is approximately $12M.

    MENTAL MODEL: Think of a sudden flood of claims landing on the
                  claims department's desk -- all at once, all unexpected.
                  The mortality SCR is the cash you need to pay them all.
```

### 3.2 Longevity Risk -- "What If People Live Longer?"

```
    SCENARIO:   Medical breakthroughs, lifestyle improvements, or simply
                a generation that turns out healthier than the tables assumed.

    WHO HURTS:  Insurers selling annuities and pensions.
                People live longer --> more pension payments --> need more money.

    SHOCK:      q_x decreases by 20% at all ages (Solvency II standard).

    EXAMPLE:    If your pension portfolio has 5,000 retirees with average
                annuity BEL of $200,000, and a 20% longevity improvement
                extends payments by ~2 extra years, the BEL increases by
                roughly $50M. That $50M delta IS the longevity SCR component.

    MENTAL MODEL: Think of retirees who keep cashing checks for years
                  longer than your actuaries predicted. Each extra year
                  is money you did not price for.
```

### 3.3 Interest Rate Risk -- "What If Rates Drop?"

```
    SCENARIO:   Central bank slashes rates, bond yields collapse,
                investment returns plummet.

    WHO HURTS:  EVERYONE. Every insurance product involves discounting.
                Lower rates --> future obligations worth MORE today.

    SHOCK:      Shift the yield curve down (e.g., -200 bps) and up (+200 bps),
                take the worse outcome.

    EXAMPLE:    A whole life reserve computed at i=5% might be $200,000.
                At i=3% (rates drop 200 bps), the same reserve is $275,000.
                That $75,000 increase is the interest rate SCR component.
                The insurer must hold $75K extra in case rates crash.

    MENTAL MODEL: Interest rate is the "exchange rate between today and
                  tomorrow." When rates fall, the future gets more expensive.
                  Every obligation on your books suddenly costs more.

    WHY IT IS USUALLY THE LARGEST:
        We showed in Sensitivity Analysis (doc 15) that interest rate
        creates a 155% spread in whole life premiums, versus 42% for
        mortality shocks. The same asymmetry applies to reserves and SCR.
        Interest rate risk typically dominates the total capital requirement.
```

### 3.4 Catastrophe Risk -- "What If COVID Happens Again?"

```
    SCENARIO:   A sudden, extreme, short-duration mortality spike.
                Not a gradual trend change (that is mortality risk),
                but a one-time mass casualty event.

    WHO HURTS:  Death benefit portfolios, concentrated exposures.

    SHOCK:      An absolute addition to q_x (e.g., +1.5 per mille across
                all ages), NOT a percentage increase. This models an event
                that kills a fixed proportion of the population regardless
                of age-specific baseline mortality.

    EXAMPLE:    COVID-19 in Mexico (2020-2021) caused an estimated
                excess mortality of ~5 per mille in the general population.
                A catastrophe shock of 1.5 per mille on a portfolio of
                50,000 policies with SA=$500,000 average:
                Expected excess deaths: 50,000 * 0.0015 = 75
                Excess claims: 75 * $500,000 = $37.5M
                That is the catastrophe SCR component.

    MENTAL MODEL: Mortality risk is "deaths are 15% higher than normal."
                  Catastrophe risk is "a specific event kills an extra
                  1,500 people per million, on top of everything else."
                  One is a percentage; the other is an absolute addition.
```

---

## 4. Why Diversification Matters: The Natural Hedge

Here is the single most beautiful idea in insurance capital management:

**A pandemic is terrible for death products and wonderful for annuity products.**

Think about it:
- Pandemic hits --> more people die --> death benefit claims skyrocket (BAD)
- But also --> fewer pensioners survive --> pension payments decrease (GOOD)

An insurer that writes BOTH death products AND annuity products has a **natural hedge**. The losses on one side are partially offset by gains on the other side.

```
    Insurer A (only sells term life):
        Pandemic hits --> Claims +$30M --> Full loss.

    Insurer B (only sells pensions):
        Pandemic hits --> Pension savings -$20M --> Full gain.

    Insurer C (sells BOTH):
        Pandemic hits --> Claims +$30M, Pension savings -$20M
        Net impact: only -$10M.
        Capital needed: MUCH LESS than A alone.
```

This is not a trick or an accounting gimmick. It is a mathematical fact about how opposite risks partially cancel. The regulator recognizes this through the **correlation matrix** in the SCR aggregation formula.

```
    WITHOUT diversification:   SCR_total = SCR_mort + SCR_long + SCR_ir + SCR_cat
                               (simple sum -- assumes everything goes wrong at once)

    WITH diversification:      SCR_total = sqrt( sum of all rho_ij * SCR_i * SCR_j )
                               (square root of quadratic form -- recognizes offsets)

    The diversification benefit = (simple sum) - (aggregated SCR)
    This is ALWAYS non-negative. You never need MORE capital for writing both products.
```

---

## 5. The Correlation Matrix: Putting Numbers on the Hedge

The correlation matrix encodes how risks move together. For the four life insurance risks:

```
                Mortality   Longevity   Interest    Catastrophe
    Mortality      1.00       -0.25       0.25         0.25
    Longevity     -0.25        1.00       0.25         0.00
    Interest       0.25        0.25       1.00         0.00
    Catastrophe    0.25        0.00       0.00         1.00
```

Reading this matrix:

**Mortality vs. Longevity (rho = -0.25):**
This is the natural hedge expressed as a number. The negative sign means "when one goes up, the other tends to go down." A pandemic (high mortality) means fewer pensioners (lower longevity cost). The -0.25 is not -1.0 because the hedge is imperfect -- the ages affected by pandemics are not the same as the ages receiving pensions. Young people dying does not save you pension money.

**Mortality vs. Interest Rate (rho = +0.25):**
Weakly positive. In a crisis, interest rates tend to drop (central bank cuts rates) at the same time mortality may rise (economic hardship, reduced healthcare access). Both hurt the insurer simultaneously. The +0.25 reflects this "double hit" tendency.

**Mortality vs. Catastrophe (rho = +0.25):**
Weakly positive. A catastrophe event (like COVID) elevates both the short-term catastrophe shock AND the longer-term mortality trend. They tend to occur together but are not the same thing: mortality risk is a persistent trend change; catastrophe risk is a one-time spike.

**Longevity vs. Catastrophe (rho = 0.00):**
Independent. A pandemic does not meaningfully change the long-term longevity trend. People who survive a pandemic do not suddenly live shorter or longer lives afterwards (roughly speaking).

**Interest vs. Catastrophe (rho = 0.00):**
Independent. A catastrophe event does not directly cause interest rates to move. (Financial crises cause rate moves, but that is captured in the interest rate risk module, not the catastrophe module.)

### How Aggregation Works: A Numerical Example

Suppose the individual SCR components are:

```
    SCR_mortality     = $12M
    SCR_longevity     = $15M
    SCR_interest      = $25M
    SCR_catastrophe   = $ 8M

    Simple sum (no diversification):
        $12M + $15M + $25M + $8M = $60M

    Quadratic aggregation:
        SCR^2 = 12^2 + 15^2 + 25^2 + 8^2
                + 2*(-0.25)*12*15      (mort-long: -$90M^2  -- reduces!)
                + 2*(0.25)*12*25       (mort-ir:   +$150M^2)
                + 2*(0.25)*12*8        (mort-cat:  +$48M^2)
                + 2*(0.25)*15*25       (long-ir:   +$187.5M^2)
                + 2*(0.00)*15*8        (long-cat:  $0)
                + 2*(0.00)*25*8        (ir-cat:    $0)

        SCR^2 = 144 + 225 + 625 + 64 - 90 + 150 + 48 + 187.5 + 0 + 0
              = 1353.5

        SCR = sqrt(1353.5) = $36.8M

    Diversification benefit: $60M - $36.8M = $23.2M (38.7% reduction!)
```

That $23.2M is real money the insurer does NOT need to hold, purely because it writes a diversified book of business. This is one of the strongest economic incentives for insurers to offer both death products and annuities.

---

## 6. Risk Margin: Compensating the Rescuer

Imagine your insurer goes bankrupt. The regulator does not want policyholders to lose their coverage, so they find another insurer willing to take over the portfolio. But that rescuer needs to hold capital against the transferred liabilities. Who compensates them for that burden?

The **risk margin** does.

```
FORMULA:    Risk Margin = CoC * sum over t of [ SCR(t) / (1+r)^t ]

            where CoC = 6% (Cost of Capital rate, fixed by regulation)
            and SCR(t) = projected SCR at each future year t

INTUITION:  Think of it as "rent" for the capital the rescuer must hold.

            Year 1: rescuer holds $36.8M of capital. At 6%, the "rent" is $2.2M.
            Year 2: as policies lapse/mature, SCR drops to $30M. Rent is $1.8M.
            Year 3: SCR drops to $24M. Rent is $1.44M.
            ...and so on until the portfolio runs off completely.

            The risk margin is the present value of ALL those future rent payments.

WHY 6%:    The 6% is a regulatory convention, not a market rate. It represents the
            excess return over risk-free that an investor would demand for locking
            up capital in an insurance company. It is the same under both Solvency II
            and CNSF frameworks.

ROLE:       The total technical provision is BEL + Risk Margin.
            BEL = what you expect to pay.
            Risk Margin = the cost of the uncertainty around that expectation.
```

Think of it this way: BEL is the price of the meal. The risk margin is the tip -- it compensates for the service of bearing the risk, and it ensures that someone is always willing to pick up the tab if the original chef walks out of the kitchen.

---

## 7. The Complete Capital Stack

Now we can see the full picture of what an insurer must hold:

```
    ┌─────────────────────────────────────┐
    │         Free Surplus                 │  "Extra cushion above minimum"
    │         (management buffer)          │
    ├─────────────────────────────────────┤
    │                                     │
    │         SCR                          │  "Capital to survive a 1-in-200
    │         (Solvency Capital            │   year disaster"
    │          Requirement)                │
    │                                     │
    ├─────────────────────────────────────┤
    │         Risk Margin                  │  "Cost of transferring the risk
    │         (CoC at 6%)                  │   to another insurer"
    ├─────────────────────────────────────┤
    │                                     │
    │         BEL                          │  "Best estimate of what you owe"
    │         (Best Estimate Liability     │
    │          = Prospective Reserve)      │
    │                                     │
    └─────────────────────────────────────┘

    Total assets must exceed BEL + Risk Margin + SCR.
    The solvency ratio = Available Capital / SCR.
    CNSF requires solvency ratio >= 100%.
```

The solvency ratio is the single number that summarizes the insurer's financial health:

```
    Solvency Ratio = (Total Assets - BEL - Risk Margin) / SCR

    > 100%:  Solvent. The regulator is satisfied.
    = 100%:  Barely solvent. Minimum capital exactly met. Any deterioration
             triggers regulatory intervention.
    < 100%:  Insolvent. The regulator steps in: may restrict new business,
             require a recovery plan, or in extreme cases, liquidate.

    In practice, well-managed insurers target 150-200% to provide a buffer
    above the regulatory minimum.
```

---

## 8. Key Numbers to Remember for Interviews

These are the numbers that anchor your understanding. Know the ballpark, not the exact digits.

```
    CONFIDENCE LEVEL:
        SCR calibrated to 99.5% VaR over 1-year horizon
        = 1-in-200-year event

    STANDARD SHOCKS (Solvency II):
        Mortality:    +15% to all q_x
        Longevity:    -20% to all q_x
        Interest:     +/-200 bps shift (take worse)
        Catastrophe:  +1.5 per mille absolute addition

    CORRELATION MATRIX (key entries):
        Mortality-Longevity:  -0.25  (natural hedge)
        Mortality-Interest:   +0.25  (crisis double-hit)
        Mortality-Catastrophe:+0.25  (related events)

    COST OF CAPITAL:
        6% per annum (fixed by regulation)

    CNSF MINIMUM:
        Solvency ratio >= 100%
        (well-managed companies target 150-200%)

    RISK DOMINANCE (from sensitivity analysis):
        Interest rate risk is usually LARGEST (affects all products)
        Mortality/longevity depends on portfolio mix
        Catastrophe is usually smallest (short-duration, bounded event)
```

---

## 9. Interview Question Patterns

### The Conceptual Questions

**Q: "What is the SCR and why does it exist?"**

> "The SCR is the capital buffer an insurer must hold above its best estimate liabilities to ensure it can absorb a 1-in-200-year adverse event without going bankrupt. It exists because insurance is a promise about the future, and the future is uncertain. The BEL covers expected claims; the SCR covers the unexpected tail. Without it, an insurer could be technically profitable on average but blow up in a bad year, leaving policyholders unpaid. The regulator mandates the SCR to protect policyholders from that tail risk."

**Q: "Explain the natural hedge between mortality and longevity."**

> "A pandemic kills more people -- terrible for death benefit products because claims spike. But those same deaths mean fewer pension payments for annuity products -- a savings. An insurer writing both product types experiences a partial offset: the mortality loss is cushioned by the longevity gain. This shows up in the correlation matrix as a negative correlation of -0.25 between mortality and longevity risk. When you aggregate the SCR using the quadratic formula, this negative correlation reduces the total capital requirement. In our numerical example, the diversification benefit was 39% -- the insurer holds $36.8M instead of $60M. This is one of the strongest economic arguments for product diversification in insurance."

**Q: "Why is interest rate risk usually the largest component?"**

> "Because interest rate affects the present value of ALL future cash flows -- both assets and liabilities. A 200-basis-point drop in rates can increase the value of long-duration liabilities by 30-50% for products like whole life or pensions. By contrast, a 15% mortality shock only affects the probability-weighted claims, which is a smaller portion of the total balance sheet. We demonstrated this in sensitivity analysis: interest rate creates a 155% spread in whole life premiums versus 42% for mortality shocks. The same relative magnitude carries through to SCR. For a typical balanced portfolio, interest rate risk accounts for 40-60% of total SCR before diversification."

### The Technical Questions

**Q: "Walk me through the SCR aggregation formula."**

> "The individual risk components -- mortality, longevity, interest rate, catastrophe -- are each computed as the change in BEL under their respective stress scenarios. Then they are aggregated using a quadratic form: SCR-squared equals the sum over all pairs (i,j) of rho(i,j) times SCR(i) times SCR(j). This is the matrix formula SCR = sqrt(S' * C * S) where S is the vector of individual SCR components and C is the correlation matrix. The square root of a quadratic form is always less than or equal to the sum of the components (by the triangle inequality), which means diversification always reduces capital. The only case where the aggregated SCR equals the simple sum is when all correlations are 1.0 -- perfect co-movement."

**Q: "What is the risk margin and why is CoC fixed at 6%?"**

> "The risk margin represents the cost of holding capital against the run-off of the existing portfolio. If the insurer were to transfer its liabilities to a third party, that third party would need to hold SCR against them for every remaining year. The risk margin compensates the third party at 6% per year for that locked-up capital. The 6% is a regulatory convention, not a market-derived rate. It was chosen as a reasonable long-term cost of equity for insurance companies. Fixing it by regulation avoids the circularity of deriving it from market data that itself depends on the regulatory framework."

**Q: "How does this connect to your sensitivity analysis from Phase 2?"**

> "Sensitivity analysis measured the gradients -- how much premiums and reserves move per unit of risk factor change. Capital requirements multiply those gradients by the size of the regulatory stress scenario. For example, we found that a 30% mortality shock raises whole life reserves by about 16%. The SCR mortality component is essentially: BEL-under-15%-shock minus BEL-base. The sensitivity analysis gave us the curve shape; the SCR picks a specific point on that curve defined by the regulatory shock magnitude. The two phases are linked: Phase 2 maps the terrain, Phase 3 marks the specific danger points."

### The Regulatory Questions

**Q: "What happens when the solvency ratio falls below 100%?"**

> "The CNSF has an escalation ladder. At 100%, the insurer is at the regulatory minimum -- any further deterioration triggers formal intervention. The regulator may require a recovery plan with specific actions and deadlines: inject fresh capital, reduce risk exposure, stop writing new business, reinsure part of the portfolio. If the solvency ratio drops significantly below 100% or the recovery plan fails, the CNSF can revoke the operating license and initiate an orderly transfer of the portfolio to a solvent insurer. The risk margin ensures there is always enough to compensate the receiving insurer for taking on the liabilities."

**Q: "How does CNSF compare to Solvency II?"**

> "The Mexican framework under LISF/CUSF follows the same conceptual structure as Solvency II: three-pillar approach (quantitative requirements, governance, disclosure), market-consistent valuation of BEL, standard formula for SCR with correlation-based aggregation, and a cost-of-capital risk margin. The main differences are calibration details: the specific shock magnitudes, the correlation parameters, and the regulatory reporting templates. CNSF may also prescribe regulatory tables like CNSF 2000-I and EMSSA-2009 as minimum mortality benchmarks, which do not have direct Solvency II equivalents. But the intellectual framework -- BEL plus risk margin plus SCR, aggregated with diversification credit -- is shared."

---

## 10. Connection to the SIMA Architecture

Where does Phase 3 fit in the existing codebase?

```
    Phase 1 (Empirical Pipeline):
        a06 --> a07 --> a08 --> a09 --> to_life_table()
                                              |
    Phase 2 (Theoretical Pipeline):           |
        a01 --> a02 --> a03 --> a04 --> a05    |
                                   \          |
                                    \         |
    Phase 2.5 (Sensitivity):         \        |
        sensitivity_analysis.py       \       |
         (interest rate, mortality,    \      |
          cross-country gradients)      \     |
                                         \    |
    Phase 3 (Capital Requirements):       v   v
        a11_capital_requirements.py  <--- stressed BEL at each scenario
             |
             |--> BEL_base (reserves from a05)
             |--> BEL_mortality_shocked (a05 with shocked life table)
             |--> BEL_longevity_shocked (a05 with improved life table)
             |--> BEL_interest_shocked (a05 with shifted rate)
             |--> BEL_catastrophe_shocked (a05 with absolute q_x addition)
             |
             |--> SCR_i = |BEL_shocked_i - BEL_base|
             |--> SCR_total = sqrt( S' * C * S )
             |--> Risk_Margin = CoC * sum( SCR(t) / (1+r)^t )
             |--> Solvency_Ratio = Available_Capital / SCR_total
```

The beauty of the modular architecture is that Phase 3 does not require rewriting any existing code. It reuses:

- `build_shocked_life_table()` from sensitivity analysis (already exists)
- `ReserveCalculator` from a05 (already exists)
- `CommutationFunctions` from a02 (already exists)

Phase 3 adds only the aggregation logic (correlation matrix, quadratic form, risk margin projection) and the solvency ratio dashboard.

---

*Created: February 2026*
