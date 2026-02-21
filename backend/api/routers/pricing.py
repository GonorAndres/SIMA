"""Pricing, reserves, and commutation function endpoints."""

from fastapi import APIRouter, Query, HTTPException

from backend.api.schemas.pricing import (
    PremiumRequest,
    PremiumResponse,
    ReserveRequest,
    ReserveResponse,
    CommutationResponse,
    SensitivityRequest,
    SensitivityResponse,
)
from backend.api.services import pricing_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/premium", response_model=PremiumResponse)
def calculate_premium(request: PremiumRequest):
    """Calculate the net annual premium for an insurance product."""
    try:
        result = pricing_service.calculate_premium(
            product_type=request.product_type,
            age=request.age,
            sum_assured=request.sum_assured,
            interest_rate=request.interest_rate,
            term=request.term,
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reserve", response_model=ReserveResponse)
def calculate_reserve(request: ReserveRequest):
    """Calculate the reserve trajectory for an insurance product."""
    try:
        result = pricing_service.calculate_reserve_trajectory(
            product_type=request.product_type,
            age=request.age,
            sum_assured=request.sum_assured,
            interest_rate=request.interest_rate,
            term=request.term,
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/commutation", response_model=CommutationResponse)
def get_commutation(
    age: int = Query(ge=0, le=100),
    interest_rate: float = Query(default=0.05, ge=0.001, le=1.0),
):
    """Get commutation function values (D, N, C, M) and actuarial values at a given age."""
    try:
        return pricing_service.get_commutation_values(age, interest_rate)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sensitivity", response_model=SensitivityResponse)
def calculate_sensitivity(request: SensitivityRequest):
    """Calculate premium at multiple interest rates (sensitivity analysis)."""
    try:
        result = pricing_service.calculate_sensitivity(
            product_type=request.product_type,
            age=request.age,
            sum_assured=request.sum_assured,
            rates=request.rates,
            term=request.term,
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
