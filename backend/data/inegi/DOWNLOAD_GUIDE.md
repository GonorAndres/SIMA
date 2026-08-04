# INEGI Mortality Download Guide

SIMA expects Mexican registered deaths by calendar year, single age, and sex.
The source is INEGI's mortality/registered-deaths data. Source layouts can
change, so retain the source URL, extraction date, and any transformations in
your analysis record.

## Required output

Export or transform the source into:

```text
backend/data/inegi/inegi_deaths.csv
```

with these exact columns:

```csv
Anio,Edad,Sexo,Defunciones
2000,0,Hombres,123
2000,0,Mujeres,110
2000,0,Total,233
```

- `Anio` and `Edad` must be integers.
- `Sexo` must be `Hombres`, `Mujeres`, or `Total`.
- `Defunciones` must be non-negative.
- Include matching age/year cells for every requested sex.

The official entry point is <https://www.inegi.org.mx/programas/mortalidad/>.
Use INEGI's current download interface and metadata rather than relying on an
undocumented endpoint.

## Trampa: el intervalo abierto "85 y mas"

INEGI's registered-deaths tabulations publish single ages **and** the open
interval `85 y mas` in the same age column. If you transform the source
mechanically, that aggregate lands in the CSV as a row labelled `Edad = 85`,
sitting alongside the genuine single-age-85 row. Nothing in the required column
contract above rejects it -- both rows are integers, both are non-negative -- and
the loader sums duplicate `(Anio, Edad, Sexo)` keys, so the open interval is added
to age 85 instead of replacing it.

The current extract still exhibits this: 105 duplicate keys (35 years x 3 sexes),
all at age 85. For 2020, `Total` age 85 appears twice -- 166,846 (the `85 y mas`
aggregate) and 19,714 (the true single age). Summed, m_85 blows past m_84 by an
order of magnitude.

When preparing the file, either drop the `85 y mas` row and keep single ages, or
keep the open interval and drop the single ages above it -- never both. Check
before committing:

```bash
.venv/bin/python -c "
import pandas as pd
d = pd.read_csv('backend/data/inegi/inegi_deaths.csv')
dup = d.duplicated(['Anio', 'Edad', 'Sexo']).sum()
print('duplicate (Anio, Edad, Sexo) keys:', dup)   # must be 0
"
```

Note that the mock file used by CI (`backend/data/mock/mock_inegi_deaths.csv`) has
no open-interval row and no duplicates, so a green test suite does **not** tell you
the real extract is clean. Run the check above against the real file.

## Coverage of the current extract

Years 1990-2024, ages 0-120, `Sexo` in {`Hombres`, `Mujeres`, `Total`}. The
Lee-Carter pipeline fits on 1990-2019 ages 0-100, so the 2020-2021 COVID years are
held out of the fit and used for validation.

## Verify

The loader combines this file with the CONAPO population file:

```bash
.venv/bin/pytest backend/tests/test_inegi_data.py
```

If real files are absent, the API intentionally falls back to committed mock
data for demonstration and CI.
