"""Pydantic schemas for sensitivity analysis endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class MortalityShockRequest(BaseModel):
    """Request for mortality shock sweep analysis."""

    age: int = Field(default=40, ge=20, le=70)
    sum_assured: float = Field(default=1_000_000, gt=0, le=1e12)
    product_type: Literal["whole_life", "term", "endowment"] = Field(default="whole_life")
    factors: list[float] = Field(
        default=[-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30],
        max_length=50,
        description="Shock factors to apply to q_x",
    )
    term: int | None = Field(default=20, ge=1)
    sex: Literal["male", "female", "unisex"] = Field(
        default="unisex", description="Sex for base mortality table"
    )


class MortalityShockResponse(BaseModel):
    """Result of mortality shock sweep."""

    factors: list[float]
    premiums: list[float]
    base_premium: float
    pct_changes: list[float]
    age: int
    product_type: str
    sex: str


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
    ages: list[int]
    values: list[float]


class CrossCountryKtProfile(BaseModel):
    """k_t trajectory for one country."""

    country: str
    years: list[int]
    kt: list[float]


class CrossCountryResponse(BaseModel):
    """Cross-country comparison results."""

    countries: list[CrossCountryEntry]
    kt_profiles: list[CrossCountryKtProfile]
    ax_profiles: list[CrossCountryProfile]
    bx_profiles: list[CrossCountryProfile]


class CovidPeriodData(BaseModel):
    """Lee-Carter data for one period."""

    drift: float
    sigma: float
    explained_var: float
    kt: list[float]
    years: list[int]


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
    premium_impact: list[CovidPremiumImpact]
