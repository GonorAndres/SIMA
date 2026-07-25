"""Solvency Capital Requirement (SCR) endpoints."""

from fastapi import APIRouter, HTTPException

from backend.api.schemas.scr import LISFComplianceResponse, SCRRequest, SCRResponse
from backend.api.services import scr_service
from backend.engine.exceptions import ActuarialValidationError

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
            sex=request.sex,
        )
        return result
    except ActuarialValidationError as e:
        raise HTTPException(status_code=422, detail=e.to_dict()) from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get("/compliance", response_model=LISFComplianceResponse)
def get_lisf_compliance():
    """Return LISF/CUSF regulatory compliance mapping for the SCR framework."""
    return scr_service.get_lisf_compliance()


@router.post("/defaults", response_model=SCRResponse)
def compute_scr_defaults():
    """Run SCR with default Solvency II parameters."""
    try:
        result = scr_service.run_scr()
        return result
    except ActuarialValidationError as e:
        raise HTTPException(status_code=422, detail=e.to_dict()) from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error") from None
