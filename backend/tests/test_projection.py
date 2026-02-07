"""
Mortality Projection Tests (a09)
=================================

Validates that RWD projection of k_t produces reasonable mortality
forecasts and the bridge to LifeTable works correctly.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator


# =============================================================================
# Test Fixtures
# =============================================================================

DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")


@pytest.fixture
def usa_lc():
    """Fit Lee-Carter to USA data."""
    data = MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )
    return LeeCarter.fit(data, reestimate_kt=True)


@pytest.fixture
def projection(usa_lc):
    """Create 30-year projection from USA Lee-Carter."""
    return MortalityProjection(usa_lc, horizon=30, n_simulations=1000, random_seed=42)


# =============================================================================
# Test: Drift and Sigma Estimation
# =============================================================================

def test_drift_computation_for_linear_kt():
    """
    THEORY: For perfectly linear k_t, drift = slope and sigma = 0.
    """
    # Create a mock LeeCarter with perfectly linear k_t
    class MockLC:
        pass

    lc = MockLC()
    lc.ages = np.arange(0, 101)
    lc.years = np.arange(1990, 2021)
    lc.ax = np.zeros(101)
    lc.bx = np.ones(101) / 101
    lc.kt = np.linspace(10, -20, 31)  # Perfect linear decline

    proj = MortalityProjection(lc, horizon=10, n_simulations=100, random_seed=42)
    expected_drift = (-20 - 10) / 30  # = -1.0
    assert proj.drift == pytest.approx(expected_drift, rel=1e-6)
    assert proj.sigma == pytest.approx(0.0, abs=1e-10)


def test_drift_is_negative(projection):
    """
    THEORY: For USA with improving mortality, drift should be negative
    (k_t is decreasing over time).
    """
    assert projection.drift < 0


def test_sigma_is_positive(projection):
    """Volatility of k_t changes should be positive."""
    assert projection.sigma > 0


# =============================================================================
# Test: Central Projection
# =============================================================================

def test_central_projection_extends_trend(projection):
    """
    THEORY: Central k_t should continue the downward trend.
    First projected value should be close to last observed + drift.
    """
    kt_last = projection.lee_carter.kt[-1]
    expected_first = kt_last + projection.drift
    assert projection.kt_central[0] == pytest.approx(expected_first)


def test_central_projection_length(projection):
    """Central projection should have exactly 'horizon' values."""
    assert len(projection.kt_central) == projection.horizon


def test_projected_years_correct(projection, usa_lc):
    """Projected years should start right after the last observed year."""
    assert projection.projected_years[0] == int(usa_lc.years[-1]) + 1
    assert len(projection.projected_years) == projection.horizon


# =============================================================================
# Test: Stochastic Simulation
# =============================================================================

def test_simulated_mean_near_central(projection):
    """
    THEORY: By law of large numbers, the mean of N simulated paths
    should be close to the central (deterministic) projection.
    Use relative tolerance since values grow with horizon.
    """
    sim_mean = np.mean(projection.kt_simulated, axis=0)
    np.testing.assert_allclose(sim_mean, projection.kt_central, atol=2.0, rtol=0.15)


def test_ci_bands_widen_with_horizon(projection):
    """
    THEORY: Uncertainty grows with horizon (sqrt(h) in RWD).
    CI should be wider for year +30 than for year +1.
    """
    ci_1 = projection.get_confidence_interval(50, projection.projected_years[0])
    ci_30 = projection.get_confidence_interval(50, projection.projected_years[-1])

    width_1 = ci_1[1] - ci_1[0]
    width_30 = ci_30[1] - ci_30[0]
    assert width_30 > width_1


def test_reproducibility_with_same_seed(usa_lc):
    """Same seed should produce identical simulations."""
    proj1 = MortalityProjection(usa_lc, horizon=10, n_simulations=100, random_seed=42)
    proj2 = MortalityProjection(usa_lc, horizon=10, n_simulations=100, random_seed=42)
    np.testing.assert_array_equal(proj1.kt_simulated, proj2.kt_simulated)


# =============================================================================
# Test: Bridge to LifeTable
# =============================================================================

def test_to_life_table_returns_valid(projection):
    """
    THEORY: The projected LifeTable must pass all standard validations:
    sum(d_x) = l_0, terminal q = 1.0, all rates in [0,1].
    """
    lt = projection.to_life_table(projection.projected_years[0])
    assert isinstance(lt, LifeTable)

    v = lt.validate()
    assert v["sum_deaths_equals_l0"], "sum(d_x) != l_0"
    assert v["terminal_mortality_is_one"], "q_omega != 1"
    assert v["all_rates_valid"], "Some q_x outside [0,1]"


def test_to_life_table_terminal_qx(projection):
    """Terminal age must have q_x = 1.0 (everyone dies)."""
    lt = projection.to_life_table(projection.projected_years[0])
    assert lt.q_x[lt.max_age] == 1.0


def test_to_life_table_radix(projection):
    """l_0 should equal the specified radix."""
    lt = projection.to_life_table(projection.projected_years[0], radix=100_000)
    assert lt.l_x[lt.min_age] == 100_000


def test_to_life_table_with_ci_returns_three(projection):
    """to_life_table_with_ci should return central, optimistic, pessimistic."""
    central, optimistic, pessimistic = projection.to_life_table_with_ci(
        projection.projected_years[5]
    )
    assert isinstance(central, LifeTable)
    assert isinstance(optimistic, LifeTable)
    assert isinstance(pessimistic, LifeTable)

    # All should be valid
    for lt in [central, optimistic, pessimistic]:
        v = lt.validate()
        assert v["sum_deaths_equals_l0"]


# =============================================================================
# Test: End-to-End Integration
# =============================================================================

def test_projected_life_table_feeds_into_commutations(projection):
    """
    INTEGRATION: Projected LifeTable should work with CommutationFunctions.
    This proves the bridge from Lee-Carter to the Phase 2 engine.
    """
    lt = projection.to_life_table(projection.projected_years[0], radix=100_000)
    # Use a subset starting at age 20 for insurance calculations
    lt_sub = lt.subset(20, 100)
    comm = CommutationFunctions(lt_sub, interest_rate=0.05)

    # D_x should be positive and decreasing
    assert comm.get_D(20) > 0
    assert comm.get_D(20) > comm.get_D(50)

    # N_x should be positive
    assert comm.get_N(20) > 0


def test_projected_life_table_feeds_into_premiums(projection):
    """
    INTEGRATION: Full pipeline from projection to premium calculation.
    HMD -> Lee-Carter -> Project -> LifeTable -> Premium.
    """
    lt = projection.to_life_table(projection.projected_years[0], radix=100_000)
    lt_sub = lt.subset(30, 100)

    comm = CommutationFunctions(lt_sub, interest_rate=0.05)
    pc = PremiumCalculator(comm)

    # Whole life premium should be positive and < SA
    sa = 1_000_000
    premium = pc.whole_life(SA=sa, x=30)
    assert premium > 0, "Premium must be positive"
    assert premium < sa, "Premium must be less than sum assured"


# =============================================================================
# Test: Validate and Summary
# =============================================================================

def test_validate_all_pass(projection):
    """All validations should pass for a well-formed projection."""
    v = projection.validate()
    assert v["drift_is_negative"]
    assert v["sigma_positive"]
    assert v["central_extends_trend"]
    assert v["no_nan_in_central"]


def test_summary_has_expected_keys(projection):
    """Summary should contain all key projection parameters."""
    s = projection.summary()
    assert "drift" in s
    assert "sigma" in s
    assert "horizon" in s
    assert s["horizon"] == 30


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
