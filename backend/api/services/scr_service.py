"""
SCR service: bridges API requests to engine modules a11-a12.
"""

import sys
from pathlib import Path
from typing import Optional

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.engine.a11_portfolio import Policy, Portfolio, create_sample_portfolio
from backend.engine.a12_scr import run_full_scr
from backend.api.services.precomputed import get_regulatory_lt


# Module-level portfolio (can be modified via API).
# NOTE: This is global mutable state shared across all requests -- intentional
# for this demo/portfolio project. In production, use per-session or per-user
# state (e.g., database-backed or session-scoped dependency injection).
_portfolio: Portfolio | None = None


def _ensure_portfolio() -> Portfolio:
    """Get or create the portfolio."""
    global _portfolio
    if _portfolio is None:
        _portfolio = create_sample_portfolio()
    return _portfolio


def reset_portfolio() -> Portfolio:
    """Reset to the sample portfolio."""
    global _portfolio
    _portfolio = create_sample_portfolio()
    return _portfolio


def get_portfolio() -> Portfolio:
    """Get the current portfolio."""
    return _ensure_portfolio()


def add_policy(
    policy_id: str,
    product_type: str,
    issue_age: int,
    sum_assured: float = 0.0,
    annual_pension: float = 0.0,
    term: Optional[int] = None,
    duration: int = 0,
) -> Policy:
    """Add a policy to the portfolio."""
    portfolio = _ensure_portfolio()
    policy = Policy(
        policy_id=policy_id,
        product_type=product_type,
        issue_age=issue_age,
        SA=sum_assured,
        annual_pension=annual_pension,
        n=term,
        duration=duration,
    )
    portfolio.policies.append(policy)
    return policy


def compute_portfolio_bel(interest_rate: float = 0.05) -> dict:
    """Compute BEL for the entire portfolio."""
    portfolio = _ensure_portfolio()
    lt = get_regulatory_lt("cnsf", "male")

    bel_by_type = portfolio.compute_bel_by_type(lt, interest_rate)
    breakdown = portfolio.compute_bel_breakdown(lt, interest_rate)

    return {
        "total_bel": bel_by_type["total_bel"],
        "death_bel": bel_by_type["death_bel"],
        "annuity_bel": bel_by_type["annuity_bel"],
        "n_policies": len(portfolio),
        "n_death": len(portfolio.death_products),
        "n_annuity": len(portfolio.annuity_products),
        "breakdown": breakdown,
    }


def run_scr(
    interest_rate: float = 0.05,
    mortality_shock: float = 0.15,
    longevity_shock: float = 0.20,
    ir_shock_bps: int = 100,
    cat_shock_factor: float = 1.35,
    coc_rate: float = 0.06,
    portfolio_duration: float = 15.0,
    available_capital: Optional[float] = None,
) -> dict:
    """Run the full SCR pipeline."""
    portfolio = _ensure_portfolio()
    lt = get_regulatory_lt("cnsf", "male")

    result = run_full_scr(
        portfolio=portfolio,
        base_lt=lt,
        interest_rate=interest_rate,
        mortality_shock=mortality_shock,
        longevity_shock=longevity_shock,
        ir_shock_bps=ir_shock_bps,
        cat_shock_factor=cat_shock_factor,
        coc_rate=coc_rate,
        portfolio_duration=portfolio_duration,
        available_capital=available_capital,
    )

    # Reshape into API response format
    response = {
        "bel_base": result["bel_base"],
        "bel_death": result["bel_breakdown"]["death_bel"],
        "bel_annuity": result["bel_breakdown"]["annuity_bel"],
        "mortality": {
            "bel_base": result["mortality"]["bel_base"],
            "bel_stressed": result["mortality"]["bel_stressed"],
            "scr": result["mortality"]["scr"],
            "shock": result["mortality"]["shock"],
        },
        "longevity": {
            "bel_base": result["longevity"]["bel_base"],
            "bel_stressed": result["longevity"]["bel_stressed"],
            "scr": result["longevity"]["scr"],
            "shock": result["longevity"]["shock"],
        },
        "interest_rate": {
            "bel_base": result["interest_rate"]["bel_base"],
            "bel_up": result["interest_rate"]["bel_up"],
            "bel_down": result["interest_rate"]["bel_down"],
            "scr": result["interest_rate"]["scr"],
            "rate_up": result["interest_rate"]["rate_up"],
            "rate_down": result["interest_rate"]["rate_down"],
        },
        "catastrophe": {
            "scr": result["catastrophe"]["scr"],
            "cat_shock_factor": result["catastrophe"]["cat_shock_factor"],
        },
        "life_aggregation": {
            "scr_aggregated": result["life_aggregation"]["scr_life"],
            "sum_individual": result["life_aggregation"]["sum_individual"],
            "diversification_benefit": result["life_aggregation"]["diversification_benefit"],
            "diversification_pct": result["life_aggregation"]["diversification_pct"],
        },
        "total_aggregation": {
            "scr_aggregated": result["total_aggregation"]["scr_total"],
            "sum_individual": result["total_aggregation"]["sum_individual"],
            "diversification_benefit": result["total_aggregation"]["diversification_benefit"],
        },
        "risk_margin": {
            "risk_margin": result["risk_margin"]["risk_margin"],
            "coc_rate": result["risk_margin"]["coc_rate"],
            "duration": result["risk_margin"]["duration"],
            "annuity_factor": result["risk_margin"]["annuity_factor"],
        },
        "technical_provisions": result["technical_provisions"],
    }

    if result["solvency"] is not None:
        response["solvency"] = {
            "ratio": result["solvency"]["ratio"],
            "ratio_pct": result["solvency"]["ratio_pct"],
            "available_capital": result["solvency"]["available_capital"],
            "scr_total": result["solvency"]["scr_total"],
            "is_solvent": result["solvency"]["is_solvent"],
        }
    else:
        response["solvency"] = None

    return response
