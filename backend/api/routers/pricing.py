"""Pricing, reserves, and commutation function endpoints."""

from fastapi import APIRouter, Query

from backend.api.exception_handlers import safe_route
from backend.api.schemas.pricing import (
    CommutationResponse,
    CrossCountryPremiumResponse,
    PremiumRequest,
    PremiumResponse,
    ReserveRequest,
    ReserveResponse,
    SensitivityRequest,
    SensitivityResponse,
)
from backend.api.services import pricing_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/premium", response_model=PremiumResponse)
@safe_route
def calculate_premium(request: PremiumRequest) -> PremiumResponse:
    """Calculate the net annual premium for an insurance product."""
    return pricing_service.calculate_premium(
        product_type=request.product_type,
        age=request.age,
        sum_assured=request.sum_assured,
        interest_rate=request.interest_rate,
        term=request.term,
        sex=request.sex,
    )


@router.post("/reserve", response_model=ReserveResponse)
@safe_route
def calculate_reserve(request: ReserveRequest) -> ReserveResponse:
    """Calculate the reserve trajectory for an insurance product."""
    return pricing_service.calculate_reserve_trajectory(
        product_type=request.product_type,
        age=request.age,
        sum_assured=request.sum_assured,
        interest_rate=request.interest_rate,
        term=request.term,
        sex=request.sex,
    )


@router.get("/commutation", response_model=CommutationResponse)
@safe_route
def get_commutation(
    age: int = Query(ge=0, le=100),
    interest_rate: float = Query(default=0.05, ge=0.0, le=1.0),
    sex: str = Query(default="male", pattern="^(male|female|unisex)$"),
) -> CommutationResponse:
    """Get commutation function values (D, N, C, M) and actuarial values at a given age."""
    return pricing_service.get_commutation_values(age, interest_rate, sex=sex)


@router.post("/sensitivity", response_model=SensitivityResponse)
@safe_route
def calculate_sensitivity(request: SensitivityRequest) -> SensitivityResponse:
    """Calculate premium at multiple interest rates (sensitivity analysis)."""
    return pricing_service.calculate_sensitivity(
        product_type=request.product_type,
        age=request.age,
        sum_assured=request.sum_assured,
        rates=request.rates,
        term=request.term,
        sex=request.sex,
    )


@router.post("/cross-country", response_model=CrossCountryPremiumResponse)
@safe_route
def cross_country_premium(request: PremiumRequest) -> CrossCountryPremiumResponse:
    """Compare premiums across Mexico, USA, and Spain."""
    return pricing_service.calculate_cross_country_premium(
        product_type=request.product_type,
        age=request.age,
        sum_assured=request.sum_assured,
        interest_rate=request.interest_rate,
        term=request.term,
        sex=request.sex,
    )
