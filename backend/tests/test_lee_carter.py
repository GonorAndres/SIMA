"""
Lee-Carter Model Tests (a08)
=============================

Validates the Lee-Carter decomposition produces correct parameters
and satisfies identifiability constraints.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter


# =============================================================================
# Test Fixtures
# =============================================================================

DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")


@pytest.fixture
def usa_data():
    """Load USA male mortality data."""
    return MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )


@pytest.fixture
def usa_lc(usa_data):
    """Fit Lee-Carter to USA data (with k_t re-estimation)."""
    return LeeCarter.fit(usa_data, reestimate_kt=True)


@pytest.fixture
def usa_lc_no_reest(usa_data):
    """Fit Lee-Carter to USA data WITHOUT k_t re-estimation."""
    return LeeCarter.fit(usa_data, reestimate_kt=False)


@pytest.fixture
def spain_data():
    """Load Spain male mortality data."""
    return MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="spain",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )


@pytest.fixture
def spain_lc(spain_data):
    """Fit Lee-Carter to Spain data."""
    return LeeCarter.fit(spain_data, reestimate_kt=True)


# =============================================================================
# Test: a_x Computation
# =============================================================================

def test_ax_equals_row_means(usa_data, usa_lc_no_reest):
    """
    THEORY: a_x = mean_t(ln(m_{x,t})).
    For the non-re-estimated version, a_x should be exact row means.
    """
    log_mx = np.log(usa_data.mx)
    expected_ax = np.mean(log_mx, axis=1)
    np.testing.assert_allclose(usa_lc_no_reest.ax, expected_ax, rtol=1e-10)


def test_ax_shape(usa_lc):
    """a_x should have one value per age."""
    assert len(usa_lc.ax) == usa_lc.n_ages


# =============================================================================
# Test: Identifiability Constraints
# =============================================================================

def test_bx_sums_to_one(usa_lc):
    """
    THEORY: sum(b_x) = 1 is the normalization constraint.
    Without it, b_x and k_t could trade scale arbitrarily.
    """
    assert np.sum(usa_lc.bx) == pytest.approx(1.0, abs=1e-6)


def test_bx_sums_to_one_no_reest(usa_lc_no_reest):
    """Constraint holds even without re-estimation."""
    assert np.sum(usa_lc_no_reest.bx) == pytest.approx(1.0, abs=1e-6)


def test_kt_sums_to_zero(usa_lc):
    """
    THEORY: sum(k_t) = 0 centers the time index.
    This ensures a_x captures the true average level.
    """
    assert np.sum(usa_lc.kt) == pytest.approx(0.0, abs=1e-6)


def test_kt_sums_to_zero_no_reest(usa_lc_no_reest):
    """Constraint holds even without re-estimation."""
    assert np.sum(usa_lc_no_reest.kt) == pytest.approx(0.0, abs=1e-6)


# =============================================================================
# Test: SVD Reconstruction Quality
# =============================================================================

def test_svd_explains_significant_variance(usa_lc):
    """
    THEORY: The first SVD component should capture the dominant mortality
    trend. For developed countries, this is typically >70%.
    """
    assert usa_lc.explained_variance > 0.70


def test_fitted_rates_approximate_input(usa_lc):
    """
    THEORY: exp(a_x + b_x * k_t) should approximate observed rates.
    Check that RMSE in log-space is reasonable (< 0.3).
    """
    gof = usa_lc.goodness_of_fit()
    assert gof["rmse"] < 0.3


# =============================================================================
# Test: k_t Behavior
# =============================================================================

def test_kt_generally_decreasing(usa_lc):
    """
    THEORY: For countries with improving mortality, k_t should
    generally decrease over time (mortality declining).
    """
    # Check overall trend: last value < first value
    assert usa_lc.kt[-1] < usa_lc.kt[0], (
        f"k_t should decrease: k_t[0]={usa_lc.kt[0]:.2f}, k_t[-1]={usa_lc.kt[-1]:.2f}"
    )


def test_kt_length_matches_years(usa_lc):
    """k_t should have one value per year."""
    assert len(usa_lc.kt) == usa_lc.n_years


# =============================================================================
# Test: k_t Re-estimation
# =============================================================================

def test_reestimated_kt_matches_deaths(usa_data, usa_lc):
    """
    THEORY: After re-estimation, model-implied deaths should match
    observed deaths per year within 0.1%.

    sum_x L_{x,t} * exp(a_x + b_x * k_t) ≈ sum_x d_{x,t}
    """
    for t_idx in range(usa_lc.n_years):
        observed = np.sum(usa_data.dx[:, t_idx])
        model_rates = np.exp(usa_lc.ax + usa_lc.bx * usa_lc.kt[t_idx])
        model_deaths = np.sum(usa_data.ex[:, t_idx] * model_rates)
        relative_error = abs(model_deaths - observed) / observed
        assert relative_error < 0.001, (
            f"Year {usa_lc.years[t_idx]}: relative error = {relative_error:.4f}"
        )


# =============================================================================
# Test: Synthetic Data Recovery
# =============================================================================

def test_synthetic_data_recovery():
    """
    THEORY: If we generate data from known a_x, b_x, k_t, the
    Lee-Carter fit should recover those parameters (up to centering).
    """
    np.random.seed(42)
    n_ages, n_years = 20, 30

    # Known parameters
    true_ax = np.linspace(-6, -1, n_ages)  # Increasing with age
    true_bx = np.ones(n_ages) / n_ages     # Uniform sensitivity
    true_kt = np.linspace(5, -5, n_years)  # Decreasing trend

    # Generate synthetic mx (no noise)
    log_mx = true_ax[:, np.newaxis] + np.outer(true_bx, true_kt)
    mx = np.exp(log_mx)

    # Create a minimal MortalityData-like object
    class SyntheticData:
        pass

    data = SyntheticData()
    data.ages = np.arange(n_ages)
    data.years = np.arange(n_years)
    data.mx = mx
    data.dx = mx * 10000  # Dummy deaths
    data.ex = np.full_like(mx, 10000)  # Uniform exposure

    # Fit (without re-estimation to test pure SVD recovery)
    lc = LeeCarter.fit(data, reestimate_kt=False)

    # a_x should match true_ax closely
    np.testing.assert_allclose(lc.ax, true_ax, atol=0.01)

    # b_x shape should match (scale may differ due to constraint)
    # But b_x should be uniform
    assert np.std(lc.bx) < 0.01, "b_x should be approximately uniform"

    # k_t trend should match
    assert lc.kt[-1] < lc.kt[0], "k_t should be decreasing like true_kt"

    # Near-perfect reconstruction
    assert lc.explained_variance > 0.999


# =============================================================================
# Test: Country Comparison
# =============================================================================

def test_usa_vs_spain_different_parameters(usa_lc, spain_lc):
    """
    Different countries should produce different a_x and k_t parameters.
    """
    # a_x should differ (different mortality levels)
    assert not np.allclose(usa_lc.ax, spain_lc.ax, atol=0.1)

    # k_t should differ (different mortality histories)
    assert not np.allclose(usa_lc.kt, spain_lc.kt, atol=1.0)


# =============================================================================
# Test: Accessor Methods
# =============================================================================

def test_get_ax_returns_float(usa_lc):
    """get_ax should return a single float."""
    val = usa_lc.get_ax(50)
    assert isinstance(val, float)


def test_fitted_rate_is_positive(usa_lc):
    """Fitted rates must be positive (exp of anything is positive)."""
    rate = usa_lc.fitted_rate(50, 2000)
    assert rate > 0


def test_fitted_mx_matrix_shape(usa_lc):
    """Fitted matrix should have same shape as input."""
    fitted = usa_lc.fitted_mx_matrix()
    assert fitted.shape == (usa_lc.n_ages, usa_lc.n_years)


# =============================================================================
# Test: Validation and Summary
# =============================================================================

def test_validate_all_pass(usa_lc):
    """All validation checks should pass for a properly fitted model."""
    v = usa_lc.validate()
    assert v["bx_sums_to_one"] is True
    assert v["kt_sums_to_zero"] is True
    assert v["no_nan"] is True
    assert v["explained_var_reasonable"] is True


def test_summary_contains_trend(usa_lc):
    """Summary should indicate k_t trend direction."""
    s = usa_lc.summary()
    assert s["kt_trend"] == "decreasing"


# =============================================================================
# Test: fit_from_hmd convenience
# =============================================================================

def test_fit_from_hmd():
    """fit_from_hmd should load data and fit in one step."""
    lc = LeeCarter.fit_from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=2000,
        year_max=2015,
        age_max=100,
    )
    assert lc.n_ages == 101
    assert lc.n_years == 16
    assert np.sum(lc.bx) == pytest.approx(1.0, abs=1e-6)


def test_fit_from_hmd_with_graduation():
    """fit_from_hmd with graduation should also work."""
    lc = LeeCarter.fit_from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=2000,
        year_max=2015,
        age_max=100,
        graduate=True,
    )
    assert lc.n_ages == 101
    assert lc.explained_variance > 0.5


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
