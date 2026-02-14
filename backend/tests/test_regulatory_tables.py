"""
Regulatory Table Tests
======================

Tests for LifeTable.from_regulatory_table() classmethod.

This method loads Mexican regulatory mortality tables (CNSF, EMSSA)
that publish q_x values by sex, and converts them into a full LifeTable
via the recurrence l_{x+1} = l_x * (1 - q_x).

Each test validates a specific actuarial property.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions


# =============================================================================
# Test Data Paths
# =============================================================================

MOCK_DIR = str(Path(__file__).parent.parent / "data" / "mock")


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def cnsf_table():
    """Load mock CNSF 2000-I regulatory table (male)."""
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")
    return LifeTable.from_regulatory_table(filepath, sex="male")


@pytest.fixture
def emssa_table():
    """Load mock EMSSA 2009 regulatory table (male)."""
    filepath = str(Path(MOCK_DIR) / "mock_emssa_2009.csv")
    return LifeTable.from_regulatory_table(filepath, sex="male")


# =============================================================================
# Test: Loading CNSF Table
# =============================================================================

def test_from_regulatory_loads_cnsf(cnsf_table):
    """
    THEORY: A regulatory table in CNSF format (age, qx_male, qx_female)
    should be loadable as a LifeTable.

    The CNSF publishes official mortality tables that insurers must use
    for minimum reserve calculations. The table should span ages 0-100.
    """
    assert cnsf_table.min_age == 0
    assert cnsf_table.max_age == 100
    assert cnsf_table.get_l(0) == 100_000.0


# =============================================================================
# Test: Loading EMSSA Table
# =============================================================================

def test_from_regulatory_loads_emssa(emssa_table):
    """
    THEORY: The EMSSA-2009 table is the Mexican experience mortality table
    derived from Social Security data. It should also be loadable.

    EMSSA stands for "Experiencia Mexicana de Seguridad Social de los
    Actuarios" -- the standard reference for Mexican mortality.
    """
    assert emssa_table.min_age == 0
    assert emssa_table.max_age == 100
    assert emssa_table.get_l(0) == 100_000.0


# =============================================================================
# Test: l_x Recurrence from q_x
# =============================================================================

def test_from_regulatory_correct_lx(cnsf_table):
    """
    THEORY: l_{x+1} = l_x * (1 - q_x)

    When building l_x from q_x, each cohort of survivors is reduced by
    the mortality rate at that age. This is the fundamental recurrence
    that connects the probability column (q_x) to the count column (l_x).

    We verify this at several ages to ensure the conversion is correct.
    """
    for age in [0, 10, 25, 50, 75, 99]:
        l_x = cnsf_table.get_l(age)
        l_x1 = cnsf_table.get_l(age + 1)
        q_x = cnsf_table.get_q(age)
        expected = l_x * (1.0 - q_x)
        assert l_x1 == pytest.approx(expected, rel=1e-9), (
            f"l_{age+1} should equal l_{age} * (1 - q_{age})"
        )


# =============================================================================
# Test: Radix
# =============================================================================

def test_from_regulatory_radix():
    """
    THEORY: The radix l_0 is the initial cohort size.

    By convention, Mexican regulatory tables use l_0 = 100,000.
    The radix scales all absolute counts but does not affect derived
    rates (q_x, p_x), since those are ratios.

    The from_regulatory_table() method should respect a custom radix.
    """
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")

    # Default radix
    lt_default = LifeTable.from_regulatory_table(filepath, sex="male")
    assert lt_default.get_l(0) == 100_000.0

    # Custom radix
    lt_custom = LifeTable.from_regulatory_table(filepath, sex="male", radix=10_000.0)
    assert lt_custom.get_l(0) == 10_000.0

    # q_x should be the same regardless of radix
    assert lt_default.get_q(50) == pytest.approx(lt_custom.get_q(50), rel=1e-9)


# =============================================================================
# Test: Terminal q_x
# =============================================================================

def test_from_regulatory_terminal_qx(cnsf_table):
    """
    THEORY: q_omega = 1.0 (everyone dies at the terminal age)

    This is an actuarial convention: at the last age in the table,
    mortality is certain. The mock data has q_100 = 1.0 for both sexes,
    which means l_101 would be 0. The LifeTable sets q_omega = 1.0
    at construction time.
    """
    assert cnsf_table.get_q(cnsf_table.max_age) == 1.0


# =============================================================================
# Test: Monotonic l_x
# =============================================================================

def test_from_regulatory_monotonic_lx(cnsf_table):
    """
    THEORY: l_x must be strictly decreasing.

    Since q_x > 0 for all ages (people always have some probability of
    dying), each successive l_x must be strictly smaller than the previous.
    This is a basic sanity check for any valid life table.
    """
    ages = cnsf_table.ages
    for i in range(len(ages) - 1):
        l_current = cnsf_table.get_l(ages[i])
        l_next = cnsf_table.get_l(ages[i + 1])
        assert l_next < l_current, (
            f"l_{ages[i+1]} = {l_next} should be less than l_{ages[i]} = {l_current}"
        )


# =============================================================================
# Test: Sex Selection
# =============================================================================

def test_from_regulatory_sex_selection():
    """
    THEORY: Male and female mortality tables differ.

    Male mortality is typically higher than female mortality at most ages.
    The from_regulatory_table() method must correctly select the q_x
    column based on the sex parameter, producing different l_x (and
    therefore different q_x) for each sex.
    """
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")

    lt_male = LifeTable.from_regulatory_table(filepath, sex="male")
    lt_female = LifeTable.from_regulatory_table(filepath, sex="female")

    # q_x should differ between sexes (mock data has different values)
    assert lt_male.get_q(0) != lt_female.get_q(0)

    # Male q_x at age 0 is higher than female (0.0155 vs 0.0128 in mock)
    assert lt_male.get_q(0) > lt_female.get_q(0)

    # l_x at later ages should differ due to accumulated mortality
    assert lt_male.get_l(50) != lt_female.get_l(50)


# =============================================================================
# Test: Integration with Commutation Functions
# =============================================================================

def test_from_regulatory_feeds_commutation(cnsf_table):
    """
    THEORY: A LifeTable from a regulatory table should be usable as input
    to CommutationFunctions without any conversion.

    This tests the integration between the regulatory loader and the
    actuarial engine: CommutationFunctions(life_table, interest_rate)
    should compute D_x, N_x, C_x, M_x without errors.
    """
    comm = CommutationFunctions(cnsf_table, interest_rate=0.05)

    # D_0 = v^0 * l_0 = 1 * 100000 = 100000
    assert comm.get_D(0) == pytest.approx(100_000.0)

    # N_0 should be the sum of all D_x, which is positive
    assert comm.get_N(0) > 0

    # M_0 should be positive (mortality cost)
    assert comm.get_M(0) > 0


# =============================================================================
# Test: Invalid File
# =============================================================================

def test_from_regulatory_invalid_file():
    """
    THEORY: Attempting to load a non-existent file should raise
    FileNotFoundError, consistent with the existing from_csv() behavior.
    """
    with pytest.raises(FileNotFoundError):
        LifeTable.from_regulatory_table("/nonexistent/path.csv")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
