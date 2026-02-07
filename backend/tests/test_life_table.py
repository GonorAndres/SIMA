"""
Life Table Tests
================

Tests for the LifeTable class (Block 1).

Each test validates a specific property from actuarial theory.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mini_table():
    """Load the mini validation table (ages 60-65)."""
    data_path = Path(__file__).parent.parent / "data" / "mini_table.csv"
    return LifeTable.from_csv(str(data_path))


@pytest.fixture
def sample_table():
    """Load the full sample table (ages 20-110)."""
    data_path = Path(__file__).parent.parent / "data" / "sample_mortality.csv"
    return LifeTable.from_csv(str(data_path))


# =============================================================================
# Test: Life Table Structure
# =============================================================================

def test_table_loads_correctly(mini_table):
    """
    THEORY: Life table should load with correct age boundaries.

    The table should know its min and max ages (omega).
    """
    assert mini_table.min_age == 60
    assert mini_table.max_age == 65
    assert mini_table.omega == 65  # omega is the ultimate age


def test_l_x_values_loaded(mini_table):
    """
    THEORY: l_x (survivors) should be loaded from CSV.

    l_60 = 1000 is our starting cohort.
    """
    assert mini_table.get_l(60) == 1000.0
    assert mini_table.get_l(65) == 200.0


# =============================================================================
# Test: d_x Derivation
# =============================================================================

def test_d_x_derivation(mini_table):
    """
    THEORY: d_x = l_x - l_{x+1}

    Deaths at age x = survivors at x minus survivors at x+1.
    This is the "flow" of people leaving the alive state.
    """
    # d_60 = l_60 - l_61 = 1000 - 850 = 150
    assert mini_table.get_d(60) == pytest.approx(150.0)

    # d_61 = l_61 - l_62 = 850 - 700 = 150
    assert mini_table.get_d(61) == pytest.approx(150.0)

    # d_64 = l_64 - l_65 = 370 - 200 = 170
    assert mini_table.get_d(64) == pytest.approx(170.0)


def test_terminal_age_deaths(mini_table):
    """
    THEORY: d_omega = l_omega (everyone remaining dies at terminal age)

    At the ultimate age, all survivors die.
    """
    # d_65 = l_65 = 200
    assert mini_table.get_d(65) == mini_table.get_l(65)
    assert mini_table.get_d(65) == 200.0


# =============================================================================
# Test: q_x Derivation
# =============================================================================

def test_q_x_derivation(mini_table):
    """
    THEORY: q_x = d_x / l_x

    Mortality rate at age x = deaths / survivors.
    This is the conditional probability of death given survival to x.
    """
    # q_60 = d_60 / l_60 = 150 / 1000 = 0.15
    assert mini_table.get_q(60) == pytest.approx(0.15)

    # q_61 = d_61 / l_61 = 150 / 850 = 0.1765
    assert mini_table.get_q(61) == pytest.approx(150 / 850)


def test_terminal_mortality_is_one(mini_table):
    """
    THEORY: q_omega = 1.0

    At the terminal age, death is certain.
    Everyone who reaches omega dies before omega+1.
    """
    assert mini_table.get_q(65) == 1.0


# =============================================================================
# Test: p_x Derivation
# =============================================================================

def test_p_x_derivation(mini_table):
    """
    THEORY: p_x = 1 - q_x

    Survival rate is the complement of mortality rate.
    """
    # p_60 = 1 - q_60 = 1 - 0.15 = 0.85
    assert mini_table.get_p(60) == pytest.approx(0.85)

    # p_65 = 1 - 1.0 = 0.0 (terminal age)
    assert mini_table.get_p(65) == 0.0


# =============================================================================
# Test: Fundamental Validation - Sum of Deaths = Initial Population
# =============================================================================

def test_sum_of_deaths_equals_l0(mini_table):
    """
    THEORY: sum(d_x) from x to omega = l_x (for any starting x)

    Everyone who is alive at the start must eventually die.
    This is a conservation law: people flow from alive to dead.

    Mathematical proof:
        sum(d_x) = (l_60 - l_61) + (l_61 - l_62) + ... + l_65
                 = l_60  (telescoping sum)
    """
    total_deaths = sum(mini_table.d_x.values())
    initial_population = mini_table.get_l(60)

    assert total_deaths == pytest.approx(initial_population)


def test_validation_method(mini_table):
    """
    THEORY: The validate() method should check all invariants.

    This is the sanity check for any life table.
    """
    results = mini_table.validate()

    assert results['sum_deaths_equals_l0'] == True
    assert results['terminal_mortality_is_one'] == True
    assert results['all_rates_valid'] == True


# =============================================================================
# Test: Subsetting
# =============================================================================

def test_subset_creation(sample_table):
    """
    THEORY: Subsetting should preserve l_x values and recompute derivatives.

    This is useful for validation: subset to ages 60-65 and compare.
    """
    subset = sample_table.subset(60, 65)

    assert subset.min_age == 60
    assert subset.max_age == 65
    assert subset.get_l(60) == sample_table.get_l(60)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
