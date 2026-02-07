"""
Lee-Carter Integration Tests
==============================

End-to-end tests that validate the FULL pipeline:

    HMD files -> MortalityData -> GraduatedRates -> LeeCarter
        -> MortalityProjection -> LifeTable -> Commutations -> Premiums

These tests prove that empirical data flows through the entire engine
and produces actuarially reasonable results.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator


# =============================================================================
# Test Fixtures
# =============================================================================

DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")


@pytest.fixture
def full_pipeline_usa():
    """
    Full pipeline: HMD -> Graduate -> Lee-Carter -> Project.
    Returns (projection, data) tuple.
    """
    data = MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )
    grad = GraduatedRates(data, lambda_param=1e5)
    lc = LeeCarter.fit(grad, reestimate_kt=True)
    proj = MortalityProjection(lc, horizon=30, n_simulations=500, random_seed=42)
    return proj, data


# =============================================================================
# Test: Full Pipeline End-to-End
# =============================================================================

def test_full_pipeline_produces_valid_premiums(full_pipeline_usa):
    """
    FULL PIPELINE: HMD -> Graduate -> Lee-Carter -> Project -> LifeTable
                    -> CommutationFunctions -> PremiumCalculator

    This is the ultimate test: can we start from raw HMD data and
    arrive at an actuarially meaningful premium for a life insurance policy?
    """
    proj, _ = full_pipeline_usa

    # Project to 10 years from now
    year = proj.projected_years[9]  # 10th projected year
    lt = proj.to_life_table(year, radix=100_000)

    # Use ages 30-100 for a typical insurance calculation
    lt_sub = lt.subset(30, 100)
    comm = CommutationFunctions(lt_sub, interest_rate=0.05)
    pc = PremiumCalculator(comm)

    sa = 1_000_000

    # Whole life premium
    p_whole = pc.whole_life(SA=sa, x=30)
    assert p_whole > 0, "Whole life premium must be positive"
    assert p_whole < sa, "Premium must be less than sum assured"

    # Term insurance (20 years)
    p_term = pc.term(SA=sa, x=30, n=20)
    assert p_term > 0, "Term premium must be positive"
    assert p_term < p_whole, "Term premium should be less than whole life"

    # Endowment (20 years)
    p_endow = pc.endowment(SA=sa, x=30, n=20)
    assert p_endow > 0, "Endowment premium must be positive"
    assert p_endow > p_term, "Endowment premium should exceed term"


def test_mortality_improvement_lowers_premiums(full_pipeline_usa):
    """
    THEORY: As mortality improves over time, death rates decrease,
    which should LOWER insurance premiums for death coverage.

    We compare premiums computed from two different projection years:
    - A near-future year (less mortality improvement)
    - A far-future year (more mortality improvement)

    The far-future premium should be lower because fewer people die.
    """
    proj, _ = full_pipeline_usa

    sa = 1_000_000

    # Near future: 5 years out
    lt_near = proj.to_life_table(proj.projected_years[4], radix=100_000)
    lt_near_sub = lt_near.subset(30, 100)
    comm_near = CommutationFunctions(lt_near_sub, interest_rate=0.05)
    pc_near = PremiumCalculator(comm_near)
    premium_near = pc_near.whole_life(SA=sa, x=30)

    # Far future: 25 years out
    lt_far = proj.to_life_table(proj.projected_years[24], radix=100_000)
    lt_far_sub = lt_far.subset(30, 100)
    comm_far = CommutationFunctions(lt_far_sub, interest_rate=0.05)
    pc_far = PremiumCalculator(comm_far)
    premium_far = pc_far.whole_life(SA=sa, x=30)

    # With improving mortality, far-future premium should be lower
    assert premium_far < premium_near, (
        f"Far-future premium ({premium_far:.2f}) should be less than "
        f"near-future premium ({premium_near:.2f}) due to mortality improvement"
    )


def test_spain_pipeline_also_works():
    """
    Verify the entire pipeline works for Spain too, not just USA.
    Different countries should produce different but reasonable results.
    """
    data = MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="spain",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )
    lc = LeeCarter.fit(data, reestimate_kt=True)
    proj = MortalityProjection(lc, horizon=20, n_simulations=200, random_seed=42)

    lt = proj.to_life_table(proj.projected_years[0], radix=100_000)
    v = lt.validate()
    assert v["sum_deaths_equals_l0"]
    assert v["terminal_mortality_is_one"]
    assert v["all_rates_valid"]

    # Should produce valid premiums
    lt_sub = lt.subset(30, 100)
    comm = CommutationFunctions(lt_sub, interest_rate=0.05)
    pc = PremiumCalculator(comm)
    premium = pc.whole_life(SA=1_000_000, x=30)
    assert premium > 0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
