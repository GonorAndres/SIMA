"""
Generate synthetic HMD-format mortality data for CI testing.

Creates mock Mx, Deaths, and Exposures files for USA and Spain using
the Gompertz-Makeham mortality law with biologically plausible features:

    mu(x) = A + B * c^x

Plus:
- Infant mortality spike at age 0
- Young-adult accident hump (ages 18-25)
- Year-over-year mortality improvement trend
- Country differentiation (Spain improves faster than USA)
- Sex differentiation (Male > Female > Total)
- Reproducible random noise (seeded)

Output files match the HMD 1x1 text format parsed by
backend.engine.a06_mortality_data._load_hmd_file():
    - 2 header lines (skipped)
    - Whitespace-separated: Year  Age  Female  Male  Total
    - Age 110+ as the open age interval
    - Positive values everywhere (required for log transform)

Data consistency: dx = mx * ex exactly, so mx = dx/ex passes
the 1% relative-error validation in a06._validate().

Usage:
    python backend/scripts/generate_mock_hmd.py
"""

import numpy as np
from pathlib import Path

# Reproducibility
RNG = np.random.default_rng(seed=20260315)

# Output directories
MOCK_DIR = Path(__file__).parent.parent / "data" / "mock" / "hmd"

# Year and age ranges (matching test fixtures: 1990-2020, ages 0-110+)
YEARS = list(range(1990, 2021))  # 31 years
AGES = list(range(0, 111))  # 0-110 (110 represents 110+)
N_YEARS = len(YEARS)
N_AGES = len(AGES)

# ============================================================================
# Gompertz-Makeham parameters by country
# ============================================================================
# These produce biologically plausible mortality curves.
# Spain has lower base mortality and faster improvement (drift ~ -2.9% vs -1.2%).

COUNTRY_PARAMS = {
    "usa": {
        "A": 0.0003,       # Makeham constant (background mortality)
        "B": 0.00003,      # Gompertz scale
        "c": 1.098,        # Gompertz rate of aging
        "drift": -0.012,   # Annual mortality improvement (~1.2% per year)
        "infant_mx": 0.008,  # Infant death rate (age 0)
        "hump_peak": 0.0008,  # Young-adult accident hump
        "hump_center": 21,
        "hump_width": 4,
        "base_exposure": 100_000,  # Base person-years at each age
    },
    "spain": {
        "A": 0.00025,
        "B": 0.000025,
        "c": 1.100,
        "drift": -0.029,   # Spain improves faster
        "infant_mx": 0.006,
        "hump_peak": 0.0005,
        "hump_center": 22,
        "hump_width": 3.5,
        "base_exposure": 80_000,
    },
}

# Sex multipliers (applied to base mortality)
SEX_MULTIPLIERS = {
    "Male": 1.15,
    "Female": 0.85,
    "Total": 1.00,
}


def gompertz_makeham(age: int, params: dict) -> float:
    """Base Gompertz-Makeham force of mortality."""
    return params["A"] + params["B"] * params["c"] ** age


def young_adult_hump(age: int, params: dict) -> float:
    """Gaussian accident hump centered around ages 18-25."""
    return params["hump_peak"] * np.exp(
        -0.5 * ((age - params["hump_center"]) / params["hump_width"]) ** 2
    )


def generate_mx(age: int, year: int, sex: str, params: dict) -> float:
    """
    Generate central death rate m(x,t) for a given age, year, and sex.

    Components:
    1. Gompertz-Makeham base: A + B * c^x
    2. Infant spike at age 0
    3. Young-adult accident hump
    4. Year trend: exp(drift * (year - 1990))
    5. Sex multiplier
    6. Small multiplicative noise
    """
    # Base mortality from Gompertz-Makeham
    if age == 0:
        base = params["infant_mx"]
    else:
        base = gompertz_makeham(age, params) + young_adult_hump(age, params)

    # Year improvement trend (exponential decline)
    year_offset = year - YEARS[0]
    trend = np.exp(params["drift"] * year_offset)

    # Sex differentiation
    sex_mult = SEX_MULTIPLIERS[sex]

    # Multiplicative noise (small: +/- 3%)
    noise = 1.0 + RNG.normal(0, 0.03)

    mx = base * trend * sex_mult * noise

    # Ensure strictly positive and cap at reasonable maximum
    return np.clip(mx, 1e-6, 0.8)


def generate_exposure(age: int, year: int, sex: str, params: dict) -> float:
    """
    Generate person-years of exposure L(x,t).

    Exposure decreases with age (population pyramid shape) and has
    a slight growth trend over time.
    """
    base = params["base_exposure"]

    # Age profile: more people at young/middle ages, fewer at extreme ages
    if age == 0:
        age_factor = 0.95
    elif age <= 5:
        age_factor = 1.0
    elif age <= 60:
        age_factor = 1.0 - 0.003 * (age - 5)
    else:
        # Accelerating decline after 60
        age_factor = max(0.01, (1.0 - 0.003 * 55) * np.exp(-0.05 * (age - 60)))

    # Slight population growth over time
    year_factor = 1.0 + 0.005 * (year - YEARS[0])

    # Sex distribution (roughly equal)
    if sex == "Male":
        sex_factor = 0.49
    elif sex == "Female":
        sex_factor = 0.51
    else:
        sex_factor = 1.0

    # Small noise
    noise = 1.0 + RNG.normal(0, 0.02)

    return max(10.0, base * age_factor * year_factor * sex_factor * noise)


def write_hmd_file(filepath: Path, data: dict, description: str):
    """
    Write a single HMD-format text file.

    data: dict of (year, age) -> {"Female": val, "Male": val, "Total": val}
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        # 2 header lines (skipped by parser)
        f.write("  Human Mortality Database\n")
        f.write(f"  {description} (synthetic mock data for CI testing)\n")

        # Column header (wider to match 10-decimal data columns)
        f.write(f"{'Year':>10s}{'Age':>10s}{'Female':>18s}{'Male':>18s}{'Total':>18s}\n")

        # Data rows
        for year in YEARS:
            for age in AGES:
                age_str = f"{age}+" if age == 110 else str(age)
                female = data[(year, age)]["Female"]
                male = data[(year, age)]["Male"]
                total = data[(year, age)]["Total"]
                # Use high precision to avoid truncation errors in the
                # mx = dx/ex consistency check (1% relative tolerance).
                # Real HMD uses 5-6 decimals but mock data needs more since
                # we generate dx = mx * ex and round-trip through text.
                f.write(
                    f"{year:>10d}{age_str:>10s}"
                    f"{female:>18.10f}{male:>18.10f}{total:>18.10f}\n"
                )


def generate_country(country: str, params: dict):
    """Generate all three HMD files for one country."""
    print(f"Generating {country}...")

    # Build data dictionaries
    mx_data = {}
    dx_data = {}
    ex_data = {}

    for year in YEARS:
        for age in AGES:
            mx_row = {}
            dx_row = {}
            ex_row = {}

            for sex in ("Female", "Male", "Total"):
                mx_val = generate_mx(age, year, sex, params)
                ex_val = generate_exposure(age, year, sex, params)
                dx_val = mx_val * ex_val  # Ensures perfect consistency

                mx_row[sex] = mx_val
                dx_row[sex] = dx_val
                ex_row[sex] = ex_val

            mx_data[(year, age)] = mx_row
            dx_data[(year, age)] = dx_row
            ex_data[(year, age)] = ex_row

    # Write files
    country_dir = MOCK_DIR / country
    write_hmd_file(
        country_dir / f"Mx_1x1_{country}.txt",
        mx_data,
        f"{country.upper()} central death rates",
    )
    write_hmd_file(
        country_dir / f"Deaths_1x1_{country}.txt",
        dx_data,
        f"{country.upper()} death counts",
    )
    write_hmd_file(
        country_dir / f"Exposures_1x1_{country}.txt",
        ex_data,
        f"{country.upper()} person-years of exposure",
    )

    # Summary stats
    male_mx_age60 = [mx_data[(y, 60)]["Male"] for y in YEARS]
    print(f"  {country} Male mx(60): {male_mx_age60[0]:.5f} (1990) -> {male_mx_age60[-1]:.5f} (2020)")
    print(f"  Files: {country_dir / f'Mx_1x1_{country}.txt'}")
    print(f"         {country_dir / f'Deaths_1x1_{country}.txt'}")
    print(f"         {country_dir / f'Exposures_1x1_{country}.txt'}")


if __name__ == "__main__":
    print("Generating mock HMD data for CI testing")
    print(f"Output: {MOCK_DIR}")
    print(f"Years: {YEARS[0]}-{YEARS[-1]} ({N_YEARS} years)")
    print(f"Ages: {AGES[0]}-{AGES[-1]}+ ({N_AGES} age groups)")
    print()

    for country, params in COUNTRY_PARAMS.items():
        generate_country(country, params)
        print()

    print("Done. Mock HMD data ready for CI.")
    print("CI copies these to backend/data/hmd/ before running tests.")
