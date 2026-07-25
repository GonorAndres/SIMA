"""Pydantic schemas for SCR-related endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SCRRequest(BaseModel):
    """Request to run the full SCR pipeline.

    Cross-field validation enforces two consistency rules beyond the
    individual field bounds:
      - The interest-rate down shock must not push the rate below zero
        (i.e. ``ir_shock_bps / 10_000 <= interest_rate``). The engine
        floors the down shock at a configurable positive value, but a
        request that is degenerate by construction should be rejected
        at the API boundary rather than silently floored.
      - ``portfolio_duration`` may be omitted (``None``); when omitted,
        the engine derives it from the portfolio. To make this
        expressible in a `float | None` Pydantic field without losing
        the OpenAPI schema, we accept ``ge=1.0`` only when a value is
        provided.
    """

    interest_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    sex: Literal["male", "female"] = Field(
        default="male", description="Sex for the regulatory mortality table (CNSF male/female)"
    )
    mortality_shock: float = Field(default=0.15, ge=0.0, le=1.0)
    longevity_shock: float = Field(default=0.20, ge=0.0, le=1.0)
    ir_shock_bps: int = Field(default=100, ge=1, le=500)
    cat_shock_factor: float = Field(default=1.35, ge=1.0, le=3.0)
    coc_rate: float = Field(default=0.06, ge=0.0, le=0.20)
    portfolio_duration: float | None = Field(
        default=None,
        ge=1.0,
        le=50.0,
        description="Average remaining duration (years). If None, the engine "
        "computes it from the portfolio (replaces the previous hardcoded 15.0).",
    )
    available_capital: float | None = Field(default=None, ge=0)
    # When True the mortality / longevity / catastrophe shocks are
    # calibrated from the fitted Lee-Carter k_t volatility rather than
    # the standard-formula defaults above.
    shocks_from_lee_carter: bool = Field(
        default=False,
        description="Calibrate mortality/longevity/cat shocks from the fitted "
        "Lee-Carter k_t volatility at 1-in-200 confidence, overriding "
        "the standard-formula defaults.",
    )

    @model_validator(mode="after")
    def _validate_shock_consistency(self) -> SCRRequest:
        # IR down shock feasibility: rate - shock_bps/10000 must remain
        # positive (the engine floors at 0.5%, but a request that needs
        # the floor is degenerate by construction).
        if self.interest_rate - self.ir_shock_bps / 10_000.0 < 0.0:
            raise ValueError(
                f"ir_shock_bps ({self.ir_shock_bps}) would push the down-shock "
                f"rate below zero at interest_rate={self.interest_rate}"
            )
        return self


class SCRComponentResult(BaseModel):
    """Result for a single SCR risk module."""

    bel_base: float
    bel_stressed: float
    scr: float
    shock: float | None = None


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
    diversification_pct: float | None = None


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


class LISFRiskModuleInfo(BaseModel):
    """Regulatory context for a single risk module."""

    module: str
    lisf_reference: str
    description_es: str
    description_en: str
    standard_shock: str
    shock_basis: str


class LISFComplianceResponse(BaseModel):
    """LISF/CUSF regulatory compliance mapping."""

    framework: str
    framework_description_es: str
    framework_description_en: str
    risk_modules: list[LISFRiskModuleInfo]
    correlation_matrix: dict[str, float]
    correlation_basis_es: str
    correlation_basis_en: str
    risk_margin_rate: float
    risk_margin_basis_es: str
    risk_margin_basis_en: str
    coverage: list[str]
    limitations: list[str]


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
    solvency: SolvencyResult | None = None
