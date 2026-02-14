# Mortality Projection -- Intuitive Reference

**Module:** `backend/engine/a09_projection.py`
**Class:** `MortalityProjection`

---

## 1. The Big Question

You have fitted a Lee-Carter model to 30 years of historical death rates. You know:

- $a_x$: the "shape" of mortality by age (fixed pattern)
- $b_x$: which ages are most sensitive to the mortality trend
- $k_t$: the time index that has been going down year after year

**Now what?** You need to predict what $k_t$ will be in 5, 10, 30 years. If you can do that, you can reconstruct the entire future mortality surface and price insurance products for future generations.

---

## 2. Projecting $k_t$: The Random Walk with Drift

### 2.1 What Is Drift?

Look at the historical $k_t$ series. It trends downward -- mortality has been improving. The **drift** is simply the average annual change:

```
drift = (last k_t - first k_t) / (number of intervals)
```

If $k_t$ went from +10 to -20 over 30 years, the drift is $(-20 - 10)/30 = -1.0$ per year. Mortality is improving by roughly 1 unit of $k_t$ per year.

**Think of drift as the speed of the mortality escalator.** Mortality is on a downward escalator. The drift tells you how fast it is descending.

### 2.2 What Is Sigma?

The drift is the average trend, but $k_t$ does not follow a perfectly straight line. Some years mortality improves more, some years less. Maybe a flu epidemic pushes $k_t$ up temporarily.

**Sigma measures the wobble around the trend.** Formally, it is the standard deviation of the year-to-year changes after removing the drift:

```
wobble_t = (k_t - k_{t-1}) - drift
sigma = standard deviation of all the wobbles
```

A small sigma means $k_t$ follows the trend closely. A large sigma means lots of year-to-year noise.

### 2.3 Deterministic vs. Stochastic Projection

**Deterministic (the central projection):**

Just extend the line. If the drift is -1.0, then next year $k_t$ drops by 1, the year after by 2, etc. This is your "best estimate" -- the expected path. It is a straight line extending from the last observed point.

```
k_{T+1} = k_T + drift
k_{T+2} = k_T + 2 * drift
...
k_{T+h} = k_T + h * drift
```

**Stochastic (the cloud of possibilities):**

Reality will not follow the straight line exactly. The stochastic projection generates 1,000 (or more) possible futures, each slightly different:

```
Path 1:  k_T + drift + wobble_1,  k_T + 2*drift + wobble_1 + wobble_2, ...
Path 2:  k_T + drift + wobble_1', k_T + 2*drift + wobble_1' + wobble_2', ...
...
```

Each path adds random noise (drawn from a normal distribution with standard deviation sigma) to the deterministic trend. The collection of paths forms a **fan** that widens over time. This widening is fundamental: the further you look ahead, the more uncertain things become.

**Analogy:** Imagine throwing a ball down a bumpy hill. The deterministic projection is the smooth trajectory you would expect. The stochastic paths are what actually happens -- the ball bounces left and right unpredictably, and the further it rolls, the wider the range of places it could end up.

### 2.4 Why a Random Walk?

When you look at the year-to-year changes in $k_t$ (the "wobbles"), they look roughly independent and identically distributed. There is no pattern in the wobbles -- each year's surprise is unrelated to the previous year's. That is exactly the definition of a random walk. It is the simplest model that captures both the trend and the uncertainty, and it has been the standard choice since Lee and Carter's original 1992 paper.

---

## 3. Confidence Intervals: The Fan of Uncertainty

For any future (age, year) combination, you can ask: "What is the range of plausible death rates?"

The answer comes from the stochastic paths:

1. Take all 1,000 simulated $k_t$ values for that year.
2. For each, compute the death rate: $m_x = \exp(a_x + b_x \cdot k_t)$.
3. Sort the 1,000 rates and pick the 5th and 95th percentiles.

That gives you a 90% confidence interval. The interval is narrow for next year and wide for 30 years out.

```
Year +1:   rate between 0.0048 and 0.0052    (narrow)
Year +10:  rate between 0.0035 and 0.0060    (wider)
Year +30:  rate between 0.0015 and 0.0075    (much wider)
```

**Why does uncertainty grow with the square root of time?** Because the variance of a random walk after $h$ steps is $h \cdot \sigma^2$, so the standard deviation is $\sigma\sqrt{h}$. Double the horizon, and the uncertainty increases by $\sqrt{2} \approx 1.41$. This is a fundamental property of random walks.

---

## 4. The Bridge: From Empirical Data to Insurance Premiums

### 4.1 The Problem

At this point you have projected death rates: $m_x$ for every age and future year. But the actuarial engine (commutation functions, premiums, reserves) needs a **LifeTable** -- an object with ages and a survivor column $l_x$.

How do you go from death rates to a life table?

### 4.2 The Conversion Chain

```
m_x  --->  q_x  --->  l_x  --->  LifeTable
```

**Step 1: $m_x \to q_x$ (rate to probability)**

$m_x$ is a **rate** (deaths per person-year of exposure). $q_x$ is a **probability** (chance of dying within the year). They are related but not the same thing.

Under the assumption that the force of mortality is constant within each year of age:

$$q_x = 1 - e^{-m_x}$$

**Why this formula?** Think of it this way: if the instantaneous hazard of death is $m_x$ throughout the year, then surviving the entire year means avoiding death for every instant. The probability of surviving is $e^{-m_x}$ (the Poisson "no event" probability), so the probability of dying is $1 - e^{-m_x}$.

For small $m_x$ (young ages), this is approximately $q_x \approx m_x$. The two diverge at old ages where rates are high: when $m_x = 0.3$, the exact $q_x$ is 0.259 while the linear approximation gives 0.3 -- a 16% overstatement. This is why we use the exact formula.

**Step 2: $q_x \to l_x$ (probability to survivors)**

Once you have $q_x$ at every age, building the survivor column is straightforward:

```
l_0     = 100,000  (starting population, the "radix")
l_1     = l_0 * (1 - q_0)
l_2     = l_1 * (1 - q_1)
...
l_{x+1} = l_x * (1 - q_x)
```

Each year, the surviving population is reduced by the fraction that died. At the terminal age $\omega$, we force $q_\omega = 1.0$ so that everyone eventually dies.

**Step 3: Create the LifeTable**

The `LifeTable` constructor takes lists of ages and $l_x$ values, and automatically derives $d_x$, $q_x$, and $p_x$. From this point on, the actuarial engine works exactly the same whether the life table came from a CSV file, from a published mortality table like EMSSA-2009, or from a Lee-Carter projection.

### 4.3 Why This Bridge Matters

Without `to_life_table()`, Lee-Carter is just an interesting statistical decomposition. It tells you that mortality is improving, but you cannot compute a premium or a reserve.

With the bridge, you can answer questions like:

- "What will a whole life policy for a 30-year-old cost in 2035, based on projected mortality?"
- "How much do reserves change under optimistic vs. pessimistic mortality scenarios?"
- "What is the capital requirement if mortality worsens by 2 standard deviations?"

The bridge is what makes the Lee-Carter model **actuarially useful**.

### 4.4 The Three LifeTables: Central, Optimistic, Pessimistic

`to_life_table_with_ci()` takes the idea further. Instead of one life table, it produces three:

| Scenario | Which $k_t$ is used | Effect on mortality | Use case |
|:---------|:---------------------|:--------------------|:---------|
| Central | Deterministic (expected path) | Best estimate | Pricing, best-estimate reserves |
| Optimistic | Low quantile (e.g., 5th percentile) | Lower mortality, longer lives | Longevity risk assessment |
| Pessimistic | High quantile (e.g., 95th percentile) | Higher mortality, shorter lives | Mortality risk assessment |

Note the subtlety: "optimistic" means lower mortality, which is good for the insured person (they live longer) but bad for an annuity provider (they pay out longer). The interpretation depends on the product.

---

## 5. The Full Journey: From Historical Data to an Insurance Premium

This is the end-to-end story that ties together the entire SIMA pipeline. If an interviewer asks "Walk me through how you go from historical data to an insurance premium," here is the answer:

```
1. LOAD DATA (a06)
   Read HMD files: death counts, exposures, and rates for USA males, 1990-2020.
   Result: matrices of m_x, d_x, L_x (101 ages x 31 years).

2. SMOOTH (a07, optional)
   Apply Whittaker-Henderson graduation to remove age-specific noise.
   Result: smoothed m_x matrix with the same shape.

3. DECOMPOSE (a08)
   Fit Lee-Carter: ln(m_x,t) = a_x + b_x * k_t.
   SVD gives a_x (shape), b_x (sensitivity), k_t (trend).
   Re-estimate k_t to match observed death counts.
   Result: three parameter vectors capturing the mortality surface.

4. PROJECT (a09)
   Model k_t as a Random Walk with Drift.
   Estimate drift and sigma from the historical k_t.
   Generate central projection and 1,000 stochastic paths.
   Result: projected k_t for the next 30 years.

5. BRIDGE (a09 -> a01)
   Pick a target year (e.g., 2035).
   Reconstruct m_x = exp(a_x + b_x * k_{2035}).
   Convert m_x -> q_x -> l_x.
   Create a LifeTable object.
   Result: a standard life table for 2035.

6. PRICE (a02 -> a04)
   Build CommutationFunctions from the life table (D_x, N_x, C_x, M_x).
   Use the equivalence principle: Premium = SA * M_x / N_x.
   Result: the annual premium for a whole life policy.
```

Each step is a separate module with its own tests. The modularity means you can swap components (e.g., use Mexican data instead of HMD, or a different projection model) without rewriting the downstream engine.

---

## 6. What Makes Mortality Projections Uncertain?

Several sources of uncertainty compound in mortality forecasting:

**Model risk:** The Lee-Carter model assumes mortality variation is driven by a single factor $k_t$. In reality, there may be cohort effects, nonlinear trends, or structural breaks.

**Parameter uncertainty:** The drift and sigma are estimated from finite data. With only 30 years of $k_t$ values, the drift estimate has substantial sampling error.

**Process risk:** Even if the model and parameters are correct, the random walk generates different paths. This is the uncertainty captured by the stochastic simulation.

**Tail risk:** Extreme events (pandemics, medical breakthroughs) are not well captured by a Gaussian random walk. The historical period may not contain sufficient extreme events to calibrate tail behavior.

**Extrapolation risk:** Projecting 30 years ahead from 30 years of data assumes the future will behave like the past. If the rate of medical progress changes, or if new diseases emerge, the projection breaks down.

For actuarial practice, these risks are why regulators (including CNSF in Mexico) require stress testing and capital buffers beyond the best-estimate projection.

---

## 7. Interview Anchors

| Question | Key Points |
|:---------|:-----------|
| "How do you project mortality into the future?" | Fit Lee-Carter to get $k_t$, model $k_t$ as a Random Walk with Drift, extrapolate. Central projection for pricing, stochastic paths for risk assessment. |
| "Why RWD and not something more complex?" | $k_t$ differences are empirically i.i.d. RWD is the simplest model that captures trend and uncertainty. Standard in practice since Lee-Carter (1992). |
| "What does the drift tell you?" | The average annual improvement in mortality. Negative drift = mortality improving. For USA males, typically around -1 to -2 units per year. |
| "How do you go from projected rates to a premium?" | $m_x \to q_x$ via $1 - e^{-m_x}$, then $q_x \to l_x$ by recursion, then $l_x$ into `LifeTable` $\to$ `CommutationFunctions` $\to$ `PremiumCalculator`. |
| "Why is $q_x = 1 - e^{-m_x}$ and not just $q_x = m_x$?" | Constant force of mortality assumption. For small rates they are nearly equal, but at old ages (high $m_x$) the difference is significant. The exponential formula is exact under the assumption. |
| "What happens to uncertainty over time?" | It grows as $\sigma\sqrt{h}$. The fan of possible outcomes widens. This is intrinsic to random walks: the variance accumulates linearly with time. |
| "How does improving mortality affect premiums?" | If mortality improves (drift < 0), fewer people die each year, so death benefit payouts are delayed. This reduces the present value of benefits, which lowers premiums. This is verified by `test_mortality_improvement_lowers_premiums`. |
| "What is the difference between the central and stochastic projections?" | Central = expected path (for best-estimate pricing). Stochastic = cloud of 1,000 paths (for confidence intervals, stress testing, and capital requirements). |

---

## 8. Summary

The Mortality Projection module completes the empirical-to-theoretical pipeline in SIMA:

```
Past data  -->  Lee-Carter fit  -->  Project k_t  -->  to_life_table()  -->  Premiums
```

The Random Walk with Drift is a simple, interpretable, and well-tested approach for forecasting the mortality trend. The stochastic simulation provides the uncertainty quantification needed for regulatory compliance and risk management. And the bridge method `to_life_table()` is the key that unlocks the entire actuarial engine for projected mortality -- connecting what we observe in the data to what we compute in the theory.
