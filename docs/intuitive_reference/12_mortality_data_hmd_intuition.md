# Mortality Data & HMD Loading -- Intuitive Reference

**Source Module:** `backend/engine/a06_mortality_data.py`

---

## 1. Why HMD Is the "Gold Standard"

```
THE PROBLEM:    Every country collects mortality data differently.
                Different formats, different age groupings,
                different definitions of "exposure."

HMD'S PROMISE:  One consistent format across 40+ countries, 100+ years.
                Harmonized definitions. Documented methodology.
                If you can load USA data, you can load Japan data
                with the same code.

WHO USES IT:    Demographers, actuaries, epidemiologists, economists.
                The Lee-Carter paper? Uses HMD.
                World Population Prospects? Informed by HMD.
                Insurance companies benchmarking mortality tables? HMD.
```

The reason this module exists is precisely because HMD provides that consistency -- we write one loader and it works for any country in the database.

---

## 2. The Spreadsheet Mental Model

Think of mortality data as a giant spreadsheet:

```
              1990    1991    1992    ...    2020
age 0        0.0103  0.0098  0.0093  ...   0.0058
age 1        0.0007  0.0007  0.0006  ...   0.0004
age 2        0.0005  0.0005  0.0004  ...   0.0003
  ...          ...     ...     ...   ...     ...
age 50       0.0055  0.0054  0.0052  ...   0.0046
  ...          ...     ...     ...   ...     ...
age 100      0.3500  0.3400  0.3300  ...   0.2800
```

- **Each row** = one age, tracking how mortality at that age changes over time
- **Each column** = one calendar year, showing the full mortality profile that year
- **Each cell** = the central death rate $m_{x,t}$

Now, HMD actually gives you **three** of these spreadsheets, all perfectly aligned:
1. **Mx** -- the death rates (the one we just showed)
2. **Deaths** -- the raw death counts
3. **Exposures** -- the person-years of observation

And the fundamental relationship linking them is trivially simple:

```
Rate = Deaths / Exposure
m_{x,t} = d_{x,t} / L_{x,t}
```

That is it. Every cell in the Mx spreadsheet equals the corresponding cell in Deaths divided by the corresponding cell in Exposures.

---

## 3. Rates vs. Probabilities: Why HMD Gives You m_x

```
WHAT YOU CAN COUNT:     Deaths (death certificates)
                        Person-years of observation (census, population registers)

WHAT YOU OBSERVE:       m_x = deaths / person-years

WHAT YOU CANNOT OBSERVE DIRECTLY:
                        q_x = probability that a person alive at exact age x
                              will die before reaching exact age x+1

WHY NOT?                You never directly observe a "cohort" from exact
                        birthday to exact birthday. People enter and leave
                        the observation window at random times.
                        Person-years handles this messiness.
                        Probability q_x requires an assumption about
                        how deaths are distributed within the year.
```

| Feature | m_x (rate) | q_x (probability) |
|:--------|:-----------|:-------------------|
| Directly observable? | Yes | No |
| Range | (0, +infinity) | [0, 1] |
| Needs assumption? | No | Yes (UDD or constant force) |
| Can exceed 1? | Yes (extreme ages) | Never |
| Used by Lee-Carter? | Yes (log m_x) | No |
| Used by life tables? | No | Yes (l_x, d_x, p_x) |

The bridge between them:

```
q_x = 1 - exp(-m_x)       (constant force of mortality assumption)

This works for any positive m_x, even when m_x > 1.
```

---

## 4. Why Exposure Matters: You Need the Denominator

```
WRONG COMPARISON:
  Country A: 50,000 deaths at age 70 last year
  Country B: 10,000 deaths at age 70 last year
  Conclusion: Country A is more dangerous?

NOT SO FAST:
  Country A population at age 70: 5,000,000 --> m_70 = 0.010
  Country B population at age 70:   200,000 --> m_70 = 0.050

  Country B has 5x the mortality rate despite fewer raw deaths.
```

Exposure (person-years) is the denominator that makes comparisons fair. Without it, you are comparing raw counts that reflect population size, not mortality risk.

```
ANALOGY:    Batting average in baseball.
            Player A: 180 hits in 600 at-bats = .300
            Player B: 50 hits in 150 at-bats  = .333
            Fewer hits, better average.
            At-bats are the "exposure" that normalizes.
```

In insurance, the exposure concept is even more important because policyholders join and leave the portfolio at different times. One policyholder observed for 6 months contributes 0.5 person-years. Two policyholders each observed for 3 months contribute the same 0.5 person-years combined. Person-years handles all of this naturally.

---

## 5. Age Capping: Why We Stop at 100

```
THE PROBLEM:   HMD has data up to age 110+.
               But at extreme ages (105, 108, 110):
               - Very few people alive (maybe 50 in the whole country)
               - Deaths are stochastic noise (3 deaths vs. 5 deaths = 67% swing)
               - Rates become wildly unstable

EXAMPLE:       Age 108, year 2005:
               Deaths: 2
               Exposure: 3.5 person-years
               m_108 = 2/3.5 = 0.571

               Age 108, year 2006:
               Deaths: 5
               Exposure: 4.1 person-years
               m_108 = 5/4.1 = 1.219

               150% jump year-over-year? Not a real mortality change.
               Just noise from tiny sample sizes.

THE SOLUTION:  Cap ages at 100. Lump everything 100+ into one group.
               Pool the deaths. Pool the exposure. Compute one rate.
               Much more stable.
```

The key subtlety: you cannot average the rates across ages. You must sum the deaths, sum the exposures, then divide. This gives the correct exposure-weighted rate.

```
WRONG:   m_100+ = (m_100 + m_101 + ... + m_110) / 11
         This gives equal weight to age 110 (5 people) and
         age 100 (10,000 people).

RIGHT:   m_100+ = (d_100 + d_101 + ... + d_110) / (L_100 + L_101 + ... + L_110)
         The 10,000 people at age 100 dominate, as they should.
```

---

## 6. The Duck Typing Design

In our engine, `MortalityData` (raw data from HMD) and `GraduatedRates` (smoothed data from Whittaker-Henderson) expose the same interface:

```
BOTH CLASSES HAVE:    .mx    .dx    .ex    .ages    .years

Lee-Carter fitter says: "Give me anything with .mx, .ages, .years."
                        Does not ask: "Are you raw or graduated?"
                        Does not check isinstance().
                        Just uses the attributes.
```

This is Python's duck typing philosophy: "If it walks like a duck and quacks like a duck, it is a duck." The downstream code does not care about the type -- only the interface.

```
WHY THIS IS GOOD:

  Option A (raw data, no smoothing):
    MortalityData --> Lee-Carter fitter
    Quick analysis, accepts whatever HMD gives you.

  Option B (graduated first):
    MortalityData --> GraduatedRates --> Lee-Carter fitter
    Smoother rates, better log-mortality surface.

  Same fitter code handles both.
  The user chooses the pipeline, not the fitter.
```

---

## 7. From HMD Files to Numpy Matrices: The Pipeline

```
STEP 1: READ
  Three text files per country.
  pd.read_csv() with whitespace separator, skip 2 header lines.
  Handle the "110+" age notation (strip the "+", parse as integer 110).
  Extract one sex column (Female, Male, or Total).
  Result: three DataFrames, each with (Year, Age, Value) columns.

STEP 2: FILTER YEARS
  Keep only years between year_min and year_max.
  Why? You rarely want all data going back to 1933.
  A 30-year window (1990-2020) is typical for Lee-Carter.

STEP 3: CAP AGES
  Collapse ages above age_max into one group.
  Deaths/exposures: sum.
  Rates: recompute as sum(deaths) / sum(exposures).

STEP 4: PIVOT
  Transform from long format (one row per age-year)
  to wide format (ages as rows, years as columns).
  This is the matrix shape Lee-Carter expects.

STEP 5: VALIDATE
  Check: no NaN, all rates positive, all exposures positive,
         recomputed d/L matches provided m_x.
  If anything fails, raise an informative error.

RESULT: MortalityData object with three aligned numpy matrices.
```

---

## 8. Interview-Ready Explanation

**"How do you go from raw mortality data to a model?"**

```
"We start with the Human Mortality Database, which provides
three things per country: death counts, exposure in person-years,
and central death rates -- where the rate is simply deaths divided
by exposure.

The data comes in long format: one row per age-year combination.
We filter to a relevant year window, say 1990 to 2020, and cap
ages at 100 because data above that age is too sparse to be reliable.
For the capped age group, we aggregate deaths and exposure, then
recompute the rate as the ratio -- you cannot average rates because
that ignores population weights.

After pivoting into matrix form -- ages down the rows, years across
the columns -- we validate: no missing values, all rates positive
(since Lee-Carter takes the log), and the rates are consistent with
deaths over exposure.

The result is a clean matrix of m_{x,t} values ready for Lee-Carter.
Optionally, we first pass it through Whittaker-Henderson graduation
to smooth out noise, especially at young ages where deaths are rare.
Both the raw and graduated data expose the same interface -- .mx,
.ages, .years -- so the Lee-Carter fitter accepts either one
without modification."
```

**Follow-up questions an interviewer might ask:**

1. "Why m_x instead of q_x?" -- Because m_x is directly observed. q_x requires an assumption (UDD or constant force). We model what we observe.

2. "Why not just use death counts?" -- Because 50,000 deaths means nothing without knowing the population at risk. Rates normalize by exposure.

3. "What if a death rate is zero?" -- Lee-Carter takes log(m_x), so zero rates break the model. This can happen at young ages in small populations. Graduation can fix this, or you adjust the age range.

4. "Why cap at 100 and not 110?" -- At very old ages, the data is so sparse that rates bounce around randomly. Pooling into an open-ended group gives more stable estimates. The exact cap age is a modeling choice -- 100 is conventional.

5. "What does '1x1' mean?" -- One-year age groups by one-year calendar periods. The finest granularity. HMD also offers 5x1, 5x5, etc., but 1x1 is what Lee-Carter needs.

---

## 9. Common Pitfalls

```
PITFALL 1: Averaging rates across ages
  WRONG:   mean(m_100, m_101, ..., m_110)
  RIGHT:   sum(deaths) / sum(exposure)
  Why:     Rates are ratios. You cannot average ratios without weighting.

PITFALL 2: Forgetting the "110+" notation
  HMD encodes the open age interval as "110+".
  If you parse this as a string without stripping "+", your
  age column becomes mixed type and pivoting breaks.

PITFALL 3: Using wrong sex column
  HMD files have Female, Male, and Total in the same file.
  Mixing them up means your model fits the wrong population.

PITFALL 4: Year range too wide
  Including years from 1933 mixes pre-antibiotic mortality
  with modern patterns. Lee-Carter assumes a single linear
  trend in k_t -- too wide a window violates this.

PITFALL 5: Not checking rate consistency
  If you accidentally load Deaths from USA and Exposures from Spain,
  the matrices will have the right shape but wrong values.
  The d/L consistency check catches this.
```
