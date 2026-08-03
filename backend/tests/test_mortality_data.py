"""
Mortality Data Tests (a06)
===========================

Validates that HMD data loading produces correct, consistent matrices
ready for Lee-Carter estimation.

These tests hit REAL HMD files, confirming the full pipeline from
raw text -> validated numpy matrices.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a06_mortality_data import HMD_DOWNLOAD_DATE, MortalityData

# =============================================================================
# Test Fixtures
# =============================================================================

DATA_DIR = str(Path(__file__).parent.parent / "data" / "hmd")


@pytest.fixture
def usa_data():
    """Load USA male mortality data, 1990-2020, ages 0-100."""
    return MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )


@pytest.fixture
def spain_data():
    """Load Spain male mortality data, 1990-2020, ages 0-100."""
    return MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="spain",
        sex="Male",
        year_min=1990,
        year_max=2020,
        age_max=100,
    )


# =============================================================================
# Test: Matrix Shape and Dimensions
# =============================================================================


def test_matrix_shape_matches_expected(usa_data):
    """
    THEORY: With age_max=100, we expect ages 0..100 = 101 rows.
    With years 1990..2020 = 31 columns.
    """
    assert usa_data.mx.shape == (101, 31)
    assert usa_data.dx.shape == (101, 31)
    assert usa_data.ex.shape == (101, 31)


def test_shape_property_consistent(usa_data):
    """Shape property should match actual matrix dimensions."""
    assert usa_data.shape == usa_data.mx.shape
    assert usa_data.n_ages == 101
    assert usa_data.n_years == 31


# =============================================================================
# Test: Age and Year Labels
# =============================================================================


def test_ages_array_range(usa_data):
    """Ages should run 0 to age_max (100), consecutively."""
    expected_ages = np.arange(0, 101)
    np.testing.assert_array_equal(usa_data.ages, expected_ages)


def test_years_array_range(usa_data):
    """Years should run from year_min to year_max, consecutively."""
    expected_years = np.arange(1990, 2021)
    np.testing.assert_array_equal(usa_data.years, expected_years)


# =============================================================================
# Test: Data Quality
# =============================================================================


def test_no_nan_in_matrices(usa_data):
    """
    THEORY: NaN would break log transforms in Lee-Carter.
    HMD data for this range should be complete.
    """
    assert not np.any(np.isnan(usa_data.mx)), "mx has NaN values"
    assert not np.any(np.isnan(usa_data.dx)), "dx has NaN values"
    assert not np.any(np.isnan(usa_data.ex)), "ex has NaN values"


def test_all_rates_positive(usa_data):
    """
    THEORY: Lee-Carter takes log(m_x,t), so all rates must be > 0.
    """
    assert np.all(usa_data.mx > 0), "Some death rates are non-positive"


def test_all_exposures_positive(usa_data):
    """Exposures (person-years) must be positive."""
    assert np.all(usa_data.ex > 0), "Some exposures are non-positive"


def test_mx_approximately_equals_dx_over_ex(usa_data):
    """
    THEORY: m_{x,t} = d_{x,t} / L_{x,t} by definition.
    Recomputed rates should match within 1%.
    """
    mx_recomputed = usa_data.dx / usa_data.ex
    relative_error = np.abs(usa_data.mx - mx_recomputed) / (usa_data.mx + 1e-12)
    assert np.max(relative_error) < 0.01


# =============================================================================
# Test: Age Capping
# =============================================================================


def test_age_capping_aggregates_correctly(usa_data):
    """
    THEORY: Ages above age_max are collapsed into age_max group.
    The max age in the array should be exactly age_max.
    """
    assert usa_data.ages[-1] == 100
    assert usa_data.ages[0] == 0


# =============================================================================
# Test: Accessor Methods
# =============================================================================


def test_get_mx_returns_scalar(usa_data):
    """get_mx should return a single float for a given (age, year)."""
    rate = usa_data.get_mx(50, 2000)
    assert isinstance(rate, float)
    assert rate > 0


def test_year_slice_returns_all_ages(usa_data):
    """year_slice should return a vector of length n_ages."""
    col = usa_data.year_slice(2000)
    assert len(col) == usa_data.n_ages
    assert np.all(col > 0)


def test_age_slice_returns_all_years(usa_data):
    """age_slice should return a vector of length n_years."""
    row = usa_data.age_slice(50)
    assert len(row) == usa_data.n_years
    assert np.all(row > 0)


# =============================================================================
# Test: Error Handling
# =============================================================================


def test_invalid_sex_raises_error():
    """Requesting an invalid sex should raise a domain DataQualityError."""
    from backend.engine.exceptions import DataQualityError

    with pytest.raises(DataQualityError, match="sex must be"):
        MortalityData.from_hmd(
            data_dir=DATA_DIR,
            country="usa",
            sex="Unknown",
        )


# =============================================================================
# Test: Spain Data Loads Correctly
# =============================================================================


def test_spain_loads_successfully(spain_data):
    """Spain data should load with same structure as USA."""
    assert spain_data.country == "spain"
    assert spain_data.sex == "Male"
    assert spain_data.n_ages == 101
    assert spain_data.n_years == 31
    assert np.all(spain_data.mx > 0)


def test_summary_returns_dict(usa_data):
    """Summary method should return a well-formed dict."""
    s = usa_data.summary()
    assert s["country"] == "usa"
    assert s["sex"] == "Male"
    assert s["shape"] == (101, 31)
    assert s["any_zeros"] is False


# =============================================================================
# Download date (HMD CC BY 4.0 citation compliance)
# =============================================================================
#
# MortalityData.download_date exists so published work can cite HMD with the
# retrieval date its licence asks for. No caller ever passed one, so it was ""
# on every production object until 2026-08-02. from_hmd() now fills it in.

MOCK_HMD_DIR = str(Path(__file__).parent.parent / "data" / "mock" / "hmd")


def test_download_date_is_recorded_for_hmd_data(usa_data):
    """
    THEORY: HMD's CC BY 4.0 terms ask that the download date be noted alongside
    the citation. An empty string in the field that exists to carry it is a
    compliance gap, not a cosmetic one.

    ci.yml stages the synthetic fixtures at DATA_DIR, and those correctly get no
    download date -- so the expected value depends on what is actually on disk.
    """
    with Path(DATA_DIR, "usa", "Mx_1x1_usa.txt").open(errors="replace") as fh:
        header = "".join(next(fh, "") for _ in range(2)).lower()
    expected = "" if ("synthetic" in header or "mock" in header) else HMD_DOWNLOAD_DATE

    assert usa_data.download_date == expected
    assert usa_data.summary()["download_date"] == expected


def test_explicit_download_date_wins():
    """THEORY: a caller loading a different extract must be able to say so."""
    data = MortalityData.from_hmd(
        data_dir=DATA_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2000,
        age_max=100,
        download_date="1999-01-01",
    )
    assert data.download_date == "1999-01-01"


def test_synthetic_fixtures_get_no_download_date():
    """
    THEORY: the honest answer for a generated file is "no download date" -- it
    was never downloaded from anywhere. Stamping the real retrieval date onto a
    fixture would be a small, quiet lie of exactly the kind this audit was about.
    """
    if not Path(MOCK_HMD_DIR, "usa", "Mx_1x1_usa.txt").exists():
        pytest.skip("no committed mock HMD fixtures")
    data = MortalityData.from_hmd(
        data_dir=MOCK_HMD_DIR,
        country="usa",
        sex="Male",
        year_min=1990,
        year_max=2000,
        age_max=100,
    )
    assert data.download_date == ""


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
