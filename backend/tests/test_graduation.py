"""
Graduation Tests (a07)
=======================

Validates Whittaker-Henderson smoothing produces graduated rates that
are smoother than raw data while preserving essential mortality patterns.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates


# =============================================================================
# Test Fixtures
# =============================================================================

DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")


@pytest.fixture
def usa_raw():
    """Load raw USA mortality data."""
    return MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )


@pytest.fixture
def graduated(usa_raw):
    """Graduate USA data with default parameters."""
    return GraduatedRates(usa_raw, lambda_param=1e5, diff_order=2)


# =============================================================================
# Test: Difference Matrix
# =============================================================================

def test_difference_matrix_shape():
    """
    THEORY: For n data points and order h, D has shape (n-h, n).
    Order 2, n=10: D is (8, 10).
    """
    D = GraduatedRates._build_difference_matrix(10, order=2)
    assert D.shape == (8, 10)


def test_difference_matrix_first_order():
    """
    THEORY: First-order D encodes consecutive differences: [-1, 1].
    """
    D = GraduatedRates._build_difference_matrix(5, order=1)
    D_dense = D.toarray()
    assert D_dense.shape == (4, 5)
    # First row: [1, -1, 0, 0, 0]  (note: diags uses [0,1] offsets)
    np.testing.assert_array_almost_equal(D_dense[0], [1, -1, 0, 0, 0])


def test_difference_matrix_second_order():
    """
    THEORY: Second-order D encodes [1, -2, 1] -- curvature detection.
    """
    D = GraduatedRates._build_difference_matrix(5, order=2)
    D_dense = D.toarray()
    assert D_dense.shape == (3, 5)
    np.testing.assert_array_almost_equal(D_dense[0], [1, -2, 1, 0, 0])


# =============================================================================
# Test: Smoothing Properties
# =============================================================================

def test_smoothing_reduces_roughness(graduated):
    """
    THEORY: The whole point of graduation is to reduce roughness
    (sum of squared second differences) while staying close to data.
    """
    raw_rough = graduated.roughness(graduated.raw_mx)
    grad_rough = graduated.roughness(graduated.mx)
    assert grad_rough < raw_rough, (
        f"Graduated ({grad_rough:.2f}) should be less rough than raw ({raw_rough:.2f})"
    )


def test_lambda_zero_returns_near_raw(usa_raw):
    """
    THEORY: With lambda=0, the penalty vanishes, so the solution
    should be very close to the original data (just W * z = W * m => z = m).
    """
    grad = GraduatedRates(usa_raw, lambda_param=0.0)
    np.testing.assert_allclose(grad.mx, grad.raw_mx, rtol=1e-4)


def test_large_lambda_produces_smoother(usa_raw):
    """
    THEORY: Larger lambda = more smoothing = lower roughness.
    lambda=1e3 should be rougher (closer to raw) than lambda=1e7.
    """
    grad_low = GraduatedRates(usa_raw, lambda_param=1e3)
    grad_high = GraduatedRates(usa_raw, lambda_param=1e7)

    rough_low = grad_low.roughness(grad_low.mx)
    rough_high = grad_high.roughness(grad_high.mx)
    assert rough_high < rough_low


# =============================================================================
# Test: Output Quality
# =============================================================================

def test_no_nan_in_graduated(graduated):
    """Graduated rates must have no NaN values."""
    assert not np.any(np.isnan(graduated.mx))


def test_all_graduated_rates_positive(graduated):
    """
    THEORY: Working in log-space and exponentiating guarantees positivity.
    This is critical because Lee-Carter takes log() of the graduated rates.
    """
    assert np.all(graduated.mx > 0)


def test_residual_mean_near_zero(graduated):
    """
    THEORY: Residuals (log-raw - log-graduated) should average near zero,
    meaning the smoothing doesn't systematically bias rates up or down.
    """
    resid = graduated.residuals()
    assert abs(np.mean(resid)) < 0.1


def test_shape_preserved(graduated, usa_raw):
    """Graduated matrix should have same dimensions as input."""
    assert graduated.mx.shape == usa_raw.mx.shape
    assert graduated.shape == usa_raw.shape


# =============================================================================
# Test: Validate and Summary
# =============================================================================

def test_validate_all_pass(graduated):
    """All validation checks should pass for properly graduated data."""
    v = graduated.validate()
    assert v["no_nan"] is True
    assert v["all_positive"] is True
    assert v["smoother_than_raw"] is True
    assert v["residual_mean_near_zero"] is True


def test_summary_has_expected_keys(graduated):
    """Summary should contain all diagnostic information."""
    s = graduated.summary()
    assert "roughness_reduction" in s
    assert s["roughness_reduction"] > 0
    assert s["lambda"] == 1e5


# =============================================================================
# Test: from_hmd convenience
# =============================================================================

def test_from_hmd_convenience():
    """from_hmd should load and graduate in one step."""
    grad = GraduatedRates.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=2000,
        year_max=2010,
        age_max=100,
    )
    assert grad.n_ages == 101
    assert grad.n_years == 11
    assert np.all(grad.mx > 0)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
