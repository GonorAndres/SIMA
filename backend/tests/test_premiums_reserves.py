"""
Premiums and Reserves Tests
============================

Tests for PremiumCalculator and ReserveCalculator (Blocks 5-6).

These tests validate the equivalence principle and reserve properties.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator


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


@pytest.fixture
def av(comm):
    """Create actuarial values calculator."""
    return ActuarialValues(comm)


@pytest.fixture
def pc(comm):
    """Create premium calculator."""
    return PremiumCalculator(comm)


@pytest.fixture
def rc(comm):
    """Create reserve calculator."""
    return ReserveCalculator(comm)


# =============================================================================
# Test: Actuarial Identity A_x + d*a_x = 1
# =============================================================================

def test_actuarial_identity(comm, av):
    """
    THEORY: A_x + d * a_due_x = 1

    Where d = i/(1+i) = iv (the discount rate).

    This identity says: the PV of $1 at death (A_x) plus the
    PV of interest earned on $1/year annuity (d * a_x) equals $1.

    Proof: A_x = 1 - d*a_x (by definition of whole life insurance)
    """
    i = comm.i
    d = i / (1 + i)  # d = iv

    for age in range(60, 66):
        A = av.A_x(age)
        a = av.a_due(age)
        result = A + d * a
        assert result == pytest.approx(1.0, rel=1e-6)


# =============================================================================
# Test: Equivalence Principle (Premium Verification)
# =============================================================================

def test_whole_life_equivalence(comm, av, pc):
    """
    THEORY: APV(Premiums) = APV(Benefits) at issue

    P * a_due_x = SA * A_x

    This is the fundamental pricing equation.
    If this holds, the premium is "fair" (no expected profit or loss).
    """
    SA = 100_000
    x = 60

    P = pc.whole_life(SA, x)
    A_x = av.A_x(x)
    a_due_x = av.a_due(x)

    apv_premiums = P * a_due_x
    apv_benefits = SA * A_x

    assert apv_premiums == pytest.approx(apv_benefits, rel=1e-6)


def test_premium_formula_directly(comm, pc):
    """
    THEORY: P = SA * M_x / N_x (for whole life)

    Direct verification of the simplified formula.
    """
    SA = 100_000
    x = 60

    M_x = comm.get_M(x)
    N_x = comm.get_N(x)
    expected_P = SA * M_x / N_x

    actual_P = pc.whole_life(SA, x)

    assert actual_P == pytest.approx(expected_P)


def test_term_premium_less_than_whole_life(pc):
    """
    THEORY: Term premium < Whole life premium (for same SA and age)

    Term insurance only covers n years, so it's cheaper than
    whole life which covers until death.
    """
    SA = 100_000
    x = 60
    n = 3

    P_term = pc.term(SA, x, n)
    P_whole = pc.whole_life(SA, x)

    assert P_term < P_whole


def test_endowment_premium_greater_than_term(pc):
    """
    THEORY: Endowment premium > Term premium (same SA, age, term)

    Endowment pays at death OR survival, so it's more expensive.
    The insurer WILL pay (either at death or maturity).
    """
    SA = 100_000
    x = 60
    n = 3

    P_term = pc.term(SA, x, n)
    P_endow = pc.endowment(SA, x, n)

    assert P_endow > P_term


# =============================================================================
# Test: Zero Reserve at Issue (Equivalence Principle)
# =============================================================================

def test_zero_reserve_at_issue_whole_life(rc):
    """
    THEORY: 0V_x = 0 (reserve at issue is zero)

    At t=0:
        0V = SA * A_x - P * a_due_x = 0

    This is a consequence of the equivalence principle.
    If P is set so APV(premiums) = APV(benefits), then reserve = 0.
    """
    SA = 100_000
    x = 60

    reserve_0 = rc.reserve_whole_life(SA, x, t=0)

    assert reserve_0 == pytest.approx(0.0, abs=0.01)


def test_zero_reserve_at_issue_term(rc):
    """
    THEORY: 0V = 0 for term insurance too.
    """
    SA = 100_000
    x = 60
    n = 5

    reserve_0 = rc.reserve_term(SA, x, n, t=0)

    assert reserve_0 == pytest.approx(0.0, abs=0.01)


def test_zero_reserve_at_issue_endowment(rc):
    """
    THEORY: 0V = 0 for endowment too.
    """
    SA = 100_000
    x = 60
    n = 5

    reserve_0 = rc.reserve_endowment(SA, x, n, t=0)

    assert reserve_0 == pytest.approx(0.0, abs=0.01)


# =============================================================================
# Test: Reserve Growth
# =============================================================================

def test_reserve_increases_over_time(rc):
    """
    THEORY: Reserve increases as policy ages (for whole life)

    As time passes:
    - Fewer premium payments remain (a_due decreases)
    - Death becomes more certain (A increases)
    - Net: reserve grows
    """
    SA = 100_000
    x = 60

    reserves = [rc.reserve_whole_life(SA, x, t) for t in range(6)]

    # Each reserve should be greater than the previous
    for i in range(1, len(reserves)):
        assert reserves[i] > reserves[i - 1]


def test_reserve_trajectory_starts_at_zero(rc):
    """
    THEORY: Trajectory should start at 0V = 0.
    """
    SA = 100_000
    x = 60

    trajectory = rc.reserve_trajectory(SA, x, product="whole_life")

    # First entry is (t=0, reserve~0)
    t_0, reserve_0 = trajectory[0]
    assert t_0 == 0
    assert reserve_0 == pytest.approx(0.0, abs=0.01)


# =============================================================================
# Test: Reserve Formula Components
# =============================================================================

def test_reserve_formula_components(comm, av, pc, rc):
    """
    THEORY: tV = SA * A_{x+t} - P * a_due_{x+t}

    Verify the formula by computing each component.
    """
    SA = 100_000
    x = 60
    t = 3

    # Get premium (fixed at issue)
    P = pc.whole_life(SA, x)

    # Get values at attained age
    attained = x + t
    A_attained = av.A_x(attained)
    a_attained = av.a_due(attained)

    # Manual calculation
    expected_reserve = SA * A_attained - P * a_attained

    # From reserve calculator
    actual_reserve = rc.reserve_whole_life(SA, x, t)

    assert actual_reserve == pytest.approx(expected_reserve)


# =============================================================================
# Test: Term Insurance Reserve at Expiry
# =============================================================================

def test_term_reserve_zero_at_expiry(rc):
    """
    THEORY: Term reserve = 0 when t >= n (policy expired)

    After the term ends, there's no coverage and no liability.
    """
    SA = 100_000
    x = 60
    n = 3

    # At t=3 (just at expiry)
    reserve_at_n = rc.reserve_term(SA, x, n, t=n)
    assert reserve_at_n == 0.0

    # After expiry
    reserve_after = rc.reserve_term(SA, x, n, t=n+1)
    assert reserve_after == 0.0


# =============================================================================
# Test: Endowment Reserve at Maturity
# =============================================================================

def test_endowment_reserve_equals_SA_at_maturity(rc):
    """
    THEORY: nV_{x:n|} = SA at maturity

    At maturity, the endowment must pay SA (survival benefit).
    So the reserve equals the full sum assured.
    """
    SA = 100_000
    x = 60
    n = 5

    reserve_at_n = rc.reserve_endowment(SA, x, n, t=n)

    assert reserve_at_n == pytest.approx(SA)


# =============================================================================
# Test: Validation Method
# =============================================================================

def test_validate_zero_reserve_method(rc):
    """
    Test the validation method returns correct structure.
    """
    SA = 100_000
    x = 60

    result = rc.validate_zero_reserve(SA, x, product="whole_life")

    assert result['product'] == "whole_life"
    assert result['issue_age'] == x
    assert result['sum_assured'] == SA
    assert result['is_zero'] == True
    assert abs(result['reserve_at_0']) < 0.01


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
