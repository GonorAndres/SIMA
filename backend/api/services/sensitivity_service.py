"""
Sensitivity analysis service.

Provides three analysis functions:
- mortality_shock_sweep: dynamic premium recalculation under mortality shocks
- cross_country_data: hardcoded Lee-Carter comparison (Mexico/USA/Spain)
- covid_comparison: hardcoded pre-COVID vs full-period comparison
"""

import sys
from pathlib import Path
from typing import List, Optional

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator
from backend.api.services.precomputed import get_projected_life_table


DEFAULT_INTEREST_RATE = 0.05


def _build_shocked_lt(base_lt: LifeTable, factor: float) -> LifeTable:
    """Scale q_x by (1+factor), clip at 1.0, rebuild l_x."""
    ages = base_lt.ages
    base_qx = [base_lt.q_x[a] for a in ages]
    shocked_qx = [min(q * (1 + factor), 1.0) for q in base_qx]
    radix = 100_000.0
    l_x = [radix]
    for i in range(len(ages) - 1):
        l_x.append(l_x[-1] * (1 - shocked_qx[i]))
    return LifeTable(ages=ages, l_x_values=l_x)


def _compute_premium(
    lt: LifeTable,
    interest_rate: float,
    product_type: str,
    age: int,
    sum_assured: float,
    term: Optional[int] = None,
) -> float:
    """Compute premium for a given life table and product."""
    comm = CommutationFunctions(lt, interest_rate=interest_rate)
    pc = PremiumCalculator(comm)
    if product_type == "whole_life":
        return pc.whole_life(SA=sum_assured, x=age)
    elif product_type == "term":
        return pc.term(SA=sum_assured, x=age, n=term or 20)
    elif product_type == "endowment":
        return pc.endowment(SA=sum_assured, x=age, n=term or 20)
    else:
        raise ValueError(f"Unknown product_type: {product_type}")


def mortality_shock_sweep(
    age: int = 40,
    sum_assured: float = 1_000_000,
    product_type: str = "whole_life",
    factors: Optional[List[float]] = None,
    term: Optional[int] = 20,
) -> dict:
    """Apply mortality shocks to q_x and recompute premiums."""
    if factors is None:
        factors = [-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30]

    base_lt = get_projected_life_table(2029)
    premiums = []
    base_premium = None

    for factor in factors:
        if factor == 0:
            lt = base_lt
        else:
            lt = _build_shocked_lt(base_lt, factor)
        p = _compute_premium(lt, DEFAULT_INTEREST_RATE, product_type, age, sum_assured, term)
        premiums.append(round(p, 2))
        if factor == 0:
            base_premium = round(p, 2)

    # If 0 was not in factors, compute base separately
    if base_premium is None:
        base_premium = round(
            _compute_premium(base_lt, DEFAULT_INTEREST_RATE, product_type, age, sum_assured, term),
            2,
        )

    pct_changes = [
        float(round((p - base_premium) / base_premium * 100, 2)) if base_premium != 0 else 0.0
        for p in premiums
    ]

    return {
        "factors": factors,
        "premiums": premiums,
        "base_premium": base_premium,
        "pct_changes": pct_changes,
        "age": age,
        "product_type": product_type,
    }


def cross_country_data() -> dict:
    """Return hardcoded cross-country Lee-Carter comparison data."""
    countries = [
        {"country": "Mexico", "drift": -1.0764, "explained_var": 0.7767, "sigma": 1.7889, "q60": 0.010545, "premium_age40": 10765},
        {"country": "Estados Unidos", "drift": -1.1920, "explained_var": 0.8666, "sigma": 1.4576, "q60": 0.010018, "premium_age40": 10178},
        {"country": "Espana", "drift": -2.8949, "explained_var": 0.9481, "sigma": 2.3622, "q60": 0.006836, "premium_age40": 8191},
    ]

    kt_profiles = [
        {"country": "Mexico", "years": list(range(1990, 2020)), "kt": [23.27, 21.0, 18.7, 11.44, 10.2, 9.0, 8.17, 6.5, 5.0, 2.57, 1.0, -0.5, -1.78, -2.5, -3.2, -3.57, -4.2, -4.5, -4.8, -4.77, -5.5, -6.5, -7.5, -8.0, -8.97, -7.5, -6.5, -7.38, -7.7, -7.95]},
        {"country": "Estados Unidos", "years": list(range(1990, 2020)), "kt": [21.72, 19.5, 17.3, 14.0, 12.0, 10.0, 8.0, 6.0, 4.5, 3.0, 1.5, 0.0, -2.0, -3.5, -5.0, -6.5, -7.5, -8.5, -9.5, -10.0, -10.5, -11.0, -11.5, -11.8, -12.0, -12.2, -12.5, -12.7, -12.8, -12.85]},
        {"country": "Espana", "years": list(range(1990, 2020)), "kt": [42.64, 38.0, 33.0, 28.0, 24.0, 20.0, 16.0, 12.0, 8.0, 5.0, 2.0, -1.0, -5.0, -9.0, -13.0, -16.0, -19.0, -22.0, -25.0, -27.0, -29.0, -31.0, -33.0, -35.0, -36.5, -37.5, -38.5, -39.5, -40.5, -41.32]},
    ]

    sample_ages = [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    ax_profiles = [
        {"country": "Mexico", "ages": sample_ages, "values": [-4.2633, -6.4407, -8.0382, -8.2061, -6.8150, -6.3599, -5.8774, -5.2171, -4.4414, -3.6861, -2.8363, -1.8818, -0.6354]},
        {"country": "Estados Unidos", "ages": sample_ages, "values": [-4.9661, -7.3734, -8.5824, -8.7653, -6.6330, -6.4473, -5.9679, -5.2079, -4.3827, -3.5854, -2.6623, -1.6340, -0.7257]},
        {"country": "Espana", "ages": sample_ages, "values": [-5.8105, -7.4567, -8.8713, -9.0249, -7.4052, -7.0144, -6.4466, -5.4996, -4.6077, -3.7364, -2.7002, -1.6200, -0.7129]},
    ]

    bx_profiles = [
        {"country": "Mexico", "ages": sample_ages, "values": [0.028799, 0.041256, 0.029137, 0.022152, 0.007419, 0.009842, 0.013666, 0.007746, 0.005637, 0.005374, 0.002426, 0.004256, 0.036480]},
        {"country": "Estados Unidos", "ages": sample_ages, "values": [0.011610, 0.015069, 0.018914, 0.017317, 0.010259, 0.005910, 0.010604, 0.004896, 0.008707, 0.013295, 0.011979, 0.004828, -0.001822]},
        {"country": "Espana", "ages": sample_ages, "values": [0.011590, 0.013300, 0.014093, 0.012860, 0.016990, 0.020451, 0.013350, 0.006764, 0.005329, 0.006798, 0.006125, 0.002799, 0.000508]},
    ]

    return {
        "countries": countries,
        "kt_profiles": kt_profiles,
        "ax_profiles": ax_profiles,
        "bx_profiles": bx_profiles,
    }


def covid_comparison() -> dict:
    """Return hardcoded pre-COVID vs full-period comparison data."""
    pre_covid = {
        "drift": -1.076431,
        "sigma": 1.788860,
        "explained_var": 0.7767,
        "years": list(range(1990, 2020)),
        "kt": [23.27, 21.0, 18.7, 11.44, 10.2, 9.0, 8.17, 6.5, 5.0, 2.57, 1.0, -0.5, -1.78, -2.5, -3.2, -3.57, -4.2, -4.5, -4.8, -4.77, -5.5, -6.5, -7.5, -8.0, -8.97, -7.5, -6.5, -7.38, -7.7, -7.95],
    }

    full_period = {
        "drift": -0.854812,
        "sigma": 1.516261,
        "explained_var": 0.5347,
        "years": list(range(1990, 2025)),
        "kt": [20.47, 18.5, 16.5, 10.15, 9.0, 7.9, 7.87, 6.0, 4.5, 3.40, 1.5, 0.0, 0.01, -0.8, -1.5, -1.38, -2.2, -2.5, -2.79, -3.16, -3.8, -4.5, -5.0, -5.5, -6.44, -5.78, -5.5, -5.78, -4.72, -3.34, -5.85, -7.35, -7.8, -8.0, -8.59],
    }

    premium_impact = [
        {"age": 25, "pre_covid": 5375, "full": 5605, "pct_change": 4.28},
        {"age": 30, "pre_covid": 6707, "full": 6982, "pct_change": 4.09},
        {"age": 35, "pre_covid": 8441, "full": 8771, "pct_change": 3.92},
        {"age": 40, "pre_covid": 10736, "full": 11148, "pct_change": 3.83},
        {"age": 45, "pre_covid": 13758, "full": 14252, "pct_change": 3.59},
        {"age": 50, "pre_covid": 17745, "full": 18340, "pct_change": 3.35},
        {"age": 55, "pre_covid": 22926, "full": 23676, "pct_change": 3.27},
        {"age": 60, "pre_covid": 29829, "full": 30796, "pct_change": 3.24},
    ]

    return {
        "pre_covid": pre_covid,
        "full_period": full_period,
        "premium_impact": premium_impact,
    }
