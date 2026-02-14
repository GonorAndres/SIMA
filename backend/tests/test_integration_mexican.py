"""
Mexican Data Integration Tests
================================

End-to-end tests that validate the FULL pipeline using Mexican-format data:

    INEGI deaths + CONAPO population -> MortalityData.from_inegi()
        -> GraduatedRates -> LeeCarter -> MortalityProjection
        -> LifeTable -> MortalityComparison(vs regulatory table)

These tests use mock data that follows realistic Mexican demographic
patterns (Gompertz mortality, infant spike, young-adult hump) but are
deterministic and committed to the repo for CI reproducibility.
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a10_validation import MortalityComparison


# =============================================================================
# Test Fixtures
# =============================================================================

MOCK_DIR = str(Path(__file__).parent.parent / "data" / "mock")


@pytest.fixture
def inegi_data():
    """Load mock INEGI/CONAPO data for Total population, 2000-2010."""
    return MortalityData.from_inegi(
        deaths_filepath=str(Path(MOCK_DIR) / "mock_inegi_deaths.csv"),
        population_filepath=str(Path(MOCK_DIR) / "mock_conapo_population.csv"),
        sex="Total",
        year_start=2000,
        year_end=2010,
        age_max=100,
    )


@pytest.fixture
def cnsf_life_table():
    """Load mock CNSF 2000-I regulatory table as LifeTable."""
    return LifeTable.from_regulatory_table(
        filepath=str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv"),
        sex="male",
        radix=100_000.0,
    )


@pytest.fixture
def emssa_life_table():
    """Load mock EMSSA-2009 regulatory table as LifeTable."""
    return LifeTable.from_regulatory_table(
        filepath=str(Path(MOCK_DIR) / "mock_emssa_2009.csv"),
        sex="male",
        radix=100_000.0,
    )


@pytest.fixture
def inegi_pipeline(inegi_data):
    """
    Full pipeline from mock INEGI data:
    MortalityData -> GraduatedRates -> LeeCarter -> MortalityProjection.
    """
    grad = GraduatedRates(inegi_data, lambda_param=1e5)
    lc = LeeCarter.fit(grad, reestimate_kt=True)
    proj = MortalityProjection(lc, horizon=5, n_simulations=200, random_seed=42)
    return proj


# =============================================================================
# Test: Full Pipeline End-to-End (INEGI -> Premiums)
# =============================================================================

def test_mock_inegi_full_pipeline(inegi_pipeline, cnsf_life_table):
    """
    THEORY: The complete actuarial pipeline must work end-to-end:

        INEGI deaths + CONAPO population
        -> MortalityData.from_inegi()   [load & compute m_x]
        -> GraduatedRates              [smooth with Whittaker-Henderson]
        -> LeeCarter.fit()             [decompose into a_x, b_x, k_t]
        -> MortalityProjection         [RWD forecast of k_t]
        -> to_life_table()             [convert back to q_x, l_x]
        -> MortalityComparison         [compare vs regulatory benchmark]

    This test verifies that Mexican-format data can flow through the
    entire engine and produce reasonable actuarial metrics.
    """
    proj = inegi_pipeline

    # Convert projection to LifeTable
    target_year = proj.projected_years[2]  # 3rd projected year
    lt = proj.to_life_table(target_year, radix=100_000)

    # Validate the projected life table
    v = lt.validate()
    assert v["sum_deaths_equals_l0"], "Deaths must sum to l_0"
    assert v["terminal_mortality_is_one"], "q_omega must be 1.0"
    assert v["all_rates_valid"], "All q_x must be in [0, 1]"

    # Compare against regulatory table
    comp = MortalityComparison(lt, cnsf_life_table, name="LC_mock_vs_CNSF")
    summary = comp.summary()

    # RMSE should be finite and positive (tables differ but are based on
    # similar Gompertz parameters, so should be reasonably close)
    assert np.isfinite(summary["rmse"]), "RMSE must be finite"
    assert summary["rmse"] >= 0, "RMSE must be non-negative"

    # Ratios should be in a reasonable range (not wildly off)
    assert summary["min_ratio"] > 0.1, "Min ratio too low -- projection far below regulatory"
    assert summary["max_ratio"] < 10.0, "Max ratio too high -- projection far above regulatory"

    # Mean ratio near 1 indicates reasonable agreement
    assert 0.3 < summary["mean_ratio"] < 3.0, (
        f"Mean ratio {summary['mean_ratio']:.3f} outside reasonable range"
    )


def test_inegi_pipeline_produces_valid_premiums(inegi_pipeline):
    """
    THEORY: If the pipeline is correct, we should be able to price
    a whole-life insurance product using Mexican projected mortality.

    The premium must satisfy the equivalence principle:
    P * a_x = SA * A_x

    where a_x is the annuity factor and A_x is the insurance value,
    both computed from the projected life table.
    """
    proj = inegi_pipeline
    target_year = proj.projected_years[0]
    lt = proj.to_life_table(target_year, radix=100_000)

    # Use working ages for pricing
    lt_sub = lt.subset(30, 100)
    comm = CommutationFunctions(lt_sub, interest_rate=0.05)
    pc = PremiumCalculator(comm)

    sa = 1_000_000

    # Whole life premium
    p_whole = pc.whole_life(SA=sa, x=30)
    assert p_whole > 0, "Whole life premium must be positive"
    assert p_whole < sa, "Annual premium must be less than sum assured"

    # Term insurance (20 years)
    p_term = pc.term(SA=sa, x=30, n=20)
    assert p_term > 0, "Term premium must be positive"
    assert p_term < p_whole, "Term < whole life (less coverage duration)"

    # Endowment (20 years)
    p_endow = pc.endowment(SA=sa, x=30, n=20)
    assert p_endow > 0, "Endowment premium must be positive"
    assert p_endow > p_term, "Endowment > term (adds survival benefit)"


def test_comparison_cnsf_vs_emssa(cnsf_life_table, emssa_life_table):
    """
    THEORY: CNSF 2000-I (general population) should show HIGHER mortality
    than EMSSA-2009 (social security population), because the general
    population includes uninsured/informal workers with higher risk.

    In practice, the EMSSA table is fitted to IMSS-affiliated workers
    who tend to have better healthcare access, so their mortality is lower.
    """
    comp = MortalityComparison(
        cnsf_life_table, emssa_life_table, name="CNSF_vs_EMSSA"
    )

    # CNSF (general) vs EMSSA (social security):
    # General population mortality should be higher on average
    ratios = comp.qx_ratio()
    mean_ratio = np.mean(ratios)
    assert mean_ratio > 1.0, (
        f"CNSF q_x should be higher than EMSSA on average, "
        f"but mean ratio = {mean_ratio:.4f}"
    )


def test_regulatory_tables_produce_valid_commutations(cnsf_life_table, emssa_life_table):
    """
    THEORY: Both regulatory tables should produce valid commutation
    functions and sensible insurance premiums when fed into the engine.
    This verifies the from_regulatory_table() -> CommutationFunctions
    -> PremiumCalculator chain works correctly.
    """
    for lt, name in [(cnsf_life_table, "CNSF"), (emssa_life_table, "EMSSA")]:
        lt_sub = lt.subset(20, 100)
        comm = CommutationFunctions(lt_sub, interest_rate=0.05)
        pc = PremiumCalculator(comm)

        premium = pc.whole_life(SA=1_000_000, x=30)
        assert premium > 0, f"{name}: premium must be positive"
        assert premium < 100_000, f"{name}: premium too high for age 30"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
