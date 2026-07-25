"""
Life Table (a01) -- analytic tests.

Pins l_x -> d_x, q_x, p_x against two mortality laws with closed-form
q_x (constant force and De Moivre), plus conservation and input-guard
behaviour. Constant force and De Moivre disagree on the *shape* of q_x,
so a single wrong denominator or off-by-one cannot pass both.
"""

import math

import pytest

from backend.engine.a01_life_table import LifeTable
from conftest import P, Q, OMEGA, DM_W, DM_MAX_AGE


# --- Constant force: q_x is exactly age-constant ---------------------------
@pytest.mark.parametrize("x", [0, 25, 60, 100, 129])
def test_constant_force_qx_is_constant(constant_force_lt, x):
    # THEORY: l_x = radix*p^x  =>  q_x = 1 - p for every non-terminal age.
    # Bug caught: q_x built from the wrong survivor pair (l_{x-1} vs l_{x+1})
    # would make q_x drift with age instead of staying flat.
    assert constant_force_lt.get_q(x) == pytest.approx(Q, rel=1e-12)
    assert constant_force_lt.get_p(x) == pytest.approx(P, rel=1e-12)


def test_dx_equals_qx_times_lx(constant_force_lt):
    # THEORY: d_x = q_x * l_x.  Binds the deaths column to the rate column.
    for x in [0, 40, 80, 120]:
        lx = constant_force_lt.get_l(x)
        assert constant_force_lt.get_d(x) == pytest.approx(Q * lx, rel=1e-12)


# --- De Moivre: q_x varies as 1/(W-x) --------------------------------------
@pytest.mark.parametrize("x", [0, 10, 50, 100, 109])
def test_de_moivre_qx_matches_closed_form(de_moivre_lt, x):
    # THEORY: l_x = k*(W-x) => d_x = k (constant), q_x = 1/(W-x).
    # Bug caught: a formula that only works for constant q_x (the constant-
    # force fixture) fails here because the true q_x now increases with age.
    assert de_moivre_lt.get_q(x) == pytest.approx(1.0 / (DM_W - x), rel=1e-12)


def test_de_moivre_deaths_are_constant(de_moivre_lt):
    # THEORY: uniform deaths -> d_x is the same at every age (= k = 1000).
    ds = [de_moivre_lt.get_d(x) for x in range(0, DM_MAX_AGE)]
    assert all(d == pytest.approx(1000.0, rel=1e-12) for d in ds)


# --- Conservation & terminal handling --------------------------------------
def test_sum_of_deaths_equals_initial_cohort(constant_force_lt):
    # THEORY: everyone eventually dies -> sum_x d_x = l_0 (radix).
    v = constant_force_lt.validate()
    assert v["sum_deaths_equals_l0"] is True
    assert v["all_rates_valid"] is True


def test_terminal_age_is_certain_death(constant_force_lt):
    # THEORY: q_omega = 1, p_omega = 0, d_omega = l_omega.
    assert constant_force_lt.get_q(OMEGA) == 1.0
    assert constant_force_lt.get_p(OMEGA) == 0.0
    assert constant_force_lt.get_d(OMEGA) == constant_force_lt.get_l(OMEGA)


# --- from_csv exact hand values --------------------------------------------
def test_from_csv_hand_computed_values():
    # THEORY: mini table l_60=1000, l_61=850 -> d_60=150, q_60=0.15, p_60=0.85.
    # Bug caught: a broken CSV parse or derivative shift changes these exact
    # numbers.
    from conftest import DATA_DIR
    lt = LifeTable.from_csv(f"{DATA_DIR}/mini_table.csv")
    assert lt.get_d(60) == pytest.approx(150.0)
    assert lt.get_q(60) == pytest.approx(0.15)
    assert lt.get_p(60) == pytest.approx(0.85)
    assert lt.min_age == 60 and lt.max_age == 65


# --- Input guards ----------------------------------------------------------
def test_construction_rejects_bad_input():
    # THEORY: malformed input must fail fast, not silently mis-index.
    with pytest.raises(ValueError):
        LifeTable([60, 61, 62], [1000.0, 900.0])       # length mismatch
    with pytest.raises(ValueError):
        LifeTable([60], [1000.0])                        # < 2 ages


def test_out_of_range_age_raises(constant_force_lt):
    # THEORY: querying an absent age is an error, not a default 0.
    with pytest.raises(KeyError):
        constant_force_lt.get_q(999)
