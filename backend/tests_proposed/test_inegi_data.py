"""
INEGI/CONAPO loading (a06.from_inegi) -- m = D/P from separate sources.

INEGI supplies deaths and CONAPO supplies population; the loader merges them
on (year, age) and forms m = D/P. We pin one cell to the raw CSV numbers
(catches a merge misalignment), check the sex filter actually selects, the
year window, and that a bad sex label fails.
"""

import pytest

from backend.engine.a06_mortality_data import MortalityData
from conftest import MOCK_DIR

DEATHS = f"{MOCK_DIR}/mock_inegi_deaths.csv"
POP = f"{MOCK_DIR}/mock_conapo_population.csv"


def _load(sex):
    return MortalityData.from_inegi(
        deaths_filepath=DEATHS, population_filepath=POP,
        sex=sex, year_start=2000, year_end=2010, age_max=100,
    )


def test_mx_equals_deaths_over_population():
    # THEORY: m_{x,t} = D_{x,t} / P_{x,t}. For 2000, Hombres, age 0 the raw
    # CSVs give 20615 deaths / 1312876 population.  Bug caught: a merge that
    # pairs the wrong (year, age) rows would corrupt this ratio.
    data = _load("Hombres")
    assert data.get_mx(0, 2000) == pytest.approx(20615.0 / 1312876.0, rel=1e-9)


def test_sex_filter_selects_column():
    # THEORY: Hombres and Mujeres have different deaths/population, so the
    # resulting rates must differ.
    hombres = _load("Hombres")
    mujeres = _load("Mujeres")
    assert hombres.get_mx(0, 2000) != mujeres.get_mx(0, 2000)


def test_year_window_is_respected():
    # THEORY: only requested years appear. Mock data holds 2000 and 2010.
    data = _load("Total")
    assert set(int(y) for y in data.years) == {2000, 2010}


def test_invalid_sex_raises():
    # THEORY: sex must be one of the Spanish category labels.
    with pytest.raises(ValueError):
        _load("Male")
