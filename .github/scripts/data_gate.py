#!/usr/bin/env python3
"""Content gate: refuse to deploy data that is not demonstrably real.

Run from the repository root, after the deploy workflow has pulled data from GCS:

    python3 .github/scripts/data_gate.py

`test -f` passes on an empty or fabricated file -- that is precisely how synthetic
HMD fixtures once reached production. These checks assert properties of the world
instead of properties of the file format, so a generator cannot satisfy them
without reimplementing demography. The fuller version (sex ratio at the young-adult
accident hump, Poisson roughness floor) lives in
backend/tests/test_data_authenticity.py and runs in CI against the mock fixtures.

Stdlib only, deliberately: this runs in the deploy job, which has no pip install
step, and it must not be able to fail for dependency reasons.
"""

import sys
from pathlib import Path

problems = []

# Real coverage: USA from 1933, Spain from 1908. The synthetic fixtures started 1990.
COUNTRIES = {"usa": (1940, 330e6), "spain": (1940, 47e6)}


def read_hmd(path):
    lines = path.read_text(errors="replace").split("\n")
    banner = " ".join(lines[:2]).lower()
    for word in ("synthetic", "mock", "fake"):
        if word in banner:
            problems.append(f"{path.name}: header declares itself {word!r} -- {lines[1].strip()!r}")
    rows = {}
    for line in lines[2:]:  # HMD puts two metadata lines first
        cells = line.split()
        if len(cells) < 5:
            continue
        try:
            year = int(cells[0])
        except ValueError:
            continue
        age = 110 if cells[1].endswith("+") else int(cells[1])
        rows[(year, age)] = [float("nan") if c == "." else float(c) for c in cells[2:5]]
    return rows


def year_total(rows, year):
    return sum(v[2] for (y, _), v in rows.items() if y == year and v[2] == v[2])


for country, (first_year_max, population) in COUNTRIES.items():
    tables = {}
    for name in ("Mx", "Deaths", "Exposures"):
        path = Path("backend/data/hmd") / country / f"{name}_1x1_{country}.txt"
        if not path.exists() or path.stat().st_size < 100_000:
            problems.append(f"{path}: missing or truncated")
            break
        tables[name] = read_hmd(path)
    if len(tables) < 3:
        continue

    years = sorted({y for (y, _) in tables["Mx"]})
    if not years:
        problems.append(f"{country}: no parseable data rows")
        continue

    # 1. Year coverage.
    if years[0] > first_year_max:
        problems.append(
            f"{country}: series starts {years[0]}, genuine HMD starts <= {first_year_max}"
        )

    # 2. Summed exposures must imply the right national population.
    probe = 2015 if 2015 in years else years[-1]
    pop = year_total(tables["Exposures"], probe)
    if not 0.5 < pop / population < 2.0:
        problems.append(
            f"{country}: exposures imply {pop / 1e6:.1f}M people in {probe},"
            f" expected ~{population / 1e6:.0f}M"
        )

    # 3. Any genuine file covering 2020 shows COVID; smooth synthetic data cannot.
    if 2019 in years and 2020 in years:
        excess = (year_total(tables["Deaths"], 2020) / year_total(tables["Deaths"], 2019) - 1) * 100
        if excess < 10.0:
            problems.append(f"{country}: 2019->2020 deaths {excess:+.1f}%, real data shows ~+18%")
        print(
            f"{country}: {years[0]}-{years[-1]}, {pop / 1e6:.1f}M in {probe}, 2020 {excess:+.1f}%"
        )
    else:
        print(f"{country}: {years[0]}-{years[-1]}, {pop / 1e6:.1f}M in {probe}, 2020 not covered")

# Mexican inputs and the CNSF regulatory table: shape only. Their authenticity is
# checked in backend/tests/test_data_authenticity.py.
for csv_path, columns, min_rows in (
    ("backend/data/inegi/inegi_deaths.csv", ("Anio", "Edad", "Sexo", "Defunciones"), 5000),
    ("backend/data/conapo/conapo_population.csv", ("Anio", "Edad", "Sexo", "Poblacion"), 5000),
    ("backend/data/cnsf/cnsf_2000_i.csv", ("age", "qx_male", "qx_female"), 50),
    # Loaded by precomputed.load_all() at every startup, so a malformed file
    # takes the whole API down, not just the CNSF 2013 tab. Published MIXTA:
    # qx_unisex is the canonical column, qx_p995 is the CUSF 99.5th percentile.
    ("backend/data/cnsf/cnsf_2013.csv", ("age", "qx_unisex", "qx_p995"), 100),
    # CUSF Anexo 14.2.4-a, ages 15-110 -> 96 rows + header.
    ("backend/data/cnsf/emssah_emssam_97.csv", ("age", "qx_male", "qx_female"), 90),
):
    path = Path(csv_path)
    if not path.exists():
        problems.append(f"{csv_path}: missing")
        continue
    lines = [ln for ln in path.read_text(errors="replace").split("\n") if ln.strip()]
    header = [c.strip() for c in lines[0].split(",")] if lines else []
    missing = [c for c in columns if c not in header]
    if len(lines) < min_rows:
        problems.append(f"{csv_path}: {len(lines)} lines, expected >= {min_rows}")
    elif missing:
        problems.append(f"{csv_path}: missing columns {missing}")
    else:
        print(f"{csv_path}: {len(lines) - 1} rows, columns {header}")

if problems:
    print("\nDATA GATE FAILED -- refusing to deploy:")
    for p in problems:
        print(f"  x {p}")
    sys.exit(1)
print("\nDATA GATE PASSED: data is consistent with genuine sources.")
