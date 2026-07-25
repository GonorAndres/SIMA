"""
Portfolio & BEL (a11) -- closed-form annuity BEL, equivalence, additivity.

The annuity BEL has a clean closed form (pension x a-due), giving an
independent target. Death-product BEL at issue must be ~0 (equivalence),
and the portfolio aggregates must be exactly additive across policies and
across the death/annuity split.
"""

import pytest

from backend.engine.a11_portfolio import Policy, Portfolio, compute_policy_bel
from conftest import cf_a_due, INTEREST


def test_annuity_bel_matches_closed_form(constant_force_lt):
    # THEORY: BEL_annuity = pension * a-due(attained_age). Checked against the
    # constant-force closed form for a-due -- independent of the engine's
    # commutation path.
    pension = 120_000.0
    pol = Policy("A1", "annuity", issue_age=65, annual_pension=pension, duration=0)
    bel = compute_policy_bel(pol, constant_force_lt, INTEREST)
    assert bel == pytest.approx(pension * cf_a_due(65), rel=1e-8)


def test_whole_life_bel_at_issue_is_zero(constant_force_lt):
    # THEORY: a newly issued death policy has BEL ~ 0 (equivalence principle).
    pol = Policy("WL", "whole_life", issue_age=40, SA=1_000_000, duration=0)
    bel = compute_policy_bel(pol, constant_force_lt, INTEREST)
    assert bel == pytest.approx(0.0, abs=1e-4)


def test_inforce_death_bel_is_positive(constant_force_lt):
    # THEORY: after some duration the reserve (=BEL) has accumulated > 0.
    pol = Policy("WL", "whole_life", issue_age=40, SA=1_000_000, duration=15)
    assert compute_policy_bel(pol, constant_force_lt, INTEREST) > 0.0


def test_portfolio_bel_is_additive(constant_force_lt):
    # THEORY: total BEL = sum of policy BELs, and death_bel + annuity_bel =
    # total_bel.  Bug caught: a double-count or a missed policy category.
    policies = [
        Policy("WL", "whole_life", issue_age=45, SA=1_000_000, duration=5),
        Policy("TM", "term", issue_age=40, SA=2_000_000, n=20, duration=10),
        Policy("AN", "annuity", issue_age=70, annual_pension=100_000, duration=0),
    ]
    pf = Portfolio(policies)
    total = pf.compute_bel(constant_force_lt, INTEREST)
    parts = sum(compute_policy_bel(p, constant_force_lt, INTEREST) for p in policies)
    assert total == pytest.approx(parts, rel=1e-12)

    by_type = pf.compute_bel_by_type(constant_force_lt, INTEREST)
    assert by_type["death_bel"] + by_type["annuity_bel"] == pytest.approx(
        by_type["total_bel"], rel=1e-12
    )
    assert by_type["total_bel"] == pytest.approx(total, rel=1e-12)


def test_policy_validation_guards():
    # THEORY: invalid policies must fail construction, not mis-price later.
    with pytest.raises(ValueError):
        Policy("X", "unknown_product", issue_age=40, SA=1000)
    with pytest.raises(ValueError):
        Policy("T", "term", issue_age=40, SA=1000)   # missing n


def test_attained_age():
    # THEORY: attained_age = issue_age + duration (drives every BEL lookup).
    pol = Policy("WL", "whole_life", issue_age=30, SA=1000, duration=12)
    assert pol.attained_age == 42
