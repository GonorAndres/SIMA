"""
INEGI Mortality Data Tests (a06 - from_inegi)
================================================

Validates that Mexican INEGI/CONAPO data loading produces correct,
consistent matrices ready for Lee-Carter estimation.

These tests use MOCK data files that replicate the INEGI/CONAPO format:
    - Deaths: (Anio, Edad, Sexo, Defunciones)
    - Population: (Anio, Edad, Sexo, Poblacion)

The mock data covers ages 0-100 and years 2000-2010 with three sex
categories: Hombres, Mujeres, Total.
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates


# =============================================================================
# Test Fixtures
# =============================================================================

MOCK_DIR = str(Path(__file__).parent.parent / "data" / "mock")

DEATHS_FILE = os.path.join(MOCK_DIR, "mock_inegi_deaths.csv")
POP_FILE = os.path.join(MOCK_DIR, "mock_conapo_population.csv")


@pytest.fixture
def inegi_data():
    """Load mock INEGI data, Total sex, years 2000-2010, ages 0-100."""
    return MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Total",
        year_start=2000,
        year_end=2010,
        age_max=100,
    )


@pytest.fixture
def inegi_hombres():
    """Load mock INEGI data, Hombres only."""
    return MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Hombres",
        year_start=2000,
        year_end=2010,
        age_max=100,
    )


# =============================================================================
# Test 1: Basic Loading
# =============================================================================

def test_from_inegi_loads_mock_data(inegi_data):
    """
    THEORY: The from_inegi() factory method must produce a valid MortalityData
    instance from INEGI deaths and CONAPO population files. This is the entry
    point for all Mexican mortality analysis -- if this fails, nothing else works.
    """
    assert isinstance(inegi_data, MortalityData)
    assert inegi_data.country == "Mexico"
    assert inegi_data.sex == "Total"


# =============================================================================
# Test 2: m_x = deaths / population
# =============================================================================

def test_from_inegi_computes_mx_correctly(inegi_data):
    """
    THEORY: Central death rate m_{x,t} = D_{x,t} / P_{x,t}, where D is deaths
    and P is mid-year population. For INEGI data, we use CONAPO population
    estimates as exposure since INEGI doesn't provide person-years directly.

    We verify specific cells against hand-computed values from the mock files:
        Age 0, Year 2000, Total: deaths=37864, pop=2653691 -> mx=0.01426843
        Age 50, Year 2005, Hombres would be checked separately.
    """
    # Age 0, Year 2000: m_x = 37864 / 2653691
    mx_00 = inegi_data.get_mx(0, 2000)
    expected = 37864 / 2653691
    np.testing.assert_allclose(mx_00, expected, rtol=1e-6)

    # Also verify via matrix indexing
    age_idx = 0   # age 0 is first row
    year_idx = 0  # year 2000 is first column
    np.testing.assert_allclose(inegi_data.mx[age_idx, year_idx], expected, rtol=1e-6)


# =============================================================================
# Test 3: Matrix Shape
# =============================================================================

def test_from_inegi_matrix_shape(inegi_data):
    """
    THEORY: With ages 0-100, we expect 101 rows. With years 2000-2010,
    we expect 11 columns. The three matrices (mx, dx, ex) must all share
    this shape for Lee-Carter's SVD to work on aligned data.
    """
    assert inegi_data.mx.shape == (101, 11)
    assert inegi_data.dx.shape == (101, 11)
    assert inegi_data.ex.shape == (101, 11)
    assert inegi_data.shape == (101, 11)
    assert inegi_data.n_ages == 101
    assert inegi_data.n_years == 11


# =============================================================================
# Test 4: Age Capping
# =============================================================================

def test_from_inegi_age_capping():
    """
    THEORY: Ages above age_max must be aggregated into the age_max group.
    For mortality rates, this means summing deaths and population above
    the threshold, then computing m_x = sum(D) / sum(P).

    The mock data has ages 0-100. Setting age_max=95 should aggregate
    ages 95-100 into a single age-95 group, yielding 96 age groups (0-95).
    """
    data = MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Total",
        year_start=2000,
        year_end=2010,
        age_max=95,
    )
    assert data.n_ages == 96  # ages 0..95
    assert data.ages[-1] == 95
    assert data.ages[0] == 0
    # The capped rate should be the weighted average, not a simple average
    assert np.all(data.mx > 0)


# =============================================================================
# Test 5: Year Filtering
# =============================================================================

def test_from_inegi_year_filtering():
    """
    THEORY: Lee-Carter estimation quality depends on the observation window.
    Year filtering lets the user select a relevant recent period. Only
    years within [year_start, year_end] should appear in the output.
    """
    data = MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Total",
        year_start=2003,
        year_end=2007,
        age_max=100,
    )
    assert data.n_years == 5  # 2003, 2004, 2005, 2006, 2007
    expected_years = np.arange(2003, 2008)
    np.testing.assert_array_equal(data.years, expected_years)


# =============================================================================
# Test 6: Sex Filtering
# =============================================================================

def test_from_inegi_sex_filtering(inegi_data, inegi_hombres):
    """
    THEORY: Mortality patterns differ significantly by sex. In Mexico,
    male mortality is notably higher due to external causes (homicide,
    accidents). The from_inegi loader must correctly filter by the
    Spanish sex labels used in INEGI data: Hombres/Mujeres/Total.
    """
    assert inegi_data.sex == "Total"
    assert inegi_hombres.sex == "Hombres"

    # Total and Hombres should have same dimensions but different rates
    assert inegi_data.shape == inegi_hombres.shape

    # Hombres rates should generally differ from Total
    assert not np.allclose(inegi_data.mx, inegi_hombres.mx)


# =============================================================================
# Test 7: Positive Rates
# =============================================================================

def test_from_inegi_positive_rates(inegi_data):
    """
    THEORY: Lee-Carter estimation takes log(m_{x,t}), so ALL death rates
    must be strictly positive. Zero or negative rates would produce -inf
    or NaN in the log-mortality matrix, breaking SVD decomposition.

    This is a critical requirement for the pipeline to work.
    """
    assert np.all(inegi_data.mx > 0), "All death rates must be positive for log transform"
    assert np.all(inegi_data.ex > 0), "All exposures must be positive"
    assert not np.any(np.isnan(inegi_data.mx)), "No NaN in death rates"


# =============================================================================
# Test 8: Validation of Bad Data
# =============================================================================

def test_from_inegi_validates_bad_data():
    """
    THEORY: Data quality checks are essential before feeding into Lee-Carter.
    Zero population would cause division by zero in m_x = D/P. Negative
    deaths are physically impossible. The loader must reject such data
    with clear error messages rather than silently producing bad matrices.
    """
    # Create temporary bad data with zero population
    with tempfile.TemporaryDirectory() as tmpdir:
        deaths_path = os.path.join(tmpdir, "bad_deaths.csv")
        pop_path = os.path.join(tmpdir, "bad_pop.csv")

        # Write minimal valid deaths
        with open(deaths_path, "w") as f:
            f.write("Anio,Edad,Sexo,Defunciones\n")
            for year in range(2000, 2003):
                for age in range(0, 5):
                    f.write(f"{year},{age},Total,100\n")

        # Write population with a ZERO value
        with open(pop_path, "w") as f:
            f.write("Anio,Edad,Sexo,Poblacion\n")
            for year in range(2000, 2003):
                for age in range(0, 5):
                    pop = 0 if (age == 2 and year == 2001) else 10000
                    f.write(f"{year},{age},Total,{pop}\n")

        with pytest.raises(ValueError):
            MortalityData.from_inegi(
                deaths_filepath=deaths_path,
                population_filepath=pop_path,
                sex="Total",
                year_start=2000,
                year_end=2002,
                age_max=4,
            )


# =============================================================================
# Test 9: Duck Typing Interface
# =============================================================================

def test_from_inegi_duck_typing_interface(inegi_data):
    """
    THEORY: The actuarial engine uses duck typing -- GraduatedRates, LeeCarter,
    and MortalityProjection all expect objects with .mx, .dx, .ex, .ages,
    .years, .n_ages, .n_years attributes. The INEGI loader must produce
    objects with this exact interface so they plug directly into the pipeline.
    """
    # Core matrix attributes
    assert hasattr(inegi_data, "mx")
    assert hasattr(inegi_data, "dx")
    assert hasattr(inegi_data, "ex")

    # Label attributes
    assert hasattr(inegi_data, "ages")
    assert hasattr(inegi_data, "years")

    # Dimension properties
    assert hasattr(inegi_data, "n_ages")
    assert hasattr(inegi_data, "n_years")

    # Verify types
    assert isinstance(inegi_data.mx, np.ndarray)
    assert isinstance(inegi_data.dx, np.ndarray)
    assert isinstance(inegi_data.ex, np.ndarray)
    assert isinstance(inegi_data.ages, np.ndarray)
    assert isinstance(inegi_data.years, np.ndarray)
    assert isinstance(inegi_data.n_ages, int)
    assert isinstance(inegi_data.n_years, int)


# =============================================================================
# Test 10: Integration with Graduation
# =============================================================================

def test_from_inegi_feeds_into_graduation():
    """
    THEORY: The full pipeline is: INEGI data -> Graduation -> Lee-Carter.
    This integration test verifies that from_inegi() output is accepted
    by GraduatedRates without error. If this works, the INEGI data
    satisfies all the contracts expected by downstream modules.

    We use age_max=95 to avoid the age-100 open interval where m_x > 1,
    which can cause numerical issues in log-space graduation.
    """
    data = MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Total",
        year_start=2000,
        year_end=2010,
        age_max=95,
    )
    # This should not raise any errors
    graduated = GraduatedRates(data, lambda_param=1e5)

    # Graduated rates should preserve dimensions
    assert graduated.mx.shape == data.mx.shape
    assert np.all(graduated.mx > 0)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
