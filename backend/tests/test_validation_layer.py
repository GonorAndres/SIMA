"""
Validation Layer & Edge-Case Tests
====================================

Phase 1 tests for the actuarial validation layer (`exceptions`, `validators`)
and hardened engine modules (`a01`-`a05`). Covers:

- Structured `ActuarialValidationError` fields.
- All domain validators reject invalid inputs cleanly.
- `a01` LifeTable: non-consecutive ages, non-monotone l_x, out-of-range
  lookups raise `ActuarialValidationError` (not bare `KeyError`).
- `a02` Commutation: `i == 0` undiscounted path, rate > 1 warns, structured
  age errors.
- `a04` Premiums: `single_premium` for every product, relative equivalence
  tolerance.
- `a05` Reserves: expired-term returns 0 with warning, pure_endowment included
  in `validate_zero_reserve`, relative zero tolerance.

Golden edge cases: i=0, terminal age omega, expired term, single premium.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator
from backend.engine.exceptions import (
    ActuarialComputationError,
    ActuarialValidationError,
)
from backend.engine.validators import (
    validate_age_in_table,
    validate_consecutive_ages,
    validate_interest_rate,
    validate_lx_monotonic,
    validate_non_negative_amount,
    validate_positive_amount,
    validate_probabilities,
    validate_term_bounds,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mini_table():
    return LifeTable.from_csv(str(Path(__file__).parent.parent / "data" / "mini_table.csv"))


@pytest.fixture
def zero_comm(mini_table):
    """Commutation functions at i=0 (undiscounted)."""
    return CommutationFunctions(mini_table, interest_rate=0.0)


@pytest.fixture
def pc(comm):
    return PremiumCalculator(comm)


@pytest.fixture
def comm(mini_table):
    return CommutationFunctions(mini_table, interest_rate=0.05)


@pytest.fixture
def rc(comm):
    return ReserveCalculator(comm)


# =============================================================================
# exceptions.py
# =============================================================================


class TestActuarialValidationError:
    def test_carries_structured_fields(self):
        err = ActuarialValidationError("bad input", field="sum_assured", constraint="SA > 0")
        assert err.field == "sum_assured"
        assert err.constraint == "SA > 0"
        assert err.message == "bad input"
        d = err.to_dict()
        assert d["error"] == "ActuarialValidationError"
        assert d["field"] == "sum_assured"
        assert "bad input" in str(err)

    def test_optional_fields_default_none(self):
        err = ActuarialValidationError("oops")
        assert err.field is None
        assert err.constraint is None
        assert err.to_dict()["field"] is None


# =============================================================================
# validators.py
# =============================================================================


class TestValidators:
    def test_consecutive_ages_rejects_gap(self):
        with pytest.raises(ActuarialValidationError, match="consecutive"):
            validate_consecutive_ages([60, 61, 63])

    def test_consecutive_ages_rejects_too_short(self):
        with pytest.raises(ActuarialValidationError, match="at least 2"):
            validate_consecutive_ages([60])

    def test_consecutive_ages_accepts_valid(self):
        validate_consecutive_ages([60, 61, 62])  # no raise

    def test_lx_monotonic_rejects_negative(self):
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            validate_lx_monotonic([100, -5, 0])

    def test_lx_monotonic_rejects_increase(self):
        with pytest.raises(ActuarialValidationError, match="non-increasing"):
            validate_lx_monotonic([100, 200], ages=[60, 61])

    def test_lx_monotonic_tolerates_float_noise(self):
        # tiny relative increase within MONO_REL_TOL is allowed
        validate_lx_monotonic([1000.0, 1000.0 + 1e-13], ages=[60, 61])

    def test_probabilities_rejects_out_of_range(self):
        with pytest.raises(ActuarialValidationError, match="out of \\[0,1\\]"):
            validate_probabilities([0.1, 1.5, 0.2])

    def test_probabilities_rejects_negative(self):
        with pytest.raises(ActuarialValidationError, match="out of \\[0,1\\]"):
            validate_probabilities([-0.01])

    def test_age_in_table_rejects_out_of_bounds(self):
        with pytest.raises(ActuarialValidationError, match="outside the life table range"):
            validate_age_in_table(99, 60, 65)

    def test_term_bounds_rejects_duration_exceeding_term(self):
        with pytest.raises(ActuarialValidationError, match="exceeds term"):
            validate_term_bounds(n=3, t=4, product_type="term")

    def test_term_bounds_requires_n_for_finite_products(self):
        with pytest.raises(ActuarialValidationError, match="n is required"):
            validate_term_bounds(n=None, t=0, product_type="endowment")

    def test_term_bounds_allows_t_equals_n(self):
        validate_term_bounds(n=3, t=3, product_type="term")  # expired boundary

    def test_term_bounds_rejects_unknown_product(self):
        with pytest.raises(ActuarialValidationError, match="Unknown product type"):
            validate_term_bounds(n=3, t=0, product_type="variable_life")

    def test_non_negative_amount_rejects_negative(self):
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            validate_non_negative_amount(-1.0, "sum_assured")

    def test_non_negative_amount_rejects_nan(self):
        with pytest.raises(ActuarialValidationError, match="finite"):
            validate_non_negative_amount(float("nan"), "sum_assured")

    def test_positive_amount_requires_strict_positive(self):
        with pytest.raises(ActuarialValidationError, match="strictly positive"):
            validate_positive_amount(0.0, "annual_pension")

    def test_positive_amount_non_strict_allows_zero(self):
        validate_positive_amount(0.0, "x", strict=False)

    def test_interest_rate_rejects_negative(self):
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            validate_interest_rate(-0.01)

    def test_interest_rate_rejects_percent_misplacement_when_strict(self):
        with pytest.raises(ActuarialValidationError, match="percentage"):
            validate_interest_rate(5.0, allow_above_one=False)

    def test_interest_rate_allows_zero(self):
        validate_interest_rate(0.0)

    def test_interest_rate_rejects_absurd(self):
        with pytest.raises(ActuarialValidationError, match="sanity ceiling"):
            validate_interest_rate(50.0)


# =============================================================================
# a01 LifeTable hardening
# =============================================================================


class TestLifeTableValidation:
    def test_non_consecutive_ages_raise(self):
        with pytest.raises(ActuarialValidationError, match="consecutive"):
            LifeTable([60, 61, 63], [1000, 900, 800])

    def test_non_monotone_lx_raise(self):
        with pytest.raises(ActuarialValidationError, match="non-increasing"):
            LifeTable([60, 61, 62], [1000, 900, 950])

    def test_negative_lx_raise(self):
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            LifeTable([60, 61, 62], [1000, 900, -5])

    def test_length_mismatch_raises(self):
        with pytest.raises(ActuarialValidationError, match="same length"):
            LifeTable([60, 61, 62], [1000, 900])

    def test_get_q_out_of_range_is_actuarial_error(self):
        lt = LifeTable([60, 61, 62], [1000, 900, 800])
        with pytest.raises(ActuarialValidationError, match="outside the life table range"):
            lt.get_q(99)

    def test_get_l_out_of_range_is_actuarial_error(self):
        lt = LifeTable([60, 61, 62], [1000, 900, 800])
        with pytest.raises(ActuarialValidationError):
            lt.get_l(30)

    def test_validate_uses_relative_tolerance(self):
        lt = LifeTable([60, 61, 62], [100_000, 90_000, 80_000])
        v = lt.validate()
        assert v["sum_deaths_equals_l0"] is True
        assert v["terminal_mortality_is_one"] is True
        assert v["all_rates_valid"] is True

    def test_subset_rejects_inverted_range(self):
        lt = LifeTable([60, 61, 62], [1000, 900, 800])
        with pytest.raises(ActuarialValidationError, match="out of bounds"):
            lt.subset(62, 60)

    def test_from_regulatory_table_string_identical_columns_warns(self, tmp_path):
        # both qx columns byte-identical -> warning about sex differentiation
        p = tmp_path / "reg.csv"
        p.write_text("age,qx_male,qx_female\n60,0.01,0.01\n61,0.02,0.02\n62,0.5,0.5\n")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            LifeTable.from_regulatory_table(str(p), sex="male")
        assert any("identical qx_male and qx_female" in str(x.message) for x in w)


# =============================================================================
# a02 CommutationFunctions hardening
# =============================================================================


class TestCommutationValidation:
    def test_rate_above_one_warns(self, mini_table):
        with pytest.warns(UserWarning, match="Interest rate"):
            CommutationFunctions(mini_table, interest_rate=1.5)

    def test_negative_rate_rejected(self, mini_table):
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            CommutationFunctions(mini_table, interest_rate=-0.01)

    def test_get_D_out_of_range_is_actuarial_error(self, comm):
        with pytest.raises(ActuarialValidationError, match="D_x not available"):
            comm.get_D(99)

    def test_get_M_out_of_range_is_actuarial_error(self, comm):
        with pytest.raises(ActuarialValidationError, match="M_x not available"):
            comm.get_M(30)


class TestZeroInterest:
    """Golden edge case: i = 0 -> undiscounted sums."""

    def test_D_x_equals_l_x_at_zero_interest(self, zero_comm):
        # D_x = v^(x-min) * l_x = 1 * l_x = l_x
        for age in zero_comm.life_table.ages:
            assert zero_comm.D[age] == pytest.approx(zero_comm.life_table.get_l(age))

    def test_v_is_exactly_one(self, zero_comm):
        assert zero_comm.v == 1.0

    def test_N_omega_equals_D_omega(self, zero_comm):
        omega = zero_comm.life_table.omega
        assert zero_comm.N[omega] == pytest.approx(zero_comm.D[omega])

    def test_zero_interest_equivalence_still_holds(self, zero_comm):
        pc = PremiumCalculator(zero_comm)
        sa, x = 100_000.0, 60
        result = pc.verify_equivalence(sa, x)
        assert result["balanced"] is True


# =============================================================================
# Terminal age (omega) edge case
# =============================================================================


class TestTerminalAge:
    def test_A_x_at_omega_is_one(self, comm):
        av = ActuarialValues(comm)
        omega = comm.max_age
        # At omega, only death is certain and payable at end of year, so
        # A_omega = v (pure discount). With normalization D_omega=l_omega,
        # M_omega = C_omega = v^(omega+1-min)*l_omega, so A_omega = v.
        assert av.A_x(omega) == pytest.approx(comm.v, rel=1e-9)

    def test_a_due_at_omega_is_one(self, comm):
        av = ActuarialValues(comm)
        omega = comm.max_age
        # one certain payment due now
        assert av.a_due(omega) == pytest.approx(1.0)

    def test_reserve_whole_life_at_beyond_omega_is_SA(self, comm):
        rc = ReserveCalculator(comm)
        sa, x = 50_000.0, 60
        beyond = comm.max_age - x + 5
        assert rc.reserve_whole_life(sa, x, beyond) == sa


# =============================================================================
# Expired term policy edge case
# =============================================================================


class TestExpiredTerm:
    def test_reserve_term_expired_returns_zero_with_warning(self, rc):
        sa, x, n = 100_000.0, 60, 3
        with pytest.warns(UserWarning, match="expired"):
            after = rc.reserve_term(sa, x, n, t=n + 1)
        assert after == 0.0

    def test_reserve_term_at_expiry_returns_zero(self, rc):
        sa, x, n = 100_000.0, 60, 3
        assert rc.reserve_term(sa, x, n, t=n) == 0.0


# =============================================================================
# Single-premium equivalence & all-product coverage
# =============================================================================


class TestSinglePremium:
    def test_whole_life_single_premium_equals_sa_times_Ax(self, comm):
        av = ActuarialValues(comm)
        pc = PremiumCalculator(comm)
        sa, x = 100_000.0, 60
        assert pc.single_premium(sa, x, "whole_life") == pytest.approx(sa * av.A_x(x))

    def test_term_single_premium_equals_sa_times_Aterm(self, comm):
        av = ActuarialValues(comm)
        pc = PremiumCalculator(comm)
        sa, x, n = 100_000.0, 60, 3
        assert pc.single_premium(sa, x, "term", n) == pytest.approx(sa * av.A_term(x, n))

    def test_endowment_single_premium(self, comm):
        av = ActuarialValues(comm)
        pc = PremiumCalculator(comm)
        sa, x, n = 100_000.0, 60, 3
        assert pc.single_premium(sa, x, "endowment", n) == pytest.approx(sa * av.A_endowment(x, n))

    def test_pure_endowment_single_premium(self, comm):
        av = ActuarialValues(comm)
        pc = PremiumCalculator(comm)
        sa, x, n = 100_000.0, 60, 3
        assert pc.single_premium(sa, x, "pure_endowment", n) == pytest.approx(sa * av.nE_x(x, n))

    def test_single_premium_rejects_missing_n(self, comm):
        pc = PremiumCalculator(comm)
        with pytest.raises(ActuarialComputationError, match="requires n"):
            pc.single_premium(100_000.0, 60, "term")

    def test_single_premium_rejects_unknown_product(self, comm):
        pc = PremiumCalculator(comm)
        with pytest.raises(ActuarialComputationError, match="Unknown product"):
            pc.single_premium(100_000.0, 60, "variable_life", 3)

    def test_single_premium_rejects_negative_sa(self, comm):
        pc = PremiumCalculator(comm)
        with pytest.raises(ActuarialValidationError, match="cannot be negative"):
            pc.single_premium(-1.0, 60, "whole_life")


# =============================================================================
# Reserve validation helpers
# =============================================================================


class TestReserveValidation:
    def test_validate_zero_reserve_includes_pure_endowment(self, comm):
        rc = ReserveCalculator(comm)
        sa, x, n = 100_000.0, 60, 3
        out = rc.validate_zero_reserve(sa, x, product="pure_endowment", n=n)
        assert out["is_zero"] is True
        assert out["product"] == "pure_endowment"

    def test_validate_zero_reserve_relative_tolerance(self, comm):
        rc = ReserveCalculator(comm)
        # very large SA -> fixed $0.01 tolerance would be wrong; relative is used
        out = rc.validate_zero_reserve(1e12, 60, product="whole_life")
        assert out["is_zero"] is True
        assert out["tolerance"] > 0.01

    def test_reserve_trajectory_rejects_missing_n(self, comm):
        rc = ReserveCalculator(comm)
        with pytest.raises(ActuarialValidationError, match="n is required"):
            rc.reserve_trajectory(100_000.0, 60, product="term", n=None)

    def test_reserve_term_rejects_negative_duration(self, comm):
        rc = ReserveCalculator(comm)
        with pytest.raises(ActuarialValidationError, match=r"cannot be negative|non-negative"):
            rc.reserve_term(100_000.0, 60, 3, t=-1)
