"""
Mortality Comparison / Validation Tests
========================================

Tests for the MortalityComparison class (Block 10).

Each test validates a specific property of mortality table comparison,
used when validating projected tables against regulatory benchmarks
(e.g., Lee-Carter projections vs EMSSA-2009).
"""

import pytest
import math
import numpy as np
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a10_validation import MortalityComparison


# =============================================================================
# Helper: Build LifeTable from q_x pattern
# =============================================================================

def build_life_table(ages, qx_func, radix=100_000):
    """
    Build a LifeTable from a q_x function.

    Args:
        ages: list of ages
        qx_func: callable age -> q_x (probability of death)
        radix: initial population l_0

    Returns:
        LifeTable
    """
    l_x = [radix]
    for i in range(len(ages) - 1):
        qx = qx_func(ages[i])
        qx = min(qx, 1.0)  # Cap at 1.0
        l_x.append(l_x[-1] * (1 - qx))
    return LifeTable(ages, l_x)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def ages():
    """Standard age range for tests."""
    return list(range(0, 101))


@pytest.fixture
def base_qx():
    """
    Gompertz-like mortality: q_x = 0.0005 * exp(0.07 * x)

    This produces a realistic increasing mortality pattern.
    """
    def qx_func(x):
        return min(0.0005 * math.exp(0.07 * x), 0.99)
    return qx_func


@pytest.fixture
def base_table(ages, base_qx):
    """A LifeTable with base mortality."""
    return build_life_table(ages, base_qx)


@pytest.fixture
def identical_table(ages, base_qx):
    """A second LifeTable with the same mortality (for identity tests)."""
    return build_life_table(ages, base_qx)


@pytest.fixture
def double_mortality_table(ages, base_qx):
    """A LifeTable with 2x the base mortality rates."""
    def double_qx(x):
        return min(2.0 * base_qx(x), 0.99)
    return build_life_table(ages, double_qx)


# =============================================================================
# Test: Identical Tables
# =============================================================================

def test_identical_tables_ratio_one(base_table, identical_table):
    """
    THEORY: When projected == regulatory, q_x ratio should be 1.0 everywhere.

    If two tables have the same mortality rates, the ratio
    projected_qx / regulatory_qx = 1.0 for every age.
    This is the baseline: no deviation means perfect agreement.
    """
    comp = MortalityComparison(base_table, identical_table, name="identity")
    ratios = comp.qx_ratio()

    np.testing.assert_allclose(ratios, 1.0, rtol=1e-10)


def test_identical_tables_rmse_zero(base_table, identical_table):
    """
    THEORY: When projected == regulatory, RMSE should be 0.0.

    RMSE = sqrt(mean((proj_qx - reg_qx)^2)) = sqrt(0) = 0.
    Zero RMSE means perfect fit between the two tables.
    """
    comp = MortalityComparison(base_table, identical_table, name="identity")
    assert comp.rmse() == pytest.approx(0.0, abs=1e-15)


# =============================================================================
# Test: Known Differences
# =============================================================================

def test_known_difference_ratio(base_table, double_mortality_table, base_qx):
    """
    THEORY: If projected has 2x the mortality, ratio should be ~2.0.

    The q_x ratio measures the multiplicative loading between tables.
    For ages where 2*q_x < 0.99 (i.e., not capped), the ratio is exactly 2.0.

    Note: at very high ages, the cap at 0.99 means the ratio will be
    less than 2.0. We check only the uncapped ages.
    """
    comp = MortalityComparison(double_mortality_table, base_table, name="2x")
    ratios = comp.qx_ratio()

    # Find ages where base q_x is small enough that doubling doesn't hit the cap
    uncapped_count = 0
    for i, age in enumerate(comp.overlap_ages[:-1]):  # Exclude terminal
        base_q = base_qx(age)
        if 2.0 * base_q < 0.99:
            assert ratios[i] == pytest.approx(2.0, rel=1e-6), \
                f"Ratio at age {age} should be 2.0, got {ratios[i]}"
            uncapped_count += 1

    assert uncapped_count > 50, "Should have many uncapped ages to verify"


def test_known_difference_rmse(ages):
    """
    THEORY: RMSE matches hand calculation for a known difference.

    For a constant q_x offset: if projected q_x = 0.02 and regulatory q_x = 0.01
    for all ages in [20, 80], then:
        RMSE = sqrt(mean((0.02 - 0.01)^2)) = sqrt(0.0001) = 0.01

    We use constant mortality for easy verification.
    """
    # Constant mortality tables
    proj_table = build_life_table(ages, lambda x: 0.02)
    reg_table = build_life_table(ages, lambda x: 0.01)

    comp = MortalityComparison(proj_table, reg_table, name="constant")
    rmse = comp.rmse(age_start=20, age_end=80)

    # Hand calculation: all differences are 0.02 - 0.01 = 0.01
    # But q_x is DERIVED from l_x, so q_x = d_x/l_x = (l_x - l_{x+1})/l_x
    # For constant survival: l_{x+1} = l_x * (1 - q), so q_x = q exactly.
    # RMSE = sqrt(mean(0.01^2)) = 0.01
    assert rmse == pytest.approx(0.01, rel=1e-6)


# =============================================================================
# Test: Difference Sign
# =============================================================================

def test_qx_difference_sign(base_table, double_mortality_table):
    """
    THEORY: Difference should be positive when projected > regulatory.

    q_x difference = projected_qx - regulatory_qx.
    If the projected table has higher mortality, the difference is positive.
    This tells us which direction the projection deviates from the benchmark.
    """
    comp = MortalityComparison(double_mortality_table, base_table, name="higher")
    diffs = comp.qx_difference()

    # All differences should be >= 0 (projected has higher or equal mortality)
    assert np.all(diffs >= -1e-15), "Differences should be non-negative"
    # At least some should be strictly positive
    assert np.any(diffs > 0), "Some differences should be strictly positive"


# =============================================================================
# Test: Age Range Filtering
# =============================================================================

def test_age_range_filtering(ages):
    """
    THEORY: RMSE computed only over specified ages [age_start, age_end].

    In practice, actuaries focus RMSE on working ages (e.g., 20-80)
    because infant mortality and extreme old ages behave differently
    and can distort aggregate fit measures.

    We verify by using two tables that differ only outside [20, 80].
    Inside [20, 80] they are identical, so RMSE over that range should be 0.
    """
    def qx_base(x):
        return 0.001 * math.exp(0.05 * x)

    def qx_modified(x):
        # Same as base for ages 20-80, different outside
        if x < 20 or x > 80:
            return min(0.002 * math.exp(0.05 * x), 0.99)
        return qx_base(x)

    table_a = build_life_table(ages, qx_base)
    table_b = build_life_table(ages, qx_modified)

    comp = MortalityComparison(table_a, table_b, name="filtered")

    # Over [20, 80] the q_x functions are identical, but l_x differs
    # because l_x depends on cumulative survival from age 0.
    # So q_x will NOT be exactly equal in [20,80] if l_x differs.
    # Instead, test with truly same q_x by using tables that start at 20.
    ages_20_80 = list(range(20, 81))
    table_c = build_life_table(ages_20_80, qx_base)
    table_d = build_life_table(ages_20_80, qx_base)

    comp2 = MortalityComparison(table_c, table_d, name="same_range")
    assert comp2.rmse(age_start=20, age_end=80) == pytest.approx(0.0, abs=1e-15)

    # Now test that specifying a narrower range excludes other ages
    # Use a table where ages 20-50 match but 51-80 differ
    def qx_split(x):
        if x <= 50:
            return qx_base(x)
        return qx_base(x) * 2

    table_e = build_life_table(ages_20_80, qx_base)
    table_f = build_life_table(ages_20_80, qx_split)

    comp3 = MortalityComparison(table_e, table_f, name="split")
    # RMSE over [20, 50] should be 0 (q_x are the same)
    assert comp3.rmse(age_start=20, age_end=50) == pytest.approx(0.0, abs=1e-15)
    # RMSE over [51, 80] should be > 0
    assert comp3.rmse(age_start=51, age_end=80) > 0


# =============================================================================
# Test: Summary Output
# =============================================================================

def test_summary_keys(base_table, identical_table):
    """
    THEORY: summary() returns expected dict keys for regulatory reporting.

    The summary provides a quick overview of how a projected table
    compares to the regulatory benchmark:
    - name: identifier for the comparison
    - rmse: overall fit measure
    - max_ratio / min_ratio: extremes of the mortality loading
    - mean_ratio: average loading factor
    - n_ages: number of ages in the comparison
    """
    comp = MortalityComparison(base_table, identical_table, name="test")
    s = comp.summary()

    expected_keys = {"name", "rmse", "max_ratio", "min_ratio", "mean_ratio", "n_ages"}
    assert set(s.keys()) == expected_keys

    assert s["name"] == "test"
    assert s["n_ages"] > 0
    assert isinstance(s["rmse"], float)
    assert isinstance(s["max_ratio"], float)
    assert isinstance(s["min_ratio"], float)
    assert isinstance(s["mean_ratio"], float)


# =============================================================================
# Test: Error Cases
# =============================================================================

def test_mismatched_ages_error():
    """
    THEORY: ValueError when age ranges don't overlap.

    Two tables with completely disjoint age ranges cannot be compared.
    For example, a pediatric table (0-18) and a geriatric table (65-100)
    have no overlapping ages, so comparison is meaningless.
    """
    ages_young = list(range(0, 20))
    ages_old = list(range(80, 101))

    table_young = build_life_table(ages_young, lambda x: 0.001)
    table_old = build_life_table(ages_old, lambda x: 0.05)

    with pytest.raises(ValueError, match="overlap"):
        MortalityComparison(table_young, table_old)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
