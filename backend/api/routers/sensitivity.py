"""Sensitivity analysis endpoints: mortality shocks, cross-country, COVID comparison."""

from fastapi import APIRouter

from backend.api.exception_handlers import safe_route
from backend.api.schemas.sensitivity import (
    CovidComparisonResponse,
    CrossCountryResponse,
    MortalityShockRequest,
    MortalityShockResponse,
)
from backend.api.services import sensitivity_service

router = APIRouter(prefix="/sensitivity", tags=["sensitivity"])


@router.post("/mortality-shock", response_model=MortalityShockResponse)
@safe_route
def mortality_shock(request: MortalityShockRequest) -> MortalityShockResponse:
    """Run a mortality shock sweep: apply factors to q_x and recompute premiums."""
    return sensitivity_service.mortality_shock_sweep(
        age=request.age,
        sum_assured=request.sum_assured,
        product_type=request.product_type,
        factors=request.factors,
        term=request.term,
        sex=request.sex,
    )


@router.get("/cross-country", response_model=CrossCountryResponse)
@safe_route
def cross_country():
    """Get cross-country Lee-Carter comparison (Mexico/USA/Spain)."""
    return sensitivity_service.cross_country_data()


@router.get("/covid-comparison", response_model=CovidComparisonResponse)
@safe_route
def covid_comparison():
    """Get pre-COVID vs full-period mortality comparison."""
    return sensitivity_service.covid_comparison()
