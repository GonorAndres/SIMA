"""
SCR service: bridges API requests to engine modules a11-a12.
"""

import logging
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.api.services.precomputed import get_lee_carter, get_regulatory_lt
from backend.engine.a11_portfolio import Policy, Portfolio, create_sample_portfolio
from backend.engine.a12_scr import run_full_scr
from backend.engine.exceptions import ActuarialValidationError

logger = logging.getLogger(__name__)

# Hard cap on the shared demo portfolio. POST /portfolio/policy is anonymous
# and the portfolio is module-level state, so without a cap any caller can grow
# it without bound. Every SCR run holds _portfolio_lock for the whole
# computation and its cost grows with the policy count, so an inflated
# portfolio degrades the endpoint for every other user until the process
# restarts. 100 is far above what the demo UI ever creates (the sample
# portfolio has a handful of policies).
MAX_PORTFOLIO_POLICIES = 100

# Portfolios are per-session, not global.
#
# They used to be one module-level Portfolio shared by every caller, which meant
# two people with the demo open at once mutated each other's portfolio: one
# adding a policy moved the other's BEL and SCR mid-presentation. The lock below
# prevented *corruption* but never gave callers separate state.
#
# Sessions are keyed by an opaque id the API sets as a cookie (see
# routers/dependencies.py). Callers that send no id -- the test suite, curl,
# anything unauthenticated -- share DEFAULT_SESSION, which preserves the old
# single-portfolio behaviour for them.
#
# Two bounds keep anonymous callers from growing this without limit: entries
# expire after SESSION_TTL_SECONDS of inactivity, and the map is capped at
# MAX_SESSIONS with least-recently-used eviction.
#
# CAVEAT: this state is per-process. Cloud Run may run several instances
# without sticky sessions, so a caller can land on an instance that has never
# seen their session and get the sample portfolio back. Fixing that properly
# means moving the portfolio out of the process (client-owned or a datastore),
# which is a larger change than this one; documented rather than hidden.
DEFAULT_SESSION = "__default__"
SESSION_TTL_SECONDS = 60 * 60
MAX_SESSIONS = 500

# A reentrant lock guards every read-modify-write so concurrent
# POST /portfolio/policy and POST /scr/compute callers cannot interleave and
# corrupt a policies list. BEL/SCR reads also acquire it for a consistent
# snapshot.
_portfolios: OrderedDict[str, Portfolio] = OrderedDict()
_session_seen: dict[str, float] = {}
_portfolio_lock = threading.RLock()


def _sweep_sessions(now: float) -> None:
    """Drop expired sessions, then LRU-evict down to the cap. Caller holds the lock."""
    expired = [
        sid
        for sid, seen in _session_seen.items()
        if sid != DEFAULT_SESSION and now - seen > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _portfolios.pop(sid, None)
        _session_seen.pop(sid, None)

    while len(_portfolios) > MAX_SESSIONS:
        oldest, _ = _portfolios.popitem(last=False)
        _session_seen.pop(oldest, None)
        if oldest == DEFAULT_SESSION:  # never evict the shared fallback
            _portfolios[DEFAULT_SESSION] = create_sample_portfolio()
            _session_seen[DEFAULT_SESSION] = now


def _ensure_portfolio(session_id: str | None = None) -> Portfolio:
    """Get or create this session's portfolio (thread-safe)."""
    sid = session_id or DEFAULT_SESSION
    with _portfolio_lock:
        now = time.monotonic()
        _sweep_sessions(now)
        if sid not in _portfolios:
            _portfolios[sid] = create_sample_portfolio()
        else:
            _portfolios.move_to_end(sid)
        _session_seen[sid] = now
        return _portfolios[sid]


def reset_portfolio(session_id: str | None = None) -> Portfolio:
    """Reset this session to the sample portfolio (thread-safe)."""
    sid = session_id or DEFAULT_SESSION
    with _portfolio_lock:
        _portfolios[sid] = create_sample_portfolio()
        _portfolios.move_to_end(sid)
        _session_seen[sid] = time.monotonic()
        return _portfolios[sid]


def get_portfolio(session_id: str | None = None) -> Portfolio:
    """Get this session's portfolio (thread-safe snapshot of the reference)."""
    return _ensure_portfolio(session_id)


def add_policy(
    policy_id: str,
    product_type: str,
    issue_age: int,
    sum_assured: float = 0.0,
    annual_pension: float = 0.0,
    annual_premium: float | None = None,
    term: int | None = None,
    duration: int = 0,
    session_id: str | None = None,
) -> Policy:
    """Add a policy to this session's portfolio (thread-safe)."""
    with _portfolio_lock:
        portfolio = _ensure_portfolio(session_id)
        # Checked inside the lock so concurrent adds cannot both pass the cap.
        if len(portfolio.policies) >= MAX_PORTFOLIO_POLICIES:
            raise ActuarialValidationError(
                f"Portfolio is full: {MAX_PORTFOLIO_POLICIES} policies is the maximum "
                f"for a demo portfolio. POST /api/portfolio/reset to start over.",
                field="portfolio_size",
                constraint=f"len(portfolio) < {MAX_PORTFOLIO_POLICIES}",
            )
        policy = Policy(
            policy_id=policy_id,
            product_type=product_type,
            issue_age=issue_age,
            SA=sum_assured,
            annual_pension=annual_pension,
            annual_premium=annual_premium,
            n=term,
            duration=duration,
        )
        # Portfolio construction enforces unique policy_id; appending a
        # duplicate would only surface the conflict on the next BEL read,
        # so re-check here for an immediate, actionable 422.
        if any(p.policy_id == policy_id for p in portfolio.policies):
            raise ActuarialValidationError(
                f"policy_id {policy_id!r} already exists in the portfolio",
                field="policy_id",
                constraint="policy_id unique within a Portfolio",
            )
        portfolio.policies.append(policy)
        return policy


def compute_portfolio_bel(
    interest_rate: float = 0.05,
    sex: str = "male",
    session_id: str | None = None,
) -> dict:
    """Compute BEL for this session's portfolio (thread-safe read)."""
    with _portfolio_lock:
        portfolio = _ensure_portfolio(session_id)
        lt = get_regulatory_lt("cnsf", sex)

        bel_by_type = portfolio.compute_bel_by_type(lt, interest_rate)
        breakdown = portfolio.compute_bel_breakdown(lt, interest_rate)

    # Audit-grade log: BEL computation inputs are recoverable from logs.
    logger.info(
        "BEL/compute port_size=%d rate=%.4f sex=%s -> total=%.2f",
        len(portfolio),
        interest_rate,
        sex,
        bel_by_type["total_bel"],
    )

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
                "standard_shock_es": "+15% q_x (permanente)",
                "standard_shock_en": "+15% q_x (permanent)",
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
                "standard_shock_es": "-20% q_x (permanente)",
                "standard_shock_en": "-20% q_x (permanent)",
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
                "standard_shock_es": "Desplazamiento paralelo +/- 100 pb",
                "standard_shock_en": "+/- 100 bps parallel shift",
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
                "standard_shock_es": "+35% de mortalidad a un año (calibrado con COVID)",
                "standard_shock_en": "+35% one-year mortality spike (COVID-calibrated)",
                "shock_basis": "Solvency II Article 105(3)(f), adapted with INEGI/CONAPO COVID data",
            },
        ],
        "correlation_matrix": {
            "mortality_longevity": -0.25,
            "mortality_catastrophe": 0.25,
            "longevity_catastrophe": 0.00,
            "life_market": 0.25,
        },
        # No se fija aquí ningún porcentaje de diversificación: el motor calcula
        # dos distintos —el del módulo de vida (mortalidad, longevidad, catástrofe)
        # y el de la agregación total, que además incorpora tasa de interés— y el
        # recuadro "Diversificación" de la página muestra el segundo. Citar una
        # cifra en este texto la dejaría descuadrada frente a la que se ve en vivo.
        "correlation_basis_es": (
            "Solvencia II Artículo 136, Reglamento Delegado Anexo IV. "
            "La correlación mortalidad-longevidad es negativa (-0.25) porque son opuestos naturales: "
            "una pandemia incrementa siniestros por muerte pero reduce obligaciones de rentas. "
            "La correlación vida-mercado es positiva (+0.25): el riesgo de tasa de interés "
            "no se compensa con los riesgos biométricos, se suma a ellos."
        ),
        "correlation_basis_en": (
            "Solvency II Article 136, Delegated Regulation Annex IV. "
            "Mortality-longevity correlation is negative (-0.25) because they are natural opposites: "
            "a pandemic increases death claims but decreases annuity obligations. "
            "The life-market correlation is positive (+0.25): interest-rate risk does not "
            "offset the biometric risks, it adds to them."
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
        # Ambas listas siguen la convención _es / _en del resto de la respuesta:
        # la página las imprime literalmente, así que deben existir en los dos idiomas.
        "coverage_es": [
            "Riesgo técnico de vida (4 submódulos: mortalidad, longevidad, tasa de interés, catástrofe)",
            "Agregación por matriz de correlaciones (módulo de vida más riesgo de mercado)",
            "Margen de riesgo por el método de costo de capital",
            "Provisiones técnicas (BEL más margen de riesgo)",
            "Cálculo del índice de cobertura del RCS",
            "Escenario catastrófico calibrado con la experiencia mexicana de COVID-19",
        ],
        "coverage_en": [
            "Life underwriting risk (4 sub-modules: mortality, longevity, interest rate, catastrophe)",
            "Correlation-based aggregation (life module + market risk)",
            "Risk margin via Cost-of-Capital method",
            "Technical provisions (BEL + risk margin)",
            "Solvency ratio computation",
            "COVID-calibrated catastrophe scenario using Mexican demographic data",
        ],
        "limitations_es": [
            "Choque de tasa de interés simplificado: desplazamiento paralelo, sin estructura temporal",
            "Sin submódulos de caducidad, gastos ni revisión",
            "Sin módulo de riesgo operativo (separado bajo Solvencia II)",
            "Margen de riesgo con RCS constante, sin proyección completa del run-off de la cartera",
            "Una sola tabla de mortalidad para toda la cartera, sin ajuste de suscripción por póliza",
            "Sin transparencia (look-through) en productos de inversión ligada a activos",
        ],
        "limitations_en": [
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
    portfolio_duration: float | None = None,
    available_capital: float | None = None,
    sex: str = "male",
    shocks_from_lee_carter: bool = False,
    session_id: str | None = None,
) -> dict:
    """Run the full SCR pipeline against this session's portfolio (thread-safe read)."""
    # Lee-Carter calibration (optional). Resolves the fitted model from the
    # precomputed cache; on a sex without a fit (e.g. "male"), fall back to
    # the unisex model so the calibration is always available.
    lc_for_shocks = None
    if shocks_from_lee_carter:
        try:
            lc_for_shocks = get_lee_carter(sex)
        except Exception:
            lc_for_shocks = get_lee_carter("unisex")

    with _portfolio_lock:
        portfolio = _ensure_portfolio(session_id)
        lt = get_regulatory_lt("cnsf", sex)

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
            shocks_from=lc_for_shocks,
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
                / result["total_aggregation"]["sum_individual"]
                * 100
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
