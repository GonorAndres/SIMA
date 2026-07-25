"""
Commutation functions (a02) -- analytic tests.

Under a constant force the discounted-survivor column is geometric, so D,
N, C, M all have closed forms. We check the ratio structure, the exact
cross-column identity linking C to D, the geometric sum for N, and the
interest-rate guards.
"""

import pytest

from backend.engine.a02_commutation import CommutationFunctions
from conftest import P, V, BETA, OMEGA


@pytest.mark.parametrize("x", [10, 40, 80, 120])
def test_D_ratio_is_geometric(comm, x):
    # THEORY: D_{x+1}/D_x = v*p = beta under constant force.
    # Bug caught: a wrong discount exponent (v^x vs v^{x+1}) breaks the ratio.
    assert comm.get_D(x + 1) / comm.get_D(x) == pytest.approx(BETA, rel=1e-12)


@pytest.mark.parametrize("x", [0, 30, 75, 129])
def test_C_equals_v_Dx_minus_Dx1(comm, x):
    # THEORY: C_x = v^{x+1}*d_x and d_x = l_x - l_{x+1}, hence exactly
    #         C_x = v*D_x - D_{x+1}.  Binds the C exponent to the D exponent.
    # Bug caught: an off-by-one in the C discounting (deaths paid mid-year
    # vs end-of-year) violates this identity.
    expected = V * comm.get_D(x) - comm.get_D(x + 1)
    assert comm.get_C(x) == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize("x", [5, 50, 100])
def test_N_and_M_backward_sums(comm, x):
    # THEORY: N_x - N_{x+1} = D_x and M_x - M_{x+1} = C_x (definition of the
    # backward recursion).  Bug caught: an indexing slip in the recursion.
    assert comm.get_N(x) - comm.get_N(x + 1) == pytest.approx(comm.get_D(x), rel=1e-12)
    assert comm.get_M(x) - comm.get_M(x + 1) == pytest.approx(comm.get_C(x), rel=1e-12)


@pytest.mark.parametrize("x", [20, 60, 110])
def test_N_matches_geometric_closed_form(comm, x):
    # THEORY: with D_y = D_x * beta^{y-x}, the finite sum gives
    #         N_x = D_x * (1 - beta^{N+1})/(1 - beta),  N = OMEGA - x.
    # This is derived WITHOUT the recursion, so it independently validates
    # both the D exponents and the N accumulation.
    n = OMEGA - x
    expected = comm.get_D(x) * (1.0 - BETA ** (n + 1)) / (1.0 - BETA)
    assert comm.get_N(x) == pytest.approx(expected, rel=1e-9)


def test_interest_rate_guards(constant_force_lt):
    # THEORY: an invalid interest rate must raise, never silently proceed.
    with pytest.raises(ValueError):
        CommutationFunctions(constant_force_lt, interest_rate=-0.01)
    with pytest.raises(ValueError):
        CommutationFunctions(constant_force_lt, interest_rate=5)   # not a decimal
    with pytest.raises(TypeError):
        CommutationFunctions(constant_force_lt, interest_rate="5%")
