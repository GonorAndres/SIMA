"""
Mortality data loading (a06, HMD path) -- structure and invariants.

HMD files in the repo are synthetic but structurally valid, so these tests
exercise the pivot/alignment/aggregation logic (not data authenticity):
matrix shape, the m = d/L relationship at the cell level (catches a
misaligned pivot), and the age-capping aggregation against an uncapped load.
"""

import numpy as np
import pytest

from backend.engine.a06_mortality_data import MortalityData
from conftest import HMD_DIR


@pytest.fixture(scope="module")
def usa():
    return MortalityData.from_hmd(
        data_dir=HMD_DIR, country="usa", sex="Male",
        year_min=1990, year_max=2020, age_max=100,
    )


def test_matrix_shape_and_labels(usa):
    # THEORY: ages 0..100 (capped) x years 1990..2020 -> 101 x 31 aligned grid.
    assert usa.shape == (101, 31)
    assert usa.ages[0] == 0 and usa.ages[-1] == 100
    assert usa.years[0] == 1990 and usa.years[-1] == 2020


@pytest.mark.parametrize("age,year", [(30, 1995), (65, 2010), (0, 2020)])
def test_mx_equals_deaths_over_exposure(usa, age, year):
    # THEORY: central rate m = d / L. Because dx, ex and mx are pivoted
    # independently, this equality only holds if all three matrices are
    # aligned on the same (age, year) axes.  Bug caught: a transposed or
    # mislabeled pivot.
    ai = np.searchsorted(usa.ages, age)
    yi = np.searchsorted(usa.years, year)
    assert usa.get_mx(age, year) == pytest.approx(usa.dx[ai, yi] / usa.ex[ai, yi], rel=1e-6)


def test_age_capping_sums_tail_exposure():
    # THEORY: capping at age_max aggregates the open tail. Exposure at the
    # capped age must equal the SUM of raw exposures for ages >= age_max in
    # the uncapped load.  Bug caught: capping that drops or averages the tail.
    capped = MortalityData.from_hmd(
        data_dir=HMD_DIR, country="usa", sex="Male",
        year_min=2000, year_max=2000, age_max=90,
    )
    uncapped = MortalityData.from_hmd(
        data_dir=HMD_DIR, country="usa", sex="Male",
        year_min=2000, year_max=2000, age_max=110,
    )
    ci = np.searchsorted(capped.ages, 90)
    tail_mask = uncapped.ages >= 90
    assert capped.ages[-1] == 90
    assert capped.ex[ci, 0] == pytest.approx(uncapped.ex[tail_mask, 0].sum(), rel=1e-9)


def test_no_zero_or_nan_rates(usa):
    # THEORY: Lee-Carter needs strictly positive rates (log transform).
    s = usa.summary()
    assert s["any_zeros"] is False
    assert not np.any(np.isnan(usa.mx))


def test_invalid_sex_raises():
    # THEORY: an unknown sex column must fail loudly.
    with pytest.raises(ValueError):
        MortalityData.from_hmd(
            data_dir=HMD_DIR, country="usa", sex="Nonbinary",
            year_min=1990, year_max=2020,
        )
