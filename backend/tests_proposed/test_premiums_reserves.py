"""
Premiums (a04) and Reserves (a05) -- analytic and cross-module tests.

The pure APV closed forms (A_x, a_x, term, endowment, premium) are covered
in test_golden_values.py. This file targets what golden-values does not:
the *reserve* recursion and the relationships *between* products. Reserves
are validated two independent ways -- the equivalence principle (0V = 0)
and a paid-up closed form that routes through annuities only -- so agreement
cannot be a self-consistency artefact.
"""

import pytest

from conftest import cf_a_due, cf_A_x, OMEGA

SA = 100_000.0


# --- 0V = 0: the equivalence principle across products ---------------------
@pytest.mark.parametrize("product,kwargs", [
    ("whole_life", {}),
    ("term", {"n": 20}),
    ("endowment", {"n": 20}),
])
def test_reserve_at_issue_is_zero(rc, product, kwargs):
    # THEORY: a net premium priced by equivalence makes 0V = 0. The premium
    # (a04) and the reserve (a05) are computed by DIFFERENT code paths, so
    # a wrong sign or exponent in either shows up as a non-zero 0V.
    x = 40
    if product == "whole_life":
        r0 = rc.reserve_whole_life(SA, x, 0)
    elif product == "term":
        r0 = rc.reserve_term(SA, x, kwargs["n"], 0)
    else:
        r0 = rc.reserve_endowment(SA, x, kwargs["n"], 0)
    assert r0 == pytest.approx(0.0, abs=1e-6)


# --- Whole-life reserve paid-up closed form --------------------------------
@pytest.mark.parametrize("x,t", [(40, 10), (30, 25), (55, 5)])
def test_whole_life_reserve_paid_up_formula(rc, x, t):
    # THEORY: tV = SA * (1 - a-due_{x+t} / a-due_x).  Derived from
    # A = 1 - d*a and P = SA*A_x/a_x, it depends ONLY on annuities, whereas
    # the engine computes SA*A_{x+t} - P*a_{x+t}. Matching the two binds the
    # insurance and annuity machinery together.
    expected = SA * (1.0 - cf_a_due(x + t) / cf_a_due(x))
    assert rc.reserve_whole_life(SA, x, t) == pytest.approx(expected, rel=1e-8)


# --- Boundary reserves -----------------------------------------------------
def test_endowment_reserve_matures_to_SA(rc):
    # THEORY: an n-year endowment pays SA on survival to n -> n_V = SA.
    assert rc.reserve_endowment(SA, 40, 20, 20) == pytest.approx(SA)


def test_term_reserve_zero_after_expiry_and_positive_within(rc):
    # THEORY: term reserve = 0 once coverage lapses (t >= n); strictly
    # positive at an interior duration (premiums have accumulated ahead of
    # the level risk cost early on).
    assert rc.reserve_term(SA, 40, 20, 20) == 0.0
    assert rc.reserve_term(SA, 40, 20, 25) == 0.0
    assert rc.reserve_term(SA, 40, 20, 10) > 0.0


def test_pure_endowment_reserve_matures_to_SA(rc):
    # THEORY: pure endowment pays SA only on survival -> at t = n reserve = SA.
    assert rc.reserve_pure_endowment(SA, 40, 20, 20) == pytest.approx(SA)


# --- Premium relationships -------------------------------------------------
def test_premium_ordering(pc):
    # THEORY: for the same (x, n), endowment >= term (endowment also pays on
    # survival) and endowment >= pure endowment (it also pays on death).
    x, n = 40, 20
    p_term = pc.term(SA, x, n)
    p_endow = pc.endowment(SA, x, n)
    p_pure = pc.pure_endowment(SA, x, n)
    assert p_endow > p_term > 0
    assert p_endow > p_pure > 0


@pytest.mark.parametrize("x", [30, 45, 60])
def test_single_premium_equals_SA_times_Ax(pc, x):
    # THEORY: a single premium is just the APV of the benefit: pi = SA*A_x,
    # here checked against the constant-force closed form for A_x.
    assert pc.single_premium(SA, x) == pytest.approx(SA * cf_A_x(x), rel=1e-8)


def test_limited_pay_exceeds_level_whole_life(pc):
    # THEORY: fewer premium payments for the same coverage => each payment is
    # larger. m-pay WL premium > ordinary WL premium.
    x = 40
    assert pc.limited_pay_whole_life(SA, x, 10) > pc.whole_life(SA, x)


def test_equivalence_principle_balances(pc):
    # THEORY: APV(premiums) = APV(benefits) at issue for whole life.
    result = pc.verify_equivalence(SA, 40)
    assert result["balanced"] is True
    assert result["apv_premiums"] == pytest.approx(result["apv_benefits"], rel=1e-9)
