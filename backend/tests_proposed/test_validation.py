"""
Mortality comparison (a10) -- controlled ratio / RMSE checks.

We build projected and regulatory tables with a KNOWN relationship between
their q_x columns, so the comparison metrics have exact expected values:
identical tables give ratio 1 and RMSE 0; a proportional table gives a flat
ratio; a constant additive gap gives RMSE equal to that gap.
"""

import numpy as np
import pytest

from backend.engine.a01_life_table import LifeTable
from backend.engine.a10_validation import MortalityComparison


def _lt_constant_q(qval, min_age=20, max_age=90, radix=100_000.0):
    ages = list(range(min_age, max_age + 1))
    lx = [radix]
    for _ in ages[:-1]:
        lx.append(lx[-1] * (1.0 - qval))
    return LifeTable(ages, lx)


def test_identical_tables_are_perfect_match():
    # THEORY: comparing a table with itself -> ratio 1 everywhere, RMSE 0,
    # differences 0.  Bug caught: a swapped numerator/denominator or a stray
    # offset would perturb these trivial values.
    lt = _lt_constant_q(0.02)
    cmp = MortalityComparison(lt, lt, name="self")
    assert np.allclose(cmp.qx_ratio(), 1.0)
    assert cmp.rmse() == pytest.approx(0.0)
    assert np.allclose(cmp.qx_difference(), 0.0)


def test_proportional_projection_gives_flat_ratio():
    # THEORY: if projected q = 1.2 * regulatory q at every age, the ratio is
    # a flat 1.2.  Bug caught: ratio computed as reg/proj (inverted) would
    # give ~0.833 instead.
    reg = _lt_constant_q(0.01)
    proj = _lt_constant_q(0.012)   # 1.2x
    cmp = MortalityComparison(proj, reg)
    assert np.allclose(cmp.qx_ratio(), 1.2, rtol=1e-9)


def test_rmse_equals_constant_gap():
    # THEORY: a constant additive gap delta between the two q_x columns gives
    # RMSE = |delta| over the (non-terminal) age window.
    delta = 0.003
    reg = _lt_constant_q(0.01, min_age=20, max_age=90)
    proj = _lt_constant_q(0.01 + delta, min_age=20, max_age=90)
    cmp = MortalityComparison(proj, reg)
    assert cmp.rmse(age_start=20, age_end=80) == pytest.approx(delta, rel=1e-9)


def test_insufficient_overlap_raises():
    # THEORY: a comparison needs >= 2 shared ages to be meaningful.
    reg = _lt_constant_q(0.01, min_age=20, max_age=30)
    proj = _lt_constant_q(0.01, min_age=30, max_age=40)   # overlap = {30}
    with pytest.raises(ValueError):
        MortalityComparison(proj, reg)
