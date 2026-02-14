"""Portfolio management and BEL computation endpoints."""

from fastapi import APIRouter, HTTPException

from backend.api.schemas.portfolio import (
    PolicyCreate,
    PolicyResponse,
    PortfolioBELRequest,
    PortfolioBELResponse,
    PortfolioSummaryResponse,
)
from backend.api.services import scr_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary():
    """Get portfolio summary (policies, counts, totals)."""
    portfolio = scr_service.get_portfolio()

    policies = []
    for p in portfolio.policies:
        policies.append(PolicyResponse(
            policy_id=p.policy_id,
            product_type=p.product_type,
            issue_age=p.issue_age,
            attained_age=p.attained_age,
            sum_assured=p.SA,
            annual_pension=p.annual_pension,
            term=p.n,
            duration=p.duration,
            is_death_product=p.is_death_product,
            is_annuity=p.is_annuity,
        ))

    return PortfolioSummaryResponse(
        n_policies=len(portfolio),
        n_death=len(portfolio.death_products),
        n_annuity=len(portfolio.annuity_products),
        total_sum_assured=sum(p.SA for p in portfolio.death_products),
        total_annual_pension=sum(p.annual_pension for p in portfolio.annuity_products),
        policies=policies,
    )


@router.post("/bel", response_model=PortfolioBELResponse)
def compute_bel(request: PortfolioBELRequest):
    """Compute Best Estimate Liability (BEL) for the portfolio."""
    try:
        result = scr_service.compute_portfolio_bel(request.interest_rate)
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/policy")
def add_policy(policy: PolicyCreate):
    """Add a policy to the portfolio."""
    try:
        p = scr_service.add_policy(
            policy_id=policy.policy_id,
            product_type=policy.product_type,
            issue_age=policy.issue_age,
            sum_assured=policy.sum_assured,
            annual_pension=policy.annual_pension,
            term=policy.term,
            duration=policy.duration,
        )
        return {
            "message": f"Policy {p.policy_id} added",
            "policy_id": p.policy_id,
            "product_type": p.product_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def reset_portfolio():
    """Reset portfolio to the default sample portfolio."""
    portfolio = scr_service.reset_portfolio()
    return {
        "message": "Portfolio reset to sample",
        "n_policies": len(portfolio),
    }
