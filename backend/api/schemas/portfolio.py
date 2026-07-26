"""Pydantic schemas for portfolio-related endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PolicyCreate(BaseModel):
    """
    Schema for creating a policy.

    Cross-field validation mirrors the engine's Policy constructor:
      - `term` is required for `term` / `endowment`
      - `duration <= term` for `term` / `endowment`
      - `sum_assured > 0` for death products
      - `annual_pension > 0` for annuities
    """

    policy_id: str = Field(min_length=1, max_length=64)
    product_type: Literal["whole_life", "term", "endowment", "annuity"] = Field(
        description="'whole_life', 'term', 'endowment', or 'annuity'"
    )
    issue_age: int = Field(ge=0, le=100)
    sum_assured: float = Field(default=0.0, ge=0)
    annual_pension: float = Field(default=0.0, ge=0)
    annual_premium: float | None = Field(
        default=None,
        ge=0,
        description="Contractual annual premium fixed at issue. If omitted, "
        "the engine derives it from the base issue basis.",
    )
    term: int | None = Field(default=None, ge=1, le=110)
    duration: int = Field(default=0, ge=0, le=110)

    @model_validator(mode="after")
    def _validate_policy_cross_fields(self) -> PolicyCreate:
        # Finite-horizon products require a term length.
        if self.product_type in ("term", "endowment") and self.term is None:
            raise ValueError(f"{self.product_type} requires a term length")
        # Duration must not exceed term for finite-horizon products. (An
        # expired policy is constructible in the engine but, at the API
        # boundary, the more useful contract is to reject duration > term
        # rather than silently create an expired policy.)
        if self.term is not None and self.duration > self.term:
            raise ValueError(f"duration ({self.duration}) cannot exceed term ({self.term})")
        # Death products need a positive sum assured to be meaningful.
        if self.product_type in ("whole_life", "term", "endowment") and self.sum_assured <= 0:
            raise ValueError(
                f"sum_assured must be > 0 for death product "
                f"{self.product_type!r} (got {self.sum_assured})"
            )
        # Annuities need a positive annual pension.
        if self.product_type == "annuity" and self.annual_pension <= 0:
            raise ValueError(
                f"annual_pension must be > 0 for annuity product (got {self.annual_pension})"
            )
        return self


class PolicyResponse(BaseModel):
    """Response for a single policy."""

    policy_id: str
    product_type: str
    issue_age: int
    attained_age: int
    sum_assured: float
    annual_pension: float
    annual_premium: float | None
    term: int | None
    duration: int
    is_death_product: bool
    is_annuity: bool


class BELBreakdownItem(BaseModel):
    """BEL for a single policy."""

    policy_id: str
    product_type: str
    issue_age: int
    attained_age: int
    duration: int
    bel: float
    sum_assured: float | None = None
    annual_pension: float | None = None


class PortfolioBELRequest(BaseModel):
    """Request to compute portfolio BEL."""

    interest_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    sex: Literal["male", "female"] = Field(
        default="male", description="Sex for the regulatory mortality table (CNSF male/female)"
    )


class PortfolioBELResponse(BaseModel):
    """Portfolio BEL computation result."""

    total_bel: float
    death_bel: float
    annuity_bel: float
    n_policies: int
    n_death: int
    n_annuity: int
    breakdown: list[BELBreakdownItem]


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary without BEL (no computation needed)."""

    n_policies: int
    n_death: int
    n_annuity: int
    total_sum_assured: float
    total_annual_pension: float
    policies: list[PolicyResponse]
