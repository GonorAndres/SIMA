# Architecture and Integration: Technical Reference

**Module:** All engine modules (`backend/engine/a01_life_table.py` through `a09_projection.py`)

---

## 1. System Overview

The SIMA actuarial engine consists of 9 Python modules organized into two pipelines that converge through a bridge method. The system takes raw mortality data from the Human Mortality Database, processes it through statistical estimation, and produces actuarially meaningful outputs (life tables, premiums, reserves).

The architecture enforces a strict **unidirectional data flow**: data enters through `a06`, transforms forward through each module, and reaches its final actuarial form in `a04`/`a05`. No module reaches backward to an earlier stage.

---

## 2. The Two Pipelines

### 2.1. Empirical Pipeline (Data-Driven)

Transforms raw mortality observations into a fitted and projected mortality model.

```
a06_mortality_data  -->  a07_graduation  -->  a08_lee_carter  -->  a09_projection
     (raw HMD)          (Whittaker-Henderson)    (SVD fitting)     (RWD forecast)
```

| Stage | Module | Input | Output | Key Operation |
|:------|:-------|:------|:-------|:--------------|
| Load | a06 | HMD text files | MortalityData (mx, dx, ex matrices) | Parse, pivot, validate |
| Smooth | a07 | MortalityData | GraduatedRates (smoothed mx) | Penalized least squares in log-space |
| Fit | a08 | MortalityData or GraduatedRates | LeeCarter (ax, bx, kt) | SVD + Brent root-finding |
| Project | a09 | LeeCarter | MortalityProjection (future kt, future mx) | Random Walk with Drift |

### 2.2. Theoretical Pipeline (Actuarial Calculations)

Transforms a life table into insurance pricing and reserving outputs.

```
a01_life_table  -->  a02_commutation  -->  a03_actuarial_values
                                       |-> a04_premiums (uses a03 internally)
                                       |-> a05_reserves (uses a03 + a04 internally)
```

| Stage | Module | Input | Output | Key Operation |
|:------|:-------|:------|:-------|:--------------|
| Foundation | a01 | ages + l_x values | LifeTable (l_x, d_x, q_x, p_x) | Derive mortality primitives |
| Discount | a02 | LifeTable + interest_rate | CommutationFunctions (D, N, C, M) | v^x weighting + backward recursion |
| Values | a03 | CommutationFunctions | ActuarialValues (A_x, a_x, nE_x) | Ratio formulas M/D, N/D |
| Pricing | a04 | CommutationFunctions | PremiumCalculator (net premiums) | Equivalence principle |
| Reserves | a05 | CommutationFunctions | ReserveCalculator (prospective reserves) | tV = SA*A_{x+t} - P*a_{x+t} |

### 2.3. The Bridge: `a09.to_life_table()`

The `MortalityProjection.to_life_table()` method is the single connection point between the two pipelines. It converts projected central death rates into a `LifeTable` object:

```
Projected m_x  --(1 - exp(-m_x))-->  q_x  --(l_{x+1} = l_x*(1-q_x))-->  l_x  -->  LifeTable
```

This is the architectural keystone: without it, the empirical pipeline produces statistical parameters with no actuarial utility, and the theoretical pipeline requires a life table with no connection to real data.

---

## 3. Module-by-Module Summary

### a01_life_table.py

- **Class:** `LifeTable`
- **Input:** `ages: List[int]`, `l_x_values: List[float]`
- **Output:** Dicts `l_x`, `d_x`, `q_x`, `p_x` keyed by age
- **Responsibility:** Derive mortality primitives from the survivor function
- **Key formulas:** `d_x = l_x - l_{x+1}`, `q_x = d_x / l_x`, `p_x = 1 - q_x`
- **Imports from:** nothing (leaf node)
- **Alternative constructor:** `from_csv(filepath)` for loading from CSV files
- **Validation:** `sum(d_x) = l_0`, `q_omega = 1.0`, all rates in [0, 1]

### a02_commutation.py

- **Class:** `CommutationFunctions`
- **Input:** `LifeTable`, `interest_rate: float`
- **Output:** Dicts `D`, `N`, `C`, `M` keyed by age
- **Responsibility:** Pre-compute discounted survival/death values
- **Key formulas:** `D_x = v^(x-min_age) * l_x`, `N_x = D_x + N_{x+1}` (backward recursion)
- **Imports from:** `a01_life_table.LifeTable`
- **Computational strategy:** O(n) backward recursion instead of O(n^2) forward summation
- **Normalization:** Exponent normalized to `x - min_age` to prevent numerical underflow

### a03_actuarial_values.py

- **Class:** `ActuarialValues`
- **Input:** `CommutationFunctions`
- **Output:** Scalar actuarial present values for given age/term
- **Responsibility:** Compute insurance and annuity APVs as commutation ratios
- **Key formulas:** `A_x = M_x/D_x`, `a_due_x = N_x/D_x`, `nE_x = D_{x+n}/D_x`
- **Imports from:** `a02_commutation.CommutationFunctions`
- **Design note:** All methods are pure ratio computations -- no loops or state mutation

### a04_premiums.py

- **Class:** `PremiumCalculator`
- **Input:** `CommutationFunctions`
- **Output:** Net annual premiums for various insurance products
- **Responsibility:** Apply equivalence principle to compute net premiums
- **Key formulas:** `P_whole = SA * M_x / N_x`, `P_term = SA * (M_x - M_{x+n}) / (N_x - N_{x+n})`
- **Imports from:** `a02_commutation.CommutationFunctions`, `a03_actuarial_values.ActuarialValues`
- **Internal dependency:** Creates `ActuarialValues` instance internally for single premium calculations
- **Products:** whole life, term, endowment, pure endowment, limited-pay whole life

### a05_reserves.py

- **Class:** `ReserveCalculator`
- **Input:** `CommutationFunctions`
- **Output:** Policy reserves at any duration t
- **Responsibility:** Compute prospective reserves using net premium method
- **Key formula:** `tV = SA * A_{x+t} - P * a_{x+t}`
- **Imports from:** `a02_commutation`, `a03_actuarial_values`, `a04_premiums`
- **Internal dependencies:** Creates both `ActuarialValues` and `PremiumCalculator` internally
- **LISF compliance:** Implements net premium method as required by Mexican regulations (Art. 217)

### a06_mortality_data.py

- **Class:** `MortalityData`
- **Input:** HMD text files (Mx, Deaths, Exposures) via `from_hmd()` class method
- **Output:** Three aligned numpy matrices: `mx`, `dx`, `ex` (ages x years)
- **Responsibility:** Load, parse, validate, and structure HMD data
- **Key operations:** Age capping (exposure-weighted aggregation), year subsetting, sex selection
- **Imports from:** nothing engine-internal (uses numpy, pandas)
- **Validation:** No NaN, positive rates, positive exposures, `d/L approx m_x` within 1%
- **Helper functions:** `_load_hmd_file()`, `_cap_ages()`, `_cap_ages_sum()`, `_validate()`

### a07_graduation.py

- **Class:** `GraduatedRates`
- **Input:** `MortalityData`, `lambda_param`, `diff_order`
- **Output:** Smoothed mx matrix (same shape as input), plus original dx, ex
- **Responsibility:** Whittaker-Henderson smoothing of mortality rates
- **Key formula:** `z = (W + lambda * D'D)^{-1} * W * m` (solved per year column)
- **Imports from:** `a06_mortality_data.MortalityData`
- **Design note:** Works in log-space to guarantee positivity of graduated rates
- **Diagnostics:** `residuals()`, `roughness()`, `validate()`

### a08_lee_carter.py

- **Class:** `LeeCarter`
- **Input:** `MortalityData` or `GraduatedRates` (duck typed)
- **Output:** Fitted parameters `ax`, `bx`, `kt`
- **Responsibility:** Lee-Carter (1992) model fitting via SVD
- **Key formula:** `ln(m_{x,t}) = a_x + b_x * k_t`
- **Imports from:** `a06_mortality_data.MortalityData` (type hint only; accepts duck types)
- **Fitting steps:** row means -> SVD -> identifiability constraints -> k_t re-estimation
- **Constraints:** `sum(b_x) = 1`, `sum(k_t) = 0`
- **Re-estimation:** Brent's method (bracket [-500, 500]) to match observed total deaths

### a09_projection.py

- **Class:** `MortalityProjection`
- **Input:** `LeeCarter`, `horizon`, `n_simulations`
- **Output:** Central and stochastic k_t projections, projected mx surfaces, LifeTable objects
- **Responsibility:** Project mortality forward and bridge to the theoretical pipeline
- **Key formula:** `k_{T+h} = k_T + h*drift + sigma*cumsum(Z)`
- **Imports from:** `a08_lee_carter.LeeCarter`, `a01_life_table.LifeTable`
- **Bridge method:** `to_life_table(year)` converts projected m_x to a LifeTable
- **CI method:** `to_life_table_with_ci()` returns (central, optimistic, pessimistic) triple

---

## 4. Interface Contracts and Duck Typing

The architecture uses **structural subtyping** (duck typing) at a critical junction: `LeeCarter.fit()` accepts any object that exposes the following interface:

```
Required attributes:
    .mx    : np.ndarray  (n_ages x n_years)  -- central death rates
    .dx    : np.ndarray  (n_ages x n_years)  -- death counts
    .ex    : np.ndarray  (n_ages x n_years)  -- exposures
    .ages  : np.ndarray  (n_ages,)           -- age labels
    .years : np.ndarray  (n_years,)          -- year labels
```

Both `MortalityData` and `GraduatedRates` satisfy this contract. This means:

```python
# Both work identically:
lc = LeeCarter.fit(raw_data)        # a06 -> a08 directly
lc = LeeCarter.fit(graduated_data)  # a06 -> a07 -> a08
```

No formal abstract base class or Protocol is defined. The contract is enforced by tests rather than type annotations.

---

## 5. Data Flow Diagram

```
                    EMPIRICAL PIPELINE
                    ==================

  HMD Text Files (Mx_1x1, Deaths_1x1, Exposures_1x1)
        |
        v
  +------------------+
  | a06: MortalityData|   mx, dx, ex matrices (ages x years)
  +------------------+
        |
        v  (optional)
  +------------------+
  | a07: GraduatedRates|  smoothed mx (same shape)
  +------------------+
        |
        v
  +------------------+
  | a08: LeeCarter    |   ax (1D), bx (1D), kt (1D)
  +------------------+
        |
        v
  +------------------+
  | a09: Projection   |   kt_central, kt_simulated, projected mx
  +------------------+
        |
        |  to_life_table()     <-- THE BRIDGE
        v
  ============================
        |
        v
                    THEORETICAL PIPELINE
                    ====================

  +------------------+
  | a01: LifeTable    |   l_x, d_x, q_x, p_x (dicts by age)
  +------------------+
        |
        v  + interest_rate
  +------------------+
  | a02: Commutation  |   D, N, C, M (dicts by age)
  +------------------+
        |
        +----+----+
        |         |
        v         v
  +----------+ +----------+
  | a03: APVs | | a04: Prem |
  | A_x, a_x | | P = SA*r |
  +----------+ +----------+
                    |
                    v
              +----------+
              | a05: Res  |
              | tV = ...  |
              +----------+
```

---

## 6. Import Dependencies

Each module's direct imports from within the engine:

| Module | Imports From |
|:-------|:-------------|
| a01_life_table | (none) |
| a02_commutation | a01_life_table |
| a03_actuarial_values | a02_commutation |
| a04_premiums | a02_commutation, a03_actuarial_values |
| a05_reserves | a02_commutation, a03_actuarial_values, a04_premiums |
| a06_mortality_data | (none -- external only: numpy, pandas) |
| a07_graduation | a06_mortality_data |
| a08_lee_carter | a06_mortality_data (type hint), a07_graduation (lazy import) |
| a09_projection | a08_lee_carter, a01_life_table |

Note that `a09_projection` is the only module that imports from both pipelines -- it imports `LeeCarter` from the empirical side and `LifeTable` from the theoretical side.

The `a08_lee_carter` module uses a **lazy import** for `a07_graduation`: the `GraduatedRates` import appears inside the `fit_from_hmd()` method body, not at module level. This avoids a circular dependency risk and makes graduation truly optional.

---

## 7. Design Decisions

### 7.1. Why Two Separate Pipelines?

The empirical and theoretical pipelines address fundamentally different questions:

- **Empirical:** "What will mortality look like in the future?" (statistical estimation)
- **Theoretical:** "Given a mortality assumption, what should we charge/reserve?" (actuarial calculation)

Separating them allows each pipeline to evolve independently. The theoretical pipeline can operate with any life table source (published tables, regulatory tables like EMSSA-2009, or Lee-Carter projections), while the empirical pipeline can feed into non-actuarial consumers (demographic studies, public health analysis).

### 7.2. Why Dict-based LifeTable vs. Array-based MortalityData?

The theoretical pipeline uses `Dict[int, float]` keyed by age because:
- Actuarial formulas reference specific ages: `M_x`, `D_{x+n}`, `N_{x+t}`
- Age lookups must be O(1) for premium and reserve calculations
- The LifeTable is 1-dimensional (single period)

The empirical pipeline uses numpy arrays because:
- Data is 2-dimensional (ages x years)
- Linear algebra operations (SVD, matrix multiplication) require array form
- Vectorized operations are essential for performance

### 7.3. Why Single Responsibility per Module?

Each module does exactly one thing:

| Module | Single Responsibility |
|:-------|:---------------------|
| a01 | Derive mortality primitives from l_x |
| a02 | Discount mortality with interest |
| a03 | Compute actuarial present values |
| a04 | Apply equivalence principle for pricing |
| a05 | Compute prospective reserves |
| a06 | Load and validate HMD data |
| a07 | Smooth noisy mortality rates |
| a08 | Decompose mortality into age + time components |
| a09 | Forecast mortality and bridge to actuarial engine |

This makes each module independently testable, replaceable, and comprehensible. A reader can understand any module by reading that file alone, without needing to understand the rest of the system.

### 7.4. Why Constructor-based Computation?

All classes compute their outputs in `__init__`. For example, `CommutationFunctions.__init__` calls `_compute_D()`, `_compute_N()`, `_compute_C()`, `_compute_M()` immediately. This means:

- Objects are **immutable after construction** -- no partial states
- Every instance is fully computed and ready to query
- No risk of accessing results before computation completes

The tradeoff is that construction is not lazy -- all values are computed even if only some are needed. For the scale of actuarial tables (typically ~100 ages), this is negligible.

### 7.5. Why Backward Recursion?

Commutation functions N_x and M_x use backward recursion:

```
N_omega = D_omega
N_x = D_x + N_{x+1}
```

This is O(n) vs. O(n^2) for forward summation. For a table with 101 ages (0-100), backward recursion requires 100 additions vs. 5,050 for forward summation.

---

## 8. External Dependencies

| Library | Used By | Purpose |
|:--------|:--------|:--------|
| numpy | a06, a07, a08, a09 | Array operations, linear algebra (SVD) |
| pandas | a06 | HMD file parsing, pivoting |
| scipy.sparse | a07 | Sparse difference and weight matrices |
| scipy.sparse.linalg | a07 | spsolve for Whittaker-Henderson linear system |
| scipy.optimize | a08 | brentq for k_t re-estimation |

The theoretical pipeline (a01-a05) has **zero external dependencies** beyond Python's standard library. This is a deliberate choice: actuarial calculations should be reproducible without third-party numerical libraries.

---

## 9. Testing Architecture

All tests reside in `backend/tests/` with 106 tests across 9 test files:

| Test File | Module Tested | Test Count |
|:----------|:-------------|:----------:|
| test_life_table.py | a01 | ~10 |
| test_commutation.py | a02 | ~10 |
| test_actuarial_values.py | a03 | ~5 |
| test_premiums.py | a04 | ~5 |
| test_reserves.py | a05 | ~8 |
| test_mortality_data.py | a06 | 15 |
| test_graduation.py | a07 | 13 |
| test_lee_carter.py | a08 | 20 |
| test_projection.py | a09 | 17 |
| test_integration_lee_carter.py | a06-a09 + a01-a04 | 3 |

Each test includes a `THEORY` docstring explaining the actuarial property being verified. Tests use real HMD data (USA and Spain) loaded from `backend/data/hmd/`.
