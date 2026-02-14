"""
Portfolio Module Tests
=======================

Tests for Policy, Portfolio, and BEL computation (Block 11).

Each test validates an actuarial property of the Best Estimate Liability
under the Solvency II / CNSF framework.
"""

import pytest
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a11_portfolio import (
    Policy,
    Portfolio,
    compute_policy_bel,
    create_sample_portfolio,
)


# =============================================================================
# Helper: Build LifeTable from Gompertz q_x
# =============================================================================

def build_gompertz_life_table(ages=None, radix=100_000):
    """
    Build a LifeTable using Gompertz mortality: q_x = 0.0005 * exp(0.07 * x).

    This gives a realistic increasing-mortality pattern suitable for
    testing all product types over a full age range.
    """
    if ages is None:
        ages = list(range(0, 111))
    l_x = [radix]
    for i in range(len(ages) - 1):
        qx = min(0.0005 * math.exp(0.07 * ages[i]), 0.99)
        l_x.append(l_x[-1] * (1.0 - qx))
    return LifeTable(ages, l_x)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def life_table():
    """Standard Gompertz life table (ages 0-110)."""
    return build_gompertz_life_table()


@pytest.fixture
def interest_rate():
    return 0.05


# =============================================================================
# Test: Policy Creation
# =============================================================================

def test_policy_creation():
    """
    THEORY: Policy stores all attributes correctly.

    A Policy is a data container for the contractual terms of an
    insurance product. Verifying attribute storage ensures the
    downstream BEL computation receives correct inputs.
    """
    p = Policy("WL-01", "whole_life", issue_age=35, SA=1_000_000, duration=5)
    assert p.policy_id == "WL-01"
    assert p.product_type == "whole_life"
    assert p.issue_age == 35
    assert p.SA == 1_000_000
    assert p.duration == 5
    assert p.attained_age == 40


def test_policy_invalid_product():
    """
    THEORY: Unknown product types should raise ValueError.

    The policy type determines how BEL is computed. An invalid type
    would cause silent errors downstream.
    """
    with pytest.raises(ValueError, match="Unknown product_type"):
        Policy("X-01", "invalid_product", issue_age=30)


def test_policy_term_requires_n():
    """
    THEORY: Term and endowment products require a term length.

    Without n, the premium and reserve formulas are undefined.
    """
    with pytest.raises(ValueError, match="requires n"):
        Policy("T-01", "term", issue_age=30, SA=1_000_000)


# =============================================================================
# Test: Policy Classification
# =============================================================================

def test_policy_is_death_product():
    """
    THEORY: whole_life, term, endowment are all death products.

    Death products pay a benefit upon the insured's death. They
    generate mortality risk and catastrophe risk in the SCR framework.
    """
    wl = Policy("W", "whole_life", issue_age=30, SA=100)
    tm = Policy("T", "term", issue_age=30, SA=100, n=20)
    en = Policy("E", "endowment", issue_age=30, SA=100, n=20)
    an = Policy("A", "annuity", issue_age=65, annual_pension=100)

    assert wl.is_death_product is True
    assert tm.is_death_product is True
    assert en.is_death_product is True
    assert an.is_death_product is False


def test_policy_is_annuity():
    """
    THEORY: Only annuity products return is_annuity=True.

    Annuity products pay as long as the annuitant survives. They
    generate longevity risk (the mirror image of mortality risk).
    """
    wl = Policy("W", "whole_life", issue_age=30, SA=100)
    an = Policy("A", "annuity", issue_age=65, annual_pension=100)

    assert wl.is_annuity is False
    assert an.is_annuity is True


# =============================================================================
# Test: Portfolio Filtering
# =============================================================================

def test_portfolio_filters():
    """
    THEORY: death_products and annuity_products partition the portfolio.

    Every policy belongs to exactly one category. The partition ensures
    that SCR computations apply shocks to the correct subset.
    """
    policies = [
        Policy("W", "whole_life", issue_age=30, SA=100),
        Policy("T", "term", issue_age=30, SA=100, n=20),
        Policy("A1", "annuity", issue_age=65, annual_pension=100),
        Policy("A2", "annuity", issue_age=70, annual_pension=100),
    ]
    port = Portfolio(policies)

    assert len(port.death_products) == 2
    assert len(port.annuity_products) == 2
    assert len(port.death_products) + len(port.annuity_products) == len(port)


# =============================================================================
# Test: BEL Computation
# =============================================================================

def test_bel_whole_life_at_issue_zero(life_table, interest_rate):
    """
    THEORY: BEL ~ 0 at issue (duration=0) for death products.

    The equivalence principle guarantees that at issue:
        APV(Future Benefits) = APV(Future Premiums)
        => BEL = Benefits - Premiums = 0

    A non-zero BEL at issue would mean the premium was mispriced.
    """
    p = Policy("WL", "whole_life", issue_age=35, SA=1_000_000, duration=0)
    bel = compute_policy_bel(p, life_table, interest_rate)

    assert abs(bel) < 1.0, f"BEL at issue should be ~0, got {bel:.4f}"


def test_bel_whole_life_positive_at_duration(life_table, interest_rate):
    """
    THEORY: BEL > 0 for in-force death products (duration > 0).

    As premiums are collected and time passes, the reserve builds up.
    The insurer has already collected premiums but hasn't paid the
    death benefit yet, so they owe a positive amount.
    """
    p = Policy("WL", "whole_life", issue_age=35, SA=1_000_000, duration=10)
    bel = compute_policy_bel(p, life_table, interest_rate)

    assert bel > 0, f"In-force BEL should be positive, got {bel:.4f}"


def test_bel_annuity_always_positive(life_table, interest_rate):
    """
    THEORY: BEL for annuities is always positive.

    BEL = pension * a_due(attained_age).
    Since a_due(x) > 0 for any living age (they'll receive at least
    one payment), and pension > 0, BEL must be positive.

    This reflects that the insurer owes money from day one -- there
    are no future premiums to offset the obligation.
    """
    p = Policy("AN", "annuity", issue_age=65, annual_pension=120_000, duration=0)
    bel = compute_policy_bel(p, life_table, interest_rate)

    assert bel > 0, f"Annuity BEL should be positive, got {bel:.4f}"


def test_bel_annuity_decreases_with_age(life_table, interest_rate):
    """
    THEORY: Annuity BEL decreases with attained age.

    a_due(60) > a_due(65) > a_due(70) because older annuitants have
    fewer expected remaining payments. A 60-year-old will collect
    for more years (in expectation) than a 70-year-old.
    """
    p60 = Policy("A60", "annuity", issue_age=60, annual_pension=120_000)
    p65 = Policy("A65", "annuity", issue_age=65, annual_pension=120_000)
    p70 = Policy("A70", "annuity", issue_age=70, annual_pension=120_000)

    bel_60 = compute_policy_bel(p60, life_table, interest_rate)
    bel_65 = compute_policy_bel(p65, life_table, interest_rate)
    bel_70 = compute_policy_bel(p70, life_table, interest_rate)

    assert bel_60 > bel_65 > bel_70, (
        f"BEL should decrease with age: {bel_60:.0f} > {bel_65:.0f} > {bel_70:.0f}"
    )


def test_aggregate_bel_is_sum(life_table, interest_rate):
    """
    THEORY: Portfolio BEL = sum of individual policy BELs.

    BEL is additive because present values are linear. This is a
    fundamental property: the total obligation equals the sum of
    per-policy obligations.
    """
    policies = [
        Policy("WL", "whole_life", issue_age=35, SA=1_000_000, duration=5),
        Policy("AN", "annuity", issue_age=65, annual_pension=120_000),
    ]
    port = Portfolio(policies)

    total_bel = port.compute_bel(life_table, interest_rate)
    sum_individual = sum(
        compute_policy_bel(p, life_table, interest_rate) for p in policies
    )

    assert total_bel == pytest.approx(sum_individual, rel=1e-10)


# =============================================================================
# Test: Sample Portfolio
# =============================================================================

def test_sample_portfolio_creation():
    """
    THEORY: create_sample_portfolio() returns the expected 12 policies.

    The sample portfolio has a balanced mix: 4 whole life, 3 term,
    2 endowment, 3 annuity. This mix is designed to demonstrate all
    four SCR risk modules (mortality, longevity, interest rate, catastrophe).
    """
    port = create_sample_portfolio()

    assert len(port) == 12
    assert len(port.death_products) == 9
    assert len(port.annuity_products) == 3


def test_bel_breakdown_matches_total(life_table, interest_rate):
    """
    THEORY: BEL breakdown entries sum to the aggregate BEL.

    The breakdown is a diagnostic tool -- its sum must match the
    aggregate computation exactly.
    """
    port = create_sample_portfolio()
    total = port.compute_bel(life_table, interest_rate)
    breakdown = port.compute_bel_breakdown(life_table, interest_rate)

    sum_breakdown = sum(entry["bel"] for entry in breakdown)
    assert total == pytest.approx(sum_breakdown, rel=1e-10)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
