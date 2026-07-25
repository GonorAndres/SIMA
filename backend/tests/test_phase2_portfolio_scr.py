"""
Phase 2 -- Portfolio & SCR correctness tests.

Covers the bullets in docs/plan-25julio.md section 2.3:
  - sex=female produces materially different BEL/SCR than sex=male
  - expired term policies contribute zero to catastrophe SCR
  - risk margin increases with portfolio duration
  - invalid correlation matrices raise a domain error
  - Lee-Carter shock calibration overrides the standard-formula defaults
  - portfolio-specific risk-margin duration (replaces hardcoded 15.0)
  - Portfolio / Policy boundary validation (duplicate ids, attained-age OOB,
    negative amounts, expired-policy construction warning)
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a11_portfolio import (
    Policy,
    Portfolio,
    compute_policy_bel,
    policy_remaining_horizon,
    portfolio_remaining_duration,
)
from backend.engine.a12_scr import (
    LIFE_CORR,
    aggregate_scr_life,
    calibrate_shocks_from_lee_carter,
    compute_risk_margin,
    compute_scr_catastrophe,
    run_full_scr,
)
from backend.engine.exceptions import ActuarialValidationError

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def build_gompertz_life_table(ages=None, radix=100_000, slope=0.07, base=0.0005):
    """Gompertz mortality: q_x = base * exp(slope * x)."""
    if ages is None:
        ages = list(range(0, 111))
    l_x = [radix]
    for i in range(len(ages) - 1):
        qx = min(base * math.exp(slope * ages[i]), 0.99)
        l_x.append(l_x[-1] * (1.0 - qx))
    return LifeTable(ages, l_x)


def _make_lc(kt: list[float], bx: list[float]):
    """Minimal stand-in object exposing the .kt and .bx attributes the
    calibrate_shocks_from_lee_carter helper consumes."""
    from types import SimpleNamespace

    return SimpleNamespace(kt=np.asarray(kt, dtype=float), bx=np.asarray(bx, dtype=float))


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def life_table():
    return build_gompertz_life_table()


@pytest.fixture
def interest_rate():
    return 0.05


@pytest.fixture
def mixed_portfolio():
    return Portfolio(
        [
            Policy("WL-01", "whole_life", issue_age=35, SA=1_000_000, duration=5),
            Policy("TM-02", "term", issue_age=40, SA=2_000_000, n=20, duration=5),
            Policy("AN-01", "annuity", issue_age=65, annual_pension=150_000),
        ]
    )


# =============================================================================
# Test: sex=female produces materially different BEL/SCR than sex=male
# =============================================================================


def test_sex_delta_in_scr():
    """
    THEORY: Female mortality (CNSF) is materially lighter than male, so the
    BEL and total SCR computed on the same portfolio must differ materially
    between sexes. Catches regressions where the sex axis is silently
    ignored downstream of the regulatory loader.
    """
    cnsf_path = str(Path(__file__).parent.parent / "data" / "cnsf" / "cnsf_2000_i.csv")
    lt_male = LifeTable.from_regulatory_table(cnsf_path, sex="male")
    lt_female = LifeTable.from_regulatory_table(cnsf_path, sex="female")

    # Issue at 25 keeps attained ages inside the CNSF table (starts at age 12).
    port = Portfolio(
        [
            Policy("WL-01", "whole_life", issue_age=25, SA=1_000_000, duration=5),
            Policy("TM-02", "term", issue_age=30, SA=2_000_000, n=20, duration=5),
            Policy("TM-03", "term", issue_age=40, SA=1_500_000, n=20, duration=8),
            Policy("EN-04", "endowment", issue_age=25, SA=1_000_000, n=20, duration=5),
        ]
    )

    i = 0.05
    res_male = run_full_scr(port, lt_male, i)
    res_female = run_full_scr(port, lt_female, i)

    assert res_male["bel_base"] != pytest.approx(res_female["bel_base"], rel=1e-3)
    assert res_male["total_aggregation"]["scr_total"] != pytest.approx(
        res_female["total_aggregation"]["scr_total"], rel=1e-3
    )
    # Female mortality is lighter -> death-product BEL is HIGHER (deaths occur
    # later, more discounting but benefits paid later in larger buckets differ);
    # at minimum the two totals must differ by a non-trivial margin.
    male_total = res_male["total_aggregation"]["scr_total"]
    female_total = res_female["total_aggregation"]["scr_total"]
    assert abs(male_total - female_total) > 1e-3 * (male_total + female_total) / 2


# =============================================================================
# Test: expired term policies contribute zero to catastrophe SCR
# =============================================================================


def test_expired_term_zero_cat_scr(life_table, interest_rate):
    """An expired term policy (duration >= n) contributes zero catastrophe
    SCR; an identical in-force term policy contributes a positive amount."""
    expired = Policy("TM-EXP", "term", issue_age=40, SA=2_000_000, n=10, duration=10)
    port_exp = Portfolio([expired])
    res_exp = compute_scr_catastrophe(port_exp, life_table, interest_rate)
    assert res_exp["scr"] == 0.0
    # No details entry produced for the expired policy.
    assert all(d["policy_id"] != "TM-EXP" for d in res_exp["details"])

    inforce = Policy("TM-IF", "term", issue_age=40, SA=2_000_000, n=10, duration=2)
    port_if = Portfolio([inforce])
    res_if = compute_scr_catastrophe(port_if, life_table, interest_rate)
    assert res_if["scr"] > 0.0
    # The survival probability must be recorded in the detail entry.
    assert res_if["details"][0]["t_p_x"] > 0.0
    assert res_if["details"][0]["t_p_x"] < 1.0


def test_cat_scr_applies_survival_probability(life_table, interest_rate):
    """The catastrophe extra claim equals SA * delta_q * v * t_p_x, NOT
    SA * delta_q * v. With t_p_x < 1 the survival-aware SCR is strictly
    smaller than the naive (certain-in-force) figure."""
    p = Policy("TM", "term", issue_age=40, SA=1_000_000, n=20, duration=5)
    port = Portfolio([p])
    res = compute_scr_catastrophe(port, life_table, interest_rate)
    cat = res["scr"]
    assert cat > 0.0

    # Naive recomputation (assumes in-force with certainty) must be larger.
    v = 1.0 / (1.0 + interest_rate)
    # build_shocked equivalent
    from backend.engine.a12_scr import build_shocked_life_table

    shocked_lt = build_shocked_life_table(life_table, 1.35)
    age = p.attained_age
    delta_q = shocked_lt.get_q(age) - life_table.get_q(age)
    naive = p.SA * delta_q * v
    assert cat < naive
    assert cat == pytest.approx(naive * res["details"][0]["t_p_x"], rel=1e-9)


# =============================================================================
# Test: risk margin increases with portfolio duration
# =============================================================================


def test_risk_margin_increases_with_duration():
    """MdR = CoC * SCR * annuity(duration). For positive SCR, MdR strictly
    increases with duration."""
    short = compute_risk_margin(scr_total=200_000, duration=5.0)
    long = compute_risk_margin(scr_total=200_000, duration=30.0)
    assert long["risk_margin"] > short["risk_margin"]

    # The auto-computed portfolio duration should also follow this monotonicity:
    # a portfolio of newly-issued 20-year term policies has a longer remaining
    # horizon than the same policies at duration 18.
    lt = build_gompertz_life_table()
    i = 0.05
    port_young = Portfolio([Policy("T", "term", issue_age=30, SA=1_000_000, n=20, duration=0)])
    port_old = Portfolio([Policy("T", "term", issue_age=30, SA=1_000_000, n=20, duration=18)])
    d_young = portfolio_remaining_duration(port_young, lt, i)
    d_old = portfolio_remaining_duration(port_old, lt, i)
    assert d_young > d_old > 0.0


def test_run_full_scr_auto_computes_duration(mixed_portfolio, life_table, interest_rate):
    """When portfolio_duration is None, run_full_scr derives it from the
    portfolio and reports it back (no longer hardcoded 15.0)."""
    res = run_full_scr(mixed_portfolio, life_table, interest_rate)
    assert res["portfolio_duration"] is not None
    assert res["portfolio_duration"] > 0.0
    assert res["portfolio_duration"] != 15.0
    assert res["risk_margin"]["duration"] == res["portfolio_duration"]


# =============================================================================
# Test: invalid correlation matrix raises a domain error
# =============================================================================


def test_invalid_corr_matrix_not_psd():
    """A non-PSD custom correlation matrix must raise ActuarialValidationError
    rather than produce a sqrt-of-negative SCR."""
    bad = np.array(
        [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, 0.9],
            [0.9, 0.9, 1.0],
        ]
    )
    # That matrix IS psd (eigenvalues 2.8, 0.1, 0.1). Use a genuinely bad one:
    bad = np.array(
        [
            [1.0, 0.95, 0.95],
            [0.95, 1.0, -0.95],
            [0.95, -0.95, 1.0],
        ]
    )
    ev = np.linalg.eigvalsh(bad)
    assert ev.min() < 0, "test matrix must be non-PSD"
    with pytest.raises(ActuarialValidationError, match="positive semi-definite"):
        aggregate_scr_life(100.0, 100.0, 100.0, corr_matrix=bad)


def test_invalid_corr_matrix_not_symmetric():
    asym = np.array(
        [
            [1.0, 0.5, 0.25],
            [0.25, 1.0, 0.0],
            [0.25, 0.0, 1.0],
        ]
    )
    with pytest.raises(ActuarialValidationError, match="symmetric"):
        aggregate_scr_life(100.0, 100.0, 100.0, corr_matrix=asym)


def test_default_life_corr_is_psd():
    """The bundled LIFE_CORR passes the new on-import PSD validation."""
    assert np.linalg.eigvalsh(LIFE_CORR).min() >= -1e-10


# =============================================================================
# Test: Lee-Carter shock calibration
# =============================================================================


def test_calibrate_shocks_from_lee_carter_positive():
    """A fitted Lee-Carter with positive k_t volatility produces positive
    mortality / longevity shocks and a cat_shock_factor > 1."""
    lc = _make_lc(kt=[0.0, -0.5, -1.0, -1.5, -2.0, -2.6, -3.1], bx=np.full(20, 1.0 / 20))
    out = calibrate_shocks_from_lee_carter(lc)
    assert out["sigma_k"] > 0.0
    assert out["z_value"] == pytest.approx(2.5758, abs=1e-2)  # Phi^{-1}(0.995)
    assert out["mortality_shock"] > 0.0
    assert out["longevity_shock"] > 0.0
    assert out["cat_shock_factor"] > 1.0


def test_calibrate_shocks_invalid_confidence():
    lc = _make_lc(kt=[0.0, -1.0, -2.0], bx=[0.5, 0.5])
    with pytest.raises(ActuarialValidationError):
        calibrate_shocks_from_lee_carter(lc, confidence=1.5)
    with pytest.raises(ActuarialValidationError):
        calibrate_shocks_from_lee_carter(lc, confidence=0.0)


def test_calibrate_shocks_short_kt_raises():
    lc = _make_lc(kt=[0.0, -1.0], bx=[0.5, 0.5])
    with pytest.raises(Exception):
        calibrate_shocks_from_lee_carter(lc)


def test_run_full_scr_uses_lc_calibration(mixed_portfolio, life_table, interest_rate):
    """Passing shocks_from triggers calibration and records it in the output,
    overriding the standard-formula defaults."""
    lc = _make_lc(kt=[0.0, -0.6, -1.2, -1.8, -2.4, -3.0, -3.6], bx=np.full(20, 1.0 / 20))
    res_default = run_full_scr(mixed_portfolio, life_table, interest_rate)
    res_cal = run_full_scr(mixed_portfolio, life_table, interest_rate, shocks_from=lc)
    assert res_cal["shock_calibration"] is not None
    assert res_cal["shock_calibration"]["sigma_k"] > 0
    # The calibrated shocks differ from the standard 15% / 20% / 35%.
    assert res_cal["mortality"]["shock"] != res_default["mortality"]["shock"]
    assert res_cal["catastrophe"]["cat_shock_factor"] != 1.35


# =============================================================================
# Test: Portfolio / Policy boundary validation
# =============================================================================


def test_portfolio_duplicate_policy_id_raises():
    with pytest.raises(ActuarialValidationError, match="Duplicate policy_id"):
        Portfolio(
            [
                Policy("DUP", "whole_life", issue_age=35, SA=1_000_000),
                Policy("DUP", "term", issue_age=40, SA=2_000_000, n=20),
            ]
        )


def test_policy_negative_sa_raises():
    with pytest.raises(ActuarialValidationError, match="SA"):
        Policy("X", "whole_life", issue_age=35, SA=-100.0)


def test_policy_negative_pension_raises():
    with pytest.raises(ActuarialValidationError, match="annual_pension"):
        Policy("X", "annuity", issue_age=65, annual_pension=-50.0)


def test_policy_lapse_rate_overflow_raises():
    with pytest.raises(ActuarialValidationError, match="lapse_rate"):
        Policy("X", "whole_life", issue_age=35, SA=100, lapse_rate=1.5)


def test_policy_construction_with_duration_over_n_warns(life_table, interest_rate):
    """Constructing a term/endowment policy with duration > n is allowed
    (it represents an expired/matured policy) but emits a UserWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        with pytest.raises(UserWarning):
            Policy("E", "term", issue_age=30, SA=1_000_000, n=10, duration=12)


def test_portfolio_out_of_table_attained_age_raises(life_table, interest_rate):
    major = build_gompertz_life_table(ages=list(range(0, 50)))
    # The full table caps at age 49 -- an in-force WHOLE LIFE policy with
    # attained_age > 49 must trigger validate_against_life_table.
    port = Portfolio(
        [Policy("OLD", "whole_life", issue_age=40, SA=1_000_000, duration=20)]  # att=60
    )
    with pytest.raises(ActuarialValidationError, match="outside the life table"):
        port.compute_bel(major, interest_rate)


def test_expired_policy_bel_zero_and_is_expired_flag(life_table, interest_rate):
    """An expired term policy reports BEL == 0 and is_expired is True."""
    p = Policy("E", "term", issue_age=40, SA=1_000_000, n=10, duration=12)
    assert p.is_expired is True
    assert compute_policy_bel(p, life_table, interest_rate) == 0.0
    # Remaining horizon of an expired policy is zero.
    assert policy_remaining_horizon(p, life_table, interest_rate) == 0.0


def test_no_op_hooks_default_and_preserve_bel(life_table, interest_rate):
    """The expense_loading / lapse_rate / commission hooks default to zero
    and do NOT change the net-premium BEL."""
    p_plain = Policy("P", "whole_life", issue_age=35, SA=1_000_000, duration=5)
    p_hook = Policy(
        "P",
        "whole_life",
        issue_age=35,
        SA=1_000_000,
        duration=5,
        expense_loading=0.1,
        lapse_rate=0.02,
        commission=0.05,
    )
    assert p_hook.expense_loading == 0.1
    assert p_hook.lapse_rate == 0.02
    assert p_hook.commission == 0.05
    # Hooks are no-ops for BEL -> identical to the plain policy.
    assert compute_policy_bel(p_plain, life_table, interest_rate) == pytest.approx(
        compute_policy_bel(p_hook, life_table, interest_rate), rel=1e-12
    )


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
