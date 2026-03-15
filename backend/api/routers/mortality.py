"""Mortality data, Lee-Carter, and projection endpoints."""

from fastapi import APIRouter, Query, HTTPException

from backend.api.schemas.mortality import (
    LifeTableResponse,
    LeeCarterFitResponse,
    ProjectionResponse,
    MortalityDataSummary,
    ValidationResponse,
    GraduationResponse,
    MortalitySurfaceResponse,
    LCDiagnosticsResponse,
)
from backend.api.services import mortality_service

router = APIRouter(prefix="/mortality", tags=["mortality"])


@router.get("/data/summary", response_model=MortalityDataSummary)
def get_data_summary(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get summary of loaded mortality data (INEGI/CONAPO)."""
    return mortality_service.get_data_summary(sex=sex)


@router.get("/lee-carter", response_model=LeeCarterFitResponse)
def get_lee_carter(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get the fitted Lee-Carter model parameters (a_x, b_x, k_t)."""
    return mortality_service.get_lee_carter_params(sex=sex)


@router.get("/projection", response_model=ProjectionResponse)
def get_projection(
    horizon: int = Query(default=30, ge=1, le=100),
    projection_year: int = Query(default=2040),
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get mortality projection with optional life table at a specific year."""
    try:
        return mortality_service.get_projection_data(
            horizon=horizon,
            projection_year=projection_year,
            sex=sex,
        )
    except (IndexError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/life-table", response_model=LifeTableResponse)
def get_life_table(
    table_type: str = Query(default="cnsf", pattern="^(cnsf|cnsf_2013|emssa)$"),
    sex: str = Query(default="male", pattern="^(male|female)$"),
):
    """Get a regulatory life table (CNSF 2000-I, CNSF 2013, or EMSSA 2009)."""
    try:
        return mortality_service.get_life_table_data(table_type, sex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/validation", response_model=ValidationResponse)
def get_validation(
    projection_year: int = Query(default=2040),
    table_type: str = Query(default="cnsf", pattern="^(cnsf|cnsf_2013|emssa)$"),
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Compare projected mortality against regulatory benchmark."""
    try:
        return mortality_service.get_validation(
            projection_year, table_type, sex=sex,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/graduation", response_model=GraduationResponse)
def get_graduation(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get raw vs graduated mortality rates with diagnostics."""
    return mortality_service.get_graduation_data(sex=sex)


@router.get("/surface", response_model=MortalitySurfaceResponse)
def get_surface(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get 2D log(mx) matrix for mortality surface visualization."""
    return mortality_service.get_surface_data(sex=sex)


@router.get("/diagnostics", response_model=LCDiagnosticsResponse)
def get_diagnostics(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get Lee-Carter goodness-of-fit diagnostics."""
    return mortality_service.get_diagnostics_data(sex=sex)
