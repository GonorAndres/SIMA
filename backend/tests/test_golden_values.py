"""
Golden-value tests: validate the actuarial engine against ANALYTIC closed-form
solutions, not against re-derivations of the engine's own formulas.

Motivation
----------
Most of the suite checks internal consistency (e.g. P == SA * M_x / N_x), which
confirms the code computes what it says but cannot catch a systematically wrong
*formula*. These tests pin the engine to independently-derived ground truth.

Method: constant force of mortality
-----------------------------------
Under a constant force of mortality ``mu``, the one-year survival probability
``p = exp(-mu)`` is age-independent, so the survivorship column is geometric:

    l_x = radix * p**x

For such a table the standard actuarial values collapse to closed-form geometric
series that can be written down WITHOUT the commutation-function machinery. With
``v = 1/(1+i)``, ``q = 1 - p`` and ``beta = v * p``, for any span that stays
below the (forced) terminal age ``omega`` (i.e. ``x + n <= omega``):

    n-year pure endowment:      nE_x            = beta**n
    n-year term insurance:      A^1_{x:n}       = q*v * (1 - beta**n) / (1 - beta)
    n-year endowment:           A_{x:n}         = A^1_{x:n} + nE_x
    n-year temporary annuity:   a-due_{x:n}     = (1 - beta**n) / (1 - beta)

Whole-life values touch the terminal age (where the table forces q_omega = 1,
d_omega = l_omega). With ``N = omega - x`` the exact finite-table results are:

    whole-life insurance:       A_x    = q*v*(1 - beta**N)/(1 - beta) + v**(N+1) * p**N
    whole-life annuity-due:     a_x    = (1 - beta**(N+1)) / (1 - beta)

These are textbook constant-force / exponential-survival results (e.g. Bowers
et al., *Actuarial Mathematics*). Because the engine reaches them through an
independent D/N/C/M recursion, agreement validates the recursion, the
discounting exponents, and the indexing (off-by-one bugs would show up here).
"""

import math

import pytest

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator

# ---- Analytic fixture parameters -------------------------------------------
MU = 0.03                      # constant force of mortality
INTEREST = 0.05                # annual effective interest
RADIX = 1_000_000
OMEGA = 130                    # terminal age (q_omega forced to 1 by the engine)

P = math.exp(-MU)              # age-independent one-year survival
Q = 1.0 - P
V = 1.0 / (1.0 + INTEREST)
BETA = V * P                   # geometric ratio of the discounted survivors
REL = 1e-9                     # these are exact identities -> very tight tolerance


@pytest.fixture(scope="module")
def av():
    ages = list(range(0, OMEGA + 1))
    l_x = [RADIX * P**x for x in ages]
    lt = LifeTable(ages, l_x)
    comm = CommutationFunctions(lt, interest_rate=INTEREST)
    return ActuarialValues(comm)


@pytest.fixture(scope="module")
def pc():
    ages = list(range(0, OMEGA + 1))
    l_x = [RADIX * P**x for x in ages]
    lt = LifeTable(ages, l_x)
    comm = CommutationFunctions(lt, interest_rate=INTEREST)
    return PremiumCalculator(comm)


# ---- Closed-form helpers (the "golden" values) -----------------------------
def _pure_endowment(n):
    return BETA**n


def _term(n):
    return Q * V * (1.0 - BETA**n) / (1.0 - BETA)


def _endowment(n):
    return _term(n) + _pure_endowment(n)


def _temp_annuity_due(n):
    return (1.0 - BETA**n) / (1.0 - BETA)


def _whole_life_A(x):
    n = OMEGA - x
    return Q * V * (1.0 - BETA**n) / (1.0 - BETA) + V**(n + 1) * P**n


def _whole_life_a_due(x):
    n = OMEGA - x
    return (1.0 - BETA**(n + 1)) / (1.0 - BETA)


# ---- Tests: insurances -----------------------------------------------------
@pytest.mark.parametrize("x, n", [(40, 20), (30, 25), (55, 10)])
def test_pure_endowment_matches_closed_form(av, x, n):
    # THEORY: nE_x = v^n * npx = (v*p)^n under constant force.
    assert av.nE_x(x, n) == pytest.approx(_pure_endowment(n), rel=REL)


@pytest.mark.parametrize("x, n", [(40, 20), (30, 25), (55, 10)])
def test_term_insurance_matches_closed_form(av, x, n):
    # THEORY: A^1_{x:n} = q*v*(1 - beta^n)/(1 - beta).
    assert av.A_term(x, n) == pytest.approx(_term(n), rel=REL)


@pytest.mark.parametrize("x, n", [(40, 20), (30, 25), (55, 10)])
def test_endowment_matches_closed_form(av, x, n):
    # THEORY: A_{x:n} = term + pure endowment.
    assert av.A_endowment(x, n) == pytest.approx(_endowment(n), rel=REL)


@pytest.mark.parametrize("x", [30, 40, 55])
def test_whole_life_insurance_matches_closed_form(av, x):
    # THEORY: exact finite-table whole life (touches the forced terminal age).
    assert av.A_x(x) == pytest.approx(_whole_life_A(x), rel=REL)


# ---- Tests: annuities ------------------------------------------------------
@pytest.mark.parametrize("x, n", [(40, 20), (30, 25), (55, 10)])
def test_temporary_annuity_due_matches_closed_form(av, x, n):
    # THEORY: a-due_{x:n} = (1 - beta^n)/(1 - beta).
    assert av.a_due_temporary(x, n) == pytest.approx(_temp_annuity_due(n), rel=REL)


@pytest.mark.parametrize("x", [30, 40, 55])
def test_whole_life_annuity_due_matches_closed_form(av, x):
    # THEORY: a-due_x = (1 - beta^(N+1))/(1 - beta), N = omega - x.
    assert av.a_due(x) == pytest.approx(_whole_life_a_due(x), rel=REL)


# ---- Tests: cross-checks that bind independent modules ---------------------
@pytest.mark.parametrize("x", [30, 40, 55])
def test_fundamental_identity_holds(av, x):
    # THEORY: A_x + d * a-due_x = 1 for ANY life table (d = 1 - v).
    d = 1.0 - V
    assert av.A_x(x) + d * av.a_due(x) == pytest.approx(1.0, rel=REL)


@pytest.mark.parametrize("x", [30, 40, 55])
def test_whole_life_net_premium_matches_closed_form(pc, x):
    # THEORY: net level whole-life premium P = SA * A_x / a-due_x.
    SA = 100_000.0
    expected = SA * _whole_life_A(x) / _whole_life_a_due(x)
    assert pc.whole_life(SA, x) == pytest.approx(expected, rel=REL)
