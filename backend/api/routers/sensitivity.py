"""Sensitivity analysis endpoints: mortality shocks, cross-country, COVID comparison."""

from fastapi import APIRouter, HTTPException

from backend.api.schemas.sensitivity import (
    MortalityShockRequest,
    MortalityShockResponse,
    CrossCountryResponse,
    CovidComparisonResponse,
)
from backend.api.services import sensitivity_service

router = APIRouter(prefix="/sensitivity", tags=["sensitivity"])


@router.post("/mortality-shock", response_model=MortalityShockResponse)
def mortality_shock(request: MortalityShockRequest):
    """Run a mortality shock sweep: apply factors to q_x and recompute premiums."""
    try:
        return sensitivity_service.mortality_shock_sweep(
            age=request.age,
            sum_assured=request.sum_assured,
            product_type=request.product_type,
            factors=request.factors,
            term=request.term,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/cross-country", response_model=CrossCountryResponse)
def cross_country():
    """Get cross-country Lee-Carter comparison (Mexico/USA/Spain)."""
    return sensitivity_service.cross_country_data()


@router.get("/covid-comparison", response_model=CovidComparisonResponse)
def covid_comparison():
    """Get pre-COVID vs full-period mortality comparison."""
    return sensitivity_service.covid_comparison()
