"""Solvency Capital Requirement (SCR) endpoints."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import demo_session
from backend.api.exception_handlers import safe_route
from backend.api.schemas.scr import LISFComplianceResponse, SCRRequest, SCRResponse
from backend.api.services import scr_service

router = APIRouter(prefix="/scr", tags=["scr"])


@router.post("/compute", response_model=SCRResponse)
@safe_route
def compute_scr(
    request: SCRRequest,
    session_id: str = Depends(demo_session),
) -> SCRResponse:
    """Run the full SCR pipeline with configurable shock parameters.

    The key inputs (interest rate, shocks, sex, portfolio size, available
    capital) are logged at INFO level for actuarial auditability: every
    SCR computation can be reconstructed from the logs alone.
    """
    portfolio = scr_service.get_portfolio(session_id)
    # Audit-grade request log: rate, shocks, sex, portfolio size, capital.
    import logging

    logging.getLogger(__name__).info(
        "SCR/compute port_size=%d rate=%.4f mort=%.3f long=%.3f ir_bps=%d cat=%.3f "
        "coc=%.3f duration=%s sex=%s capital=%s lc_calib=%s",
        len(portfolio),
        request.interest_rate,
        request.mortality_shock,
        request.longevity_shock,
        request.ir_shock_bps,
        request.cat_shock_factor,
        request.coc_rate,
        request.portfolio_duration,
        request.sex,
        request.available_capital,
        request.shocks_from_lee_carter,
    )

    result = scr_service.run_scr(
        interest_rate=request.interest_rate,
        mortality_shock=request.mortality_shock,
        longevity_shock=request.longevity_shock,
        ir_shock_bps=request.ir_shock_bps,
        cat_shock_factor=request.cat_shock_factor,
        coc_rate=request.coc_rate,
        portfolio_duration=request.portfolio_duration,
        available_capital=request.available_capital,
        sex=request.sex,
        shocks_from_lee_carter=request.shocks_from_lee_carter,
        session_id=session_id,
    )
    return result


@router.get("/compliance", response_model=LISFComplianceResponse)
@safe_route
def get_lisf_compliance():
    """Return LISF/CUSF regulatory compliance mapping for the SCR framework."""
    return scr_service.get_lisf_compliance()


@router.post("/defaults", response_model=SCRResponse)
@safe_route
def compute_scr_defaults(session_id: str = Depends(demo_session)) -> SCRResponse:
    """Run SCR with default Solvency II parameters."""
    import logging

    portfolio = scr_service.get_portfolio(session_id)
    logging.getLogger(__name__).info("SCR/defaults port_size=%d", len(portfolio))
    return scr_service.run_scr(session_id=session_id)
