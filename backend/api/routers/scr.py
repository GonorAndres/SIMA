"""Solvency Capital Requirement (SCR) endpoints."""

from fastapi import APIRouter, HTTPException

from backend.api.schemas.scr import SCRRequest, SCRResponse
from backend.api.services import scr_service

router = APIRouter(prefix="/scr", tags=["scr"])


@router.post("/compute", response_model=SCRResponse)
def compute_scr(request: SCRRequest):
    """Run the full SCR pipeline with configurable shock parameters."""
    try:
        result = scr_service.run_scr(
            interest_rate=request.interest_rate,
            mortality_shock=request.mortality_shock,
            longevity_shock=request.longevity_shock,
            ir_shock_bps=request.ir_shock_bps,
            cat_shock_factor=request.cat_shock_factor,
            coc_rate=request.coc_rate,
            portfolio_duration=request.portfolio_duration,
            available_capital=request.available_capital,
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/defaults", response_model=SCRResponse)
def compute_scr_defaults():
    """Run SCR with default Solvency II parameters."""
    try:
        result = scr_service.run_scr()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
