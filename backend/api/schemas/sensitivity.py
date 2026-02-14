"""Pydantic schemas for sensitivity analysis endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional


class MortalityShockRequest(BaseModel):
    """Request for mortality shock sweep analysis."""
    age: int = Field(default=40, ge=20, le=70)
    sum_assured: float = Field(default=1_000_000, gt=0)
    product_type: str = Field(default="whole_life")
    factors: List[float] = Field(
        default=[-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30],
        description="Shock factors to apply to q_x",
    )
    term: Optional[int] = Field(default=20, ge=1)


class MortalityShockResponse(BaseModel):
    """Result of mortality shock sweep."""
    factors: List[float]
    premiums: List[float]
    base_premium: float
    pct_changes: List[float]
    age: int
    product_type: str


class CrossCountryEntry(BaseModel):
    """Single country comparison entry."""
    country: str
    drift: float
    explained_var: float
    sigma: float
    q60: float
    premium_age40: float


class CrossCountryProfile(BaseModel):
    """Parameter profile for one country."""
    country: str
    ages: List[int]
    values: List[float]


class CrossCountryKtProfile(BaseModel):
    """k_t trajectory for one country."""
    country: str
    years: List[int]
    kt: List[float]


class CrossCountryResponse(BaseModel):
    """Cross-country comparison results."""
    countries: List[CrossCountryEntry]
    kt_profiles: List[CrossCountryKtProfile]
    ax_profiles: List[CrossCountryProfile]
    bx_profiles: List[CrossCountryProfile]


class CovidPeriodData(BaseModel):
    """Lee-Carter data for one period."""
    drift: float
    sigma: float
    explained_var: float
    kt: List[float]
    years: List[int]


class CovidPremiumImpact(BaseModel):
    """Premium impact at one age."""
    age: int
    pre_covid: float
    full: float
    pct_change: float


class CovidComparisonResponse(BaseModel):
    """COVID-19 impact comparison."""
    pre_covid: CovidPeriodData
    full_period: CovidPeriodData
    premium_impact: List[CovidPremiumImpact]
