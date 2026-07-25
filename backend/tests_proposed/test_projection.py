"""
Mortality projection (a09) -- RWD drift recovery and the LifeTable bridge.

We feed a Lee-Carter object whose k_t is EXACTLY linear (known slope). Then
drift must equal that slope, sigma must be 0 (no residual innovations), and
the central projection must continue the straight line. Separately we check
the m -> q -> l_x bridge and the confidence-interval ordering.
"""

import numpy as np
import pytest

from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a09_projection import MortalityProjection


SLOPE = -0.9  # known annual change in k_t


@pytest.fixture(scope="module")
def linear_kt_lc():
    ages = np.arange(40, 90)
    years = np.arange(2000, 2020)
    ax = -9.0 + 0.06 * (ages - 40)
    bx_raw = np.linspace(2.0, 0.5, ages.size)
    bx = bx_raw / bx_raw.sum()
    kt = 5.0 + SLOPE * np.arange(years.size)          # exactly linear
    log_mx = ax[:, None] + np.outer(bx, kt)
    return LeeCarter(ages, years, ax, bx, kt, log_mx, explained_variance=1.0)


@pytest.fixture(scope="module")
def proj(linear_kt_lc):
    return MortalityProjection(linear_kt_lc, horizon=30, n_simulations=500, random_seed=7)


def test_drift_recovers_slope_and_sigma_is_zero(proj):
    # THEORY: drift = (k_T - k_1)/(T-1); for a linear k_t this equals the
    # slope exactly, and every innovation (diff - drift) is 0 so sigma = 0.
    # Bug caught: a drift computed over the wrong span or a sigma that fails
    # to subtract the drift.
    assert proj.drift == pytest.approx(SLOPE, rel=1e-12)
    assert proj.sigma == pytest.approx(0.0, abs=1e-12)


def test_central_projection_continues_the_line(proj, linear_kt_lc):
    # THEORY: central k_{T+h} = k_T + h*drift. On a linear trend the forecast
    # lies on the same straight line as the history.
    kt_last = linear_kt_lc.kt[-1]
    for h in (1, 10, 30):
        assert proj.kt_central[h - 1] == pytest.approx(kt_last + h * SLOPE, rel=1e-12)


def test_bridge_to_life_table_is_valid(proj):
    # THEORY: q_x = 1 - exp(-m_x), terminal q = 1, l_x strictly decreasing,
    # and the result must plug into the commutation engine. Bug caught: a
    # broken m->q conversion or a non-monotone survivor column.
    year = int(proj.projected_years[10])
    lt = proj.to_life_table(year, radix=100_000)
    age = int(lt.ages[5])
    m = proj.get_projected_mx(age, year)
    assert lt.get_q(age) == pytest.approx(1.0 - np.exp(-m), rel=1e-9)
    assert lt.get_q(lt.max_age) == 1.0
    lx = [lt.get_l(a) for a in lt.ages]
    assert all(b <= a for a, b in zip(lx, lx[1:]))
    CommutationFunctions(lt, interest_rate=0.05)  # must not raise


def test_confidence_interval_orders_scenarios(linear_kt_lc):
    # THEORY: with positive sigma, the pessimistic (high-k_t) life table must
    # have higher mortality than central, which exceeds optimistic. We give
    # k_t a small noise component so the simulated band is non-degenerate.
    ages = linear_kt_lc.ages
    years = linear_kt_lc.years
    rng = np.random.default_rng(0)
    kt = linear_kt_lc.kt + rng.normal(0, 0.5, size=years.size)
    lc = LeeCarter(ages, years, linear_kt_lc.ax, linear_kt_lc.bx, kt,
                   linear_kt_lc.log_mx, 1.0)
    p = MortalityProjection(lc, horizon=20, n_simulations=2000, random_seed=1)
    year = int(p.projected_years[10])
    central, optimistic, pessimistic = p.to_life_table_with_ci(year)
    a = int(ages[10])
    assert pessimistic.get_q(a) > central.get_q(a) > optimistic.get_q(a)


def test_simulation_is_reproducible(linear_kt_lc):
    # THEORY: a fixed seed must give identical stochastic paths.
    p1 = MortalityProjection(linear_kt_lc, horizon=10, n_simulations=100, random_seed=42)
    p2 = MortalityProjection(linear_kt_lc, horizon=10, n_simulations=100, random_seed=42)
    assert np.array_equal(p1.kt_simulated, p2.kt_simulated)
