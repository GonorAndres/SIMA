"""
Solvency Capital Requirement (SCR) Tests
==========================================

Tests for the SCR engine (Block 12): individual risk modules,
correlation-based aggregation, risk margin, and solvency ratio.

Each test validates a specific actuarial property of the Solvency II /
CNSF capital requirement framework.
"""

import pytest
import math
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a11_portfolio import Policy, Portfolio, compute_policy_bel
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
    run_full_scr,
    LIFE_CORR,
)


# =============================================================================
# Helper: Build LifeTable from Gompertz q_x
# =============================================================================

def build_gompertz_life_table(ages=None, radix=100_000):
    """Gompertz mortality: q_x = 0.0005 * exp(0.07 * x)."""
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
    return build_gompertz_life_table()


@pytest.fixture
def interest_rate():
    return 0.05


@pytest.fixture
def death_portfolio():
    """Portfolio with only death products."""
    return Portfolio([
        Policy("WL-01", "whole_life", issue_age=35, SA=1_000_000, duration=5),
        Policy("TM-02", "term", issue_age=40, SA=2_000_000, n=20, duration=5),
        Policy("EN-03", "endowment", issue_age=30, SA=1_500_000, n=20, duration=8),
    ])


@pytest.fixture
def annuity_portfolio():
    """Portfolio with only annuity products."""
    return Portfolio([
        Policy("AN-01", "annuity", issue_age=60, annual_pension=120_000),
        Policy("AN-02", "annuity", issue_age=65, annual_pension=150_000),
        Policy("AN-03", "annuity", issue_age=70, annual_pension=100_000),
    ])


@pytest.fixture
def mixed_portfolio():
    """Portfolio with both death and annuity products."""
    return Portfolio([
        Policy("WL-01", "whole_life", issue_age=35, SA=1_000_000, duration=5),
        Policy("TM-02", "term", issue_age=40, SA=2_000_000, n=20, duration=5),
        Policy("AN-01", "annuity", issue_age=65, annual_pension=150_000),
    ])


# =============================================================================
# Test 1: Mortality shock increases death BEL
# =============================================================================

def test_mortality_shock_increases_death_bel(death_portfolio, life_table, interest_rate):
    """
    THEORY: A +15% q_x shock increases BEL for death products.

    Higher mortality means more expected claims sooner. The insurer
    must set aside MORE to cover these elevated death benefits.
    Therefore BEL_stressed > BEL_base.
    """
    result = compute_scr_mortality(death_portfolio, life_table, interest_rate)

    assert result["bel_stressed"] > result["bel_base"]
    assert result["scr"] > 0


# =============================================================================
# Test 2: Mortality SCR excludes annuities
# =============================================================================

def test_mortality_scr_excludes_annuities(annuity_portfolio, life_table, interest_rate):
    """
    THEORY: Annuity-only portfolio has SCR_mort = 0.

    Mortality risk only affects death products. Annuities actually
    BENEFIT from higher mortality (fewer pension payments), so they
    are excluded from the mortality shock module.
    """
    result = compute_scr_mortality(annuity_portfolio, life_table, interest_rate)

    assert result["scr"] == 0.0
    assert result["bel_base"] == 0.0


# =============================================================================
# Test 3: Mortality SCR proportional to shock
# =============================================================================

def test_mortality_scr_proportional(death_portfolio, life_table, interest_rate):
    """
    THEORY: A 30% shock produces approximately 2x the SCR of a 15% shock.

    The relationship between shock magnitude and SCR is approximately
    linear for small shocks. This is because BEL is roughly linear in
    mortality rates for death products (more claims proportional to q_x).
    """
    scr_15 = compute_scr_mortality(
        death_portfolio, life_table, interest_rate, shock=0.15
    )["scr"]
    scr_30 = compute_scr_mortality(
        death_portfolio, life_table, interest_rate, shock=0.30
    )["scr"]

    ratio = scr_30 / scr_15
    assert 1.5 < ratio < 2.5, f"30% shock should be ~2x of 15%, got ratio={ratio:.2f}"


# =============================================================================
# Test 4: Mortality SCR non-negative
# =============================================================================

def test_mortality_scr_positive(death_portfolio, life_table, interest_rate):
    """
    THEORY: SCR_mort >= 0 for any death portfolio.

    The mortality shock only increases q_x, which can only increase
    death claims. Therefore BEL_stressed >= BEL_base and SCR >= 0.
    """
    result = compute_scr_mortality(death_portfolio, life_table, interest_rate)
    assert result["scr"] >= 0


# =============================================================================
# Test 5: Longevity shock increases annuity BEL
# =============================================================================

def test_longevity_shock_increases_annuity_bel(annuity_portfolio, life_table, interest_rate):
    """
    THEORY: A -20% q_x shock increases BEL for annuity products.

    Lower mortality means people live longer, requiring the insurer
    to pay pensions for more years. This is why longevity is a RISK
    for annuity writers.
    """
    result = compute_scr_longevity(annuity_portfolio, life_table, interest_rate)

    assert result["bel_stressed"] > result["bel_base"]
    assert result["scr"] > 0


# =============================================================================
# Test 6: Longevity SCR excludes death products
# =============================================================================

def test_longevity_scr_excludes_death(death_portfolio, life_table, interest_rate):
    """
    THEORY: Death-only portfolio has SCR_long = 0.

    Longevity risk only affects annuity products. Death products
    actually benefit from lower mortality (fewer claims sooner).
    """
    result = compute_scr_longevity(death_portfolio, life_table, interest_rate)

    assert result["scr"] == 0.0
    assert result["bel_base"] == 0.0


# =============================================================================
# Test 7: Longevity larger for younger annuitants
# =============================================================================

def test_longevity_larger_for_younger_annuitants(life_table, interest_rate):
    """
    THEORY: A 60-year-old annuitant has more longevity risk than a 70-year-old.

    A younger annuitant has more remaining expected payments, so a
    permanent mortality improvement affects them over MORE years.
    The absolute BEL change is larger for younger annuitants.
    """
    port_60 = Portfolio([
        Policy("A60", "annuity", issue_age=60, annual_pension=120_000)
    ])
    port_70 = Portfolio([
        Policy("A70", "annuity", issue_age=70, annual_pension=120_000)
    ])

    scr_60 = compute_scr_longevity(port_60, life_table, interest_rate)["scr"]
    scr_70 = compute_scr_longevity(port_70, life_table, interest_rate)["scr"]

    assert scr_60 > scr_70


# =============================================================================
# Test 8: Longevity SCR non-negative
# =============================================================================

def test_longevity_scr_positive(annuity_portfolio, life_table, interest_rate):
    """
    THEORY: SCR_long >= 0 for any annuity portfolio.

    Decreasing q_x always increases the expected pension payments,
    so BEL_stressed >= BEL_base and SCR >= 0.
    """
    result = compute_scr_longevity(annuity_portfolio, life_table, interest_rate)
    assert result["scr"] >= 0


# =============================================================================
# Test 9: Interest rate down is worse
# =============================================================================

def test_ir_down_worse_than_up(mixed_portfolio, life_table, interest_rate):
    """
    THEORY: Lower interest rates increase BEL (down scenario typically dominates).

    When discount rates decrease, the present value of all future cash
    flows increases. Since BEL = PV(obligations), lower rates =>
    higher PV => higher BEL. This is why interest rate risk is often
    the LARGEST SCR component.
    """
    result = compute_scr_interest_rate(mixed_portfolio, life_table, interest_rate)

    assert result["bel_down"] > result["bel_base"], (
        f"BEL at lower rate should exceed base: "
        f"{result['bel_down']:.0f} vs {result['bel_base']:.0f}"
    )


# =============================================================================
# Test 10: Interest rate affects all products
# =============================================================================

def test_ir_affects_all_products(life_table, interest_rate):
    """
    THEORY: Interest rate risk affects BOTH death and annuity products.

    Unlike mortality/longevity (which affect only one product type),
    interest rate changes impact every discounted cash flow. This test
    verifies that both a death-only and annuity-only portfolio have
    positive IR SCR.
    """
    death_port = Portfolio([
        Policy("WL", "whole_life", issue_age=35, SA=1_000_000, duration=5)
    ])
    annuity_port = Portfolio([
        Policy("AN", "annuity", issue_age=65, annual_pension=150_000)
    ])

    scr_death = compute_scr_interest_rate(death_port, life_table, interest_rate)["scr"]
    scr_annuity = compute_scr_interest_rate(annuity_port, life_table, interest_rate)["scr"]

    assert scr_death > 0, "Death products should have IR risk"
    assert scr_annuity > 0, "Annuity products should have IR risk"


# =============================================================================
# Test 11: Interest rate SCR non-negative
# =============================================================================

def test_ir_scr_non_negative(mixed_portfolio, life_table, interest_rate):
    """
    THEORY: SCR_ir >= 0 by construction.

    The formula takes max(BEL_up - BEL_base, BEL_down - BEL_base, 0),
    so the result is always non-negative.
    """
    result = compute_scr_interest_rate(mixed_portfolio, life_table, interest_rate)
    assert result["scr"] >= 0


# =============================================================================
# Test 12: Catastrophe SCR positive
# =============================================================================

def test_cat_scr_positive(death_portfolio, life_table, interest_rate):
    """
    THEORY: A one-year mortality spike produces extra claims -> positive SCR.

    Catastrophe risk captures the impact of a sudden, short-term
    mortality event (pandemic, earthquake). The excess deaths above
    baseline translate directly to extra claims.
    """
    result = compute_scr_catastrophe(death_portfolio, life_table, interest_rate)
    assert result["scr"] > 0


# =============================================================================
# Test 13: Catastrophe SCR proportional to SA
# =============================================================================

def test_cat_proportional_to_sa(life_table, interest_rate):
    """
    THEORY: Doubling the sum assured doubles the catastrophe SCR.

    SCR_cat = sum(SA * delta_q * v), which is LINEAR in SA.
    A portfolio with 2x the coverage faces 2x the catastrophe claims.
    """
    port_1x = Portfolio([
        Policy("W1", "whole_life", issue_age=40, SA=1_000_000, duration=0)
    ])
    port_2x = Portfolio([
        Policy("W2", "whole_life", issue_age=40, SA=2_000_000, duration=0)
    ])

    scr_1x = compute_scr_catastrophe(port_1x, life_table, interest_rate)["scr"]
    scr_2x = compute_scr_catastrophe(port_2x, life_table, interest_rate)["scr"]

    assert scr_2x == pytest.approx(2.0 * scr_1x, rel=1e-10)


# =============================================================================
# Test 14: Aggregated SCR_life less than sum (diversification)
# =============================================================================

def test_aggregated_less_than_sum():
    """
    THEORY: SCR_life < sum of individual SCRs (diversification benefit).

    With the correlation matrix, the aggregated SCR is LESS than the
    simple sum because mortality and longevity are negatively correlated
    (-0.25). A pandemic increases death claims but decreases annuity
    obligations, creating a natural hedge.

    Specifically, if all three SCR components are positive:
        SCR_life = sqrt(vec' * CORR * vec)
    which is less than sum(vec) when off-diagonal correlations < 1.
    """
    scr_mort = 100_000
    scr_long = 80_000
    scr_cat = 50_000

    result = aggregate_scr_life(scr_mort, scr_long, scr_cat)

    assert result["scr_life"] < result["sum_individual"]
    assert result["diversification_benefit"] > 0
    assert result["diversification_pct"] > 0


# =============================================================================
# Test 15: Correlation matrix is PSD
# =============================================================================

def test_correlation_matrix_psd():
    """
    THEORY: The life underwriting correlation matrix must be positive
    semi-definite (PSD).

    A non-PSD matrix could produce negative variances (sqrt of negative
    number). Eigenvalues >= 0 guarantees physical consistency.
    """
    eigenvalues = np.linalg.eigvalsh(LIFE_CORR)

    for ev in eigenvalues:
        assert ev >= -1e-10, f"Eigenvalue {ev} is negative -- matrix is not PSD"


# =============================================================================
# Test 16: Total aggregation hand calculation
# =============================================================================

def test_total_aggregation():
    """
    THEORY: Verify total SCR against hand calculation.

    SCR_total = sqrt(SCR_life^2 + SCR_ir^2 + 2 * rho * SCR_life * SCR_ir)

    With SCR_life=150,000, SCR_ir=200,000, rho=0.25:
    = sqrt(150000^2 + 200000^2 + 2*0.25*150000*200000)
    = sqrt(22.5e9 + 40e9 + 15e9)
    = sqrt(77.5e9)
    = 278,388.22
    """
    result = aggregate_scr_total(150_000, 200_000, rho=0.25)

    expected = math.sqrt(150_000**2 + 200_000**2 + 2 * 0.25 * 150_000 * 200_000)
    assert result["scr_total"] == pytest.approx(expected, rel=1e-10)

    # Also: should be less than simple sum (diversification)
    assert result["scr_total"] < 150_000 + 200_000


# =============================================================================
# Test 17: Risk margin positive
# =============================================================================

def test_risk_margin_positive():
    """
    THEORY: Risk margin > 0 when SCR > 0 and duration > 0.

    The risk margin is the "price of capital" that compensates a
    hypothetical transferee for holding SCR over the remaining
    portfolio lifetime. CoC > 0, SCR > 0, duration > 0 => MdR > 0.
    """
    result = compute_risk_margin(scr_total=200_000, duration=15.0)

    assert result["risk_margin"] > 0
    assert result["annuity_factor"] > 0


# =============================================================================
# Test 18: Solvency ratio computation
# =============================================================================

def test_solvency_ratio():
    """
    THEORY: Solvency ratio = Available Capital / SCR.

    Above 100% means the insurer can absorb a 1-in-200-year shock.
    The formula is straightforward but the regulatory interpretation
    is critical: below 100% triggers CNSF supervisory action.
    """
    # Exactly at 100%
    result_100 = compute_solvency_ratio(200_000, 200_000)
    assert result_100["ratio"] == pytest.approx(1.0)
    assert result_100["is_solvent"] is True

    # At 150%
    result_150 = compute_solvency_ratio(300_000, 200_000)
    assert result_150["ratio"] == pytest.approx(1.5)
    assert result_150["is_solvent"] is True

    # Below 100%
    result_80 = compute_solvency_ratio(160_000, 200_000)
    assert result_80["ratio"] == pytest.approx(0.8)
    assert result_80["is_solvent"] is False


# =============================================================================
# Test 19: Full pipeline integration
# =============================================================================

def test_full_scr_pipeline(life_table, interest_rate):
    """
    THEORY: run_full_scr produces consistent, non-degenerate results.

    The full pipeline ties all components together. Key invariants:
    - Technical provisions = BEL + Risk Margin
    - SCR_total < sum of individual SCRs (diversification)
    - All individual SCRs >= 0
    - No NaN or Inf values in output
    """
    from backend.engine.a11_portfolio import create_sample_portfolio
    port = create_sample_portfolio()

    result = run_full_scr(
        port, life_table, interest_rate, available_capital=5_000_000
    )

    # All SCR components non-negative
    assert result["mortality"]["scr"] >= 0
    assert result["longevity"]["scr"] >= 0
    assert result["interest_rate"]["scr"] >= 0
    assert result["catastrophe"]["scr"] >= 0

    # Diversification works
    life_agg = result["life_aggregation"]
    assert life_agg["scr_life"] <= life_agg["sum_individual"]

    total_agg = result["total_aggregation"]
    assert total_agg["scr_total"] <= total_agg["sum_individual"]

    # Technical provisions = BEL + MdR
    tp = result["technical_provisions"]
    expected_tp = result["bel_base"] + result["risk_margin"]["risk_margin"]
    assert tp == pytest.approx(expected_tp, rel=1e-10)

    # Solvency computed
    assert result["solvency"] is not None
    assert result["solvency"]["ratio"] > 0

    # No NaN
    assert not math.isnan(result["bel_base"])
    assert not math.isnan(total_agg["scr_total"])
    assert not math.isnan(tp)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
