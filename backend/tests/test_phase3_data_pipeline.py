"""Focused regression tests for Phase 3 data-pipeline hardening."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.engine.a01_life_table import LifeTable
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a10_validation import MortalityComparison
from backend.engine.data_validation import (
    DataQualityReport,
    validate_age_year_range,
    validate_integer_columns,
    validate_mx_consistency,
    validate_no_missing_cells,
    validate_required_columns,
)
from backend.engine.exceptions import ActuarialValidationError, DataQualityError


def _mortality_data(mx: np.ndarray) -> MortalityData:
    ages = np.arange(mx.shape[0])
    years = np.arange(2000, 2000 + mx.shape[1])
    ex = np.full_like(mx, 100_000.0)
    return MortalityData("synthetic", "Total", ages, years, mx, mx * ex, ex)


def _lee_carter() -> SimpleNamespace:
    return SimpleNamespace(
        ages=np.arange(20, 23),
        years=np.arange(2000, 2003),
        ax=np.log(np.array([0.001, 0.002, 0.004])),
        bx=np.array([0.2, 0.3, 0.5]),
        kt=np.array([1.0, 0.5, 0.0]),
    )


def _life_table(qx: float) -> LifeTable:
    ages = list(range(20, 24))
    lx = [100_000.0]
    for _ in ages[:-1]:
        lx.append(lx[-1] * (1.0 - qx))
    return LifeTable(ages, lx)


def test_schema_validators_reject_malformed_frames():
    frame = pd.DataFrame({"Year": [2000], "Age": ["not-an-age"], "mx": [np.nan]})

    with pytest.raises(DataQualityError, match="missing required columns"):
        validate_required_columns(frame, ["Year", "Age", "dx"], source="mock")
    with pytest.raises(DataQualityError, match="missing values"):
        validate_no_missing_cells(frame, ["mx"], source="mock")
    with pytest.raises(DataQualityError, match="non-numeric"):
        validate_integer_columns(frame, ["Age"], source="mock")


@pytest.mark.parametrize(
    ("ages", "years", "message"),
    [
        (np.array([], dtype=int), np.array([2000]), "age range is empty"),
        (np.array([0]), np.array([], dtype=int), "year range is empty"),
        (np.array([-1, 0]), np.array([2000]), "minimum age"),
        (np.array([0]), np.array([1989]), "minimum year"),
    ],
)
def test_age_year_range_bounds(ages, years, message):
    with pytest.raises(DataQualityError, match=message):
        validate_age_year_range(
            ages,
            years,
            age_min=0,
            year_min=1990,
            source="mock",
        )


def test_mx_consistency_reports_worst_cell():
    ages = np.array([20, 21])
    years = np.array([2020, 2021])
    ex = np.full((2, 2), 100.0)
    dx = np.ones((2, 2))
    mx = dx / ex
    mx[1, 1] = 0.02

    with pytest.raises(DataQualityError, match=r"age 21, year 2021"):
        validate_mx_consistency(mx, dx, ex, ages, years, tolerance=0.01)


def test_data_quality_report_summary_and_conversion():
    mx = np.array([[0.01, 0.02], [0.03, 0.04]])
    report = DataQualityReport(
        country="Mexico",
        sex="Total",
        ages=np.array([0, 1]),
        years=np.array([2020, 2021]),
        mx=mx,
        dx=mx * 100,
        ex=np.full_like(mx, 100.0),
        missing_imputed=2,
        open_age_group=1,
        source="mock",
    )

    assert report.summary()["n_missing_imputed"] == 2
    assert report.summary()["shape"] == (2, 2)
    assert report.to_mortality_data_kwargs()["mx"] is mx


@pytest.mark.parametrize(
    ("lambda_param", "diff_order", "field"),
    [(-1.0, 2, "lambda_param"), (1.0, 0, "diff_order")],
)
def test_graduation_rejects_invalid_parameters(lambda_param, diff_order, field):
    data = _mortality_data(np.array([[0.01], [0.02], [0.03], [0.04]]))
    with pytest.raises(ActuarialValidationError) as exc:
        GraduatedRates(
            data,
            lambda_param=lambda_param,
            diff_order=diff_order,
            check_monotonicity=False,
        )
    assert exc.value.field == field


def test_graduation_rejects_non_positive_rates():
    data = _mortality_data(np.array([[0.01], [0.0], [0.03], [0.04]]))
    with pytest.raises(DataQualityError, match="non-positive rates"):
        GraduatedRates(data, check_monotonicity=False)


def test_graduation_warns_for_pathological_decreasing_curve():
    data = _mortality_data(np.array([[0.08], [0.07], [0.06], [0.05], [0.04], [0.03]]))
    with pytest.warns(UserWarning, match="not monotonically increasing"):
        GraduatedRates(data, lambda_param=0.0)


@pytest.mark.parametrize(
    ("horizon", "n_simulations", "field"),
    [(0, 10, "horizon"), (10, 0, "n_simulations"), (10, 1_000_001, "n_simulations")],
)
def test_projection_constructor_bounds(horizon, n_simulations, field):
    with pytest.raises(ActuarialValidationError) as exc:
        MortalityProjection(_lee_carter(), horizon=horizon, n_simulations=n_simulations)
    assert exc.value.field == field


def test_projection_rejects_single_observation_year():
    model = _lee_carter()
    model.years = np.array([2000])
    model.kt = np.array([0.0])
    with pytest.raises(ActuarialValidationError) as exc:
        MortalityProjection(model)
    assert exc.value.field == "lee_carter.years"


def test_projection_lookup_and_age_subset_bounds():
    projection = MortalityProjection(_lee_carter(), horizon=2, n_simulations=10)

    with pytest.raises(ActuarialValidationError, match="not in projection range"):
        projection.get_projected_mx(20, 2002)
    with pytest.raises(ActuarialValidationError, match="not in Lee-Carter model"):
        projection.get_projected_mx(19, 2003)
    with pytest.raises(ActuarialValidationError, match="cannot exceed"):
        projection.to_life_table(2003, age_min=22, age_max=20)
    with pytest.raises(ActuarialValidationError, match="No ages"):
        projection.to_life_table(2003, age_min=30, age_max=40)


def test_weighted_rmse_and_bias_have_known_values():
    comparison = MortalityComparison(_life_table(0.02), _life_table(0.01))

    assert comparison.bias(20, 22) == pytest.approx(0.01)
    assert comparison.weighted_rmse(20, 22, weights=np.array([1.0, 2.0, 3.0])) == pytest.approx(
        0.01
    )


def test_weighted_rmse_rejects_wrong_weight_count():
    comparison = MortalityComparison(_life_table(0.02), _life_table(0.01))
    with pytest.raises(ActuarialValidationError, match="weights length"):
        comparison.weighted_rmse(20, 22, weights=np.array([1.0]))


def test_summary_is_nan_safe_when_regulatory_qx_is_zero():
    comparison = MortalityComparison(_life_table(0.01), _life_table(0.0))
    summary = comparison.summary(20, 22)

    assert np.isnan(summary["max_ratio"])
    assert np.isnan(summary["min_ratio"])
    assert np.isnan(summary["mean_ratio"])
