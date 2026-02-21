"""Pydantic schemas for pricing-related endpoints."""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Tuple


class PremiumRequest(BaseModel):
    """Request to calculate a net premium."""
    product_type: Literal["whole_life", "term", "endowment", "pure_endowment"] = Field(
        description="'whole_life', 'term', 'endowment', or 'pure_endowment'"
    )
    age: int = Field(ge=0, le=100, description="Issue age")
    sum_assured: float = Field(gt=0, le=1e12, description="Sum assured (face amount)")
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)
    term: Optional[int] = Field(
        default=None, ge=1,
        description="Term in years (required for term/endowment)"
    )


class PremiumResponse(BaseModel):
    """Calculated net premium."""
    product_type: str
    age: int
    sum_assured: float
    interest_rate: float
    term: Optional[int]
    annual_premium: float
    premium_rate: float


class ReserveRequest(BaseModel):
    """Request to calculate a reserve trajectory."""
    product_type: Literal["whole_life", "term", "endowment", "pure_endowment"] = Field(
        description="'whole_life', 'term', or 'endowment'"
    )
    age: int = Field(ge=0, le=100, description="Issue age")
    sum_assured: float = Field(gt=0, le=1e12)
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)
    term: Optional[int] = Field(default=None, ge=1)
    duration: Optional[int] = Field(
        default=None, ge=0,
        description="Specific duration to evaluate (if None, returns trajectory)"
    )


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
    term: Optional[int]
    annual_premium: float
    trajectory: List[ReservePoint]


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
    term: Optional[int] = Field(default=20, ge=1)
    rates: List[float] = Field(
        default=[0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
        max_length=50,
        description="Interest rates to evaluate"
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
    results: List[SensitivityPoint]
