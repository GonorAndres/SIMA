# Mortality Data & HMD Loading -- Technical Reference

**Source Module:** `backend/engine/a06_mortality_data.py`

---

## 1. The Human Mortality Database (HMD)

The Human Mortality Database (www.mortality.org) is a collaborative project of the Max Planck Institute for Demographic Research, the University of California Berkeley, and the French Institute for Demographic Studies. It provides detailed, quality-controlled mortality data for national populations.

HMD supplies three types of files per country, each in **1x1 format** (1-year age groups x 1-year calendar periods):

| File | Content | Symbol | Unit |
|:-----|:--------|:-------|:-----|
| `Mx_1x1_{country}.txt` | Central death rates | $m_{x,t}$ | deaths per person-year |
| `Deaths_1x1_{country}.txt` | Death counts | $d_{x,t}$ | count |
| `Exposures_1x1_{country}.txt` | Person-years of exposure | $L_{x,t}$ | person-years |

**"1x1" notation:** The first "1" means single-year age groups (age 0, age 1, ..., not 5-year groups). The second "1" means single-year calendar periods (1990, 1991, ..., not 5-year intervals). This is the finest granularity HMD provides.

### 1.1 HMD File Format

All three files share the same layout:

```
            Human Mortality Database
[header line 2 -- file description]
  Year   Age   Female   Male   Total
  1933    0    0.06339  0.07620  0.06990
  1933    1    0.00605  0.00677  0.00641
  ...
  1933   110+  1.00000  1.00000  1.00000
```

Key format details:
- **2 header lines** (skipped during parsing)
- **Whitespace-separated columns** (not comma-separated)
- **Age column** contains `110+` for the open age interval (ages 110 and above)
- **Missing values** encoded as `.` (period), parsed as NaN
- **Three sex columns** per row: Female, Male, Total

---

## 2. Core Definition: Central Death Rate

$$
m_{x,t} = \frac{d_{x,t}}{L_{x,t}}
$$

| Symbol | Meaning |
|:-------|:--------|
| $m_{x,t}$ | Central death rate at age $x$ in year $t$ |
| $d_{x,t}$ | Observed death count at age $x$ in year $t$ |
| $L_{x,t}$ | Person-years of exposure at age $x$ in year $t$ |

This is a **rate**, not a probability. It can exceed 1.0 in extreme cases (very old ages, short observation windows). The conversion to probability of death is:

$$
q_{x,t} = 1 - \exp(-m_{x,t})
$$

under the constant force of mortality assumption.

---

## 3. The `MortalityData` Class

### 3.1 Constructor

```python
MortalityData(
    country: str,        # e.g., 'usa', 'spain'
    sex: str,            # 'Female', 'Male', or 'Total'
    ages: np.ndarray,    # 1D array of integer ages (row labels)
    years: np.ndarray,   # 1D array of integer years (column labels)
    mx: np.ndarray,      # 2D (n_ages x n_years) death rates
    dx: np.ndarray,      # 2D (n_ages x n_years) death counts
    ex: np.ndarray,      # 2D (n_ages x n_years) exposures
    download_date: str = "",
)
```

### 3.2 Class Method: `from_hmd()`

The primary entry point. Loads HMD text files and constructs validated matrices.

```python
MortalityData.from_hmd(
    data_dir: str,       # Path containing country subfolders
    country: str,        # Subfolder name (e.g., 'usa')
    sex: str = "Male",   # Which sex column to extract
    year_min: int = 1990,
    year_max: int = 2023,
    age_max: int = 100,
    download_date: str = "",
)
```

**Expected file structure:**
```
data_dir/
  usa/
    Mx_1x1_usa.txt
    Deaths_1x1_usa.txt
    Exposures_1x1_usa.txt
  spain/
    Mx_1x1_spain.txt
    Deaths_1x1_spain.txt
    Exposures_1x1_spain.txt
```

### 3.3 Properties

| Property | Return Type | Description |
|:---------|:-----------|:------------|
| `n_ages` | `int` | Number of age groups (rows) |
| `n_years` | `int` | Number of calendar years (columns) |
| `shape` | `Tuple[int, int]` | `(n_ages, n_years)` |

### 3.4 Accessor Methods

| Method | Signature | Returns |
|:-------|:----------|:--------|
| `get_mx(age, year)` | `(int, int) -> float` | Single death rate for given age and year |
| `year_slice(year)` | `(int) -> np.ndarray` | All ages' death rates for one year (column vector) |
| `age_slice(age)` | `(int) -> np.ndarray` | One age's death rates across all years (row vector) |
| `summary()` | `() -> Dict` | Dictionary of summary statistics |

---

## 4. Matrix Construction Pipeline

The loading pipeline transforms HMD long-format text files into aligned numpy matrices:

```
HMD .txt files (long format)
    |
    |  _load_hmd_file(): pd.read_csv, extract one sex column
    v
pandas DataFrames (Year, Age, Value)
    |
    |  Year filtering: year_min <= Year <= year_max
    v
Filtered DataFrames
    |
    |  Age capping: aggregate ages > age_max
    v
Capped DataFrames
    |
    |  df.pivot(index="Age", columns="Year", values="Value")
    v
pandas pivot tables (ages as rows, years as columns)
    |
    |  .values.astype(float)
    v
numpy 2D arrays: mx (n_ages x n_years), dx, ex
    |
    |  _validate(): shape, NaN, positivity, consistency
    v
MortalityData object
```

---

## 5. Age Capping

Ages above `age_max` are collapsed into a single open-ended group at `age_max`. The capping strategy differs by data type.

### 5.1 Death Counts and Exposures (`_cap_ages_sum`)

Deaths and exposures are **summed** across all ages $\geq$ `age_max`:

$$
d_{\text{age\_max}+, t} = \sum_{x \geq \text{age\_max}} d_{x,t}
$$

$$
L_{\text{age\_max}+, t} = \sum_{x \geq \text{age\_max}} L_{x,t}
$$

### 5.2 Death Rates (`_cap_ages`)

Death rates **cannot be averaged** across ages because this would ignore population weights. Instead, the rate is **recomputed** from the aggregated counts:

$$
m_{\text{age\_max}+, t} = \frac{\sum_{x \geq \text{age\_max}} d_{x,t}}{\sum_{x \geq \text{age\_max}} L_{x,t}}
$$

This is the exposure-weighted aggregate rate -- the only correct way to combine rates across heterogeneous groups.

**Why not average the rates?** Consider two ages: age 100 with $m_{100} = 0.30$ and 10,000 exposed, and age 110 with $m_{110} = 0.80$ and 5 exposed. A simple average $(0.30 + 0.80)/2 = 0.55$ drastically overweights age 110. The exposure-weighted rate reflects the actual mortality experience of the combined group.

---

## 6. Data Validation (`_validate`)

After matrix construction, five validation checks are performed:

| Check | Condition | Reason |
|:------|:----------|:-------|
| Shape consistency | `mx.shape == dx.shape == ex.shape` | All three matrices must be aligned |
| No NaN values | `np.isnan(arr).sum() == 0` for all matrices | Missing values break Lee-Carter's log transform |
| Positive rates | `mx > 0` everywhere | `ln(m_x)` is undefined for $m_x \leq 0$ |
| Positive exposures | `ex > 0` everywhere | Zero exposure means no observation |
| Rate consistency | $\|m_x - d_x/L_x\| / m_x < 0.01$ | Recomputed rates must match provided rates within 1% |

The rate consistency check guards against file mismatches (e.g., loading deaths from one country and exposure from another).

---

## 7. Duck Typing Interface

`MortalityData` exposes the same core attributes as `GraduatedRates` (from `a07_graduation.py`):

| Attribute | Type | Shared by Both |
|:----------|:-----|:---------------|
| `.mx` | `np.ndarray` (2D) | Yes |
| `.dx` | `np.ndarray` (2D) | Yes |
| `.ex` | `np.ndarray` (2D) | Yes |
| `.ages` | `np.ndarray` (1D) | Yes |
| `.years` | `np.ndarray` (1D) | Yes |

This duck typing means that downstream modules (`a08_lee_carter.py`, `a09_projection.py`) can accept **either** raw or graduated data without type checking. The Lee-Carter fitter does not care whether the rates were smoothed -- it only needs `.mx`, `.ages`, and `.years`.

```
MortalityData  ──>  Lee-Carter fitter  (via .mx, .ages, .years)
                        ^
GraduatedRates  ──>     |
```

---

## 8. Connection to Downstream Modules

| Downstream Module | What It Uses | Why |
|:------------------|:-------------|:----|
| `a07_graduation.py` | Entire `MortalityData` object | Smooths `.mx` via Whittaker-Henderson; passes through `.dx`, `.ex` unchanged |
| `a08_lee_carter.py` | `.mx`, `.ages`, `.years` | Takes $\ln(m_{x,t})$ for SVD decomposition |
| `a09_projection.py` | Lee-Carter parameters (indirect) | Projects $k_t$ forward; uses `to_life_table()` bridge to actuarial engine |

---

## 9. Internal Helper Functions

| Function | Signature | Purpose |
|:---------|:----------|:--------|
| `_load_hmd_file(filepath, sex)` | `(Path, str) -> DataFrame` | Parse one HMD text file, extract one sex column, handle `110+` age notation |
| `_cap_ages_sum(df, age_max)` | `(DataFrame, int) -> DataFrame` | Sum values for ages > `age_max` into `age_max` group (for deaths, exposures) |
| `_cap_ages(mx_df, dx_df, ex_df, age_max)` | `(DataFrame, DataFrame, DataFrame, int) -> DataFrame` | Recompute $m_x$ for capped group as $d/L$ (for rates) |
| `_validate(mx, dx, ex, ages, years, country, sex)` | `(...) -> None` | Run all five validation checks, raise `ValueError` on failure |

---

## 10. Typical Usage

```python
from backend.engine.a06_mortality_data import MortalityData

# Load USA male data, 1990-2020, ages 0-100
data = MortalityData.from_hmd(
    data_dir="backend/data/hmd",
    country="usa",
    sex="Male",
    year_min=1990,
    year_max=2020,
    age_max=100,
)

# Inspect
print(data.shape)         # (101, 31) -- 101 ages x 31 years
print(data.summary())

# Access individual rate
rate = data.get_mx(50, 2000)

# Feed to graduation or Lee-Carter
from backend.engine.a07_graduation import GraduatedRates
graduated = GraduatedRates(data, lambda_param=100)
```

---

## 11. Test Coverage

Tests in `backend/tests/test_mortality_data.py` verify:

| Test | What It Checks |
|:-----|:---------------|
| Matrix shape | 101 ages x 31 years for (0-100, 1990-2020) |
| Shape property | `.shape`, `.n_ages`, `.n_years` consistency |
| Age range | Ages run consecutively 0 to 100 |
| Year range | Years run consecutively 1990 to 2020 |
| No NaN | All three matrices are complete |
| Positive rates | All $m_x > 0$ |
| Positive exposures | All $L_x > 0$ |
| Rate consistency | Recomputed $d/L$ matches $m_x$ within 1% |
| Age capping | Max age is exactly `age_max` |
| Accessors | `get_mx`, `year_slice`, `age_slice` return correct types and sizes |
| Error handling | Invalid sex raises `ValueError` |
| Multi-country | Spain loads successfully with same structure |
| Summary | `summary()` returns well-formed dictionary |
