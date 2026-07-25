"""Pydantic schemas for mortality-related endpoints."""

from pydantic import BaseModel, Field


class LifeTableRequest(BaseModel):
    """Request to generate a life table from regulatory data."""

    table_type: str = Field(default="cnsf", description="Regulatory table type: 'cnsf' or 'emssa'")
    sex: str = Field(default="male", description="'male' or 'female'")
    interest_rate: float = Field(default=0.05, ge=0.0, le=1.0)


class LifeTableResponse(BaseModel):
    """Life table data returned to the client."""

    ages: list[int]
    l_x: list[float]
    q_x: list[float]
    d_x: list[float]
    min_age: int
    max_age: int


class LeeCarterFitResponse(BaseModel):
    """Lee-Carter model parameters returned to the client."""

    ages: list[int]
    years: list[int]
    ax: list[float]
    bx: list[float]
    kt: list[float]
    explained_variance: float
    drift: float
    sigma: float
    sex: str
    validations: dict[str, bool]


class ProjectionResponse(BaseModel):
    """Projected mortality results."""

    projected_years: list[int]
    kt_central: list[float]
    drift: float
    sigma: float
    sex: str
    life_table: LifeTableResponse | None = None


class MortalityDataSummary(BaseModel):
    """Summary of loaded mortality data."""

    country: str
    sex: str
    age_range: list[int]
    year_range: list[int]
    shape: list[int]
    mx_min: float
    mx_max: float
    mx_mean: float


class GraduationResponse(BaseModel):
    """Graduation overlay data: raw vs graduated mortality rates."""

    ages: list[int]
    raw_mx: list[float]
    graduated_mx: list[float]
    residuals: list[float]
    roughness_raw: float
    roughness_graduated: float
    roughness_reduction: float
    lambda_param: float
    sex: str


class MortalitySurfaceResponse(BaseModel):
    """2D mortality surface data for 3D visualization."""

    ages: list[int]
    years: list[int]
    log_mx: list[list[float]]


class ValidationResponse(BaseModel):
    """Mortality validation: projected vs regulatory table comparison."""

    name: str
    rmse: float
    max_ratio: float
    min_ratio: float
    mean_ratio: float
    n_ages: int
    ages: list[int]
    qx_ratios: list[float]
    qx_differences: list[float]


class LCDiagnosticsResponse(BaseModel):
    """Lee-Carter goodness-of-fit diagnostics."""

    rmse: float
    max_abs_error: float
    mean_abs_error: float
    explained_variance: float
    residuals_sample: list[dict[str, float]]
