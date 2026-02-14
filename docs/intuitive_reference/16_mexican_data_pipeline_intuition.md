# 16 -- Mexican Data Pipeline: Intuitive Reference

## The Two Data Worlds

The engine was originally built for HMD data: clean, standardized, English-language files from an international academic database. Then we needed to make it work with Mexican government data: INEGI (deaths) and CONAPO (population), which arrive in Spanish-language CSV files with a completely different format.

The design goal: make Mexican data look identical to HMD data from the engine's perspective. Once `from_inegi()` produces a `MortalityData` object, the rest of the pipeline cannot tell whether the data came from HMD or INEGI.

```
  HMD (international)                  INEGI/CONAPO (Mexican)
  ═══════════════════                  ═══════════════════════
  Mx_1x1_usa.txt ─────► from_hmd()    mock_inegi_deaths.csv ──┐
  Deaths_1x1_usa.txt ──►    |         mock_conapo_population ─┤
  Exposures_1x1_usa.txt►    |                                  ├──► from_inegi()
                             |                                  |
                             ▼                                  ▼
                    ┌─────────────────────────────────┐
                    │     MortalityData               │
                    │  .mx  (n_ages x n_years)        │
                    │  .dx  (n_ages x n_years)        │
                    │  .ex  (n_ages x n_years)        │
                    │  .ages, .years                   │
                    └──────────────┬──────────────────┘
                                   │
                        (identical interface)
                                   │
                                   ▼
                    GraduatedRates ──► LeeCarter ──► MortalityProjection
```

The key insight: `from_inegi()` is an **adapter**. It translates one data format into another, then the rest of the system works unchanged.

---

## Why m_x = D / P, Not Something Fancier

```
FORMULA:  m_{x,t} = D_{x,t} / P_{x,t}
INTUITION: How many people died at age x in year t,
           divided by how many people were alive at age x in year t.
ROLE:     Central death rate -- the raw material for Lee-Carter.
USE:      Lee-Carter takes log(m_x), so m_x must be strictly positive.
```

HMD provides "exposures" (person-years at risk), which is the theoretically correct denominator. INEGI does not provide person-years, so we use CONAPO mid-year population as a proxy. For national-level data with annual granularity, this approximation is standard practice.

The important thing: the engine does not care how `m_x` was computed. It only needs the three matrices (`mx`, `dx`, `ex`) to be aligned (same ages, same years) and internally consistent (`mx` approximately equals `dx / ex`).

---

## The Age Capping Problem

Real mortality data extends to age 110+, but at extreme ages the data gets noisy: tiny populations, large random fluctuations. Age capping solves this by collapsing all ages above a threshold into one group.

The trap: you cannot average death rates across ages. If age 95 has `m_x = 0.2` with 5000 people and age 110 has `m_x = 0.8` with 3 people, the average `(0.2 + 0.8) / 2 = 0.5` is wrong. The correct rate is `sum(deaths) / sum(population)`, which will be close to 0.2 because age 95 dominates the exposure.

```
  WRONG: m_capped = mean(m_95, m_96, ..., m_110)     ← ignores population weights
  RIGHT: m_capped = sum(D_95 + ... + D_110)           ← exposure-weighted
                    ─────────────────────────
                    sum(P_95 + ... + P_110)
```

---

## The Regulatory Table Path

Regulatory tables are a completely different animal from raw mortality data. They do not come as deaths and population. They come as `q_x` values: the official probability of death at each age, as decreed by the regulator.

```
  Raw data world:           Regulatory world:
  ════════════════          ═════════════════
  D_{x,t}, P_{x,t}         q_x (male), q_x (female)
       │                         │
       ▼                         ▼
  m_x = D/P                l_0 = 100,000
  (rate)                    l_{x+1} = l_x * (1 - q_x)
       │                         │
       ▼                         ▼
  Lee-Carter pipeline       LifeTable directly
       │                         │
       ▼                         ▼
  to_life_table()           (already a LifeTable)
       │                         │
       └──────────┬──────────────┘
                  ▼
         MortalityComparison
```

The conversion from `q_x` to `l_x` is a one-line recurrence:

```
FORMULA:  l_{x+1} = l_x * (1 - q_x)
INTUITION: Start with 100,000 people. At each age, remove q_x fraction.
           What's left are the survivors.
ROLE:     Converts a published regulatory column into a full LifeTable.
USE:      LifeTable.from_regulatory_table("cnsf_2000_i.csv", sex="male")
```

Terminal convention: `q_omega = 1.0`. Everyone alive at the last age dies. This is forced by the `LifeTable` constructor regardless of what the CSV says.

---

## Why Mock Data Exists

Real INEGI and CONAPO files are gitignored because:
- They are large (millions of rows for decades of data).
- They must be downloaded manually from government websites.
- CI/CD cannot depend on external downloads.

The mock data solves this: 4 small CSV files committed to the repo that follow the exact same format as the real files. Tests run against mock data, so `pytest` works on any machine without downloading anything.

The mock data uses Gompertz-Makeham mortality to produce realistic-looking patterns:

```
FORMULA:  mu(x) = A + B * c^x
INTUITION: Mortality has a constant background hazard (A)
           plus an exponentially increasing age component (B * c^x).
ROLE:     Standard actuarial model for generating synthetic mortality.
USE:      Creates mock data with realistic age-mortality curves.
```

Three additional features make the mock data look like real Mexican data:
1. **Infant spike** -- elevated mortality at age 0 (neonatal/perinatal deaths).
2. **Young-adult hump** -- peak at ages 15-25 (accidents, violence).
3. **Sex differential** -- male rates roughly 1.5x female rates.

---

## The Validation Module: Quality Control

After projecting mortality with Lee-Carter, the actuary must answer: "How far off are we from what the regulator assumes?"

`MortalityComparison` answers this with three metrics:

```
FORMULA:  ratio   = projected_qx / regulatory_qx
INTUITION: If ratio = 1.5, our projection predicts 50% more deaths
           than the regulatory table at that age.
ROLE:     Multiplicative comparison -- are we conservative or optimistic?
USE:      comp.qx_ratio()
```

```
FORMULA:  diff    = projected_qx - regulatory_qx
INTUITION: The absolute gap in mortality probability.
           Positive means we predict more deaths; negative means fewer.
ROLE:     Additive comparison -- how many extra deaths per person?
USE:      comp.qx_difference()
```

```
FORMULA:  RMSE    = sqrt(mean((proj_qx - reg_qx)^2))
INTUITION: Single number summarizing overall fit.
           Like a grade: lower is better.
ROLE:     Aggregate fit measure for regulatory reports.
USE:      comp.rmse(age_start=20, age_end=80)
```

The `age_start` and `age_end` parameters in `rmse()` let actuaries focus on the working-age range. Infant mortality and extreme old ages behave differently and can distort aggregate measures.

---

## The Sex Value Gotcha

This is the number one bug source when switching between data sources.

```
  ┌──────────────────────────────────────────────────────┐
  │  HMD calls it:    "Male",    "Female",    "Total"    │
  │  INEGI calls it:  "Hombres", "Mujeres",   "Total"   │
  │  Regulatory CSV:   qx_male,   qx_female              │
  └──────────────────────────────────────────────────────┘
```

If you pass `sex="Male"` to `from_inegi()`, you get a `ValueError` -- it expects `"Hombres"`. If you pass `sex="Hombres"` to `from_hmd()`, you get a `ValueError` -- it expects `"Male"`.

The `from_inegi()` method enforces this explicitly:

```python
if sex not in ("Hombres", "Mujeres", "Total"):
    raise ValueError(
        f"sex must be 'Hombres', 'Mujeres', or 'Total', got '{sex}'"
    )
```

The `from_regulatory_table()` method uses a different convention entirely: `sex="male"` or `sex="female"` (lowercase English), which maps to CSV columns `qx_male` and `qx_female`.

Three different conventions, three different entry points. The only reliable approach: read the docstring for whichever loader you are using.

---

## The Full Pipeline: INEGI to Insurance Premiums

```
  INEGI deaths ──┐
                 ├──► from_inegi() ──► MortalityData
  CONAPO pop ───┘                         │
                                          ▼
                                   GraduatedRates         (Whittaker-Henderson)
                                          │
                                          ▼
                                      LeeCarter.fit()     (SVD, a_x + b_x*k_t)
                                          │
                                          ▼
                                   MortalityProjection    (RWD on k_t)
                                          │
                                          ▼
                                    to_life_table()       (m_x -> q_x -> l_x)
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                     CommutationFunctions    MortalityComparison
                              │              (vs CNSF/EMSSA)
                              ▼
                     PremiumCalculator
                              │
                              ▼
                         Net Premium
```

Every arrow is a function call. Every box is a class. The pipeline is deterministic given the same input data and random seed (for stochastic projection).

The integration test `test_mock_inegi_full_pipeline` exercises this entire chain: it starts from mock INEGI CSV files and ends with a `MortalityComparison.summary()` dict containing RMSE and ratio statistics.

---

## What "Overlap Ages" Means

When comparing two LifeTables, they might not cover the same age range. A Lee-Carter projection starting at age 0 with `age_max=95` covers ages 0-95. A CNSF table covers ages 0-100. The comparison can only happen over ages both tables share.

```
  Projected:    [0 ──────────── 95]
  Regulatory:   [0 ──────────────── 100]
  Overlap:      [0 ──────────── 95]

  Projected:    [    20 ──── 80    ]
  Regulatory:   [0 ──────────────── 100]
  Overlap:      [    20 ──── 80    ]
```

The terminal age of the overlap is excluded from ratio and difference calculations because `q_omega = 1.0` in both tables, making the ratio trivially 1.0 and the difference trivially 0.0.

If the tables have no overlap (e.g., one covers 0-18, the other covers 65-100), `MortalityComparison` raises a `ValueError`. You cannot compare tables that do not share ages.

---

## Interpreting Results: What the Numbers Mean

| Scenario | mean_ratio | Interpretation |
|----------|:----------:|----------------|
| Projection matches regulatory table | ~1.0 | Model is well-calibrated |
| Projection higher than regulatory | > 1.0 | Model is more conservative (predicts more deaths) |
| Projection lower than regulatory | < 1.0 | Model is more optimistic (predicts fewer deaths) |

From the real Mexican data analysis:

- **CNSF 2000-I comparison**: mean ratio ~0.95. Projection slightly below regulatory table. The CNSF table was published in 2000, mortality has improved since then, so the projection naturally shows lower mortality.
- **EMSSA 2009 comparison**: ratios of 1.7-2.9 at ages 60+. EMSSA is fitted to IMSS-insured workers who have healthcare access. The general population has substantially higher mortality at older ages.

These are not errors -- they are real demographic differences between populations.
