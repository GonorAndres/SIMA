# Data provenance

Every data file SIMA reads, where it came from, and what was done to it before the
engine saw it. Checksums for all of them live in
[`backend/data/CHECKSUMS.txt`](backend/data/CHECKSUMS.txt).

Compiled 2026-08-02, when the synthetic HMD fixtures that had been sitting on the
real-data path since the project began were replaced with genuine extracts.

**Rule of thumb:** a file under `backend/data/mock/` is synthetic and exists so CI can
run without redistributable data. It is never valid for a published actuarial result.
Everything else is real, and the checks in
[`backend/tests/test_data_authenticity.py`](backend/tests/test_data_authenticity.py)
run against it whenever it is present.

---

## Real data

| File | Source | URL | Vintage | Downloaded | Data rows | sha256 (first 12) |
|------|--------|-----|---------|-----------|----------:|-------------------|
| `backend/data/hmd/usa/Mx_1x1_usa.txt` | HMD (USA, death rates 1x1) | https://www.mortality.org | Last modified 2026-06-09, Methods Protocol v6 (2017); years 1933-2024 | 2026-08-02 | 10,212 | `6ed11f34dc76` |
| `backend/data/hmd/usa/Deaths_1x1_usa.txt` | HMD (USA, death counts 1x1) | https://www.mortality.org | same | 2026-08-02 | 10,212 | `55afeb39a705` |
| `backend/data/hmd/usa/Exposures_1x1_usa.txt` | HMD (USA, exposure-to-risk 1x1) | https://www.mortality.org | same | 2026-08-02 | 10,212 | `5ebf0751498e` |
| `backend/data/hmd/spain/Mx_1x1_spain.txt` | HMD (Spain, death rates 1x1) | https://www.mortality.org | Last modified 2025-02-20, Methods Protocol v6 (2017); years 1908-2023 | 2026-08-02 | 12,876 | `4b95fefa6892` |
| `backend/data/hmd/spain/Deaths_1x1_spain.txt` | HMD (Spain, death counts 1x1) | https://www.mortality.org | same | 2026-08-02 | 12,876 | `1c5d52892682` |
| `backend/data/hmd/spain/Exposures_1x1_spain.txt` | HMD (Spain, exposure-to-risk 1x1) | https://www.mortality.org | same | 2026-08-02 | 12,876 | `a7287c259b1a` |
| `backend/data/inegi/inegi_deaths.csv` | INEGI, Defunciones registradas | https://www.inegi.org.mx/programas/mortalidad/ | Years 1990-2024, ages 0-120, sexes Hombres/Mujeres/Total | 2026-08-02 | 12,786 | `d3f516dee51b` |
| `backend/data/conapo/conapo_population.csv` | CONAPO, Conciliacion demografica 1950-2019 + Proyecciones 2020-2070 | https://www.gob.mx/conapo | Years 1950-2070, ages 0-109 | 2026-08-02 | 39,930 | `ffa9e1222f8e` |
| `backend/data/cnsf/cnsf_2013.csv` | CNSF, CUSF **Anexo 5.3.3-a** -- "CNSFM 2013, mortalidad MIXTA" | https://www.gob.mx/cms/uploads/attachment/file/73530/ANEXO_5.3.3-a.pdf | Ages 0-110, **unisex**, plus the 99.5th-percentile series | 2026-08-02 | 111 | `9f51c69fd1f5` |
| `backend/data/cnsf/emssah_emssam_97.csv` | CNSF, CUSF **Anexo 14.2.4-a** -- EMSSAH-97 / EMSSAM-97 | https://www.gob.mx/cms/uploads/attachment/file/74206/ANEXO_14.2.4-a.pdf | Ages 15-110, sex-differentiated | 2026-08-02 | 96 | `38c9abeff2c0` |
| `backend/data/cnsf/cnsf_2000_i.csv` | CNSF 2000-I, CUSF Anexo 14.2.1 | https://lisfcusf.cnsf.gob.mx/CUSF/ | Ages 12-100, sex-differentiated | unrecorded | 89 | `f849327cb153` |
| `backend/data/cnsf/cnsf_2000_g.csv` | CNSF 2000-G, CUSF Anexo 14.2.1 | https://lisfcusf.cnsf.gob.mx/CUSF/ | Ages 12-100, sex-differentiated | unrecorded | 89 | `51a63ffdd603` |
| `backend/data/mortality_tables/Tabla de mortalidad CNSFM-2013 - Hoja 1.csv` | Spreadsheet working copy of CNSF M 2013 with commutation columns | — | Ages 0-110, i = 5% | unrecorded | 111 | `749c4bd033ab` |

`cnsf_2000_i.csv` and `cnsf_2000_g.csv` were **not** re-verified against the annex on
2026-08-02. Treat their provenance as unconfirmed. `mortality_tables/…CNSFM-2013…` is
unreferenced by any code; its q_x column independently reproduces the Anexo 5.3.3-a
values at the ages checked (0.000433 at age 0, 0.000434 at 2, 0.000436 at 5).

The CUSF corpus is browsable annex by annex at https://lisfcusf.cnsf.gob.mx/CUSF/
(for example `/CUSF/A_5_3_3_A`).

---

## Synthetic fixtures (CI only)

Committed on purpose so the suite runs without redistributable data. Each HMD fixture
carries `synthetic mock data for CI testing` in line 2, which is how both the loader
and `test_data_authenticity.py` tell them apart from the real thing.

| File | What it is | Data rows | sha256 (first 12) |
|------|-----------|----------:|-------------------|
| `backend/data/mock/hmd/{usa,spain}/{Mx,Deaths,Exposures}_1x1_*.txt` | Gompertz-Makeham curves, years 1990-2020 | 3,441 each | see CHECKSUMS.txt |
| `backend/data/mock/mock_inegi_deaths.csv` | INEGI-shaped deaths, 2000-2010, ages 0-105 **including an "85 y mas" open-interval row** | 3,531 | `1f37609c7fb8` |
| `backend/data/mock/mock_conapo_population.csv` | CONAPO-shaped population, 2000-2010, ages 0-105 | 3,498 | `e1137880ca13` |
| `backend/data/mock/mock_cnsf_2000_i.csv` | CNSF-shaped q_x table | 101 | `83c72b536f6c` |
| `backend/data/mock/mock_emssa_97.csv` | Synthetic sexed q_x table, ages 0-100. A CI fixture only: it does **not** reproduce the published EMSSAH-97/EMSSAM-97, which covers 15-110 | 101 | `b15aed00b611` |
| `backend/data/mini_table.csv` | Hand-built 6-row l_x table, ages 60-65, for arithmetic validation | 6 | `308cedad6492` |
| `backend/data/sample_mortality.csv` | Illustrative l_x table, ages 20-110 | 91 | `da1b37ba8951` |

`gs://sima-mortality-data/hmd/` holds the real extracts (object versioning on);
`gs://sima-mortality-data/mock/hmd/` holds the synthetic ones, off every deploy path.

`ci.yml` copies `backend/data/mock/hmd/*` into `backend/data/hmd/*` so the HMD-dependent
tests can run without redistributable data. That is why the authenticity checks skip in
CI: the files there are the committed fixtures, byte for byte, and
`.github/scripts/data_gate.py` is what stops them reaching production. A file on the
real-data path that carries a synthetic marker but does **not** match a committed
fixture is a hard test failure -- and an *unmarked* fabrication is treated as real, so
the five substantive checks run against it and fail.

---

## Transforms applied before the engine sees the data

### INEGI deaths: the "85 y mas" row must be dropped

**This is the important one.** INEGI publishes the open interval `85 y mas` in the same
age column as the single ages, so a mechanical transform lands it in the CSV as a row
labelled `Edad = 85` next to the genuine single age 85. The current extract contains
**105 such duplicated `(Anio, Edad, Sexo)` keys** -- 35 years x 3 sexes, all at age 85.
For 2020, `Total` age 85 appears twice: **166,846** (the open group) and **19,714** (the
true single age).

Summing them, which is what `_cap_ages_sum()` did until 2026-08-02, gave:

| | m_85 (1990) | m_85 (2019) | cells with m_x > 1 |
|---|---|---|---|
| before | 1.071073 | 0.947199 | 18 (11 at age 85, 7 at the age-100 open group) |
| after | 0.143523 | 0.092728 | 7 (all at the age-100 open group) |

Against neighbouring m_84 = 0.091108 and m_86 = 0.110441 in 1990.

Downstream, on a 2019 period life table built from the graduated rates
(lambda = 1e5, second differences, exposure-weighted; q_x = 1 - exp(-m_x); i = 5%):

| | e_65 | net annual premium, whole life, age 60, SA 1,000,000 |
|---|---|---|
| before | 17.4679 | 30,193.16 |
| after | 18.2318 | 29,198.69 |
| change | **+4.37%** | **-3.29%** |

Phantom deaths at 85 shorten the tail of the survival curve, so the fix lengthens life
expectancy and cheapens death cover.

`_drop_open_interval_duplicates()` in `backend/engine/a06_mortality_data.py` now removes
it, identifying the aggregate by the identity `aggregate = single age + sum of ages
above it` -- which holds exactly at all 105 keys -- and raising `DataQualityError` on any
duplicated key it cannot explain that way. **If you refresh the INEGI extract, leave the
row in: the loader handles it. Do not drop it manually and do not let a transform sum
it.**

### Age capping

Deaths and exposure above `age_max` (100 by default in every production pipeline) are
summed into an `age_max+` open group; the rate for that group is recomputed as
sum(deaths)/sum(exposure), not averaged, so it stays exposure-weighted.

### Known source artifact: m_100 above 1 in the early 1990s

Mexico's 100+ group has m_x above 1 in 7 year-cells (peaking at **1.7788 in 1990**),
because INEGI registers more centenarian deaths than CONAPO projects centenarians
alive -- age heaping at 100 in death registration against a projected denominator. That
is a property of the two sources, not a loader defect. The loader's plausibility check
therefore allows up to 2.0 at the open group (where m -> 2 as q -> 1) and hard-rejects
anything above 1.0 at every closed age.

### Regulatory tables

- **CNSF M 2013 is unisex.** The annex publishes one q_x column for hombres y mujeres.
  `cnsf_2013.csv` stores it as `qx_unisex` and repeats it verbatim into `qx_male` /
  `qx_female` so the existing `qx_{sex}` loader keeps working. Those are **not** a sex
  split. `qx_p995` is the annex's own 99.5th-percentile series, kept for use as a
  CUSF-prescribed mortality stress.
- **There is no "EMSSA 2009."** The CUSF annex index contains no such table. The file
  that used to sit at `backend/data/cnsf/emssa_2009.csv` **disagreed** with the real
  Anexo 14.2.4-a at effectively every age (ratios from 0.159x to 2.733x, with only two
  coincidental matches in 96 -- age 31, and the trivial q = 1.0 at age 110) and invented
  ages 0-14 the published table does not cover. It was deleted on 2026-08-02 and replaced
  by `emssah_emssam_97.csv`, which `backend/api/services/precomputed.py` has resolved
  since 2026-08-03 (`REAL_EMSSA_97`). The mock fallback was renamed to
  `mock_emssa_97.csv` in the same change; the API identifier is `emssa_97`.
- Annex rates printed per mille are stored as decimals.

---

## Licensing and citation

### HMD (CC BY 4.0)

> HMD. Human Mortality Database. Max Planck Institute for Demographic Research
> (Germany), University of California, Berkeley (USA), and French Institute for
> Demographic Studies (France). Available at www.mortality.org.
> Data downloaded 2026-08-02.

- Always acknowledge HMD as source or intermediary provider, with the download date.
- **Do not redistribute copies.** Point people at www.mortality.org to download their
  own. This is why `backend/data/hmd/` is gitignored and the authenticity tests skip
  when it is absent.
- HMD's own estimates (exposure-to-risk, death rates, life tables) are CC BY 4.0. The
  *input* data on the country pages remain under each national provider's license and
  must not be used commercially or republished without their permission.

### INEGI / CONAPO

Mexican open government data. Cite the programme and the extraction date.

### CNSF

Regulatory tables published in the Circular Unica de Seguros y Fianzas. Public.

---

## Refreshing the data

```bash
# 1. Replace the files (see the DOWNLOAD_GUIDE.md in each data directory)
# 2. Regenerate the checksums
cd backend/data && find . -type f ! -name '*.md' ! -name 'CHECKSUMS.txt' -print0 \
  | LC_ALL=C sort -z | xargs -0 sha256sum > CHECKSUMS.txt

# 3. Prove the new files are real, not a regenerated fixture
.venv/bin/pytest backend/tests/test_data_authenticity.py -v

# 4. Full suite
.venv/bin/pytest backend/tests -q
```

Then update the table above: vintage, download date, row count, checksum. A skipped
authenticity test is not a passing one -- it means the file was not there to check.
