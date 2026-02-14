# Architecture and Integration: Intuitive Reference

**Module:** All engine modules (`backend/engine/a01_life_table.py` through `a09_projection.py`)

---

## 1. The Two Rivers Merging

Think of the SIMA engine as two rivers that merge into one.

**River 1 -- The Empirical River** starts with raw, messy data: death counts and population numbers downloaded from the Human Mortality Database. This river flows through filters (cleaning), smoothing (graduation), decomposition (Lee-Carter), and forecasting (projection). By the end, the water is clean, structured, and pointed toward the future.

**River 2 -- The Theoretical River** starts with a simple table of survivors by age. This river flows through discounting (commutation functions), valuation (actuarial present values), pricing (premiums), and liability measurement (reserves). It answers: "Given this mortality, what should we charge and hold?"

**The confluence** is a single method called `to_life_table()`. It takes the clean, future-facing water from River 1 and pours it into the channel of River 2. The projected death rates from Lee-Carter become a life table, which becomes commutation functions, which become premiums and reserves.

Without this bridge, River 1 produces academic statistics and River 2 requires assumptions plucked from thin air. Together, they produce data-driven actuarial outputs.

---

## 2. Pipeline 1: "We Have Dead People"

The empirical pipeline answers: **"We have messy mortality data. How do we make it clean and predictive?"**

### Stage 1: Load the Data (a06)

The HMD gives us three files per country: death rates (Mx), death counts (Deaths), and person-years of exposure (Exposures). Each file has one row per age-year combination spanning decades. The `MortalityData` class reads these text files and pivots them into matrices where rows are ages and columns are years.

The tricky part: ages above 100 have tiny populations. A single death in a population of 3 people gives a death rate of 0.33 -- is that reliable? No. So we cap ages at 100 by summing all deaths and exposures above that age, then recomputing the rate as the total-deaths/total-exposure ratio. This is exposure-weighted aggregation, not naive averaging.

### Stage 2: Smooth the Noise (a07)

Raw death rates are noisy, especially at the extremes. A 95-year-old population might have 12 people one year and 8 the next -- small numbers produce wild fluctuations. Lee-Carter needs smooth rates because it works with logarithms, and noisy log-rates produce noisy SVD components.

Whittaker-Henderson graduation is the solution. Think of it as fitting a flexible ruler to the data: the ruler wants to pass through each data point (fidelity) but also wants to be smooth (penalty for curvature). The parameter lambda controls the tradeoff -- lambda=0 means "follow every bump", large lambda means "ignore bumps and draw a smooth curve."

The graduation works in log-space (smooth log-rates, then exponentiate) which guarantees that graduated rates are always positive -- you can't get a negative death rate from exp(anything).

### Stage 3: Fit the Model (a08)

Now we have a clean surface of death rates across ages and years. Lee-Carter says this surface can be decomposed as:

```
ln(death rate at age x, year t) = a_x + b_x * k_t
```

- **a_x** is the average shape of mortality across ages (high for infants, low for teens, rising through old age)
- **b_x** tells us which ages are improving fastest (some ages benefit more from medical advances)
- **k_t** is a single number per year capturing the overall mortality level (usually declining over time)

The fitting uses SVD (Singular Value Decomposition) to find the best rank-1 approximation to the residual matrix. Then k_t is re-estimated using Brent's root-finding method so that the model reproduces the correct total number of deaths each year -- not just the correct log-rates.

### Stage 4: Project the Future (a09)

With a_x, b_x fitted and k_t showing a trend over time (usually downward -- mortality is improving), we extrapolate k_t into the future using a Random Walk with Drift:

```
k(future) = k(last observed) + drift * years_ahead + noise
```

The drift is the average annual change in k_t. The noise (sigma) captures year-to-year randomness. Running 1,000 simulated paths gives us not just one forecast but a fan of possibilities -- confidence intervals for future mortality.

---

## 3. Pipeline 2: "We Have a Survival Table"

The theoretical pipeline answers: **"Given clean mortality assumptions, what should we charge for insurance and how much should we hold in reserves?"**

### Stage 1: Build the Life Table (a01)

Everything starts with l_x -- the number of survivors at each age from an initial cohort (conventionally 100,000). From l_x, we derive:
- d_x (deaths): how many people die between age x and x+1
- q_x (death probability): what fraction of the age-x population dies this year
- p_x (survival probability): what fraction survives to next year

This is a "closed" system: the sum of all deaths equals the initial population. Everyone eventually dies; the table just tells us when.

### Stage 2: Add the Time Value of Money (a02)

Death happens in the future, and money today is worth more than money tomorrow. Commutation functions bake in a discount factor v = 1/(1+i):

- **D_x = v^x * l_x**: "How much is the pool of survivors at age x worth in today's dollars?"
- **N_x = D_x + D_{x+1} + ... + D_omega**: "How much are ALL future survivor-pools worth?"
- **C_x = v^{x+1} * d_x**: "How much is the death benefit payout at age x worth today?"
- **M_x = C_x + C_{x+1} + ... + C_omega**: "How much are ALL future death payouts worth?"

N and M are computed using backward recursion (start at the end, work backwards), which is dramatically faster than summing forward from each age.

### Stage 3: Compute Actuarial Values (a03)

Now the magic of commutation functions pays off. Every actuarial present value is a simple ratio:

- A_x = M_x / D_x ("expected present value of a $1 death benefit")
- a_x = N_x / D_x ("expected present value of a $1/year annuity")
- nE_x = D_{x+n} / D_x ("expected present value of $1 paid if you survive n years")

Division by D_x converts cohort-level aggregates into per-person expected values. This is the key insight: cohort total / cohort size = individual expected value.

### Stage 4: Price Insurance Products (a04)

The equivalence principle says: at policy issue, the expected premiums collected must equal the expected benefits paid. For whole life insurance:

```
P * a_x = SA * A_x
P = SA * A_x / a_x = SA * M_x / N_x
```

The D_x terms cancel beautifully. The premium is just the ratio of "expected death benefit cost" to "expected years of premium payment."

### Stage 5: Compute Reserves (a05)

After the policy has been in force for t years, the reserve is:

```
tV = SA * A_{x+t} - P * a_{x+t}
```

"Future expected benefits minus future expected premiums." At issue (t=0), these are equal (that's how P was set), so the reserve is zero. Over time, the reserve grows because fewer premium payments remain but the insured is closer to death.

---

## 4. The Bridge: "From Statistics to Actuarial Science"

The `to_life_table()` method on `MortalityProjection` is where the two worlds meet. Here is the exact chain:

1. Lee-Carter gives us projected death rates m_x for a future year
2. Convert to death probabilities: `q_x = 1 - exp(-m_x)` (the "constant force" assumption)
3. Build survivors: start with l_0 = 100,000, then `l_{x+1} = l_x * (1 - q_x)`
4. Force q_omega = 1.0 (everyone dies at the terminal age)
5. Return a `LifeTable` object

This LifeTable is indistinguishable from one loaded from a CSV file or a published table. Once created, it feeds into CommutationFunctions, which feeds into premiums and reserves. The entire theoretical pipeline works without knowing or caring that the life table came from a Lee-Carter projection.

---

## 5. Why 9 Modules? (Single Responsibility)

Each module does exactly ONE thing:

| Module | One-Line Job |
|:-------|:-------------|
| a01 | Turn survivor counts into death probabilities |
| a02 | Discount mortality for the time value of money |
| a03 | Compute expected present values of contingent payments |
| a04 | Set premiums so expected income = expected outgo |
| a05 | Measure the insurer's liability at any duration |
| a06 | Load and validate mortality data from files |
| a07 | Smooth noisy rates to prepare for modeling |
| a08 | Decompose mortality into age-pattern and time-trend |
| a09 | Forecast mortality and convert back to life tables |

If you wanted to swap Whittaker-Henderson for a different smoother, you only change a07. If you wanted to use a different mortality model (Cairns-Blake-Dowd instead of Lee-Carter), you only change a08. The rest of the system is unaffected.

---

## 6. Duck Typing: Why It Matters Here

`LeeCarter.fit()` accepts either `MortalityData` or `GraduatedRates`. It does not check the type -- it just accesses `.mx`, `.dx`, `.ex`, `.ages`, `.years`. This works because `GraduatedRates` was deliberately designed to expose the same interface as `MortalityData`.

This is **structural subtyping** (also called duck typing): "If it walks like a duck and quacks like a duck, it's a duck." The benefit is that you can:

1. Fit Lee-Carter on raw data: `LeeCarter.fit(raw_data)`
2. Fit Lee-Carter on graduated data: `LeeCarter.fit(graduated_data)`
3. In the future, fit Lee-Carter on any new data source that exposes the same attributes

No abstract base class, no interface definition, no type hierarchy. The contract is implicit, documented, and tested.

---

## 7. The Complete Journey: From Raw Death Counts to an Insurance Premium

Here is the full path through the system, in plain language:

1. **Download** mortality data for the USA from HMD (death rates, death counts, exposures for ages 0-100, years 1990-2020)
2. **Load** it into a `MortalityData` object -- three aligned matrices, validated for completeness
3. **Graduate** the rates with Whittaker-Henderson -- smooth out noise, especially at old ages
4. **Fit** a Lee-Carter model -- decompose the mortality surface into a_x (age shape), b_x (age sensitivity), k_t (time trend)
5. **Project** k_t 30 years forward -- Random Walk with Drift gives central forecast plus 1,000 stochastic paths
6. **Bridge** to a life table for year 2040 -- convert projected m_x to q_x to l_x, return a LifeTable
7. **Build** commutation functions from the life table at 5% interest -- D, N, C, M for all ages
8. **Price** a whole life policy for a 35-year-old: P = SA * M_35 / N_35

The premium you get reflects real mortality data, statistical modeling, future mortality improvement, and the time value of money. Change any assumption (interest rate, projection horizon, country) and the premium changes accordingly.

---

## 8. Interview-Ready Explanation

**Q: "Explain your system architecture."**

A: "The SIMA engine has two pipelines. The empirical pipeline takes raw HMD mortality data, smooths it with Whittaker-Henderson graduation, fits a Lee-Carter model via SVD to decompose mortality into age and time components, and projects future mortality using a Random Walk with Drift. The theoretical pipeline takes a life table, builds commutation functions with discounting, and computes actuarial present values, premiums, and reserves.

The two pipelines connect through a single bridge method: `to_life_table()` converts projected death rates into a standard life table. This design means the pricing engine doesn't know or care where its life table came from -- it could be a Lee-Carter projection, a published regulatory table, or a hand-crafted scenario. The pipelines are independently testable and independently extensible.

Key technical decisions: duck typing allows Lee-Carter to accept either raw or graduated data without type-checking; backward recursion gives O(n) commutation computation instead of O(n^2); and all computations happen in the constructor so objects are immutable after creation."

---

## 9. Extensibility for Future Phases

The architecture is designed to accommodate the project's remaining phases:

### Mexican Data (INEGI/CONAPO)

A new loader class (perhaps `MexicanMortalityData`) needs only to produce the same interface as `MortalityData` -- `.mx`, `.dx`, `.ex`, `.ages`, `.years`. The entire downstream pipeline (a07 through a09, then a01 through a05) works unchanged.

### EMSSA-2009 Validation

The published Mexican experience table can be loaded as a `LifeTable` directly, bypassing the empirical pipeline entirely. Compare premiums from EMSSA-2009 vs. Lee-Carter projections to validate the model against regulatory benchmarks.

### Sensitivity Analysis

The theoretical pipeline already accepts any `LifeTable` and any interest rate. Interest rate sensitivity means looping over rates; mortality shock analysis means perturbing the projected m_x before calling `to_life_table()`.

### Capital Requirements (Phase 3)

Stress scenarios require running the theoretical pipeline under multiple adverse assumptions. The 1,000 stochastic paths from `MortalityProjection` provide the mortality dimension; varying interest rates provides the financial dimension. The modular architecture means each scenario is just a different (LifeTable, interest_rate) pair fed into the same a02-a05 chain.

### Web Platform (Phase 4)

The engine modules are pure Python with no I/O dependencies (except a06's file loading). Wrapping them in a FastAPI backend requires only serializing the outputs -- no refactoring of the calculation logic.
