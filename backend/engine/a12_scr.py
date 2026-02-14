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

import math
from typing import Dict, Optional

import numpy as np

from .a01_life_table import LifeTable
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues
from .a11_portfolio import Portfolio, Policy, compute_policy_bel


# =============================================================================
# Solvency II Constants (Standard Formula)
# =============================================================================

# Life underwriting correlation matrix (Solvency II Article 136)
#             Mort   Long    Cat
LIFE_CORR = np.array([
    [1.00, -0.25, 0.25],
    [-0.25, 1.00, 0.00],
    [0.25,  0.00, 1.00],
])

# Default correlation between life underwriting and market risk
RHO_LIFE_MARKET = 0.25

# Default Cost-of-Capital rate for risk margin
DEFAULT_COC_RATE = 0.06


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
) -> Dict:
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
    death_policies = portfolio.death_products

    if not death_policies:
        return {"bel_base": 0.0, "bel_stressed": 0.0, "scr": 0.0, "shock": shock}

    # Base BEL for death products
    bel_base = sum(
        compute_policy_bel(p, base_lt, interest_rate) for p in death_policies
    )

    # Stressed BEL: mortality increases by shock factor
    stressed_lt = build_shocked_life_table(base_lt, 1.0 + shock)
    bel_stressed = sum(
        compute_policy_bel(p, stressed_lt, interest_rate) for p in death_policies
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
) -> Dict:
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
    annuity_policies = portfolio.annuity_products

    if not annuity_policies:
        return {"bel_base": 0.0, "bel_stressed": 0.0, "scr": 0.0, "shock": shock}

    # Base BEL for annuity products
    bel_base = sum(
        compute_policy_bel(p, base_lt, interest_rate) for p in annuity_policies
    )

    # Stressed BEL: mortality decreases by shock factor (people live longer)
    stressed_lt = build_shocked_life_table(base_lt, 1.0 - shock)
    bel_stressed = sum(
        compute_policy_bel(p, stressed_lt, interest_rate) for p in annuity_policies
    )

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
) -> Dict:
    """
    Compute SCR for interest rate risk.

    A +/- 100 bps parallel shift in the yield curve (simplified).
    ALL products are affected because every future cash flow is discounted.

    The adverse scenario is typically the DOWN shock: lower rates mean
    future obligations have a HIGHER present value.

    SCR_ir = max(BEL_up - BEL_base, BEL_down - BEL_base, 0)

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        base_rate: Base risk-free interest rate
        shock_bps: Shock in basis points (default 100 = 1%)

    Returns:
        Dict with bel_base, bel_up, bel_down, scr, rate_up, rate_down
    """
    shock_decimal = shock_bps / 10_000.0

    rate_up = base_rate + shock_decimal
    rate_down = max(base_rate - shock_decimal, 0.005)  # Floor at 0.5%

    bel_base = portfolio.compute_bel(base_lt, base_rate)
    bel_up = portfolio.compute_bel(base_lt, rate_up)
    bel_down = portfolio.compute_bel(base_lt, rate_down)

    scr = max(bel_up - bel_base, bel_down - bel_base, 0.0)

    return {
        "bel_base": bel_base,
        "bel_up": bel_up,
        "bel_down": bel_down,
        "scr": scr,
        "rate_up": rate_up,
        "rate_down": rate_down,
    }


# =============================================================================
# SCR Component 4: Catastrophe Risk (COVID-Calibrated)
# =============================================================================

def compute_scr_catastrophe(
    portfolio: Portfolio,
    base_lt: LifeTable,
    interest_rate: float,
    cat_shock_factor: float = 1.35,
) -> Dict:
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

    For each death policy:
        delta_q = q_shocked(attained_age) - q_base(attained_age)
        extra_claim = SA * delta_q * v  (discounted one year)

    Args:
        portfolio: Insurance portfolio
        base_lt: Best-estimate life table
        interest_rate: Risk-free rate
        cat_shock_factor: Multiplicative one-year mortality spike

    Returns:
        Dict with scr, cat_shock_factor, details
    """
    death_policies = portfolio.death_products
    v = 1.0 / (1.0 + interest_rate)

    if not death_policies:
        return {"scr": 0.0, "cat_shock_factor": cat_shock_factor}

    shocked_lt = build_shocked_life_table(base_lt, cat_shock_factor)

    total_extra = 0.0
    details = []
    for p in death_policies:
        age = p.attained_age
        if age > base_lt.max_age or age > shocked_lt.max_age:
            continue

        q_base = base_lt.get_q(age)
        q_shocked = shocked_lt.get_q(age)
        delta_q = q_shocked - q_base

        extra_claim = p.SA * delta_q * v
        total_extra += extra_claim
        details.append({
            "policy_id": p.policy_id,
            "attained_age": age,
            "q_base": q_base,
            "q_shocked": q_shocked,
            "delta_q": delta_q,
            "extra_claim": extra_claim,
        })

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
    corr_matrix: Optional[np.ndarray] = None,
) -> Dict:
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
    if corr_matrix is None:
        corr_matrix = LIFE_CORR

    vec = np.array([scr_mort, scr_long, scr_cat])
    sum_individual = np.sum(vec)

    # Quadratic form: vec' * CORR * vec
    scr_life_sq = vec @ corr_matrix @ vec
    scr_life = math.sqrt(max(scr_life_sq, 0.0))

    diversification_benefit = sum_individual - scr_life
    diversification_pct = (
        (diversification_benefit / sum_individual * 100)
        if sum_individual > 0
        else 0.0
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
) -> Dict:
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
    scr_total_sq = (
        scr_life ** 2
        + scr_ir ** 2
        + 2.0 * rho * scr_life * scr_ir
    )
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
) -> Dict:
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
    if duration <= 0 or scr_total <= 0:
        return {
            "risk_margin": 0.0,
            "coc_rate": coc_rate,
            "duration": duration,
            "annuity_factor": 0.0,
        }

    v = 1.0 / (1.0 + discount_rate)
    annuity_factor = (1.0 - v ** duration) / discount_rate

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

def compute_solvency_ratio(available_capital: float, scr_total: float) -> Dict:
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
    if scr_total <= 0:
        ratio = float('inf') if available_capital > 0 else 0.0
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
    portfolio_duration: float = 15.0,
    available_capital: Optional[float] = None,
) -> Dict:
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
        portfolio_duration: Average remaining duration (years)
        available_capital: Available capital (optional)

    Returns:
        Comprehensive dict with all SCR results
    """
    # Base BEL
    bel_base = portfolio.compute_bel(base_lt, interest_rate)
    bel_breakdown = portfolio.compute_bel_by_type(base_lt, interest_rate)

    # Individual SCR components
    mort_result = compute_scr_mortality(
        portfolio, base_lt, interest_rate, shock=mortality_shock
    )
    long_result = compute_scr_longevity(
        portfolio, base_lt, interest_rate, shock=longevity_shock
    )
    ir_result = compute_scr_interest_rate(
        portfolio, base_lt, interest_rate, shock_bps=ir_shock_bps
    )
    cat_result = compute_scr_catastrophe(
        portfolio, base_lt, interest_rate, cat_shock_factor=cat_shock_factor
    )

    # Life underwriting aggregation
    life_agg = aggregate_scr_life(
        mort_result["scr"], long_result["scr"], cat_result["scr"]
    )

    # Total aggregation
    total_agg = aggregate_scr_total(life_agg["scr_life"], ir_result["scr"])

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
    }
