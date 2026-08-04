"""
Open-Interval Aggregate Tests (a06 - _drop_open_interval_duplicates)
====================================================================

Regression tests for the INEGI "85 y mas" double count.

The bug
-------
INEGI's "Defunciones registradas" file publishes the open group "85 y mas" as a
row whose ``Edad`` is the bare integer 85, sitting next to the genuine single
age 85. Same Anio, same Sexo, same Edad -- nothing in the file tells them apart.
``_cap_ages_sum()`` grouped by (Year, Age) and summed, so d_85 absorbed every
death from 85 to 120 on top of the real d_85. On the 1990-2024 file that is 105
duplicated keys (35 years x 3 sexes), m_85 ~ 0.93 against m_84 ~ 0.095, and 11
cells with m_x > 1.

Why it shipped green
--------------------
``mock_inegi_deaths.csv`` used to cover 2000-2010, ages 0-100, with no duplicate
keys and no open-interval row -- the broken branch was literally unreachable
from the test suite. The fixture now carries both the open group and ages above
the cap, so these tests exercise the same code path production does.

Verified against the pre-fix loader: with ``_drop_open_interval_duplicates()``
neutralised, the fixture yields m_85 = 1.465 in 2005 against m_84 = 0.0675 and
d_85 = 57330 instead of 2878. Every value assertion below fails on that loader.
"""

import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import (
    MortalityData,
    _cap_ages_sum,
    _drop_open_interval_duplicates,
)
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.exceptions import DataQualityError

MOCK_DIR = Path(__file__).parent.parent / "data" / "mock"
DEATHS_FILE = str(MOCK_DIR / "mock_inegi_deaths.csv")
POP_FILE = str(MOCK_DIR / "mock_conapo_population.csv")

REAL_DEATHS = Path(__file__).parent.parent / "data" / "inegi" / "inegi_deaths.csv"
REAL_POP = Path(__file__).parent.parent / "data" / "conapo" / "conapo_population.csv"

OPEN_GROUP_AGE = 85


@pytest.fixture
def mock_deaths_frame():
    """The raw mock deaths file, unfiltered."""
    return pd.read_csv(DEATHS_FILE)


@pytest.fixture
def mock_data():
    """Mock INEGI/CONAPO loaded through the fixed loader."""
    return MortalityData.from_inegi(
        deaths_filepath=DEATHS_FILE,
        population_filepath=POP_FILE,
        sex="Total",
        year_start=2000,
        year_end=2010,
        age_max=100,
    )


# =============================================================================
# Test: the fixture really does reproduce the source's shape
# =============================================================================


def test_mock_fixture_contains_open_interval_row(mock_deaths_frame):
    """
    THEORY: a regression test is only worth anything if the fixture can express
    the defect. This guards the fixture itself: if someone regenerates
    mock_inegi_deaths.csv without the open group, every other test in this file
    silently stops testing anything.
    """
    dup = mock_deaths_frame[mock_deaths_frame.duplicated(["Anio", "Edad", "Sexo"], keep=False)]
    assert not dup.empty, "fixture lost its open-interval row"
    assert set(dup["Edad"].unique()) == {OPEN_GROUP_AGE}
    # 11 years x 3 sexes x 2 rows per duplicated key
    assert len(dup) == 11 * 3 * 2


def test_mock_fixture_has_ages_above_the_cap(mock_deaths_frame):
    """
    THEORY: the drop has to happen before ages above the cap are reassigned to
    age_max, because after that reassignment a genuine age 103 is
    indistinguishable from a duplicate of age 100. Ages above the cap must
    therefore exist in the fixture for the ordering to be under test.
    """
    assert mock_deaths_frame["Edad"].max() > 100


def test_open_interval_row_equals_single_age_plus_tail(mock_deaths_frame):
    """
    THEORY: the open group at age a covers a and everything above it. That
    identity -- aggregate = single + sum(ages > a) -- is how the loader tells
    the two rows apart, and it holds exactly in the real INEGI file for all 105
    duplicated keys.
    """
    for (year, sex), group in mock_deaths_frame.groupby(["Anio", "Sexo"]):
        rows = group.loc[group["Edad"] == OPEN_GROUP_AGE, "Defunciones"].tolist()
        assert len(rows) == 2, f"{year}/{sex}"
        single, aggregate = sorted(rows)
        tail = int(group.loc[group["Edad"] > OPEN_GROUP_AGE, "Defunciones"].sum())
        assert aggregate == single + tail, f"{year}/{sex}"


# =============================================================================
# Test: the loader drops it instead of summing it
# =============================================================================


def test_open_interval_row_is_dropped_not_summed(mock_deaths_frame, mock_data):
    """
    THEORY: d_85 must be the deaths of people aged exactly 85. Summing the open
    group into it inflates the numerator while the denominator stays the
    single-age population, so m_85 stops being a rate at all.

    Pre-fix this cell held 57330 deaths and m_85 = 1.465.
    """
    year = 2005
    age_idx = list(mock_data.ages).index(OPEN_GROUP_AGE)
    year_idx = list(mock_data.years).index(year)

    rows = mock_deaths_frame[
        (mock_deaths_frame.Anio == year)
        & (mock_deaths_frame.Sexo == "Total")
        & (mock_deaths_frame.Edad == OPEN_GROUP_AGE)
    ]["Defunciones"].tolist()
    genuine_single_age = min(rows)

    assert mock_data.dx[age_idx, year_idx] == pytest.approx(genuine_single_age)
    assert mock_data.dx[age_idx, year_idx] != pytest.approx(sum(rows))


def test_mx_85_sits_between_its_neighbours(mock_data):
    """
    THEORY: mortality rises monotonically through the old ages. m_85 landing an
    order of magnitude above m_84 and m_86 is not a mortality signal, it is an
    arithmetic accident.
    """
    for year in (2000, 2005, 2010):
        assert mock_data.get_mx(84, year) < mock_data.get_mx(85, year)
        assert mock_data.get_mx(85, year) < mock_data.get_mx(86, year)


def test_no_death_rate_above_one_at_closed_ages(mock_data):
    """
    THEORY: below the open group a central death rate cannot exceed 1 -- deaths
    and exposure describe the same people. The pre-fix loader produced 11 such
    cells on this fixture.
    """
    closed = mock_data.mx[:-1, :]
    assert np.all(closed <= 1.0), f"max closed-age m_x = {closed.max()}"


def test_ages_above_the_cap_are_aggregated_not_discarded(mock_deaths_frame, mock_data):
    """
    THEORY: capping is not truncation. Ages 101-105 must be folded into the
    age-100 open group, not thrown away -- otherwise the terminal rate is
    understated and the life table runs off the end of the data.
    """
    year = 2005
    expected = int(
        mock_deaths_frame[
            (mock_deaths_frame.Anio == year)
            & (mock_deaths_frame.Sexo == "Total")
            & (mock_deaths_frame.Edad >= 100)
        ]["Defunciones"].sum()
    )
    age_idx = list(mock_data.ages).index(100)
    year_idx = list(mock_data.years).index(year)
    assert mock_data.dx[age_idx, year_idx] == pytest.approx(expected)


# =============================================================================
# Test: unexplained duplicates fail loudly
# =============================================================================


def _long_frame(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Year", "Age", "Value"])


def test_duplicate_that_is_not_an_open_group_raises():
    """
    THEORY: a duplicated key the loader cannot explain must stop the load. The
    failure mode being fixed here is precisely a silent sum, so falling back to
    "drop the bigger one" for an unrecognised shape would reintroduce the class
    of bug in a new disguise.
    """
    # 85 appears twice but neither row equals the other plus the tail (10 + 20).
    frame = _long_frame([(2000, 85, 40.0), (2000, 85, 35.0), (2000, 86, 10.0), (2000, 87, 20.0)])
    with pytest.raises(DataQualityError, match="open-interval aggregate"):
        _drop_open_interval_duplicates(frame, source="test")


def test_triplicated_key_raises():
    """THEORY: an open group duplicates its single age once, never twice."""
    frame = _long_frame([(2000, 85, 1.0), (2000, 85, 2.0), (2000, 85, 3.0)])
    with pytest.raises(DataQualityError, match="rows share"):
        _drop_open_interval_duplicates(frame, source="test")


def test_genuine_open_group_is_dropped_by_the_helper():
    """THEORY: aggregate = single + tail is recognised and removed."""
    frame = _long_frame([(2000, 85, 34.0), (2000, 85, 4.0), (2000, 86, 20.0), (2000, 87, 10.0)])
    out = _drop_open_interval_duplicates(frame, source="test")
    assert len(out) == 3
    assert out.loc[out["Age"] == 85, "Value"].tolist() == [4.0]


def test_cap_ages_sum_drops_before_reassigning_ages():
    """
    THEORY: order of operations. If the age reassignment ran first, ages 101 and
    102 would already be labelled 100 and the dedup could not distinguish them
    from a duplicate of 100 -- so it would delete real deaths.
    """
    frame = _long_frame(
        [(2000, 85, 34.0), (2000, 85, 4.0), (2000, 100, 20.0), (2000, 101, 6.0), (2000, 102, 4.0)]
    )
    out = _cap_ages_sum(frame, age_max=100, source="test")
    assert out.loc[out["Age"] == 85, "Value"].tolist() == [4.0]
    assert out.loc[out["Age"] == 100, "Value"].tolist() == [30.0]


def test_frames_without_duplicates_are_returned_unchanged():
    """THEORY: HMD files have no open-group duplicates; the helper is a no-op."""
    frame = _long_frame([(2000, 98, 1.0), (2000, 99, 2.0), (2000, 100, 3.0)])
    assert _drop_open_interval_duplicates(frame, source="test") is frame


# =============================================================================
# Test: the real Mexican files (skipped when only the mock fixtures exist)
# =============================================================================

real_data = pytest.mark.skipif(
    not (REAL_DEATHS.exists() and REAL_POP.exists()),
    reason="real INEGI/CONAPO files not present (they are gitignored; see DATA.md)",
)


@pytest.fixture
def real_mexico():
    return MortalityData.from_inegi(
        deaths_filepath=str(REAL_DEATHS),
        population_filepath=str(REAL_POP),
        sex="Total",
        year_start=1990,
        year_end=2019,
        age_max=100,
    )


@real_data
def test_real_inegi_has_no_rate_above_one_below_the_open_group(real_mexico):
    """
    THEORY: the production window (1990-2019, ages 0-100) must not contain a
    central rate above 1 at any closed age. It contained 11 -- all at age 85 --
    until the open group was dropped.

    The age-100 group is excluded on purpose: it is an open interval, where
    m -> 2 as q -> 1, and Mexico genuinely sits above 1 there in the early
    1990s because INEGI registers more centenarian deaths than CONAPO projects
    centenarians alive. That is a source artifact, documented in DATA.md, not a
    loader defect.
    """
    closed = real_mexico.mx[:-1, :]
    assert np.all(closed <= 1.0), f"max closed-age m_x = {closed.max()}"


@real_data
def test_real_inegi_graduated_curve_is_monotone_through_the_old_ages(real_mexico):
    """
    THEORY: after Whittaker-Henderson graduation the force of mortality must
    rise smoothly through ages 83-90. The double count put a spike at 85 that
    graduation could only smear across its neighbours. Measured on a 2019 period
    table built from the graduated rates: the fix moves e_65 by +4.37%
    (17.4679 -> 18.2318) and the age-60 whole-life premium by -3.29%
    (30,193.16 -> 29,198.69). See DATA.md for the full comparison.
    """
    grad = GraduatedRates(real_mexico, lambda_param=1e5, diff_order=2, weight_by_exposure=True)
    mean_mx = np.mean(grad.mx, axis=1)
    window = [float(mean_mx[i]) for i, age in enumerate(grad.ages) if 83 <= age <= 90]

    assert all(b > a for a, b in pairwise(window)), window
    # Smoothness: no second difference larger than 5% of the level of the
    # series. A spike at 85 blows this out by two orders of magnitude.
    second_diff = [
        abs(window[i + 2] - 2 * window[i + 1] + window[i]) for i in range(len(window) - 2)
    ]
    assert max(second_diff) < 0.05 * min(window), second_diff
