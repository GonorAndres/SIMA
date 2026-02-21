"""Pydantic schemas for mortality-related endpoints."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class LifeTableRequest(BaseModel):
    """Request to generate a life table from regulatory data."""
    table_type: str = Field(
        default="cnsf",
        description="Regulatory table type: 'cnsf' or 'emssa'"
    )
    sex: str = Field(default="male", description="'male' or 'female'")
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)


class LifeTableResponse(BaseModel):
    """Life table data returned to the client."""
    ages: List[int]
    l_x: List[float]
    q_x: List[float]
    d_x: List[float]
    min_age: int
    max_age: int


class LeeCarterFitRequest(BaseModel):
    """Request to fit a Lee-Carter model on preloaded mock data."""
    graduate: bool = Field(
        default=True,
        description="Apply Whittaker-Henderson graduation before fitting"
    )
    lambda_param: float = Field(
        default=1e5,
        description="Smoothing parameter for graduation"
    )
    reestimate_kt: bool = Field(
        default=False,
        description="Re-estimate k_t to match observed deaths"
    )


class LeeCarterFitResponse(BaseModel):
    """Lee-Carter model parameters returned to the client."""
    ages: List[int]
    years: List[int]
    ax: List[float]
    bx: List[float]
    kt: List[float]
    explained_variance: float
    drift: float
    sigma: float
    validations: Dict[str, bool]


class ProjectionRequest(BaseModel):
    """Request to project mortality forward."""
    horizon: int = Field(default=30, ge=1, le=100)
    projection_year: int = Field(
        default=2040,
        description="Specific year for life table extraction"
    )


class ProjectionResponse(BaseModel):
    """Projected mortality results."""
    projected_years: List[int]
    kt_central: List[float]
    drift: float
    sigma: float
    life_table: Optional[LifeTableResponse] = None


class MortalityDataSummary(BaseModel):
    """Summary of loaded mortality data."""
    country: str
    sex: str
    age_range: List[int]
    year_range: List[int]
    shape: List[int]
    mx_min: float
    mx_max: float
    mx_mean: float


class GraduationResponse(BaseModel):
    """Graduation overlay data: raw vs graduated mortality rates."""
    ages: List[int]
    raw_mx: List[float]
    graduated_mx: List[float]
    residuals: List[float]
    roughness_raw: float
    roughness_graduated: float
    roughness_reduction: float
    lambda_param: float


class MortalitySurfaceResponse(BaseModel):
    """2D mortality surface data for 3D visualization."""
    ages: List[int]
    years: List[int]
    log_mx: List[List[float]]


class ValidationResponse(BaseModel):
    """Mortality validation: projected vs regulatory table comparison."""
    name: str
    rmse: float
    max_ratio: float
    min_ratio: float
    mean_ratio: float
    n_ages: int
    ages: List[int]
    qx_ratios: List[float]
    qx_differences: List[float]


class LCDiagnosticsResponse(BaseModel):
    """Lee-Carter goodness-of-fit diagnostics."""
    rmse: float
    max_abs_error: float
    mean_abs_error: float
    explained_variance: float
    residuals_sample: List[Dict[str, float]]
