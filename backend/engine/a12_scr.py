"""
Solvency Capital Requirement (SCR) Module - Block 12
=====================================================

Implements the SCR computation under the Solvency II / CNSF standard
formula framework for a life insurance portfolio.

Theory Connection:
-----------------
The SCR is the amount of capital an insurer needs to absorb a 1-in-200-year
loss event (VaR at 99.5% confidence, 1-year horizon). Under the standard
formula, it is computed as:

    SCR_i = BEL_stressed(shock_i) - BEL_base

for each risk module i, then aggregated using a correlation matrix:

    SCR_life = sqrt(vec' * CORR * vec)

where vec = [SCR_mort, SCR_long, SCR_cat].

Risk Modules Implemented:
------------------------
1. Mortality:   +15% permanent q_x increase (death products only)
2. Longevity:   -20% permanent q_x decrease (annuity products only)
3. Interest Rate: +/- 100 bps parallel shift (all products)
4. Catastrophe: +35% one-year mortality spike (death products only)
                (COVID-calibrated from Mexican INEGI/CONAPO data)

Top-Level Aggregation:
---------------------
    SCR_total = sqrt(SCR_life^2 + SCR_ir^2 + 2 * rho * SCR_life * SCR_ir)

where rho = 0.25 (life underwriting vs market risk correlation).

Risk Margin:
-----------
    MdR = CoC * SCR * annuity_factor
    Technical Provisions = BEL + MdR

LISF / CUSF Compliance:
-----------------------
Mexican regulation follows Solvency II closely. The RCS (Requerimiento de
Capital de Solvencia) = SCR, and technical provisions (Reservas Tecnicas)
must include both BEL (Mejor Estimacion) and risk margin (Margen de Riesgo).
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, cast

import numpy as np

from .a01_life_table import LifeTable
from .a02_commutation import CommutationFunctions
from .a11_portfolio import (
    Portfolio,
    compute_policy_bel,
    portfolio_remaining_duration,
    resolve_policy_annual_premium,
)
from .exceptions import ActuarialComputationError, ActuarialValidationError

if TYPE_CHECKING:
    from .a08_lee_carter import LeeCarter

logger = logging.getLogger(__name__)

# =============================================================================
# Solvency II Constants (Standard Formula)
# =============================================================================
# The shock magnitudes below (+15% mortality, -20% longevity, +/-100 bps
# interest rate, +35% one-year catastrophe) are the ILLUSTRATIVE Solvency II
# standard-formula values and are used as defaults. They are NOT calibrated
# from any particular mortality volatility; use
# :func:`calibrate_shocks_from_lee_carter` to derive portfolio-specific
# shocks from a fitted Lee-Carter model when supported by the data.

# Life underwriting correlation matrix (Solvency II Article 136)
#             Mort   Long    Cat
LIFE_CORR = np.array(
    [
        [1.00, -0.25, 0.25],
        [-0.25, 1.00, 0.00],
        [0.25, 0.00, 1.00],
    ]
)

# Default correlation between life underwriting and market risk
RHO_LIFE_MARKET = 0.25

# Default Cost-of-Capital rate for risk margin
DEFAULT_COC_RATE = 0.06

# Default floor applied to a DOWN interest-rate shock (the standard-formula
# convention prevents negative nominal rates in the down scenario).
DEFAULT_IR_FLOOR = 0.005

# Tolerance for positive-semi-definiteness checks on correlation matrices.
PSD_TOL = 1e-10


def _validate_non_negative_finite(value: float, name: str) -> None:
    """Validate a public SCR numeric input."""
    if not math.isfinite(value) or value < 0:
        raise ActuarialValidationError(
            f"{name} must be finite and non-negative (got {value})",
            field=name,
            constraint=f"{name} >= 0 and finite",
        )


def _contractual_premiums(
    portfolio: Portfolio,
    base_lt: LifeTable,
    issue_rate: float,
) -> dict[str, float]:
    """Resolve death-policy premiums once from the unstressed issue basis."""
    comm = CommutationFunctions(base_lt, interest_rate=issue_rate)
    return {
        policy.policy_id: premium
        for policy in portfolio.death_products
        if (premium := resolve_policy_annual_premium(policy, comm)) is not None
    }


def _validate_psd(corr_matrix: np.ndarray, *, name: str = "correlation matrix") -> None:
    """
    Validate that ``corr_matrix`` is a square, symmetric, positive
    semi-definite matrix with unit diagonal.

    A non-PSD correlation matrix would make the quadratic form
    ``vec' * CORR * vec`` numerically negative (sqrt of a negative number),
    which is physically meaningless for a variance aggregation.
    """
    arr = np.asarray(corr_matrix, dtype=float)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ActuarialValidationError(
            f"{name} must be square (got shape {arr.shape})",
            field="corr_matrix",
            constraint="corr_matrix.shape == (n, n)",
        )
    diag = np.diag(arr)
    if not np.allclose(diag, 1.0, atol=PSD_TOL):
        raise ActuarialValidationError(
            f"{name} must have a unit diagonal (got {diag})",
            field="corr_matrix",
            constraint="diag(corr_matrix) == 1",
        )
    if not np.allclose(arr, arr.T, atol=PSD_TOL):
        raise ActuarialValidationError(
            f"{name} must be symmetric",
            field="corr_matrix",
            constraint="corr_matrix == corr_matrix.T",
        )
    if np.any(arr < -1.0 - PSD_TOL) or np.any(arr > 1.0 + PSD_TOL):
        raise ActuarialValidationError(
            f"{name} entries must lie in [-1,1]",
            field="corr_matrix",
            constraint="-1 <= corr_matrix[i,j] <= 1",
        )
    eig = np.linalg.eigvalsh(arr)
    if eig.min() < -PSD_TOL:
        raise ActuarialValidationError(
            f"{name} is not positive semi-definite: min eigenvalue {float(eig.min()):.3e} < 0",
            field="corr_matrix",
            constraint="min eigval(corr_matrix) >= -tol",
        )


# Validate the bundled default LIFE_CORR at import time so a typo in the
# constant is caught immediately rather than producing a negative SCR.
_validate_psd(LIFE_CORR, name="LIFE_CORR")


# =============================================================================
# Helper: Build Shocked Life Table
# =============================================================================


def build_shocked_life_table(
    base_lt: LifeTable,
    shock_factor: float,
    radix: float = 100_000.0,
) -> LifeTable:
    """
    Create a new LifeTable with q_x scaled by shock_factor.

    For each age: shocked_q_x = min(base_q_x * factor, 1.0).
    Then rebuild l_x from the shocked q_x values.

    A shock_factor > 1.0 means WORSE mortality (higher death rates).
    A shock_factor < 1.0 means BETTER mortality (lower death rates).

    Args:
        base_lt: Base (best-estimate) life table
        shock_factor: Multiplicative factor for q_x
        radix: l_0 for the new table

    Returns:
        New LifeTable with shocked mortality
    """
    if not math.isfinite(shock_factor) or shock_factor < 0:
        raise ActuarialValidationError(
            f"shock_factor must be finite and non-negative (got {shock_factor})",
            field="shock_factor",
            constraint="shock_factor >= 0 and finite",
        )
    ages = base_lt.ages
    shocked_qx = []
    for age in ages[:-1]:
        shocked_qx.append(min(base_lt.get_q(age) * shock_factor, 1.0))
    shocked_qx.append(1.0)  # terminal q = 1.0

    l_x = [radix]
    for qx in shocked_qx[:-1]:
        l_x.append(l_x[-1] * (1.0 - qx))

    return LifeTable(ages=ages, l_x_values=l_x)


# =============================================================================
# SCR Component 1: Mortality Risk
# =============================================================================


def compute_scr_mortality(
    portfolio: Portfolio,
    base_lt: LifeTable,
    interest_rate: float,
    shock: float = 0.15,
) -> dict[str, float]:
    """
    Compute SCR for mortality risk.

    A permanent +15% increase in q_x (Solvency II standard).
    Only DEATH products are affected. Annuities BENEFIT from higher
    mortality (fewer payments), but the standard formula applies the
    shock only to the adverse direction per product type.

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        interest_rate: Risk-free rate
        shock: Proportional q_x increase (default 0.15 = +15%)

    Returns:
        Dict with bel_base, bel_stressed, scr, shock
    """
    portfolio.validate_non_empty()
    _validate_non_negative_finite(shock, "mortality_shock")
    death_policies = portfolio.death_products

    if not death_policies:
        return {"bel_base": 0.0, "bel_stressed": 0.0, "scr": 0.0, "shock": shock}

    premiums = _contractual_premiums(portfolio, base_lt, interest_rate)
    bel_base = sum(
        compute_policy_bel(
            p,
            base_lt,
            interest_rate,
            annual_premium=premiums[p.policy_id],
        )
        for p in death_policies
    )

    # Stressed BEL: mortality increases by shock factor
    stressed_lt = build_shocked_life_table(base_lt, 1.0 + shock)
    bel_stressed = sum(
        compute_policy_bel(
            p,
            stressed_lt,
            interest_rate,
            annual_premium=premiums[p.policy_id],
        )
        for p in death_policies
    )

    scr = max(bel_stressed - bel_base, 0.0)

    return {
        "bel_base": bel_base,
        "bel_stressed": bel_stressed,
        "scr": scr,
        "shock": shock,
    }


# =============================================================================
# SCR Component 2: Longevity Risk
# =============================================================================


def compute_scr_longevity(
    portfolio: Portfolio,
    base_lt: LifeTable,
    interest_rate: float,
    shock: float = 0.20,
) -> dict[str, float]:
    """
    Compute SCR for longevity risk.

    A permanent -20% decrease in q_x (Solvency II standard).
    Only ANNUITY products are affected. Death products benefit from
    lower mortality (fewer claims), but the standard formula applies
    the shock only to the adverse direction per product type.

    For annuities, the insurer pays as long as the annuitant lives.
    Lower mortality => longer life => more payments => higher BEL.

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        interest_rate: Risk-free rate
        shock: Proportional q_x decrease (default 0.20 = -20%)

    Returns:
        Dict with bel_base, bel_stressed, scr, shock
    """
    portfolio.validate_non_empty()
    _validate_non_negative_finite(shock, "longevity_shock")
    if shock > 1:
        raise ActuarialValidationError(
            f"longevity_shock cannot exceed 1 (got {shock})",
            field="longevity_shock",
            constraint="0 <= longevity_shock <= 1",
        )
    annuity_policies = portfolio.annuity_products

    if not annuity_policies:
        return {"bel_base": 0.0, "bel_stressed": 0.0, "scr": 0.0, "shock": shock}

    # Base BEL for annuity products
    bel_base = sum(compute_policy_bel(p, base_lt, interest_rate) for p in annuity_policies)

    # Stressed BEL: mortality decreases by shock factor (people live longer)
    stressed_lt = build_shocked_life_table(base_lt, 1.0 - shock)
    bel_stressed = sum(compute_policy_bel(p, stressed_lt, interest_rate) for p in annuity_policies)

    scr = max(bel_stressed - bel_base, 0.0)

    return {
        "bel_base": bel_base,
        "bel_stressed": bel_stressed,
        "scr": scr,
        "shock": shock,
    }


# =============================================================================
# SCR Component 3: Interest Rate Risk
# =============================================================================


def compute_scr_interest_rate(
    portfolio: Portfolio,
    base_lt: LifeTable,
    base_rate: float,
    shock_bps: int = 100,
    rate_floor: float = DEFAULT_IR_FLOOR,
) -> dict[str, object]:
    """
    Compute SCR for interest rate risk.

    A +/- 100 bps parallel shift in the yield curve (simplified).
    ALL products are affected because every future cash flow is discounted.

    The adverse scenario is typically the DOWN shock: lower rates mean
    future obligations have a HIGHER present value.

    SCR_ir = max(BEL_up - BEL_base, BEL_down - BEL_base, 0)

    The down scenario is floored at ``rate_floor`` (default 0.5%). The Solvency
    II standard formula convention prevents the down shock from producing a
    negative nominal rate; the floor is made configurable so a regulator or
    a yield-curve-specific calibration can override it. A warning is logged
    whenever the floor binds, for auditability.

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        base_rate: Base risk-free interest rate
        shock_bps: Shock in basis points (default 100 = 1%)
        rate_floor: Floor for the down shock (default 0.5%, configurable)

    Returns:
        Dict with bel_base, bel_up, bel_down, scr, rate_up, rate_down,
        floor_applied
    """
    portfolio.validate_non_empty()
    _validate_non_negative_finite(base_rate, "base_rate")
    _validate_non_negative_finite(rate_floor, "rate_floor")
    if isinstance(shock_bps, bool) or not isinstance(shock_bps, int) or shock_bps < 0:
        raise ActuarialValidationError(
            f"shock_bps must be a non-negative integer (got {shock_bps!r})",
            field="shock_bps",
            constraint="shock_bps: int >= 0",
        )
    shock_decimal = shock_bps / 10_000.0

    rate_up = base_rate + shock_decimal
    raw_down = base_rate - shock_decimal
    floor_applied = raw_down < rate_floor
    if floor_applied:
        logger.warning(
            "IR down-shock %.4f below floor %.4f; floor applied",
            raw_down,
            rate_floor,
        )
    rate_down = max(raw_down, rate_floor)

    premiums = _contractual_premiums(portfolio, base_lt, base_rate)

    def _bel_at(rate: float) -> float:
        comm = CommutationFunctions(base_lt, interest_rate=rate)
        return sum(
            compute_policy_bel(
                policy,
                base_lt,
                rate,
                comm=comm,
                annual_premium=premiums.get(policy.policy_id),
            )
            for policy in portfolio.policies
        )

    bel_base = _bel_at(base_rate)
    bel_up = _bel_at(rate_up)
    bel_down = _bel_at(rate_down)

    scr = max(bel_up - bel_base, bel_down - bel_base, 0.0)

    return {
        "bel_base": bel_base,
        "bel_up": bel_up,
        "bel_down": bel_down,
        "scr": scr,
        "rate_up": rate_up,
        "rate_down": rate_down,
        "floor_applied": floor_applied,
    }


# =============================================================================
# SCR Component 4: Catastrophe Risk (COVID-Calibrated)
# =============================================================================


def compute_scr_catastrophe(
    portfolio: Portfolio,
    base_lt: LifeTable,
    interest_rate: float,
    cat_shock_factor: float = 1.35,
) -> dict[str, object]:
    """
    Compute SCR for catastrophe risk.

    A one-year mortality spike (not permanent). Calibrated from
    COVID-19 impact on Mexican mortality data:
    - Pre-COVID k_t trend: -1.076/year
    - COVID k_t reversal: ~6.76 units above trend
    - Conservative estimate: +35% mortality spike at working ages

    Unlike mortality risk (+15% permanent), catastrophe is a
    ONE-YEAR spike. Only the first-year excess deaths matter.
    Only DEATH products are affected.

    Convention (one-year shock):
        The portfolio is an inventory of policies known to be in force at the
        valuation date. The catastrophe death probability is therefore
        conditional on survival to attained age:

            expected_extra_claim = SA * delta_q(attained_age) * v

        Historical issue-to-date survival is not applied again. A cohort
        projection would require survival weighting consistently across BEL
        and every SCR module, which is a different portfolio convention.

        For term/endowment policies past their term (``duration >= n``), the
        policy has expired and contributes ZERO to catastrophe SCR (zero
        in-force exposure). Whole-life policies whose attained age exceeds
        omega also contribute zero (no mortality beyond the table).

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        interest_rate: Risk-free rate
        cat_shock_factor: Multiplicative one-year mortality spike

    Returns:
        Dict with scr, cat_shock_factor, details
    """
    portfolio.validate_non_empty()
    if not math.isfinite(cat_shock_factor) or cat_shock_factor < 1:
        raise ActuarialValidationError(
            f"cat_shock_factor must be finite and at least 1 (got {cat_shock_factor})",
            field="cat_shock_factor",
            constraint="cat_shock_factor >= 1 and finite",
        )
    death_policies = portfolio.death_products
    v = 1.0 / (1.0 + interest_rate)

    if not death_policies:
        return {"scr": 0.0, "cat_shock_factor": cat_shock_factor}

    shocked_lt = build_shocked_life_table(base_lt, cat_shock_factor)

    total_extra = 0.0
    details = []
    for p in death_policies:
        # Expired finite-horizon policy: no in-force exposure.
        if p.is_expired or p.is_matured:
            continue
        age = p.attained_age
        if age > base_lt.max_age or age > shocked_lt.max_age:
            continue
        if age < base_lt.min_age:
            continue

        q_base = base_lt.get_q(age)
        q_shocked = shocked_lt.get_q(age)
        delta_q = q_shocked - q_base

        # The portfolio is an inventory of policies known to be in force at
        # the valuation date. q_x is therefore conditional on survival to the
        # attained age; applying issue-to-date survival again would double
        # count historical survival.
        extra_claim = p.SA * delta_q * v
        total_extra += extra_claim
        details.append(
            {
                "policy_id": p.policy_id,
                "attained_age": age,
                "q_base": q_base,
                "q_shocked": q_shocked,
                "delta_q": delta_q,
                "extra_claim": extra_claim,
            }
        )

    return {
        "scr": max(total_extra, 0.0),
        "cat_shock_factor": cat_shock_factor,
        "details": details,
    }


# =============================================================================
# Aggregation: Life Underwriting
# =============================================================================


def aggregate_scr_life(
    scr_mort: float,
    scr_long: float,
    scr_cat: float,
    corr_matrix: np.ndarray | None = None,
) -> dict[str, float]:
    """
    Aggregate life underwriting SCR components using correlation matrix.

    SCR_life = sqrt(vec' * CORR * vec)

    The diversification benefit arises because mortality and longevity
    are NEGATIVELY correlated (-0.25): a pandemic increases death claims
    but decreases annuity obligations. An insurer selling BOTH products
    has a natural hedge.

    Args:
        scr_mort: SCR for mortality risk
        scr_long: SCR for longevity risk
        scr_cat: SCR for catastrophe risk
        corr_matrix: 3x3 correlation matrix (default: LIFE_CORR)

    Returns:
        Dict with scr_life, sum_individual, diversification_benefit,
        diversification_pct
    """
    for value, name in (
        (scr_mort, "scr_mort"),
        (scr_long, "scr_long"),
        (scr_cat, "scr_cat"),
    ):
        _validate_non_negative_finite(value, name)

    if corr_matrix is None:
        corr_matrix = LIFE_CORR
    else:
        _validate_psd(corr_matrix, name="custom correlation matrix")

    vec = np.array([scr_mort, scr_long, scr_cat])
    sum_individual = np.sum(vec)

    # Quadratic form: vec' * CORR * vec
    scr_life_sq = vec @ corr_matrix @ vec
    scr_life = math.sqrt(max(scr_life_sq, 0.0))

    diversification_benefit = sum_individual - scr_life
    diversification_pct = (
        (diversification_benefit / sum_individual * 100) if sum_individual > 0 else 0.0
    )

    return {
        "scr_life": scr_life,
        "sum_individual": sum_individual,
        "diversification_benefit": diversification_benefit,
        "diversification_pct": diversification_pct,
    }


# =============================================================================
# Aggregation: Total SCR (Life + Market)
# =============================================================================


def aggregate_scr_total(
    scr_life: float,
    scr_ir: float,
    rho: float = RHO_LIFE_MARKET,
) -> dict[str, float]:
    """
    Aggregate SCR across life underwriting and market risk.

    SCR_total = sqrt(SCR_life^2 + SCR_ir^2 + 2 * rho * SCR_life * SCR_ir)

    Args:
        scr_life: Aggregated life underwriting SCR
        scr_ir: Interest rate SCR (market risk)
        rho: Correlation between life and market modules

    Returns:
        Dict with scr_total, scr_life, scr_ir, rho,
        sum_individual, diversification_benefit
    """
    _validate_non_negative_finite(scr_life, "scr_life")
    _validate_non_negative_finite(scr_ir, "scr_ir")
    if not math.isfinite(rho) or not -1.0 <= rho <= 1.0:
        raise ActuarialValidationError(
            f"rho must be a finite correlation in [-1,1] (got {rho})",
            field="rho",
            constraint="-1 <= rho <= 1 and finite",
        )
    scr_total_sq = scr_life**2 + scr_ir**2 + 2.0 * rho * scr_life * scr_ir
    scr_total = math.sqrt(max(scr_total_sq, 0.0))

    sum_individual = scr_life + scr_ir
    diversification_benefit = sum_individual - scr_total

    return {
        "scr_total": scr_total,
        "scr_life": scr_life,
        "scr_ir": scr_ir,
        "rho": rho,
        "sum_individual": sum_individual,
        "diversification_benefit": diversification_benefit,
    }


# =============================================================================
# Risk Margin
# =============================================================================


def compute_risk_margin(
    scr_total: float,
    duration: float,
    coc_rate: float = DEFAULT_COC_RATE,
    discount_rate: float = 0.05,
) -> dict[str, float]:
    """
    Compute the risk margin (Margen de Riesgo / MdR).

    Simplified approach:
        MdR = CoC * SCR * annuity_factor(duration, discount_rate)

    where annuity_factor = (1 - v^duration) / i for i > 0.

    The risk margin is the "price of capital": if another insurer took
    over the portfolio, they'd need to hold SCR for the remaining policy
    lifetime. The CoC (6% under Solvency II) compensates them annually.

    Full formula: MdR = CoC * sum_t [SCR(t) / (1+r)^(t+1)]
    We use the simplified version assuming constant SCR.

    Args:
        scr_total: Total SCR amount
        duration: Average remaining duration of the portfolio (years)
        coc_rate: Cost-of-Capital rate (default 6%)
        discount_rate: Risk-free rate for discounting

    Returns:
        Dict with risk_margin, coc_rate, duration, annuity_factor
    """
    for value, name in (
        (scr_total, "scr_total"),
        (duration, "duration"),
        (coc_rate, "coc_rate"),
        (discount_rate, "discount_rate"),
    ):
        _validate_non_negative_finite(value, name)

    if duration == 0 or scr_total == 0:
        return {
            "risk_margin": 0.0,
            "coc_rate": coc_rate,
            "duration": duration,
            "annuity_factor": 0.0,
        }

    if discount_rate == 0:
        annuity_factor = duration
    else:
        v = 1.0 / (1.0 + discount_rate)
        annuity_factor = (1.0 - v**duration) / discount_rate

    risk_margin = coc_rate * scr_total * annuity_factor

    return {
        "risk_margin": risk_margin,
        "coc_rate": coc_rate,
        "duration": duration,
        "annuity_factor": annuity_factor,
    }


# =============================================================================
# Solvency Ratio
# =============================================================================


def compute_solvency_ratio(available_capital: float, scr_total: float) -> dict[str, object]:
    """
    Compute the solvency ratio.

    ratio = Available Capital / SCR

    Interpretation:
        > 100%: Solvent (can survive a 1-in-200-year event)
        = 100%: Minimum CNSF requirement
        150-200%: Well-managed insurer target range
        < 100%: Supervisory intervention required

    Args:
        available_capital: Available capital (funds propios)
        scr_total: Total SCR

    Returns:
        Dict with ratio, available_capital, scr_total, is_solvent
    """
    _validate_non_negative_finite(available_capital, "available_capital")
    _validate_non_negative_finite(scr_total, "scr_total")
    if scr_total == 0:
        ratio = float("inf") if available_capital > 0 else 0.0
    else:
        ratio = available_capital / scr_total

    return {
        "ratio": ratio,
        "ratio_pct": ratio * 100,
        "available_capital": available_capital,
        "scr_total": scr_total,
        "is_solvent": ratio >= 1.0,
    }


# =============================================================================
# Shock calibration from Lee-Carter volatility
# =============================================================================


def calibrate_shocks_from_lee_carter(
    lee_carter: LeeCarter,
    *,
    confidence: float = 0.995,
    representative_b: float | None = None,
) -> dict[str, float]:
    """
    Derive SCR shock magnitudes from a fitted Lee-Carter model's volatility.

    Under Lee-Carter, the time index follows ``k_{t+1} = k_t + drift + sigma*Z``
    with ``Z ~ N(0,1)``. A 1-year VaR at ``confidence`` (default 0.995, i.e.
    the 1-in-200 Solvency II horizon) maps to a k_t shock of magnitude
    ``sigma * z``, where ``z = Phi^{-1}(confidence)``.

    Because q_x = 1 - exp(-m_x) and ``ln m_x = a_x + b_x * k_t``, a k_t shock
    of ``delta_k`` maps roughly to a multiplicative mortality shock of
    ``exp(|b_x| * delta_k) - 1``. We summarise this with a single
    representative ``b`` (the mean of positive ``b_x`` over the working-age
    range by default), yielding:

        mortality_shock  = exp(delta) - 1       (adverse: worse mortality)
        longevity_shock  = 1 - exp(-delta)      (adverse: better mortality)
        cat_shock_factor = 1 + (exp(b_rep * sigma * z) - 1) = exp(b_rep * sigma * z)

    This inverse mapping keeps the longevity multiplier ``1-shock`` positive
    and consistent with a symmetric log-mortality displacement.

    The defaults remain the Solvency II ``+15% / -20% / +35%`` values -- this
    helper only provides an OPTIONAL, data-driven override when a fitted
    Lee-Carter model is available.

    Args:
        lee_carter: A fitted Lee-Carter model with ``kt`` and ``bx``.
        confidence: VaR confidence (default 0.995 = 1-in-200).
        representative_b: Override for the representative b_x (otherwise the
            mean of positive working-age b_x is used).

    Returns:
        Dict with mortality_shock, longevity_shock, cat_shock_factor, sigma_k,
        z_value, representative_b.
    """
    if not 0.0 < confidence < 1.0:
        raise ActuarialValidationError(
            f"confidence must be in (0,1) (got {confidence})",
            field="confidence",
            constraint="0 < confidence < 1",
        )
    kt = np.asarray(lee_carter.kt, dtype=float)
    if len(kt) < 3:
        raise ActuarialComputationError(
            f"Lee-Carter k_t has too few points to estimate volatility (need >=3, got {len(kt)})",
            field="lee_carter.kt",
            constraint="len(kt) >= 3",
        )
    innovations = np.diff(kt)
    sigma_k = float(np.std(innovations, ddof=1)) if len(innovations) >= 2 else 0.0

    z = _inv_norm_cdf(confidence)

    if representative_b is None:
        bx = np.asarray(lee_carter.bx, dtype=float)
        ages_attr = getattr(lee_carter, "ages", None)
        if ages_attr is None:
            positive = bx[bx > 0]
        else:
            ages = np.asarray(ages_attr)
            working_age = (ages >= 20) & (ages <= 80)
            positive = bx[(bx > 0) & working_age]
        if not positive.size:
            positive = bx[bx > 0]
        b_rep = float(positive.mean()) if positive.size else 1.0
    else:
        b_rep = float(representative_b)
    if not math.isfinite(b_rep) or b_rep < 0:
        raise ActuarialValidationError(
            f"representative_b must be finite and non-negative (got {b_rep})",
            field="representative_b",
            constraint="representative_b >= 0 and finite",
        )

    delta_lnq = b_rep * sigma_k * z
    mortality_increase = math.expm1(delta_lnq)
    longevity_decrease = -math.expm1(-delta_lnq)  # 1 - exp(-delta)

    return {
        "mortality_shock": mortality_increase,
        "longevity_shock": longevity_decrease,
        "cat_shock_factor": 1.0 + mortality_increase,
        "sigma_k": sigma_k,
        "z_value": z,
        "representative_b": b_rep,
    }


def _inv_norm_cdf(p: float) -> float:
    """Inverse standard-normal CDF via the inverse error function (Beasley-Springer-Moro fallback)."""
    # Acklam's algorithm: decent accuracy without scipy.stats.
    # https://www.wilmottwiki.com/quantnotes/AcklamAlgorithm.htm
    a = [
        -3.969683028665376e01,
        2.209460983245205e02,
        -2.775758516594995e02,
        1.383577551577929e02,
        -3.066479806487985e01,
        2.506628277458239e00,
    ]
    b = [
        -5.447609979032057e01,
        1.615858368580409e02,
        -1.556989798752604e02,
        6.680131188771972e01,
        -1.328068914711492e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549726583709849e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow

    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / ((((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + b[5]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    return x


# =============================================================================
# Full SCR Pipeline
# =============================================================================


def run_full_scr(
    portfolio: Portfolio,
    base_lt: LifeTable,
    interest_rate: float,
    mortality_shock: float = 0.15,
    longevity_shock: float = 0.20,
    ir_shock_bps: int = 100,
    cat_shock_factor: float = 1.35,
    coc_rate: float = DEFAULT_COC_RATE,
    portfolio_duration: float | None = None,
    available_capital: float | None = None,
    ir_rate_floor: float = DEFAULT_IR_FLOOR,
    shocks_from: LeeCarter | None = None,
) -> dict[str, object]:
    """
    Run the complete SCR computation pipeline.

    Steps:
        1. Compute base BEL for the portfolio
        2. Compute 4 individual SCR components
        3. Aggregate life underwriting (correlation matrix)
        4. Aggregate total (life + market)
        5. Compute risk margin
        6. Compute technical provisions (BEL + MdR)
        7. Compute solvency ratio (if capital provided)

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        interest_rate: Risk-free rate
        mortality_shock: q_x increase for mortality risk
        longevity_shock: q_x decrease for longevity risk
        ir_shock_bps: Interest rate shock in basis points
        cat_shock_factor: Catastrophe one-year mortality multiplier
        coc_rate: Cost-of-Capital rate for risk margin
        portfolio_duration: Average remaining duration (years). If ``None``,
            it is computed from the portfolio via
            :func:`portfolio_remaining_duration` (replaces the previous
            hardcoded 15.0).
        available_capital: Available capital (optional)
        ir_rate_floor: Floor for the IR down shock (default ``DEFAULT_IR_FLOOR``)
        shocks_from: Optional fitted Lee-Carter model. When provided, the
            mortality / longevity / catastrophe shocks are recalibrated from
            the model's k_t volatility (see
            :func:`calibrate_shocks_from_lee_carter`) and override the
            ``mortality_shock`` / ``longevity_shock`` / ``cat_shock_factor``
            arguments above.

    Returns:
        Comprehensive dict with all SCR results, plus ``portfolio_duration``
        and ``shock_calibration`` keys when those paths are exercised.
    """
    # Optional Lee-Carter shock calibration overrides the standard-formula
    # defaults.
    shock_calibration: dict[str, float] | None = None
    if shocks_from is not None:
        shock_calibration = calibrate_shocks_from_lee_carter(shocks_from)
        mortality_shock = shock_calibration["mortality_shock"]
        longevity_shock = shock_calibration["longevity_shock"]
        cat_shock_factor = shock_calibration["cat_shock_factor"]

    # Portfolio-specific risk-margin duration (replaces hardcoded 15.0).
    if portfolio_duration is None:
        portfolio_duration = portfolio_remaining_duration(portfolio, base_lt, interest_rate)

    # Base BEL
    bel_base = portfolio.compute_bel(base_lt, interest_rate)
    bel_breakdown = portfolio.compute_bel_by_type(base_lt, interest_rate)

    # Individual SCR components
    mort_result = compute_scr_mortality(portfolio, base_lt, interest_rate, shock=mortality_shock)
    long_result = compute_scr_longevity(portfolio, base_lt, interest_rate, shock=longevity_shock)
    ir_result = compute_scr_interest_rate(
        portfolio, base_lt, interest_rate, shock_bps=ir_shock_bps, rate_floor=ir_rate_floor
    )
    cat_result = compute_scr_catastrophe(
        portfolio, base_lt, interest_rate, cat_shock_factor=cat_shock_factor
    )

    # Life underwriting aggregation
    life_agg = aggregate_scr_life(
        mort_result["scr"], long_result["scr"], cast(float, cat_result["scr"])
    )

    # Total aggregation
    total_agg = aggregate_scr_total(life_agg["scr_life"], cast(float, ir_result["scr"]))

    # Risk margin
    rm_result = compute_risk_margin(
        total_agg["scr_total"], portfolio_duration, coc_rate, interest_rate
    )

    # Technical provisions
    technical_provisions = bel_base + rm_result["risk_margin"]

    # Solvency ratio
    solvency = None
    if available_capital is not None:
        solvency = compute_solvency_ratio(available_capital, total_agg["scr_total"])

    return {
        "bel_base": bel_base,
        "bel_breakdown": bel_breakdown,
        "mortality": mort_result,
        "longevity": long_result,
        "interest_rate": ir_result,
        "catastrophe": cat_result,
        "life_aggregation": life_agg,
        "total_aggregation": total_agg,
        "risk_margin": rm_result,
        "technical_provisions": technical_provisions,
        "solvency": solvency,
        "portfolio_duration": portfolio_duration,
        "shock_calibration": shock_calibration,
    }
