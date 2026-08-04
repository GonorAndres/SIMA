"""
Regulatory Table Tests
======================

Tests for LifeTable.from_regulatory_table() classmethod.

This method loads Mexican regulatory mortality tables (CNSF 2000-I,
CNSF M 2013, EMSSAH-97/EMSSAM-97)
that publish q_x values by sex, and converts them into a full LifeTable
via the recurrence l_{x+1} = l_x * (1 - q_x).

Each test validates a specific actuarial property.
"""

import sys
from itertools import pairwise
from pathlib import Path

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions

# =============================================================================
# Test Data Paths
# =============================================================================

MOCK_DIR = str(Path(__file__).parent.parent / "data" / "mock")


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def cnsf_table():
    """Load mock CNSF 2000-I regulatory table (male)."""
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")
    return LifeTable.from_regulatory_table(filepath, sex="male")


@pytest.fixture
def emssa_table():
    """Load the synthetic sexed regulatory fixture (male).

    This is a CI fixture, not a published table: it exercises the sexed
    two-column code path over ages 0-100. The real EMSSAH-97/EMSSAM-97 covers
    ages 15-110 and is tested separately, further down, against the file at
    backend/data/cnsf/emssah_emssam_97.csv.
    """
    filepath = str(Path(MOCK_DIR) / "mock_emssa_97.csv")
    return LifeTable.from_regulatory_table(filepath, sex="male")


# =============================================================================
# Test: Loading CNSF Table
# =============================================================================


def test_from_regulatory_loads_cnsf(cnsf_table):
    """
    THEORY: A regulatory table in CNSF format (age, qx_male, qx_female)
    should be loadable as a LifeTable.

    The CNSF publishes official mortality tables that insurers must use
    for minimum reserve calculations. The table should span ages 0-100.
    """
    assert cnsf_table.min_age == 0
    assert cnsf_table.max_age == 100
    assert cnsf_table.get_l(0) == 100_000.0


# =============================================================================
# Test: Loading EMSSA Table
# =============================================================================


def test_from_regulatory_loads_emssa(emssa_table):
    """
    THEORY: a second sexed table in the same format must load identically --
    the loader keys off the column names, not off which table it is.

    This asserts the CI fixture's own shape (ages 0-100). Do not read it as a
    statement about the published EMSSAH-97/EMSSAM-97, which starts at 15.
    """
    assert emssa_table.min_age == 0
    assert emssa_table.max_age == 100
    assert emssa_table.get_l(0) == 100_000.0


# =============================================================================
# Test: l_x Recurrence from q_x
# =============================================================================


def test_from_regulatory_correct_lx(cnsf_table):
    """
    THEORY: l_{x+1} = l_x * (1 - q_x)

    When building l_x from q_x, each cohort of survivors is reduced by
    the mortality rate at that age. This is the fundamental recurrence
    that connects the probability column (q_x) to the count column (l_x).

    We verify this at several ages to ensure the conversion is correct.
    """
    for age in [0, 10, 25, 50, 75, 99]:
        l_x = cnsf_table.get_l(age)
        l_x1 = cnsf_table.get_l(age + 1)
        q_x = cnsf_table.get_q(age)
        expected = l_x * (1.0 - q_x)
        assert l_x1 == pytest.approx(expected, rel=1e-9), (
            f"l_{age + 1} should equal l_{age} * (1 - q_{age})"
        )


# =============================================================================
# Test: Radix
# =============================================================================


def test_from_regulatory_radix():
    """
    THEORY: The radix l_0 is the initial cohort size.

    By convention, Mexican regulatory tables use l_0 = 100,000.
    The radix scales all absolute counts but does not affect derived
    rates (q_x, p_x), since those are ratios.

    The from_regulatory_table() method should respect a custom radix.
    """
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")

    # Default radix
    lt_default = LifeTable.from_regulatory_table(filepath, sex="male")
    assert lt_default.get_l(0) == 100_000.0

    # Custom radix
    lt_custom = LifeTable.from_regulatory_table(filepath, sex="male", radix=10_000.0)
    assert lt_custom.get_l(0) == 10_000.0

    # q_x should be the same regardless of radix
    assert lt_default.get_q(50) == pytest.approx(lt_custom.get_q(50), rel=1e-9)


# =============================================================================
# Test: Terminal q_x
# =============================================================================


def test_from_regulatory_terminal_qx(cnsf_table):
    """
    THEORY: q_omega = 1.0 (everyone dies at the terminal age)

    This is an actuarial convention: at the last age in the table,
    mortality is certain. The mock data has q_100 = 1.0 for both sexes,
    which means l_101 would be 0. The LifeTable sets q_omega = 1.0
    at construction time.
    """
    assert cnsf_table.get_q(cnsf_table.max_age) == 1.0


# =============================================================================
# Test: Monotonic l_x
# =============================================================================


def test_from_regulatory_monotonic_lx(cnsf_table):
    """
    THEORY: l_x must be strictly decreasing.

    Since q_x > 0 for all ages (people always have some probability of
    dying), each successive l_x must be strictly smaller than the previous.
    This is a basic sanity check for any valid life table.
    """
    ages = cnsf_table.ages
    for i in range(len(ages) - 1):
        l_current = cnsf_table.get_l(ages[i])
        l_next = cnsf_table.get_l(ages[i + 1])
        assert l_next < l_current, (
            f"l_{ages[i + 1]} = {l_next} should be less than l_{ages[i]} = {l_current}"
        )


# =============================================================================
# Test: Sex Selection
# =============================================================================


def test_from_regulatory_sex_selection():
    """
    THEORY: Male and female mortality tables differ.

    Male mortality is typically higher than female mortality at most ages.
    The from_regulatory_table() method must correctly select the q_x
    column based on the sex parameter, producing different l_x (and
    therefore different q_x) for each sex.
    """
    filepath = str(Path(MOCK_DIR) / "mock_cnsf_2000_i.csv")

    lt_male = LifeTable.from_regulatory_table(filepath, sex="male")
    lt_female = LifeTable.from_regulatory_table(filepath, sex="female")

    # q_x should differ between sexes (mock data has different values)
    assert lt_male.get_q(0) != lt_female.get_q(0)

    # Male q_x at age 0 is higher than female (0.0155 vs 0.0128 in mock)
    assert lt_male.get_q(0) > lt_female.get_q(0)

    # l_x at later ages should differ due to accumulated mortality
    assert lt_male.get_l(50) != lt_female.get_l(50)


# =============================================================================
# Test: Integration with Commutation Functions
# =============================================================================


def test_from_regulatory_feeds_commutation(cnsf_table):
    """
    THEORY: A LifeTable from a regulatory table should be usable as input
    to CommutationFunctions without any conversion.

    This tests the integration between the regulatory loader and the
    actuarial engine: CommutationFunctions(life_table, interest_rate)
    should compute D_x, N_x, C_x, M_x without errors.
    """
    comm = CommutationFunctions(cnsf_table, interest_rate=0.05)

    # D_0 = v^0 * l_0 = 1 * 100000 = 100000
    assert comm.get_D(0) == pytest.approx(100_000.0)

    # N_0 should be the sum of all D_x, which is positive
    assert comm.get_N(0) > 0

    # M_0 should be positive (mortality cost)
    assert comm.get_M(0) > 0


# =============================================================================
# Test: Invalid File
# =============================================================================


def test_from_regulatory_invalid_file():
    """
    THEORY: Attempting to load a non-existent file should raise
    FileNotFoundError, consistent with the existing from_csv() behavior.
    """
    with pytest.raises(FileNotFoundError):
        LifeTable.from_regulatory_table("/nonexistent/path.csv")


# =============================================================================
# Test: The published CNSF M 2013 table (CUSF Anexo 5.3.3-a)
# =============================================================================
#
# Until 2026-08-02 backend/data/cnsf/cnsf_2013.csv carried qx_male and qx_female
# columns whose arithmetic mean reproduced the official value to 6 decimal
# places at all 111 ages -- someone had taken the real unisex table and split it
# with an invented ratio. The split ran from 0.638 to 5.138 and at some ages
# made female mortality higher than male. Male q_65 read 0.010039 against the
# published 0.006119: +64%.
#
# The official table is "CNSFM 2013 - Experiencia demografica de mortalidad
# MIXTA (hombres y mujeres)". One q_x column, ages 0-110, no sex split.

CNSF_DIR = Path(__file__).parent.parent / "data" / "cnsf"
CNSF_2013_FILE = CNSF_DIR / "cnsf_2013.csv"
EMSSA_97_FILE = CNSF_DIR / "emssah_emssam_97.csv"

# Spot values read from the annex, ages chosen across the range.
CNSF_2013_PUBLISHED = {
    0: 0.000433,
    20: 0.000517,
    40: 0.001033,
    65: 0.006119,
    80: 0.030257,
    100: 0.353919,
    110: 0.758991,
}


@pytest.fixture
def cnsf_2013_rows():
    """Raw rows of the CNSF M 2013 file."""
    import csv

    with CNSF_2013_FILE.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_cnsf_2013_matches_the_published_values(cnsf_2013_rows):
    """
    THEORY: a regulatory table is a legal instrument, not a modelling choice.
    The values an insurer reserves on are the values the regulator published;
    reproducing them is a transcription obligation, not an approximation.
    """
    by_age = {int(r["age"]): float(r["qx_unisex"]) for r in cnsf_2013_rows}
    assert min(by_age) == 0 and max(by_age) == 110
    assert len(by_age) == 111
    for age, expected in CNSF_2013_PUBLISHED.items():
        assert by_age[age] == pytest.approx(expected, abs=5e-7), f"age {age}"


def test_cnsf_2013_is_unisex(cnsf_2013_rows):
    """
    THEORY: CNSF M 2013 is a table MIXTA -- one q_x for hombres y mujeres. The
    per-sex columns exist only so the loader's `qx_{sex}` lookup keeps working;
    they must repeat the published column verbatim, never a derived split.
    """
    for row in cnsf_2013_rows:
        assert row["qx_male"] == row["qx_unisex"] == row["qx_female"], row["age"]


def test_cnsf_2013_carries_the_995th_percentile_stress(cnsf_2013_rows):
    """
    THEORY: the same annex publishes CNSF M 2013 at the 99.5th percentile. That
    is a CUSF-prescribed calibration of mortality stress -- the regulator's own
    1-in-200 table -- and it is a far better basis for the SCR mortality module
    than a generic Solvency II shock. Kept in the file for that later use.

    The published stress runs at about 1.51x the central rate up to age 80 and
    tapers towards 1.10 at 110, because at extreme ages q_x cannot be scaled
    without exceeding 1.
    """
    ratios = {int(r["age"]): float(r["qx_p995"]) / float(r["qx_unisex"]) for r in cnsf_2013_rows}
    assert all(v > 1.0 for v in ratios.values())
    for age in (0, 40, 80):
        assert ratios[age] == pytest.approx(1.51, abs=0.02), f"age {age}"
    assert ratios[110] == pytest.approx(1.10, abs=0.02)

    # The shape is "flat, then taper" -- NOT monotone decreasing, which an
    # earlier docstring here claimed while asserting only ordered[-1] < ordered[0].
    # Measured: from age 0 to 80 the ratio stays inside [1.5000, 1.5121] -- a
    # band 0.012 wide around 1.506, with 32 of the 110 single-age steps ticking
    # UP because the published table is rounded. Only past 80 does it fall away,
    # because there q_x cannot be scaled by 1.5 without exceeding 1.
    flat = [ratios[a] for a in range(0, 81)]
    assert max(flat) - min(flat) < 0.015, (min(flat), max(flat))
    assert min(flat) >= 1.50 and max(flat) <= 1.52, (min(flat), max(flat))

    taper = [ratios[a] for a in range(80, 111)]
    assert all(b < a for a, b in pairwise(taper)), taper


def test_cnsf_2013_loads_as_a_life_table():
    """
    THEORY: the unisex column is the one to read. sex="unisex" is already
    special-cased by from_regulatory_table(), which suppresses the
    "identical qx columns" warning precisely for a table like this one.
    """
    lt = LifeTable.from_regulatory_table(str(CNSF_2013_FILE), sex="unisex")
    assert lt.min_age == 0
    assert lt.max_age == 110
    assert lt.get_l(0) == 100_000.0
    assert lt.get_q(65) == pytest.approx(CNSF_2013_PUBLISHED[65], abs=5e-7)


def test_cnsf_2013_warns_when_loaded_as_a_sexed_table():
    """
    THEORY: asking a unisex table for male mortality should say so out loud.
    The values returned are correct -- they are the published ones -- but the
    caller is not getting sex-differentiated mortality, and pricing that
    depends on the difference needs to know.
    """
    with pytest.warns(UserWarning, match="identical qx_male and qx_female"):
        lt = LifeTable.from_regulatory_table(str(CNSF_2013_FILE), sex="male")
    assert lt.get_q(65) == pytest.approx(CNSF_2013_PUBLISHED[65], abs=5e-7)


# =============================================================================
# Test: EMSSAH-97 / EMSSAM-97 (CUSF Anexo 14.2.4-a)
# =============================================================================
#
# There is no "EMSSA 2009" in the CUSF annex index. The file that used to sit at
# backend/data/cnsf/emssa_2009.csv disagreed with the real annex at effectively
# every age -- two coincidental matches in 96 (age 31, and the trivial q = 1.0 at
# age 110), ratios swinging from 0.159x to 2.733x, and it invented ages 0-14
# that the published table does not cover.


def test_emssa_97_is_sex_differentiated_and_starts_at_15():
    """
    THEORY: EMSSAH-97 (hombres) and EMSSAM-97 (mujeres) are two separate
    published tables covering ages 15-110 -- they price working-life and
    pension obligations under social security, so childhood ages are out of
    scope by design. A table claiming ages 0-14 is not this table.
    """
    male = LifeTable.from_regulatory_table(str(EMSSA_97_FILE), sex="male")
    female = LifeTable.from_regulatory_table(str(EMSSA_97_FILE), sex="female")

    assert male.min_age == 15
    assert male.max_age == 110
    assert male.get_q(30) != female.get_q(30)
    # Male mortality exceeds female across the working ages.
    assert all(male.get_q(a) > female.get_q(a) for a in range(20, 60))


def test_no_file_claims_to_be_emssa_2009():
    """
    THEORY: a filename is an assertion about provenance. Nothing named
    "EMSSA 2009" should reappear under backend/data/cnsf/, because the CUSF
    annex index contains no such table.
    """
    stale = sorted(p.name for p in CNSF_DIR.glob("*emssa*2009*"))
    assert not stale, f"fabricated table name is back: {stale}"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
