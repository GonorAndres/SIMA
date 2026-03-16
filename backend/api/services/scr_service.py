"""
SCR service: bridges API requests to engine modules a11-a12.
"""

import sys
from pathlib import Path
from typing import Optional

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.engine.a11_portfolio import Policy, Portfolio, create_sample_portfolio
from backend.engine.a12_scr import run_full_scr
from backend.api.services.precomputed import get_regulatory_lt


# Module-level portfolio (can be modified via API).
# NOTE: This is global mutable state shared across all requests -- intentional
# for this demo/portfolio project. In production, use per-session or per-user
# state (e.g., database-backed or session-scoped dependency injection).
_portfolio: Portfolio | None = None


def _ensure_portfolio() -> Portfolio:
    """Get or create the portfolio."""
    global _portfolio
    if _portfolio is None:
        _portfolio = create_sample_portfolio()
    return _portfolio


def reset_portfolio() -> Portfolio:
    """Reset to the sample portfolio."""
    global _portfolio
    _portfolio = create_sample_portfolio()
    return _portfolio


def get_portfolio() -> Portfolio:
    """Get the current portfolio."""
    return _ensure_portfolio()


def add_policy(
    policy_id: str,
    product_type: str,
    issue_age: int,
    sum_assured: float = 0.0,
    annual_pension: float = 0.0,
    term: Optional[int] = None,
    duration: int = 0,
) -> Policy:
    """Add a policy to the portfolio."""
    portfolio = _ensure_portfolio()
    policy = Policy(
        policy_id=policy_id,
        product_type=product_type,
        issue_age=issue_age,
        SA=sum_assured,
        annual_pension=annual_pension,
        n=term,
        duration=duration,
    )
    portfolio.policies.append(policy)
    return policy


def compute_portfolio_bel(interest_rate: float = 0.05) -> dict:
    """Compute BEL for the entire portfolio."""
    portfolio = _ensure_portfolio()
    lt = get_regulatory_lt("cnsf", "male")

    bel_by_type = portfolio.compute_bel_by_type(lt, interest_rate)
    breakdown = portfolio.compute_bel_breakdown(lt, interest_rate)

    return {
        "total_bel": bel_by_type["total_bel"],
        "death_bel": bel_by_type["death_bel"],
        "annuity_bel": bel_by_type["annuity_bel"],
        "n_policies": len(portfolio),
        "n_death": len(portfolio.death_products),
        "n_annuity": len(portfolio.annuity_products),
        "breakdown": breakdown,
    }


def get_lisf_compliance() -> dict:
    """Return LISF/CUSF regulatory compliance mapping for SCR computation."""
    return {
        "framework": "LISF/CUSF (Ley de Instituciones de Seguros y Fianzas / Circular Única de Seguros y Fianzas)",
        "framework_description_es": (
            "El RCS (Requerimiento de Capital de Solvencia) es el capital que una aseguradora "
            "debe mantener para absorber pérdidas con un nivel de confianza del 99.5% en un "
            "horizonte de un año. México adopta el marco de Solvencia II europeo a través de "
            "la LISF (2013) y la CUSF, supervisado por la CNSF."
        ),
        "framework_description_en": (
            "The SCR (Solvency Capital Requirement, RCS in Spanish) is the capital an insurer "
            "must hold to absorb losses at a 99.5% confidence level over a one-year horizon. "
            "Mexico adopted the European Solvency II framework through LISF (2013) and CUSF, "
            "supervised by the CNSF (Comisión Nacional de Seguros y Fianzas)."
        ),
        "risk_modules": [
            {
                "module": "mortality",
                "lisf_reference": "CUSF Título 5, Capítulo 1, Sección II - Riesgo de mortalidad",
                "description_es": (
                    "Incremento permanente del 15% en las tasas de mortalidad q_x. "
                    "Afecta solo productos de muerte (temporal, vitalicio, dotal). "
                    "Las rentas vitalicias se benefician de mayor mortalidad."
                ),
                "description_en": (
                    "Permanent 15% increase in mortality rates q_x. "
                    "Affects only death products (term, whole life, endowment). "
                    "Annuities benefit from higher mortality."
                ),
                "standard_shock": "+15% q_x (permanent)",
                "shock_basis": "Solvency II Article 105(3)(a), CUSF Anexo 5.1.2",
            },
            {
                "module": "longevity",
                "lisf_reference": "CUSF Título 5, Capítulo 1, Sección II - Riesgo de longevidad",
                "description_es": (
                    "Disminución permanente del 20% en las tasas de mortalidad q_x. "
                    "Afecta solo rentas vitalicias y pensiones. "
                    "Los productos de muerte se benefician de menor mortalidad."
                ),
                "description_en": (
                    "Permanent 20% decrease in mortality rates q_x. "
                    "Affects only annuities and pensions. "
                    "Death products benefit from lower mortality."
                ),
                "standard_shock": "-20% q_x (permanent)",
                "shock_basis": "Solvency II Article 105(3)(b), CUSF Anexo 5.1.2",
            },
            {
                "module": "interest_rate",
                "lisf_reference": "CUSF Título 5, Capítulo 1, Sección I - Riesgo de mercado (tasas de interés)",
                "description_es": (
                    "Desplazamiento paralelo de +/- 100 puntos base en la curva de rendimientos. "
                    "Afecta todos los productos porque cada flujo futuro se descuenta. "
                    "El escenario adverso es típicamente la baja de tasas: menor descuento "
                    "significa mayor valor presente de obligaciones."
                ),
                "description_en": (
                    "Parallel shift of +/- 100 basis points in the yield curve. "
                    "Affects all products because every future cash flow is discounted. "
                    "The adverse scenario is typically the down shock: lower discount "
                    "means higher present value of liabilities."
                ),
                "standard_shock": "+/- 100 bps parallel shift",
                "shock_basis": "Solvency II Article 105(5)(a), CUSF Anexo 5.1.1",
            },
            {
                "module": "catastrophe",
                "lisf_reference": "CUSF Título 5, Capítulo 1, Sección II - Riesgo de catástrofe de vida",
                "description_es": (
                    "Pico de mortalidad de un solo año (+35%), no permanente. "
                    "Calibrado con datos COVID-19 mexicanos (INEGI/CONAPO): "
                    "el k_t de Lee-Carter revirtió ~6.76 unidades por encima de la tendencia. "
                    "Solo afecta productos de muerte en el primer año."
                ),
                "description_en": (
                    "One-year mortality spike (+35%), not permanent. "
                    "Calibrated from Mexican COVID-19 data (INEGI/CONAPO): "
                    "Lee-Carter k_t reversed ~6.76 units above trend. "
                    "Only affects death products in the first year."
                ),
                "standard_shock": "+35% one-year mortality spike (COVID-calibrated)",
                "shock_basis": "Solvency II Article 105(3)(f), adapted with INEGI/CONAPO COVID data",
            },
        ],
        "correlation_matrix": {
            "mortality_longevity": -0.25,
            "mortality_catastrophe": 0.25,
            "longevity_catastrophe": 0.00,
            "life_market": 0.25,
        },
        "correlation_basis_es": (
            "Solvencia II Artículo 136, Reglamento Delegado Anexo IV. "
            "La correlación mortalidad-longevidad es negativa (-0.25) porque son opuestos naturales: "
            "una pandemia incrementa siniestros por muerte pero reduce obligaciones de rentas. "
            "Esta cobertura natural genera un beneficio por diversificación de ~14.4%."
        ),
        "correlation_basis_en": (
            "Solvency II Article 136, Delegated Regulation Annex IV. "
            "Mortality-longevity correlation is negative (-0.25) because they are natural opposites: "
            "a pandemic increases death claims but decreases annuity obligations. "
            "This natural hedge yields a diversification benefit of ~14.4%."
        ),
        "risk_margin_rate": 0.06,
        "risk_margin_basis_es": (
            "Tasa de Costo de Capital del 6% según Solvencia II Artículo 37(1). "
            "MdR = CoC * RCS * factor_anualidad. Representa el precio que otra aseguradora "
            "cobraría por asumir los requerimientos de capital del portafolio."
        ),
        "risk_margin_basis_en": (
            "Cost-of-Capital rate of 6% per Solvency II Article 37(1). "
            "MdR = CoC * SCR * annuity_factor. Represents the price another insurer would "
            "charge to take over the portfolio's capital requirements."
        ),
        "coverage": [
            "Life underwriting risk (4 sub-modules: mortality, longevity, interest rate, catastrophe)",
            "Correlation-based aggregation (life module + market risk)",
            "Risk margin via Cost-of-Capital method",
            "Technical provisions (BEL + risk margin)",
            "Solvency ratio computation",
            "COVID-calibrated catastrophe scenario using Mexican demographic data",
        ],
        "limitations": [
            "Simplified interest rate shock (parallel shift only, no term structure)",
            "No lapse risk, expense risk, or revision risk sub-modules",
            "No operational risk module (separate under Solvency II)",
            "Risk margin uses simplified constant-SCR approach, not full run-off projection",
            "Single life table for all policies (no policy-level underwriting adjustments)",
            "No look-through approach for unit-linked products",
        ],
    }


def run_scr(
    interest_rate: float = 0.05,
    mortality_shock: float = 0.15,
    longevity_shock: float = 0.20,
    ir_shock_bps: int = 100,
    cat_shock_factor: float = 1.35,
    coc_rate: float = 0.06,
    portfolio_duration: float = 15.0,
    available_capital: Optional[float] = None,
) -> dict:
    """Run the full SCR pipeline."""
    portfolio = _ensure_portfolio()
    lt = get_regulatory_lt("cnsf", "male")

    result = run_full_scr(
        portfolio=portfolio,
        base_lt=lt,
        interest_rate=interest_rate,
        mortality_shock=mortality_shock,
        longevity_shock=longevity_shock,
        ir_shock_bps=ir_shock_bps,
        cat_shock_factor=cat_shock_factor,
        coc_rate=coc_rate,
        portfolio_duration=portfolio_duration,
        available_capital=available_capital,
    )

    # Reshape into API response format
    response = {
        "bel_base": result["bel_base"],
        "bel_death": result["bel_breakdown"]["death_bel"],
        "bel_annuity": result["bel_breakdown"]["annuity_bel"],
        "mortality": {
            "bel_base": result["mortality"]["bel_base"],
            "bel_stressed": result["mortality"]["bel_stressed"],
            "scr": result["mortality"]["scr"],
            "shock": result["mortality"]["shock"],
        },
        "longevity": {
            "bel_base": result["longevity"]["bel_base"],
            "bel_stressed": result["longevity"]["bel_stressed"],
            "scr": result["longevity"]["scr"],
            "shock": result["longevity"]["shock"],
        },
        "interest_rate": {
            "bel_base": result["interest_rate"]["bel_base"],
            "bel_up": result["interest_rate"]["bel_up"],
            "bel_down": result["interest_rate"]["bel_down"],
            "scr": result["interest_rate"]["scr"],
            "rate_up": result["interest_rate"]["rate_up"],
            "rate_down": result["interest_rate"]["rate_down"],
        },
        "catastrophe": {
            "scr": result["catastrophe"]["scr"],
            "cat_shock_factor": result["catastrophe"]["cat_shock_factor"],
        },
        "life_aggregation": {
            "scr_aggregated": result["life_aggregation"]["scr_life"],
            "sum_individual": result["life_aggregation"]["sum_individual"],
            "diversification_benefit": result["life_aggregation"]["diversification_benefit"],
            "diversification_pct": result["life_aggregation"]["diversification_pct"],
        },
        "total_aggregation": {
            "scr_aggregated": result["total_aggregation"]["scr_total"],
            "sum_individual": result["total_aggregation"]["sum_individual"],
            "diversification_benefit": result["total_aggregation"]["diversification_benefit"],
            "diversification_pct": (
                result["total_aggregation"]["diversification_benefit"]
                / result["total_aggregation"]["sum_individual"] * 100
                if result["total_aggregation"]["sum_individual"] > 0
                else 0.0
            ),
        },
        "risk_margin": {
            "risk_margin": result["risk_margin"]["risk_margin"],
            "coc_rate": result["risk_margin"]["coc_rate"],
            "duration": result["risk_margin"]["duration"],
            "annuity_factor": result["risk_margin"]["annuity_factor"],
        },
        "technical_provisions": result["technical_provisions"],
    }

    if result["solvency"] is not None:
        response["solvency"] = {
            "ratio": result["solvency"]["ratio"],
            "ratio_pct": result["solvency"]["ratio_pct"],
            "available_capital": result["solvency"]["available_capital"],
            "scr_total": result["solvency"]["scr_total"],
            "is_solvent": result["solvency"]["is_solvent"],
        }
    else:
        response["solvency"] = None

    return response
