# Mexican Data Pipeline -- Project Report

**Date:** 2026-02-08
**Branch:** `7feb`
**Tests before:** 106 | **Tests after:** 137 (31 new)

---

## Actions

- Generated 4 synthetic CSV files in `backend/data/mock/` replicating INEGI deaths, CONAPO population, CNSF 2000-I, and EMSSA-2009 formats using Gompertz-Makeham mortality with infant spike and young-adult accident hump
- Added `MortalityData.from_inegi()` classmethod to `a06_mortality_data.py` for loading INEGI deaths and CONAPO population data, computing m_x = D_x / P_x with age capping and sex filtering
- Added `LifeTable.from_regulatory_table()` classmethod to `a01_life_table.py` for loading CNSF/EMSSA CSV files and converting q_x to l_x via the recurrence l_{x+1} = l_x * (1 - q_x)
- Created `backend/engine/a10_validation.py` with `MortalityComparison` class for comparing projected vs regulatory life tables (qx_ratio, qx_difference, RMSE, summary)
- Wrote 4 new test files covering the INEGI loader, regulatory loader, validation module, and end-to-end Mexican pipeline integration
- Created `DOWNLOAD_GUIDE.md` files in `backend/data/inegi/`, `backend/data/conapo/`, and `backend/data/cnsf/` with instructions for acquiring real data
- Downloaded real INEGI, CONAPO, and CNSF/EMSSA data into their respective directories (gitignored)
- Updated `.gitignore` to exclude real data directories while keeping `backend/data/mock/` tracked

## Outputs

| Artifact | Type | Tests |
|:---------|:-----|------:|
| `backend/data/mock/mock_inegi_deaths.csv` | New data file | -- |
| `backend/data/mock/mock_conapo_population.csv` | New data file | -- |
| `backend/data/mock/mock_cnsf_2000_i.csv` | New data file | -- |
| `backend/data/mock/mock_emssa_2009.csv` | New data file | -- |
| `backend/engine/a06_mortality_data.py` | Modified (from_inegi) | -- |
| `backend/engine/a01_life_table.py` | Modified (from_regulatory_table) | -- |
| `backend/engine/a10_validation.py` | New module | -- |
| `backend/tests/test_inegi_data.py` | New test file | 10 |
| `backend/tests/test_regulatory_tables.py` | New test file | 9 |
| `backend/tests/test_validation.py` | New test file | 8 |
| `backend/tests/test_integration_mexican.py` | New test file | 4 |
| `backend/data/inegi/DOWNLOAD_GUIDE.md` | New guide | -- |
| `backend/data/conapo/DOWNLOAD_GUIDE.md` | New guide | -- |
| `backend/data/cnsf/DOWNLOAD_GUIDE.md` | New guide | -- |
| `.gitignore` | Modified | -- |

---

## Chronology

* **Designing the mock data (Gompertz-Makeham)**
The first decision was how to create test data that behaves like real Mexican mortality without depending on real files that cannot be committed (INEGI data is government-owned, CNSF tables are regulatory). We chose a Gompertz-Makeham model: mu(x) = A + B*c^x, which produces the exponentially increasing mortality pattern observed in all human populations. On top of this base curve, we added two features specific to Mexican demographics: an infant mortality spike at age 0 (neonatal causes) and a young-adult accident hump around ages 15-25 (external causes, particularly relevant for the "Hombres" sex category). The mock data covers ages 0-100 and years 2000-2010 with three sex groups in Spanish labels ("Hombres", "Mujeres", "Total") matching INEGI's actual format. The CNSF and EMSSA mock tables use the same Gompertz base but with different parameters: CNSF represents general population mortality (higher), while EMSSA represents social security workers (lower). For detailed look see `12_mortality_data_hmd_reference.md`.

* **Building the INEGI/CONAPO loader (a06)**
With mock data in place, we extended `a06_mortality_data.py` to accept Mexican-format data via a new `from_inegi()` classmethod. The key design decision was to keep the same output contract as `from_hmd()`: three aligned matrices (mx, dx, ex) plus age/year vectors. The loader reads two separate CSV files (INEGI deaths with columns Anio/Edad/Sexo/Defunciones, and CONAPO population with Anio/Edad/Sexo/Poblacion), filters by sex and year range, pivots into matrices, and computes m_x = D_x / P_x. Age capping aggregates all ages above age_max by summing both deaths and population before dividing, which gives exposure-weighted rates rather than naive averaging. Data validation rejects zero population (would cause division by zero in m_x) and negative deaths (physically impossible). The country attribute is set to "Mexico" so downstream code can distinguish the data source. The 10 tests in `test_inegi_data.py` verify loading, m_x computation against hand-calculated values, matrix shape, age capping, year filtering, sex filtering, positive rates, bad data rejection, duck typing interface, and integration with graduation. For detailed look see `12_mortality_data_hmd_reference.md`.

* **Building the regulatory table loader (a01)**
The second extension adds `LifeTable.from_regulatory_table()` to `a01_life_table.py`. Mexican regulatory tables (CNSF 2000-I, EMSSA-2009) publish q_x by sex in a simple three-column CSV format (age, qx_male, qx_female). The loader reads the CSV, selects the appropriate q_x column based on the sex parameter, and builds l_x via the fundamental recurrence: l_{x+1} = l_x * (1 - q_x), starting from a configurable radix (default 100,000). Terminal mortality q_omega = 1.0 is enforced at the last age. This produces a standard LifeTable that plugs directly into CommutationFunctions and the rest of the actuarial engine. The 9 tests in `test_regulatory_tables.py` verify CNSF loading, EMSSA loading, the l_x recurrence, radix handling, terminal q_x, monotonic l_x, sex selection, integration with commutation functions, and error handling for invalid files. For detailed look see `11_life_table_foundations_reference.md`.

* **Creating the validation module (a10)**
The validation module is the final piece needed to close the loop between the empirical pipeline (Lee-Carter projections) and the regulatory pipeline (CNSF/EMSSA tables). `MortalityComparison` takes two LifeTable objects and computes three comparison metrics over their overlapping ages: qx_ratio (multiplicative loading), qx_difference (additive deviation), and RMSE over a configurable age window. The overlap-age logic handles the common case where projected tables cover ages 0-100 but regulatory tables may start at a different age or end earlier. The `summary()` method returns a dict with min/max/mean ratio, RMSE, and age count for quick regulatory reporting. Under LISF/CUSF, Mexican insurers must demonstrate that their mortality assumptions are consistent with EMSSA-2009 or justify deviations, so this module provides exactly the tools needed for that comparison. The 8 tests in `test_validation.py` verify identity (ratio=1, RMSE=0 for identical tables), known differences (2x mortality gives ratio=2), difference sign, age-range filtering, summary output structure, and error handling for disjoint age ranges. For detailed look see `14_architecture_integration_reference.md`.

* **Integration testing the full Mexican pipeline**
The 4 integration tests in `test_integration_mexican.py` prove the complete chain works end-to-end with Mexican-format data: INEGI deaths + CONAPO population enter through `from_inegi()`, flow through Whittaker-Henderson graduation, Lee-Carter fitting (with k_t re-estimation), RWD projection, conversion to LifeTable via `to_life_table()`, and finally comparison against regulatory benchmarks via MortalityComparison. One test validates that the projected LifeTable passes all structural checks (deaths sum to l_0, terminal q_omega = 1, all rates in [0,1]). A second test confirms premium calculation works (whole life, term, endowment) with sensible ordering (term < whole life < endowment). A third test verifies that CNSF mortality exceeds EMSSA mortality on average (general population vs social security workers). The fourth test checks that both regulatory tables produce valid commutation functions and reasonable premiums. These tests demonstrate that the entire engine, originally built and tested with HMD data from the USA and Spain, generalizes to the Mexican data format without any changes to the core Lee-Carter or pricing modules.

* **Data acquisition strategy and gitignore**
Real INEGI deaths, CONAPO population estimates, and CNSF/EMSSA regulatory tables were downloaded into `backend/data/inegi/`, `backend/data/conapo/`, and `backend/data/cnsf/` respectively. These directories are gitignored because the data is government-owned and should not be redistributed. Each directory contains a `DOWNLOAD_GUIDE.md` with step-by-step instructions for obtaining the files from official sources. The mock data in `backend/data/mock/` is committed to the repo so that all 137 tests can run in CI without any external data dependencies. This separation -- committed mock data for testing, gitignored real data for analysis -- is a deliberate design choice that keeps the repo self-contained while respecting data licensing.
