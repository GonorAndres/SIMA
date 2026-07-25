"""
Regulatory table loading (a01.from_regulatory_table) -- q_x -> l_x rebuild.

Mexican CNSF/EMSSA tables publish q_x by sex; the loader must rebuild the
survivor column via l_{x+1} = l_x*(1 - q_x). We check the first recurrence
step against the exact CSV value, radix linearity, terminal q, and that the
male/female columns are actually distinguished.
"""

import pytest

from backend.engine.a01_life_table import LifeTable
from conftest import MOCK_DIR

CNSF = f"{MOCK_DIR}/mock_cnsf_2000_i.csv"


def test_lx_rebuilt_from_qx():
    # THEORY: l_0 = radix; l_1 = radix*(1 - q_0). CNSF male q_0 = 0.0155,
    # radix 100000 -> l_1 = 98450.  Bug caught: a loader that skips the
    # (1 - q) recurrence or shifts the q column by one age.
    lt = LifeTable.from_regulatory_table(CNSF, sex="male")
    assert lt.get_l(0) == pytest.approx(100_000.0)
    assert lt.get_q(0) == pytest.approx(0.0155, rel=1e-9)
    assert lt.get_l(1) == pytest.approx(100_000.0 * (1.0 - 0.0155), rel=1e-9)


def test_radix_scales_linearly():
    # THEORY: l_x is homogeneous in the radix; doubling l_0 doubles every l_x.
    a = LifeTable.from_regulatory_table(CNSF, sex="male", radix=100_000.0)
    b = LifeTable.from_regulatory_table(CNSF, sex="male", radix=10_000.0)
    for age in (0, 20, 50, 90):
        assert a.get_l(age) == pytest.approx(10.0 * b.get_l(age), rel=1e-9)


def test_terminal_mortality_is_one():
    # THEORY: the table closes with q = 1 at the top age (CSV has q_100 = 1).
    lt = LifeTable.from_regulatory_table(CNSF, sex="male")
    assert lt.get_q(100) == pytest.approx(1.0)


def test_sex_columns_are_distinguished():
    # THEORY: male and female q_x differ in the source, so the two loaded
    # tables must differ.  Bug caught: always reading the same column.
    male = LifeTable.from_regulatory_table(CNSF, sex="male")
    female = LifeTable.from_regulatory_table(CNSF, sex="female")
    assert male.get_q(0) != female.get_q(0)
