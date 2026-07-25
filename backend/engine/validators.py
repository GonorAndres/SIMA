"""
Actuarial Validators - Domain Validation Layer
==============================================

Reusable, pure validation functions for actuarial inputs. Each validator
either returns ``None`` (success) or raises
:class:`~backend.engine.exceptions.ActuarialValidationError` with a
structured ``field`` / ``constraint`` so callers can surface clean errors.

Rationale (per LISF/CUSF):
--------------------------
Actuarial computations are only meaningful when their inputs satisfy
domain invariants (consecutive ages, monotone survivors, probabilities in
``[0, 1]``, term bounds). Validating once at the boundary -- rather than
letting a ``KeyError`` surface mid-computation -- produces auditable,
regulator-friendly errors.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

from .exceptions import ActuarialValidationError


# ---------------------------------------------------------------------------
# Numeric tolerances
# ---------------------------------------------------------------------------
# Probabilities are compared with this tolerance to absorb float rounding
# from regulatory-table recurrences (l_{x+1} = l_x * (1 - q_x)).
PROB_TOL = 1e-9
# Relative tolerance for "monotone non-increasing" survivor counts. Because
# l_x is rebuilt via multiplicative recurrence, we allow a tiny relative slip
# rather than insisting on strict float ordering.
MONO_REL_TOL = 1e-9


# ---------------------------------------------------------------------------
# Age / life-table validators
# ---------------------------------------------------------------------------
def validate_consecutive_ages(ages: Sequence[int]) -> None:
    """
    Ensure ``ages`` are strictly increasing by exactly 1 (consecutive).

    A life table requires ages ``x, x+1, x+2, ...`` because the d_x, q_x
    recurrences assume ``l_{x+1}`` exists for every non-terminal age.
    """
    if len(ages) < 2:
        raise ActuarialValidationError(
            "Life table requires at least 2 ages",
            field="ages",
            constraint="len(ages) >= 2",
        )
    for i in range(1, len(ages)):
        if ages[i] != ages[i - 1] + 1:
            raise ActuarialValidationError(
                f"Ages must be consecutive integers; gap between "
                f"{ages[i - 1]} and {ages[i]} at index {i}",
                field="ages",
                constraint="ages[i] == ages[i-1] + 1 for all i",
            )


def validate_lx_monotonic(l_x: Sequence[float], ages: Optional[Sequence[int]] = None) -> None:
    """
    Ensure survivor counts ``l_x`` are non-negative and (weakly) monotone
    non-increasing.

    Survivors cannot increase with age and can never be negative. A tiny
    relative increase is tolerated to absorb float recurrence noise.
    """
    if len(l_x) == 0:
        raise ActuarialValidationError(
            "Survivor counts (l_x) must not be empty",
            field="l_x",
            constraint="len(l_x) > 0",
        )
    for v in l_x:
        if v < 0:
            raise ActuarialValidationError(
                f"Survivor count l_x cannot be negative (got {v})",
                field="l_x",
                constraint="l_x[i] >= 0 for all i",
            )
    for i in range(1, len(l_x)):
        prev, curr = float(l_x[i - 1]), float(l_x[i])
        # allow tiny relative increase from float recurrence
        denom = max(abs(prev), 1.0)
        if curr > prev and (curr - prev) / denom > MONO_REL_TOL:
            where = f"ages {ages[i-1]}->{ages[i]}" if ages is not None else f"index {i-1}->{i}"
            raise ActuarialValidationError(
                f"Survivor counts must be non-increasing; l_x increased at {where} "
                f"({prev} -> {curr})",
                field="l_x",
                constraint="l_x[i] <= l_x[i-1] (weakly monotone non-increasing)",
            )


def validate_probabilities(q_x: Iterable[float]) -> None:
    """
    Ensure every mortality/transition probability lies in ``[0, 1]``.

    A probability outside the unit interval is not a probability and would
    break every downstream recurrence (l_x, commutation functions, reserves).
    """
    for i, q in enumerate(q_x):
        if q < -PROB_TOL or q > 1.0 + PROB_TOL:
            raise ActuarialValidationError(
                f"Probability out of [0,1] at index {i}: q={q}",
                field="q_x",
                constraint="0 <= q_x[i] <= 1 for all i",
            )


def validate_age_in_table(age: int, min_age: int, max_age: int) -> None:
    """
    Ensure ``age`` is within the life-table range ``[min_age, max_age]``.

    Looking up mortality outside the table is an actuarial error (we have no
    data there), not an indexing accident.
    """
    if age < min_age or age > max_age:
        raise ActuarialValidationError(
            f"Age {age} is outside the life table range [{min_age}, {max_age}]",
            field="age",
            constraint=f"min_age({min_age}) <= age <= max_age({max_age})",
        )


# ---------------------------------------------------------------------------
# Term / duration validators
# ---------------------------------------------------------------------------
_PRODUCT_TYPES = {"whole_life", "term", "endowment", "pure_endowment"}


def validate_product_type(product: str) -> None:
    """Ensure ``product`` is a supported product type."""
    if product not in _PRODUCT_TYPES:
        raise ActuarialValidationError(
            f"Unknown product type: {product!r}",
            field="product_type",
            constraint=f"product_type in {_sorted(_PRODUCT_TYPES)}",
        )


def _sorted(s: set) -> str:
    return "{" + ", ".join(sorted(s)) + "}"


def validate_term_bounds(
    n: Optional[int], t: int = 0, product_type: str = "term"
) -> None:
    """
    Validate duration ``t`` against term ``n`` for finite-horizon products.

    For ``term`` and ``endowment`` products the policy duration ``t`` must
    satisfy ``0 <= t <= n`` (with ``t == n`` meaning expired / matured).
    For whole-life products ``n`` is irrelevant and should be passed as ``0``.

    Args:
        n: Policy term in years (``>= 0``). ``None`` is rejected for finite
            products with a clear "n is required" error.
        t: Duration since issue in years (``>= 0``).
        product_type: One of the supported product types.
    """
    validate_product_type(product_type)
    if not isinstance(t, int) or isinstance(t, bool):
        raise ActuarialValidationError(
            f"Duration t must be an integer (got {type(t).__name__})",
            field="t",
            constraint="t: int",
        )
    if t < 0:
        raise ActuarialValidationError(
            f"Duration t cannot be negative (got {t})",
            field="t",
            constraint="t >= 0",
        )
    if product_type in ("term", "endowment", "pure_endowment"):
        if n is None or isinstance(n, bool) or not isinstance(n, int):
            raise ActuarialValidationError(
                f"Term n is required and must be an integer for "
                f"{product_type!r} product (got {n!r})",
                field="n",
                constraint="n: int (non-None) for finite-horizon products",
            )
        if n < 0:
            raise ActuarialValidationError(
                f"Term n cannot be negative (got {n})",
                field="n",
                constraint="n >= 0",
            )
        if t > n:
            raise ActuarialValidationError(
                f"Duration t={t} exceeds term n={n} for {product_type} product",
                field="t",
                constraint=f"0 <= t <= n for product_type={product_type!r}",
            )
    else:
        # whole life: n is irrelevant; still reject negative n if provided.
        if n is not None and (isinstance(n, bool) or not isinstance(n, int)):
            raise ActuarialValidationError(
                f"Term n must be an integer if provided (got {n!r})",
                field="n",
                constraint="n: int | None for whole_life",
            )
        if isinstance(n, int) and not isinstance(n, bool) and n < 0:
            raise ActuarialValidationError(
                f"Term n cannot be negative (got {n})",
                field="n",
                constraint="n >= 0",
            )


# ---------------------------------------------------------------------------
# Amount validators
# ---------------------------------------------------------------------------
def validate_non_negative_amount(value: float, name: str) -> None:
    """
    Ensure a monetary amount is non-negative and finite.

    Negative sums assured / pensions have no actuarial meaning and would
    flip the sign of reserves and BEL.
    """
    if not isinstance(value, (int, float)):
        raise ActuarialValidationError(
            f"{name} must be a number, got {type(value).__name__}",
            field=name,
            constraint=f"{name}: (int|float)",
        )
    if math.isnan(value) or math.isinf(value):
        raise ActuarialValidationError(
            f"{name} must be finite (got {value})",
            field=name,
            constraint=f"{name}: finite",
        )
    if value < 0:
        raise ActuarialValidationError(
            f"{name} cannot be negative (got {value})",
            field=name,
            constraint=f"{name} >= 0",
        )


def validate_positive_amount(value: float, name: str, *, strict: bool = True) -> None:
    """
    Ensure a monetary amount is positive (``> 0``) when ``strict``, else
    non-negative. Used for sums assured / pensions that must be strictly
    positive to produce a meaningful benefit.
    """
    validate_non_negative_amount(value, name)
    if strict and value <= 0:
        raise ActuarialValidationError(
            f"{name} must be strictly positive (got {value})",
            field=name,
            constraint=f"{name} > 0",
        )


def validate_interest_rate(
    interest_rate: float,
    *,
    allow_above_one: bool = True,
    max_rate: float = 10.0,
) -> None:
    """
    Validate an annual interest rate.

    ``i == 0`` is explicitly allowed (undiscounted sums). Negative rates are
    rejected (not meaningful for LISF reserving). Rates above 1 (100%) are
    allowed by default with the assumption the caller passed a decimal; an
    абсолютно unreasonable ``max_rate`` guards against a misplaced percentage
    (e.g. ``5`` meaning 5%).
    """
    if not isinstance(interest_rate, (int, float)):
        raise ActuarialValidationError(
            f"Interest rate must be a number, got {type(interest_rate).__name__}",
            field="interest_rate",
            constraint="interest_rate: (int|float)",
        )
    if math.isnan(interest_rate) or math.isinf(interest_rate):
        raise ActuarialValidationError(
            f"Interest rate must be finite (got {interest_rate})",
            field="interest_rate",
            constraint="interest_rate: finite",
        )
    if interest_rate < 0:
        raise ActuarialValidationError(
            f"Interest rate cannot be negative (got {interest_rate})",
            field="interest_rate",
            constraint="interest_rate >= 0",
        )
    if not allow_above_one and interest_rate > 1.0 + PROB_TOL:
        raise ActuarialValidationError(
            f"Interest rate appears to be a percentage, not a decimal: {interest_rate}",
            field="interest_rate",
            constraint="interest_rate <= 1 (decimal form, e.g. 0.05 for 5%)",
        )
    if interest_rate > max_rate:
        raise ActuarialValidationError(
            f"Interest rate {interest_rate} exceeds the sanity ceiling {max_rate}",
            field="interest_rate",
            constraint=f"interest_rate <= {max_rate}",
        )


__all__ = [
    "PROB_TOL",
    "MONO_REL_TOL",
    "validate_consecutive_ages",
    "validate_lx_monotonic",
    "validate_probabilities",
    "validate_age_in_table",
    "validate_product_type",
    "validate_term_bounds",
    "validate_non_negative_amount",
    "validate_positive_amount",
    "validate_interest_rate",
]