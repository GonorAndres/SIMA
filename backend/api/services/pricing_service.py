"""
Pricing service: bridges API requests to engine modules a01-a05.

All pricing uses Lee-Carter projected life tables:
    - Mexico: INEGI/CONAPO pipeline (male/female/unisex)
    - USA/Spain: HMD pipeline (male/female/unisex)
"""

import sys
from pathlib import Path
from typing import List, Optional

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator

from backend.api.services.precomputed import (
    get_projected_life_table,
    get_hmd_projected_life_table,
    get_lee_carter,
    get_projection,
    get_hmd_pipeline,
)


def _get_life_table(table_type: str, sex: str) -> LifeTable:
    """Get the appropriate life table -- always uses LC projected tables."""
    return get_projected_life_table(2029, sex=sex)


def calculate_premium(
    product_type: str,
    age: int,
    sum_assured: float,
    interest_rate: float,
    term: Optional[int] = None,
    table_type: str = "cnsf",
    sex: str = "male",
) -> dict:
    """Calculate a net premium using the equivalence principle."""
    lt = _get_life_table(table_type, sex)
    comm = CommutationFunctions(lt, interest_rate=interest_rate)
    pc = PremiumCalculator(comm)

    if product_type == "whole_life":
        premium = pc.whole_life(SA=sum_assured, x=age)
    elif product_type == "term":
        if term is None:
            raise ValueError("term is required for term product")
        premium = pc.term(SA=sum_assured, x=age, n=term)
    elif product_type == "endowment":
        if term is None:
            raise ValueError("term is required for endowment product")
        premium = pc.endowment(SA=sum_assured, x=age, n=term)
    elif product_type == "pure_endowment":
        if term is None:
            raise ValueError("term is required for pure_endowment product")
        premium = pc.pure_endowment(SA=sum_assured, x=age, n=term)
    else:
        raise ValueError(f"Unknown product_type: {product_type}")

    premium_rate = premium / sum_assured

    return {
        "product_type": product_type,
        "age": age,
        "sum_assured": sum_assured,
        "interest_rate": interest_rate,
        "term": term,
        "sex": sex,
        "annual_premium": premium,
        "premium_rate": premium_rate,
    }


def calculate_reserve_trajectory(
    product_type: str,
    age: int,
    sum_assured: float,
    interest_rate: float,
    term: Optional[int] = None,
    table_type: str = "cnsf",
    sex: str = "male",
) -> dict:
    """Calculate the full reserve trajectory for a policy."""
    lt = _get_life_table(table_type, sex)
    comm = CommutationFunctions(lt, interest_rate=interest_rate)
    rc = ReserveCalculator(comm)
    pc = PremiumCalculator(comm)

    # Get the premium
    if product_type == "whole_life":
        premium = pc.whole_life(SA=sum_assured, x=age)
    elif product_type == "term":
        premium = pc.term(SA=sum_assured, x=age, n=term)
    elif product_type == "endowment":
        premium = pc.endowment(SA=sum_assured, x=age, n=term)
    elif product_type == "pure_endowment":
        premium = pc.pure_endowment(SA=sum_assured, x=age, n=term)
    else:
        raise ValueError(f"Unknown product_type: {product_type}")

    trajectory = rc.reserve_trajectory(SA=sum_assured, x=age, product=product_type, n=term)

    return {
        "product_type": product_type,
        "issue_age": age,
        "sum_assured": sum_assured,
        "interest_rate": interest_rate,
        "term": term,
        "sex": sex,
        "annual_premium": premium,
        "trajectory": [
            {"duration": t, "age": age + t, "reserve": v}
            for t, v in trajectory
        ],
    }


def get_commutation_values(
    age: int,
    interest_rate: float,
    table_type: str = "cnsf",
    sex: str = "male",
) -> dict:
    """Get commutation function values and actuarial values at a given age."""
    lt = _get_life_table(table_type, sex)
    comm = CommutationFunctions(lt, interest_rate=interest_rate)
    av = ActuarialValues(comm)

    return {
        "age": age,
        "D_x": comm.get_D(age),
        "N_x": comm.get_N(age),
        "C_x": comm.get_C(age),
        "M_x": comm.get_M(age),
        "A_x": av.A_x(age),
        "a_due_x": av.a_due(age),
    }


def calculate_sensitivity(
    product_type: str,
    age: int,
    sum_assured: float,
    rates: List[float],
    term: Optional[int] = None,
    table_type: str = "cnsf",
    sex: str = "male",
) -> dict:
    """Calculate premium at multiple interest rates."""
    lt = _get_life_table(table_type, sex)
    results = []

    for rate in rates:
        comm = CommutationFunctions(lt, interest_rate=rate)
        pc = PremiumCalculator(comm)

        if product_type == "whole_life":
            premium = pc.whole_life(SA=sum_assured, x=age)
        elif product_type == "term":
            premium = pc.term(SA=sum_assured, x=age, n=term)
        elif product_type == "endowment":
            premium = pc.endowment(SA=sum_assured, x=age, n=term)
        elif product_type == "pure_endowment":
            premium = pc.pure_endowment(SA=sum_assured, x=age, n=term)
        else:
            raise ValueError(f"Unknown product_type: {product_type}")

        results.append({
            "interest_rate": rate,
            "annual_premium": premium,
        })

    return {
        "product_type": product_type,
        "age": age,
        "sum_assured": sum_assured,
        "results": results,
    }


def _compute_premium(
    lt: LifeTable,
    product_type: str,
    age: int,
    sum_assured: float,
    interest_rate: float,
    term: Optional[int],
) -> float:
    """Compute a single premium from a life table."""
    comm = CommutationFunctions(lt, interest_rate=interest_rate)
    pc = PremiumCalculator(comm)
    if product_type == "whole_life":
        return pc.whole_life(SA=sum_assured, x=age)
    elif product_type == "term":
        if term is None:
            raise ValueError("term is required for term product")
        return pc.term(SA=sum_assured, x=age, n=term)
    elif product_type == "endowment":
        if term is None:
            raise ValueError("term is required for endowment product")
        return pc.endowment(SA=sum_assured, x=age, n=term)
    elif product_type == "pure_endowment":
        if term is None:
            raise ValueError("term is required for pure_endowment product")
        return pc.pure_endowment(SA=sum_assured, x=age, n=term)
    raise ValueError(f"Unknown product_type: {product_type}")


def calculate_cross_country_premium(
    product_type: str,
    age: int,
    sum_assured: float,
    interest_rate: float,
    term: Optional[int] = None,
    sex: str = "male",
) -> dict:
    """Compare premiums across Mexico, USA, and Spain for the same product."""
    entries = []

    # Mexico (INEGI/CONAPO pipeline)
    mx_lt = get_projected_life_table(2029, sex=sex)
    mx_lc = get_lee_carter(sex)
    mx_proj = get_projection(sex)
    mx_premium = _compute_premium(mx_lt, product_type, age, sum_assured, interest_rate, term)
    entries.append({
        "country": "Mexico",
        "annual_premium": mx_premium,
        "premium_rate": mx_premium / sum_assured,
        "drift": float(mx_proj.drift),
        "explained_var": float(mx_lc.explained_variance),
    })

    # USA and Spain (HMD pipelines)
    for country, label in [("usa", "Estados Unidos"), ("spain", "España")]:
        lt = get_hmd_projected_life_table(country, 2029, sex=sex)
        pipeline = get_hmd_pipeline(country, sex)
        lc = pipeline["lee_carter"]
        proj = pipeline["projection"]
        premium = _compute_premium(lt, product_type, age, sum_assured, interest_rate, term)
        entries.append({
            "country": label,
            "annual_premium": premium,
            "premium_rate": premium / sum_assured,
            "drift": float(proj.drift),
            "explained_var": float(lc.explained_variance),
        })

    return {
        "product_type": product_type,
        "age": age,
        "sum_assured": sum_assured,
        "interest_rate": interest_rate,
        "term": term,
        "sex": sex,
        "entries": entries,
    }
