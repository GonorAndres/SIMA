"""Pydantic schemas for pricing-related endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PremiumRequest(BaseModel):
    """Request to calculate a net premium.

    Cross-field validation: ``term`` is required for ``term`` / ``endowment``
    / ``pure_endowment`` products (the engine rejects ``None`` for those).
    """

    product_type: Literal["whole_life", "term", "endowment", "pure_endowment"] = Field(
        description="'whole_life', 'term', 'endowment', or 'pure_endowment'"
    )
    age: int = Field(ge=0, le=100, description="Issue age")
    sum_assured: float = Field(gt=0, le=1e12, description="Sum assured (face amount)")
    interest_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    term: int | None = Field(
        default=None, ge=1, le=110, description="Term in years (required for term/endowment)"
    )
    sex: Literal["male", "female", "unisex"] = Field(
        default="male", description="Sex for mortality table selection"
    )

    @model_validator(mode="after")
    def _validate_term_required(self) -> PremiumRequest:
        if self.product_type in ("term", "endowment", "pure_endowment") and self.term is None:
            raise ValueError(f"{self.product_type} requires a term length")
        return self


class PremiumResponse(BaseModel):
    """Calculated net premium."""

    product_type: str
    age: int
    sum_assured: float
    interest_rate: float
    term: int | None
    sex: str
    annual_premium: float
    premium_rate: float


class ReserveRequest(BaseModel):
    """Request to calculate a reserve trajectory.

    Cross-field validation: ``term`` is required for finite-horizon products,
    and ``duration`` (when provided) must not exceed ``term``.
    """

    product_type: Literal["whole_life", "term", "endowment", "pure_endowment"] = Field(
        description="'whole_life', 'term', or 'endowment'"
    )
    age: int = Field(ge=0, le=100, description="Issue age")
    sum_assured: float = Field(gt=0, le=1e12)
    interest_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    term: int | None = Field(default=None, ge=1, le=110)
    duration: int | None = Field(
        default=None,
        ge=0,
        le=110,
        description="Specific duration to evaluate (if None, returns trajectory)",
    )
    sex: Literal["male", "female", "unisex"] = Field(
        default="male", description="Sex for mortality table selection"
    )

    @model_validator(mode="after")
    def _validate_term_and_duration(self) -> ReserveRequest:
        if self.product_type in ("term", "endowment", "pure_endowment") and self.term is None:
            raise ValueError(f"{self.product_type} requires a term length")
        if self.term is not None and self.duration is not None and self.duration > self.term:
            raise ValueError(f"duration ({self.duration}) cannot exceed term ({self.term})")
        return self


class ReservePoint(BaseModel):
    """A single (duration, reserve) point."""

    duration: int
    age: int
    reserve: float


class ReserveResponse(BaseModel):
    """Reserve calculation result."""

    product_type: str
    issue_age: int
    sum_assured: float
    interest_rate: float
    term: int | None
    sex: str
    annual_premium: float
    trajectory: list[ReservePoint]


class CommutationResponse(BaseModel):
    """Commutation function values at a specific age."""

    age: int
    D_x: float
    N_x: float
    C_x: float
    M_x: float
    A_x: float
    a_due_x: float


class SensitivityRequest(BaseModel):
    """Request for interest rate sensitivity analysis."""

    product_type: Literal["whole_life", "term", "endowment"] = Field(default="whole_life")
    age: int = Field(default=40, ge=0, le=100)
    sum_assured: float = Field(default=1_000_000, gt=0, le=1e12)
    term: int | None = Field(default=20, ge=1)
    rates: list[float] = Field(
        default=[0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
        max_length=50,
        description="Interest rates to evaluate",
    )
    sex: Literal["male", "female", "unisex"] = Field(
        default="male", description="Sex for mortality table selection"
    )


class SensitivityPoint(BaseModel):
    """Premium at a specific interest rate."""

    interest_rate: float
    annual_premium: float


class SensitivityResponse(BaseModel):
    """Interest rate sensitivity results."""

    product_type: str
    age: int
    sum_assured: float
    results: list[SensitivityPoint]


class CrossCountryPremiumEntry(BaseModel):
    """Premium for a single country."""

    country: str
    annual_premium: float
    premium_rate: float
    drift: float
    explained_var: float


class CrossCountryPremiumResponse(BaseModel):
    """Cross-country premium comparison."""

    product_type: str
    age: int
    sum_assured: float
    interest_rate: float
    term: int | None
    sex: str
    entries: list[CrossCountryPremiumEntry]
