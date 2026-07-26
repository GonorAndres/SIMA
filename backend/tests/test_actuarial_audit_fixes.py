"""Regression tests for the independent actuarial-programmer audit."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a11_portfolio import (
    Policy,
    Portfolio,
    compute_policy_bel,
    policy_remaining_horizon,
)
from backend.engine.a12_scr import (
    aggregate_scr_total,
    build_shocked_life_table,
    calibrate_shocks_from_lee_carter,
    compute_risk_margin,
    compute_scr_interest_rate,
    compute_scr_mortality,
)
from backend.engine.exceptions import ActuarialValidationError


@pytest.fixture
def life_table() -> LifeTable:
    ages = list(range(30, 101))
    lx = [100_000.0]
    for age in ages[:-1]:
        qx = min(0.0005 * 1.09 ** (age - 30), 0.95)
        lx.append(lx[-1] * (1.0 - qx))
    return LifeTable(ages, lx)


def test_mortality_scr_holds_contractual_premium_fixed(life_table):
    policy = Policy("WL", "whole_life", 40, SA=1_000_000, duration=15)
    portfolio = Portfolio([policy])
    base_comm = CommutationFunctions(life_table, 0.05)
    premium = PremiumCalculator(base_comm).whole_life(policy.SA, policy.issue_age)
    shocked = build_shocked_life_table(life_table, 1.15)

    expected_base = compute_policy_bel(policy, life_table, 0.05, annual_premium=premium)
    expected_stressed = compute_policy_bel(policy, shocked, 0.05, annual_premium=premium)
    result = compute_scr_mortality(portfolio, life_table, 0.05)

    assert result["bel_base"] == pytest.approx(expected_base)
    assert result["bel_stressed"] == pytest.approx(expected_stressed)
    assert result["scr"] == pytest.approx(max(expected_stressed - expected_base, 0.0))


def test_interest_scr_holds_contractual_premium_fixed(life_table):
    policy = Policy("WL", "whole_life", 40, SA=1_000_000, duration=15)
    portfolio = Portfolio([policy])
    premium = PremiumCalculator(CommutationFunctions(life_table, 0.05)).whole_life(
        policy.SA, policy.issue_age
    )

    def bel(rate):
        return compute_policy_bel(policy, life_table, rate, annual_premium=premium)

    result = compute_scr_interest_rate(portfolio, life_table, 0.05)
    expected = max(bel(0.06) - bel(0.05), bel(0.04) - bel(0.05), 0.0)
    assert result["scr"] == pytest.approx(expected)


def test_explicit_policy_premium_overrides_derived_issue_premium(life_table):
    policy = Policy(
        "WL",
        "whole_life",
        40,
        SA=1_000_000,
        duration=10,
        annual_premium=12_345.0,
    )
    av = ActuarialValues(CommutationFunctions(life_table, 0.05))
    expected = policy.SA * av.A_x(policy.attained_age) - 12_345.0 * av.a_due(policy.attained_age)
    assert compute_policy_bel(policy, life_table, 0.05) == pytest.approx(expected)


def test_endowment_bel_at_and_after_maturity(life_table):
    due = Policy("E-DUE", "endowment", 40, SA=100_000, n=10, duration=10)
    paid = Policy("E-PAID", "endowment", 40, SA=100_000, n=10, duration=11)

    assert due.is_matured
    assert not due.is_expired
    assert compute_policy_bel(due, life_table, 0.05) == 100_000
    assert paid.is_expired
    assert compute_policy_bel(paid, life_table, 0.05) == 0


def test_remaining_horizon_is_undiscounted_curtate_expectation(life_table):
    policy = Policy("WL", "whole_life", 40, SA=100_000, duration=15)
    zero_rate_av = ActuarialValues(CommutationFunctions(life_table, 0.0))
    expected = zero_rate_av.a_due(policy.attained_age) - 1.0
    assert policy_remaining_horizon(policy, life_table, 0.05) == pytest.approx(expected)


def test_empty_portfolio_rejected_for_bel(life_table):
    with pytest.raises(ActuarialValidationError, match="at least one policy"):
        Portfolio([]).compute_bel(life_table, 0.05)


def test_risk_margin_supports_zero_discount_rate():
    result = compute_risk_margin(1_000.0, duration=10.0, discount_rate=0.0)
    assert result["annuity_factor"] == 10.0
    assert result["risk_margin"] == pytest.approx(600.0)


def test_calibrated_longevity_shock_uses_inverse_direction():
    model = SimpleNamespace(
        kt=np.array([0.0, -0.2, -0.7, -0.9, -1.5]),
        bx=np.array([0.02, 0.03, 0.04]),
        ages=np.array([20, 50, 80]),
    )
    result = calibrate_shocks_from_lee_carter(model)
    delta = np.log1p(result["mortality_shock"])
    assert result["longevity_shock"] == pytest.approx(1.0 - np.exp(-delta))
    assert 0 <= result["longevity_shock"] < 1


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"scr_life": -1.0, "scr_ir": 1.0}, "scr_life"),
        ({"scr_life": 1.0, "scr_ir": 1.0, "rho": 1.1}, "rho"),
    ],
)
def test_scr_aggregation_rejects_invalid_public_inputs(kwargs, field):
    with pytest.raises(ActuarialValidationError) as exc:
        aggregate_scr_total(**kwargs)
    assert exc.value.field == field


def test_fractional_term_rejected_at_boundary(life_table):
    av = ActuarialValues(CommutationFunctions(life_table, 0.05))
    with pytest.raises(ActuarialValidationError) as exc:
        av.A_term(40, 1.5)
    assert exc.value.field == "n"


def test_pure_endowment_summary_no_longer_crashes(life_table):
    summary = ReserveCalculator(CommutationFunctions(life_table, 0.05)).summary(
        100_000, 40, "pure_endowment", 10
    )
    assert "Annual Premium" in summary


def test_lee_carter_summary_exposes_reestimation_fallbacks():
    model = LeeCarter(
        ages=np.array([20, 21]),
        years=np.array([2000, 2001]),
        ax=np.array([-5.0, -4.0]),
        bx=np.array([0.5, 0.5]),
        kt=np.array([0.1, -0.1]),
        log_mx=np.array([[-5.0, -5.1], [-4.0, -4.1]]),
        explained_variance=0.9,
        reestimation_fallback_indices=[1],
    )
    assert model.summary()["reestimation_fallback_indices"] == [1]


def test_inegi_missing_value_imputation_recomputes_consistent_mx(tmp_path):
    deaths = []
    population = []
    for year in (2000, 2001):
        for age in range(10):
            deaths.append(
                {
                    "Anio": year,
                    "Edad": age,
                    "Sexo": "Total",
                    "Defunciones": np.nan if (year, age) == (2000, 5) else 10 + age,
                }
            )
            population.append(
                {
                    "Anio": year,
                    "Edad": age,
                    "Sexo": "Total",
                    "Poblacion": 10_000 + 100 * age,
                }
            )
    deaths_path = tmp_path / "deaths.csv"
    population_path = tmp_path / "population.csv"
    pd.DataFrame(deaths).to_csv(deaths_path, index=False)
    pd.DataFrame(population).to_csv(population_path, index=False)

    data = MortalityData.from_inegi(
        str(deaths_path),
        str(population_path),
        sex="Total",
        year_start=2000,
        year_end=2001,
        age_max=9,
        impute_missing=True,
    )
    np.testing.assert_allclose(data.mx, data.dx / data.ex)
    assert np.isfinite(data.mx).all()
