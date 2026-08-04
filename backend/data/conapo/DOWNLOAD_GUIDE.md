# CONAPO Population Download Guide

SIMA uses CONAPO mid-year population estimates as exposure for Mexican
mortality rates. Obtain the current population projections from the official
CONAPO data portal and preserve the release/version in your analysis record.

## Required output

Export or transform the source into:

```text
backend/data/conapo/conapo_population.csv
```

with these exact columns:

```csv
Anio,Edad,Sexo,Poblacion
2000,0,Hombres,1000000
2000,0,Mujeres,980000
2000,0,Total,1980000
```

- `Anio` and `Edad` must be integers.
- `Sexo` must be `Hombres`, `Mujeres`, or `Total`.
- `Poblacion` must be strictly positive.
- Age/year/sex cells must align with the INEGI deaths extract.

## Coverage of the current extract

Years 1950-2070 (historical conciliation plus projections), ages 0-109. Sanity
anchor: summing `Total` for 2020 gives 128.2 million, which matches the published
CONAPO mid-year estimate. If a refreshed file misses that by more than a few
percent, the transformation is wrong -- most likely an age or sex filter was
dropped, or projections were mixed with the conciliation series.

Start at the official CONAPO site:
<https://www.gob.mx/conapo/acciones-y-programas/conciliacion-demografica-de-mexico-1950-2019-y-proyecciones-de-la-poblacion-de-mexico-y-de-las-entidades-federativas-2020-2070>.
Use the current documented download offered there.

## Verify

```bash
.venv/bin/pytest backend/tests/test_inegi_data.py
```

SIMA computes `m_x = Defunciones / Poblacion` and rejects missing, zero, or
misaligned exposure cells.
