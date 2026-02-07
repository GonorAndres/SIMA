"""
Commutation Functions Tests
============================

Tests for the CommutationFunctions class (Blocks 2-3).

Each test validates a specific property from actuarial theory.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mini_table():
    """Load the mini validation table."""
    data_path = Path(__file__).parent.parent / "data" / "mini_table.csv"
    return LifeTable.from_csv(str(data_path))


@pytest.fixture
def comm(mini_table):
    """Create commutation functions with i=5%."""
    return CommutationFunctions(mini_table, interest_rate=0.05)


# =============================================================================
# Test: Basic Setup
# =============================================================================

def test_discount_factor(comm):
    """
    THEORY: v = 1 / (1 + i)

    The discount factor v is the present value of $1 in one year.
    With i=5%, v = 1/1.05 = 0.952381
    """
    assert comm.v == pytest.approx(1 / 1.05)
    assert comm.v == pytest.approx(0.952381, rel=1e-5)


# =============================================================================
# Test: D_x Calculation
# =============================================================================

def test_D_x_at_min_age(comm):
    """
    THEORY: D_x = v^(x - min_age) * l_x

    At min_age (60), exponent is 0, so D_60 = 1^0 * l_60 = l_60.
    With our normalization, D_60 = 1000.
    """
    # D_60 = v^0 * l_60 = 1 * 1000 = 1000
    assert comm.get_D(60) == pytest.approx(1000.0)


def test_D_x_with_discounting(comm):
    """
    THEORY: D_{x+1} = v * l_{x+1} (normalized)

    Each additional year adds one more power of v (discounting).
    D_61 = v^1 * l_61 = 0.952381 * 850 = 809.52
    """
    v = comm.v
    expected_D_61 = v * 850  # l_61 = 850
    assert comm.get_D(61) == pytest.approx(expected_D_61)


def test_D_decreases_with_age(comm):
    """
    THEORY: D_x decreases with age (both mortality and discounting)

    D combines fewer survivors AND more discounting at higher ages.
    So D_60 > D_61 > D_62 > ... > D_65
    """
    D_values = [comm.get_D(age) for age in range(60, 66)]
    for i in range(len(D_values) - 1):
        assert D_values[i] > D_values[i + 1]


# =============================================================================
# Test: N_x Recursion
# =============================================================================

def test_N_omega_equals_D_omega(comm):
    """
    THEORY: N_omega = D_omega (base case of recursion)

    At the terminal age, N is just D (no future ages to sum).
    """
    assert comm.get_N(65) == comm.get_D(65)


def test_N_recursion_formula(comm):
    """
    THEORY: N_x = D_x + N_{x+1}

    This is the recursive definition computed backwards from omega.
    """
    # N_64 = D_64 + N_65
    expected_N_64 = comm.get_D(64) + comm.get_N(65)
    assert comm.get_N(64) == pytest.approx(expected_N_64)

    # N_60 = D_60 + N_61
    expected_N_60 = comm.get_D(60) + comm.get_N(61)
    assert comm.get_N(60) == pytest.approx(expected_N_60)


def test_N_equals_sum_of_D(comm):
    """
    THEORY: N_x = sum(D_y) for y = x to omega

    N_60 should equal D_60 + D_61 + D_62 + D_63 + D_64 + D_65.
    This validates the recursion implementation.
    """
    sum_D = sum(comm.D.values())
    assert comm.get_N(60) == pytest.approx(sum_D)


# =============================================================================
# Test: C_x Calculation
# =============================================================================

def test_C_x_extra_discounting(comm):
    """
    THEORY: C_x = v^{x+1 - min_age} * d_x

    C has one more power of v than D because death benefits
    are paid at END of year (age x+1), not beginning.
    """
    # C_60 = v^1 * d_60 = 0.952381 * 150 = 142.857
    v = comm.v
    d_60 = 150  # From mini table
    expected_C_60 = v * d_60
    assert comm.get_C(60) == pytest.approx(expected_C_60)


def test_C_vs_D_relationship(comm, mini_table):
    """
    THEORY: C_x / D_x should relate to q_x * v

    C_x = v^{x+1} * d_x, D_x = v^x * l_x
    C_x / D_x = v * (d_x / l_x) = v * q_x
    """
    for age in range(60, 65):  # Not 65 (terminal is special)
        q_x = mini_table.get_q(age)
        ratio = comm.get_C(age) / comm.get_D(age)
        expected = comm.v * q_x
        assert ratio == pytest.approx(expected, rel=1e-4)


# =============================================================================
# Test: M_x Recursion
# =============================================================================

def test_M_omega_equals_C_omega(comm):
    """
    THEORY: M_omega = C_omega (base case of recursion)

    At the terminal age, M is just C (no future ages to sum).
    """
    assert comm.get_M(65) == comm.get_C(65)


def test_M_recursion_formula(comm):
    """
    THEORY: M_x = C_x + M_{x+1}

    This parallels the N recursion.
    """
    # M_64 = C_64 + M_65
    expected_M_64 = comm.get_C(64) + comm.get_M(65)
    assert comm.get_M(64) == pytest.approx(expected_M_64)


def test_M_equals_sum_of_C(comm):
    """
    THEORY: M_x = sum(C_y) for y = x to omega

    M_60 should equal C_60 + C_61 + ... + C_65.
    """
    sum_C = sum(comm.C.values())
    assert comm.get_M(60) == pytest.approx(sum_C)


# =============================================================================
# Test: Difference Formulas (Used in Term Insurance)
# =============================================================================

def test_N_difference_gives_limited_sum(comm):
    """
    THEORY: N_x - N_{x+n} = D_x + D_{x+1} + ... + D_{x+n-1}

    This is used for temporary annuities (n payments).
    The difference excludes ages x+n and beyond.
    """
    # N_60 - N_63 should equal D_60 + D_61 + D_62 (3 terms)
    difference = comm.get_N(60) - comm.get_N(63)
    expected = comm.get_D(60) + comm.get_D(61) + comm.get_D(62)
    assert difference == pytest.approx(expected)


def test_M_difference_gives_limited_sum(comm):
    """
    THEORY: M_x - M_{x+n} = C_x + C_{x+1} + ... + C_{x+n-1}

    This is used for term insurance (n years of coverage).
    """
    # M_60 - M_63 should equal C_60 + C_61 + C_62
    difference = comm.get_M(60) - comm.get_M(63)
    expected = comm.get_C(60) + comm.get_C(61) + comm.get_C(62)
    assert difference == pytest.approx(expected)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
