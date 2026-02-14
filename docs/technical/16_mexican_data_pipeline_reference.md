# 16 -- Mexican Data Pipeline: Technical Reference

## Data Sources

| Source | Format | Columns | Description |
|--------|--------|---------|-------------|
| INEGI deaths | CSV | Anio, Edad, Sexo, Defunciones | Registered deaths by age, year, sex |
| CONAPO population | CSV | Anio, Edad, Sexo, Poblacion | Mid-year population estimates |
| CNSF regulatory | CSV | age, qx_male, qx_female | Official mortality tables (e.g., CNSF 2000-I) |
| EMSSA 2009 | CSV | age, qx_male, qx_female | Mexican social security experience table |

Sex labels differ by source:

| Source | Values | Language |
|--------|--------|----------|
| INEGI / CONAPO | `"Hombres"`, `"Mujeres"`, `"Total"` | Spanish |
| HMD | `"Male"`, `"Female"`, `"Total"` | English |
| Regulatory tables | `"male"`, `"female"` (column suffix) | English (lowercase) |

---

## API: MortalityData.from_inegi()

**File:** `backend/engine/a06_mortality_data.py`

```python
MortalityData.from_inegi(
    deaths_filepath: str,       # Path to INEGI deaths CSV
    population_filepath: str,   # Path to CONAPO population CSV
    sex: str = "Total",         # "Hombres", "Mujeres", or "Total"
    year_start: int = 1990,
    year_end: int = 2023,
    age_max: int = 100,
) -> MortalityData
```

### Processing Steps

1. Load INEGI deaths CSV, filter rows where `Sexo == sex` and `Anio` in `[year_start, year_end]`.
2. Load CONAPO population CSV, same filter.
3. Rename columns: `Anio -> Year`, `Edad -> Age`, `Defunciones -> Value` (deaths), `Poblacion -> Value` (population).
4. Cap ages: rows with `Age > age_max` get `Age = age_max`, then group by `(Year, Age)` and sum `Value`.
5. Merge deaths and population on `(Year, Age)`.
6. Validate: reject if any population cell is zero or negative (division by zero in step 7).
7. Compute central death rates: `m_{x,t} = D_{x,t} / P_{x,t}`.
8. Pivot three long-format DataFrames to matrices (ages as rows, years as columns).
9. Run `_validate()`: no NaN, all `m_x > 0`, all exposures positive, `d/L` consistency within 1%.

### Validation Checks (_validate)

| Check | Condition | Error if violated |
|-------|-----------|-------------------|
| Shape consistency | `mx.shape == dx.shape == ex.shape` | AssertionError |
| No NaN | `np.isnan(arr).sum() == 0` for each matrix | ValueError with count |
| Positive rates | `mx > 0` everywhere | ValueError with sample (age, year) locations |
| Positive exposure | `ex > 0` everywhere | ValueError |
| d/L consistency | `abs(mx - dx/ex) / mx < 0.01` | ValueError with max relative error |

### Returns

`MortalityData` instance with attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `country` | `str` | Always `"Mexico"` |
| `sex` | `str` | The sex filter used (`"Hombres"`, `"Mujeres"`, `"Total"`) |
| `ages` | `np.ndarray` | Integer ages, shape `(n_ages,)` |
| `years` | `np.ndarray` | Integer years, shape `(n_years,)` |
| `mx` | `np.ndarray` | Central death rates, shape `(n_ages, n_years)` |
| `dx` | `np.ndarray` | Death counts, shape `(n_ages, n_years)` |
| `ex` | `np.ndarray` | Population (exposure proxy), shape `(n_ages, n_years)` |
| `n_ages` | `int` | `len(ages)` |
| `n_years` | `int` | `len(years)` |
| `shape` | `tuple` | `(n_ages, n_years)` |

---

## API: LifeTable.from_regulatory_table()

**File:** `backend/engine/a01_life_table.py`

```python
LifeTable.from_regulatory_table(
    filepath: str,           # Path to CSV with (age, qx_male, qx_female)
    sex: str = "male",       # "male" or "female"
    radix: float = 100_000.0,
) -> LifeTable
```

### Processing Steps

1. Read CSV. Select column `qx_{sex}` (i.e., `qx_male` or `qx_female`).
2. Build `l_x` from `q_x` via recurrence:
   ```
   l_0 = radix
   l_{x+1} = l_x * (1 - q_x)     for x = 0, 1, ..., omega-1
   ```
3. Construct `LifeTable(ages, l_x_values)`.
4. `_compute_derivatives()` derives `d_x`, `q_x`, `p_x` from `l_x`.
5. Terminal age forced: `q_omega = 1.0`, `d_omega = l_omega`, `p_omega = 0.0`.

### Key Detail

The CSV provides `q_x` for all ages including omega. But only `q_x` for ages `0` through `omega-1` are used to build `l_x`. The final `q_omega` is forced to 1.0 by the `LifeTable.__init__` constructor regardless of the CSV value.

---

## API: MortalityComparison (a10_validation.py)

**File:** `backend/engine/a10_validation.py`

```python
MortalityComparison(
    projected: LifeTable,    # From Lee-Carter projection (or any source)
    regulatory: LifeTable,   # From CNSF/EMSSA table
    name: str = "",          # Label for reports
)
```

### Constructor Logic

1. Compute `overlap_ages = sorted(set(projected.ages) & set(regulatory.ages))`.
2. Raise `ValueError` if fewer than 2 overlapping ages.

### Methods

| Method | Signature | Returns | Formula |
|--------|-----------|---------|---------|
| `qx_ratio()` | `() -> np.ndarray` | Array of ratios | `projected_q_x / regulatory_q_x` |
| `qx_difference()` | `() -> np.ndarray` | Array of differences | `projected_q_x - regulatory_q_x` |
| `rmse()` | `(age_start=20, age_end=80) -> float` | Scalar | `sqrt(mean((proj_qx - reg_qx)^2))` |
| `summary()` | `() -> dict` | Dict | See below |

All methods **exclude the terminal overlap age** (where both `q_x = 1.0`), except `rmse()` which filters by `[age_start, age_end]`.

### summary() Return Keys

```python
{
    "name": str,          # Comparison label
    "rmse": float,        # RMSE over default range [20, 80]
    "max_ratio": float,   # max(projected_qx / regulatory_qx)
    "min_ratio": float,   # min(projected_qx / regulatory_qx)
    "mean_ratio": float,  # mean(projected_qx / regulatory_qx)
    "n_ages": int,        # Number of overlapping ages
}
```

### Interpretation

| Metric | Value | Meaning |
|--------|-------|---------|
| `mean_ratio` | `~1.0` | Projection agrees with regulatory table on average |
| `mean_ratio` | `> 1.0` | Projection assumes higher mortality (more conservative) |
| `mean_ratio` | `< 1.0` | Projection assumes lower mortality (optimistic relative to regulatory) |
| `rmse` | low | Good quantitative fit to regulatory benchmark |
| `qx_difference > 0` | at age x | Projection has higher mortality at that age |

---

## Mock Data Specification

Generated with Gompertz-Makeham baseline: `mu(x) = A + B * c^x`

With modifications:
- Infant spike: elevated mortality at age 0
- Young-adult hump: accident/violence peak at ages 15-25
- Sex differential: male rates approximately 1.5x female rates
- Total derived from combined male/female counts

### File Inventory

**Location:** `backend/data/mock/`

| File | Data rows | Header | Years | Ages | Sex values |
|------|-----------|--------|-------|------|------------|
| `mock_inegi_deaths.csv` | 3,333 | `Anio,Edad,Sexo,Defunciones` | 2000-2010 | 0-100 | Hombres, Mujeres, Total |
| `mock_conapo_population.csv` | 3,333 | `Anio,Edad,Sexo,Poblacion` | 2000-2010 | 0-100 | Hombres, Mujeres, Total |
| `mock_cnsf_2000_i.csv` | 101 | `age,qx_male,qx_female` | -- | 0-100 | (columns) |
| `mock_emssa_2009.csv` | 101 | `age,qx_male,qx_female` | -- | 0-100 | (columns) |

Row count formula for INEGI/CONAPO: `101 ages * 3 sexes * 11 years = 3,333`.

### Sample Values

```
# mock_inegi_deaths.csv
Anio,Edad,Sexo,Defunciones
2000,0,Hombres,20615
2000,0,Mujeres,17249
2000,0,Total,37864

# mock_conapo_population.csv
Anio,Edad,Sexo,Poblacion
2000,0,Hombres,1312876
2000,0,Mujeres,1340815
2000,0,Total,2653691

# mock_cnsf_2000_i.csv
age,qx_male,qx_female
0,0.01550000,0.01280000
1,0.00696460,0.00575141

# mock_emssa_2009.csv
age,qx_male,qx_female
0,0.01400000,0.01150000
1,0.00629061,0.00516728
```

CNSF q_0 (male) = 0.0155 > EMSSA q_0 (male) = 0.0140. General population mortality exceeds social security population mortality.

---

## Internal Helper Functions (a06_mortality_data.py)

| Function | Purpose |
|----------|---------|
| `_load_inegi_deaths(filepath, sex, year_start, year_end)` | Load + filter INEGI CSV, rename columns to `Year, Age, Value` |
| `_load_conapo_population(filepath, sex, year_start, year_end)` | Load + filter CONAPO CSV, rename columns to `Year, Age, Value` |
| `_cap_ages_sum(df, age_max)` | For deaths/exposure: set `Age = age_max` where `Age > age_max`, then groupby sum |
| `_cap_ages(mx_df, dx_df, ex_df, age_max)` | For rates (HMD path only): recompute capped `m_x = sum(D) / sum(L)` |
| `_validate(mx, dx, ex, ages, years, country, sex)` | Five consistency checks (see Validation table above) |

Age capping for `from_inegi()` uses `_cap_ages_sum` on both deaths and population, then recomputes `m_x = D/P` from the capped values. This gives the correct exposure-weighted rate for the open age group.

---

## Test Coverage

| Test file | Test count | What it validates |
|-----------|:----------:|-------------------|
| `test_inegi_data.py` | 10 | `from_inegi()` loading, `m_x = D/P` correctness, matrix shapes, age capping, year filtering, sex filtering, positive rates, bad data rejection, duck typing interface, graduation integration |
| `test_regulatory_tables.py` | 8 | `from_regulatory_table()` loading (CNSF + EMSSA), `l_x` recurrence from `q_x`, radix handling, terminal `q_omega = 1.0`, `l_x` monotonicity, sex selection, commutation integration, invalid file error |
| `test_validation.py` | 8 | Identical-table identity (ratio=1, RMSE=0), known 2x ratio, hand-computed RMSE, difference sign, age range filtering, summary keys, disjoint-age error |
| `test_integration_mexican.py` | 4 | Full pipeline INEGI->Grad->LC->Proj->Compare, premium pricing from projected table, CNSF-vs-EMSSA ratio, regulatory tables into commutations |

**Total: 30 new tests** across 4 test files.

---

## File Locations

| File | Role |
|------|------|
| `backend/engine/a06_mortality_data.py` | `from_inegi()` classmethod (lines 215-312) |
| `backend/engine/a01_life_table.py` | `from_regulatory_table()` classmethod (lines 128-175) |
| `backend/engine/a10_validation.py` | `MortalityComparison` class (full module) |
| `backend/data/mock/` | 4 synthetic CSV files (committed to repo) |
| `backend/data/inegi/` | Real INEGI data (gitignored, see `DOWNLOAD_GUIDE.md`) |
| `backend/data/conapo/` | Real CONAPO data (gitignored, see `DOWNLOAD_GUIDE.md`) |
| `backend/data/cnsf/` | Real CNSF/EMSSA tables (gitignored, see `DOWNLOAD_GUIDE.md`) |
| `backend/tests/test_inegi_data.py` | INEGI loader tests (10 tests) |
| `backend/tests/test_regulatory_tables.py` | Regulatory table tests (8 tests) |
| `backend/tests/test_validation.py` | MortalityComparison tests (8 tests) |
| `backend/tests/test_integration_mexican.py` | End-to-end pipeline tests (4 tests) |

---

## Age Capping Detail

When `age_max = 95` and raw data has ages 0-110:

```
Before capping:
  age 94: D=200, P=5000  -> m_94 = 0.040
  age 95: D=180, P=4000  -> m_95 = 0.045
  age 96: D=150, P=3000  -> m_96 = 0.050
  ...
  age 110: D=5,  P=20    -> m_110 = 0.250

After capping:
  age 94: D=200, P=5000  -> m_94 = 0.040   (unchanged)
  age 95: D=sum(D for ages 95-110), P=sum(P for ages 95-110)
          -> m_95 = total_D / total_P       (exposure-weighted)
```

Cannot average rates directly because `mean(m_95, m_96, ..., m_110)` ignores population weights. Must sum numerator and denominator separately, then divide.

---

## Conversion Chain: q_x -> l_x -> Full LifeTable

```
Input:  q_x = [q_0, q_1, ..., q_omega]     (from CSV)
Radix:  l_0 = 100,000

Step 1: l_{x+1} = l_x * (1 - q_x)
        l_1 = 100000 * (1 - 0.0155) = 98450.0
        l_2 = 98450.0 * (1 - 0.006965) = 97764.2
        ...

Step 2: LifeTable(ages, l_x_values) constructor calls _compute_derivatives()
        d_x = l_x - l_{x+1}
        q_x = d_x / l_x          (recomputed, matches input)
        p_x = 1 - q_x

Step 3: Terminal: d_omega = l_omega, q_omega = 1.0, p_omega = 0.0
```
