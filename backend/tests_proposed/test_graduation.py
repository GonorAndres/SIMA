"""
Whittaker-Henderson graduation (a07) -- analytic invariants.

Two exact properties pin the smoother:
  * the order-2 difference operator must return true second differences;
  * a log-linear input has zero second differences, so the order-2 penalty
    is inert and graduation must be a NO-OP for ANY lambda.
Plus a limiting case (lambda -> 0 returns the raw data) and the roughness
guarantee on noisy input.
"""

import numpy as np
import pytest

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates


def _make_data(mx):
    """Wrap a rate matrix in a MortalityData with consistent d, e."""
    n_ages, n_years = mx.shape
    ages = np.arange(0, n_ages)
    years = np.arange(2000, 2000 + n_years)
    ex = np.full_like(mx, 1000.0)
    dx = ex * mx
    return MortalityData("test", "Male", ages, years, mx, dx, ex)


def test_second_difference_operator_is_exact():
    # THEORY: the order-2 difference of x^2 is the constant 2 everywhere.
    # This is the algebraic core of the penalty; a wrong recursion here
    # corrupts every graduated curve.
    D2 = GraduatedRates._build_difference_matrix(6, order=2)
    x = np.array([0, 1, 4, 9, 16, 25], dtype=float)  # x^2
    assert D2.shape == (4, 6)
    assert np.allclose(D2 @ x, 2.0)


def test_log_linear_input_is_unchanged_for_any_lambda():
    # THEORY: if log(m_x) is linear in age, its 2nd differences are 0, so the
    # order-2 penalty contributes nothing and z = m exactly -- regardless of
    # lambda.  Bug caught: any smoother that shrinks toward a wrong target or
    # mishandles the weight matrix distorts a curve it should leave alone.
    ages = np.arange(0, 40)
    log_lin = -9.0 + 0.08 * ages
    mx = np.exp(log_lin)[:, None]           # single year column
    data = _make_data(mx)
    grad = GraduatedRates(data, lambda_param=1e6, diff_order=2)
    assert np.allclose(grad.mx, grad.raw_mx, rtol=1e-6)


def test_lambda_zero_returns_raw_rates():
    # THEORY: with no penalty the fit interpolates the data: z = m.
    rng = np.random.default_rng(0)
    ages = np.arange(0, 30)
    mx = np.exp(-9 + 0.07 * ages + rng.normal(0, 0.1, size=ages.size))[:, None]
    data = _make_data(mx)
    grad = GraduatedRates(data, lambda_param=0.0, diff_order=2)
    assert np.allclose(grad.mx, grad.raw_mx, rtol=1e-6)


def test_graduation_reduces_roughness_and_stays_positive():
    # THEORY: smoothing noisy rates must lower the roughness and keep every
    # graduated rate strictly positive (log-space fit guarantees positivity).
    rng = np.random.default_rng(1)
    ages = np.arange(0, 50)
    years = np.arange(2000, 2010)
    clean = np.exp(-9 + 0.08 * ages)[:, None]
    noise = rng.normal(0, 0.15, size=(ages.size, years.size))
    mx = clean * np.exp(noise)
    data = _make_data(mx)
    grad = GraduatedRates(data, lambda_param=1e4, diff_order=2)
    v = grad.validate()
    assert v["smoother_than_raw"] is True
    assert v["all_positive"] is True
    assert v["no_nan"] is True
