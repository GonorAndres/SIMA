"""Pydantic schemas for portfolio-related endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""
    policy_id: str
    product_type: str = Field(
        description="'whole_life', 'term', 'endowment', or 'annuity'"
    )
    issue_age: int = Field(ge=0, le=100)
    sum_assured: float = Field(default=0.0, ge=0)
    annual_pension: float = Field(default=0.0, ge=0)
    term: Optional[int] = Field(default=None, ge=1)
    duration: int = Field(default=0, ge=0)


class PolicyResponse(BaseModel):
    """Response for a single policy."""
    policy_id: str
    product_type: str
    issue_age: int
    attained_age: int
    sum_assured: float
    annual_pension: float
    term: Optional[int]
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
    sum_assured: Optional[float] = None
    annual_pension: Optional[float] = None


class PortfolioBELRequest(BaseModel):
    """Request to compute portfolio BEL."""
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)


class PortfolioBELResponse(BaseModel):
    """Portfolio BEL computation result."""
    total_bel: float
    death_bel: float
    annuity_bel: float
    n_policies: int
    n_death: int
    n_annuity: int
    breakdown: List[BELBreakdownItem]


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary without BEL (no computation needed)."""
    n_policies: int
    n_death: int
    n_annuity: int
    total_sum_assured: float
    total_annual_pension: float
    policies: List[PolicyResponse]
