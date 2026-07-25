"""
SCR engine (a12) -- shocks, closed-form aggregation, risk margin.

The aggregation formulas (quadratic form, top-level correlation, risk
margin, solvency ratio) are pure math with hand-computable targets, so we
pin them to exact numbers. The risk-module tests check the economically
correct *direction* and product scoping that a wrong shock sign would break.
"""

import math

import numpy as np
import pytest

from backend.engine.a11_portfolio import Policy, Portfolio
from backend.engine.a12_scr import (
    build_shocked_life_table,
    compute_scr_mortality,
    compute_scr_longevity,
    compute_scr_interest_rate,
    compute_scr_catastrophe,
    aggregate_scr_life,
    aggregate_scr_total,
    compute_risk_margin,
    compute_solvency_ratio,
    LIFE_CORR,
)
from conftest import Q, V, INTEREST


# --- Shocked life table ----------------------------------------------------
def test_shocked_life_table_scales_qx(constant_force_lt):
    # THEORY: shocked q_x = min(base_q_x * factor, 1). Constant force base
    # q = Q, factor 1.5 -> 1.5*Q (well below 1 here).  Bug caught: a shock
    # applied to l_x instead of q_x, or a missing cap.
    shocked = build_shocked_life_table(constant_force_lt, 1.5)
    for age in (20, 60, 100):
        assert shocked.get_q(age) == pytest.approx(min(Q * 1.5, 1.0), rel=1e-9)


# --- Aggregation: exact hand values ----------------------------------------
def test_life_aggregation_quadratic_form():
    # THEORY: SCR_life = sqrt(vec' CORR vec). With vec=[300,400,0] and the
    # standard corr (mort/long = -0.25): sqrt(300^2+400^2-2*0.25*300*400)
    # = sqrt(190000).  Bug caught: a wrong correlation sign or a dropped
    # cross term.
    res = aggregate_scr_life(300.0, 400.0, 0.0)
    assert res["scr_life"] == pytest.approx(math.sqrt(190_000.0), rel=1e-12)
    assert res["scr_life"] < res["sum_individual"]  # diversification


def test_total_aggregation_hand_value():
    # THEORY: SCR_total = sqrt(L^2 + IR^2 + 2*rho*L*IR). L=400, IR=300,
    # rho=0.25 -> sqrt(160000+90000+60000)=sqrt(310000).
    res = aggregate_scr_total(400.0, 300.0, rho=0.25)
    assert res["scr_total"] == pytest.approx(math.sqrt(310_000.0), rel=1e-12)


def test_correlation_matrix_is_psd():
    # THEORY: a valid correlation matrix must be positive semi-definite, else
    # the quadratic form could go negative. Bug caught: a typo'd off-diagonal.
    eig = np.linalg.eigvalsh(LIFE_CORR)
    assert np.all(eig >= -1e-12)


def test_risk_margin_closed_form():
    # THEORY: MdR = CoC * SCR * (1 - v^duration)/i.
    scr, dur, coc, disc = 1_000.0, 10.0, 0.06, 0.05
    v = 1.0 / (1.0 + disc)
    af = (1.0 - v ** dur) / disc
    res = compute_risk_margin(scr, dur, coc_rate=coc, discount_rate=disc)
    assert res["annuity_factor"] == pytest.approx(af, rel=1e-12)
    assert res["risk_margin"] == pytest.approx(coc * scr * af, rel=1e-12)


def test_solvency_ratio():
    # THEORY: ratio = available capital / SCR; solvent iff ratio >= 1.
    res = compute_solvency_ratio(1_500.0, 1_000.0)
    assert res["ratio"] == pytest.approx(1.5)
    assert res["is_solvent"] is True
    assert compute_solvency_ratio(900.0, 1_000.0)["is_solvent"] is False


# --- Risk-module direction & scoping ---------------------------------------
def _death_pf():
    return Portfolio([Policy("WL", "whole_life", issue_age=40, SA=1_000_000, duration=10)])


def _annuity_pf():
    return Portfolio([Policy("AN", "annuity", issue_age=65, annual_pension=100_000)])


def test_mortality_scr_only_death_and_positive(constant_force_lt):
    # THEORY: a +q shock raises death-product BEL -> SCR > 0; an all-annuity
    # portfolio has zero mortality SCR (wrong-direction risk not charged).
    assert compute_scr_mortality(_death_pf(), constant_force_lt, INTEREST)["scr"] > 0
    assert compute_scr_mortality(_annuity_pf(), constant_force_lt, INTEREST)["scr"] == 0.0


def test_longevity_scr_only_annuity_and_positive(constant_force_lt):
    # THEORY: a -q shock lengthens annuitant lives -> annuity BEL up, SCR > 0;
    # death-only portfolio has zero longevity SCR.
    assert compute_scr_longevity(_annuity_pf(), constant_force_lt, INTEREST)["scr"] > 0
    assert compute_scr_longevity(_death_pf(), constant_force_lt, INTEREST)["scr"] == 0.0


def test_interest_down_is_the_binding_shock(constant_force_lt):
    # THEORY: lower rates raise the PV of future obligations more than higher
    # rates lower them, so BEL_down > BEL_up and the down-shock binds.
    pf = Portfolio([
        Policy("WL", "whole_life", issue_age=40, SA=1_000_000, duration=10),
        Policy("AN", "annuity", issue_age=65, annual_pension=100_000),
    ])
    res = compute_scr_interest_rate(pf, constant_force_lt, INTEREST, shock_bps=100)
    assert res["bel_down"] > res["bel_up"]
    assert res["scr"] == pytest.approx(res["bel_down"] - res["bel_base"], rel=1e-9)


def test_catastrophe_scr_closed_form(constant_force_lt):
    # THEORY: one-year spike -> SCR = SA * (q_shocked - q_base) * v for a
    # single death policy. With constant force q=Q, factor 1.35:
    # delta_q = 0.35*Q, so SCR = SA * 0.35*Q * v.
    SA = 1_000_000.0
    pf = Portfolio([Policy("WL", "whole_life", issue_age=40, SA=SA, duration=10)])
    res = compute_scr_catastrophe(pf, constant_force_lt, INTEREST, cat_shock_factor=1.35)
    expected = SA * (0.35 * Q) * V
    assert res["scr"] == pytest.approx(expected, rel=1e-9)
