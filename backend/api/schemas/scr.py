"""Pydantic schemas for SCR-related endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class SCRRequest(BaseModel):
    """Request to run the full SCR pipeline."""
    interest_rate: float = Field(default=0.05, ge=0.001, le=1.0)
    mortality_shock: float = Field(default=0.15, ge=0.0, le=1.0)
    longevity_shock: float = Field(default=0.20, ge=0.0, le=1.0)
    ir_shock_bps: int = Field(default=100, ge=1, le=500)
    cat_shock_factor: float = Field(default=1.35, ge=1.0, le=3.0)
    coc_rate: float = Field(default=0.06, ge=0.0, le=0.20)
    portfolio_duration: float = Field(default=15.0, ge=1.0, le=50.0)
    available_capital: Optional[float] = Field(default=None, ge=0)


class SCRComponentResult(BaseModel):
    """Result for a single SCR risk module."""
    bel_base: float
    bel_stressed: float
    scr: float
    shock: Optional[float] = None


class SCRInterestRateResult(BaseModel):
    """Result for interest rate SCR."""
    bel_base: float
    bel_up: float
    bel_down: float
    scr: float
    rate_up: float
    rate_down: float


class SCRCatastropheResult(BaseModel):
    """Result for catastrophe SCR."""
    scr: float
    cat_shock_factor: float


class SCRAggregationResult(BaseModel):
    """Aggregation result (life or total)."""
    scr_aggregated: float
    sum_individual: float
    diversification_benefit: float
    diversification_pct: Optional[float] = None


class RiskMarginResult(BaseModel):
    """Risk margin computation result."""
    risk_margin: float
    coc_rate: float
    duration: float
    annuity_factor: float


class SolvencyResult(BaseModel):
    """Solvency ratio result."""
    ratio: float
    ratio_pct: float
    available_capital: float
    scr_total: float
    is_solvent: bool


class SCRResponse(BaseModel):
    """Full SCR pipeline response."""
    bel_base: float
    bel_death: float
    bel_annuity: float
    mortality: SCRComponentResult
    longevity: SCRComponentResult
    interest_rate: SCRInterestRateResult
    catastrophe: SCRCatastropheResult
    life_aggregation: SCRAggregationResult
    total_aggregation: SCRAggregationResult
    risk_margin: RiskMarginResult
    technical_provisions: float
    solvency: Optional[SolvencyResult] = None
