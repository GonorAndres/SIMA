"""Mortality data, Lee-Carter, and projection endpoints."""

from fastapi import APIRouter, Query

from backend.api.exception_handlers import safe_route
from backend.api.schemas.mortality import (
    GraduationResponse,
    LCDiagnosticsResponse,
    LeeCarterFitResponse,
    LifeTableResponse,
    MortalityDataSummary,
    MortalitySurfaceResponse,
    ProjectionResponse,
    ValidationResponse,
)
from backend.api.services import mortality_service

router = APIRouter(prefix="/mortality", tags=["mortality"])


@router.get("/data/summary", response_model=MortalityDataSummary)
@safe_route
def get_data_summary(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get summary of loaded mortality data (INEGI/CONAPO)."""
    return mortality_service.get_data_summary(sex=sex)


@router.get("/lee-carter", response_model=LeeCarterFitResponse)
@safe_route
def get_lee_carter(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get the fitted Lee-Carter model parameters (a_x, b_x, k_t)."""
    return mortality_service.get_lee_carter_params(sex=sex)


@router.get("/projection", response_model=ProjectionResponse)
@safe_route
def get_projection(
    horizon: int = Query(default=30, ge=1, le=100),
    projection_year: int = Query(default=2040),
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
) -> ProjectionResponse:
    """Get mortality projection with optional life table at a specific year."""
    return mortality_service.get_projection_data(
        horizon=horizon,
        projection_year=projection_year,
        sex=sex,
    )


@router.get("/life-table", response_model=LifeTableResponse)
@safe_route
def get_life_table(
    table_type: str = Query(default="cnsf", pattern="^(cnsf|cnsf_2013|emssa_97)$"),
    sex: str = Query(default="male", pattern="^(male|female)$"),
) -> LifeTableResponse:
    """Get a regulatory life table (CNSF 2000-I, CNSF M 2013 mixta, or EMSSAH/M-97)."""
    return mortality_service.get_life_table_data(table_type, sex)


@router.get("/validation", response_model=ValidationResponse)
@safe_route
def get_validation(
    projection_year: int = Query(default=2040),
    table_type: str = Query(default="cnsf", pattern="^(cnsf|cnsf_2013|emssa_97)$"),
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
) -> ValidationResponse:
    """Compare projected mortality against regulatory benchmark."""
    return mortality_service.get_validation(
        projection_year,
        table_type,
        sex=sex,
    )


@router.get("/graduation", response_model=GraduationResponse)
@safe_route
def get_graduation(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get raw vs graduated mortality rates with diagnostics."""
    return mortality_service.get_graduation_data(sex=sex)


@router.get("/surface", response_model=MortalitySurfaceResponse)
@safe_route
def get_surface(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get 2D log(mx) matrix for mortality surface visualization."""
    return mortality_service.get_surface_data(sex=sex)


@router.get("/diagnostics", response_model=LCDiagnosticsResponse)
@safe_route
def get_diagnostics(
    sex: str = Query(default="unisex", pattern="^(male|female|unisex)$"),
):
    """Get Lee-Carter goodness-of-fit diagnostics."""
    return mortality_service.get_diagnostics_data(sex=sex)
