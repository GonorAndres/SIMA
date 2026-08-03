"""
Sensitivity analysis service.

Provides three analysis functions, all computed from the live engine:
- mortality_shock_sweep: premium recalculation under mortality shocks
- cross_country_data: Lee-Carter comparison (Mexico/USA/Spain)
- covid_comparison: pre-COVID (1990-2019) vs full-period Mexican fit

cross_country_data() and covid_comparison() returned hardcoded constants until
2026-08-02. They were transcribed from a run against synthetic mortality data
and never re-derived, so the endpoints kept publishing figures the engine no
longer produced. Nothing here may be a literal that a reader could mistake for
a measurement: if a number is actuarial, it is computed below.
"""

import csv
import sys
from functools import lru_cache
from pathlib import Path

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.api.services.precomputed import (
    PROJECTION_YEAR,
    _fit_pipeline,
    _resolve_paths,
    get_hmd_pipeline,
    get_projected_life_table,
)
from backend.api.services.precomputed import _get_pipeline as get_pipeline
from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a12_scr import build_shocked_life_table

DEFAULT_INTEREST_RATE = 0.05

# Ages sampled for the a_x / b_x profile charts. Not every age is plotted: the
# fit runs 0-100 and 101 points per country makes the small-multiples unreadable.
CROSS_COUNTRY_SAMPLE_AGES = [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Ages priced for the COVID premium-impact table.
COVID_PREMIUM_AGES = [25, 30, 35, 40, 45, 50, 55, 60]

# Start of the Mexican fit window. 1990 is the first year CONAPO publishes
# single-age population, so it bounds both the pre-COVID and full-period fits.
PRE_COVID_YEAR_START = 1990


def _compute_premium(
    lt: LifeTable,
    interest_rate: float,
    product_type: str,
    age: int,
    sum_assured: float,
    term: int | None = None,
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
    factors: list[float] | None = None,
    term: int | None = 20,
    sex: str = "unisex",
) -> dict:
    """Apply mortality shocks to q_x and recompute premiums."""
    if factors is None:
        factors = [-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30]

    base_lt = get_projected_life_table(2029, sex=sex)
    premiums = []
    base_premium = None

    for factor in factors:
        lt = base_lt if factor == 0 else build_shocked_life_table(base_lt, 1 + factor)
        p = _compute_premium(lt, DEFAULT_INTEREST_RATE, product_type, age, sum_assured, term)
        premiums.append(p)
        if factor == 0:
            base_premium = p

    # If 0 was not in factors, compute base separately
    if base_premium is None:
        base_premium = _compute_premium(
            base_lt,
            DEFAULT_INTEREST_RATE,
            product_type,
            age,
            sum_assured,
            term,
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
        "sex": sex,
    }


def _country_pipelines() -> list[tuple[str, dict]]:
    """(display name, pipeline) for the three unisex Lee-Carter fits.

    Unisex ("Total") is the right basis for a cross-country comparison: the
    sex mix differs between the three populations, so comparing male fits would
    confound the improvement rate with composition. All three are fitted on the
    same window (1990-2019) and the same age range (0-100) -- see
    precomputed._build_inegi_pipeline / _build_hmd_pipeline.
    """
    return [
        ("México", get_pipeline("unisex")),
        ("Estados Unidos", get_hmd_pipeline("usa", "unisex")),
        ("España", get_hmd_pipeline("spain", "unisex")),
    ]


def _whole_life_premium_age40(lt: LifeTable) -> float:
    """Net single-basis whole-life premium at age 40, SA = 1,000,000, i = 5%."""
    return _compute_premium(lt, DEFAULT_INTEREST_RATE, "whole_life", 40, 1_000_000)


def cross_country_data() -> dict:
    """Cross-country Lee-Carter comparison, computed from the live fits.

    Every figure here used to be a hardcoded constant. Those constants were
    read off a run against synthetic Gompertz-Makeham data and then drifted
    away from the engine: they still reported Spain drift -2.8949 (which is the
    *male* fit) and USA -1.1920 long after the real HMD extracts landed, so the
    Sensibilidad page showed one number in its prose and another in the metric
    tile directly beneath it. Audit items M2/F3.

    q60 and premium_age40 are evaluated on each country's life table projected
    to precomputed.PROJECTION_YEAR, so the comparison is like-for-like.
    """
    countries = []
    kt_profiles = []
    ax_profiles = []
    bx_profiles = []

    for name, pipeline in _country_pipelines():
        lc = pipeline["lee_carter"]
        proj = pipeline["projection"]
        lt = proj.to_life_table(year=PROJECTION_YEAR, radix=100_000)

        countries.append(
            {
                "country": name,
                "drift": float(proj.drift),
                "explained_var": float(lc.explained_variance),
                "sigma": float(proj.sigma),
                "q60": float(lt.get_q(60)),
                "premium_age40": float(_whole_life_premium_age40(lt)),
            }
        )
        kt_profiles.append(
            {
                "country": name,
                "years": [int(y) for y in lc.years],
                "kt": [float(k) for k in lc.kt],
            }
        )
        ages = [int(a) for a in lc.ages]
        sample = [a for a in CROSS_COUNTRY_SAMPLE_AGES if a in ages]
        ax_profiles.append(
            {"country": name, "ages": sample, "values": [float(lc.get_ax(a)) for a in sample]}
        )
        bx_profiles.append(
            {"country": name, "ages": sample, "values": [float(lc.get_bx(a)) for a in sample]}
        )

    return {
        "countries": countries,
        "kt_profiles": kt_profiles,
        "ax_profiles": ax_profiles,
        "bx_profiles": bx_profiles,
    }


def _period_payload(pipeline: dict) -> dict:
    """Serialise one fitted period into the CovidPeriodData shape."""
    lc = pipeline["lee_carter"]
    proj = pipeline["projection"]
    return {
        "drift": float(proj.drift),
        "sigma": float(proj.sigma),
        "explained_var": float(lc.explained_variance),
        "years": [int(y) for y in lc.years],
        "kt": [float(k) for k in lc.kt],
    }


@lru_cache(maxsize=1)
def _full_period_pipeline() -> dict:
    """Fit Mexico over the full window, COVID years included.

    Not precomputed at startup: this is the only consumer, and one extra
    graduation + SVD costs well under a second. COVID_FULL_YEAR_END is read
    from the loaded data rather than hardcoded, so a data refresh that adds a
    year extends the comparison instead of silently truncating it.
    """
    deaths, population, _cnsf, _cnsf_2013, _emssa, _sources = _resolve_paths()
    md = MortalityData.from_inegi(
        deaths_filepath=deaths,
        population_filepath=population,
        sex="Total",
        year_start=PRE_COVID_YEAR_START,
        year_end=_latest_available_year(deaths),
        age_max=100,
    )
    return _fit_pipeline(md)


def _latest_available_year(deaths_filepath: str) -> int:
    """Last calendar year present in the deaths file."""
    with open(deaths_filepath, newline="") as fh:
        reader = csv.DictReader(fh)
        return max(int(row["Anio"]) for row in reader)


def covid_comparison() -> dict:
    """Pre-COVID (1990-2019) vs full-period Mexico fit, computed live.

    The pre-COVID period is the same fit the rest of the API serves, so the
    Mexican drift quoted on this page and on /mortality/lee-carter can no
    longer disagree -- they did while both were hardcoded, by about 0.01.

    Note the direction of the COVID effect: adding 2020-2021 does not make the
    fitted improvement look faster, it makes it look SLOWER, because a mortality
    shock at the end of the series flattens the k_t slope that the random walk
    with drift extrapolates. Higher projected mortality means higher premiums.
    """
    pre = get_pipeline("unisex")
    full = _full_period_pipeline()

    pre_lt = pre["projection"].to_life_table(year=PROJECTION_YEAR, radix=100_000)
    full_lt = full["projection"].to_life_table(year=PROJECTION_YEAR, radix=100_000)

    premium_impact = []
    for age in COVID_PREMIUM_AGES:
        p_pre = _compute_premium(pre_lt, DEFAULT_INTEREST_RATE, "whole_life", age, 1_000_000)
        p_full = _compute_premium(full_lt, DEFAULT_INTEREST_RATE, "whole_life", age, 1_000_000)
        premium_impact.append(
            {
                "age": age,
                "pre_covid": float(p_pre),
                "full": float(p_full),
                "pct_change": float(round((p_full - p_pre) / p_pre * 100, 2)) if p_pre else 0.0,
            }
        )

    return {
        "pre_covid": _period_payload(pre),
        "full_period": _period_payload(full),
        "premium_impact": premium_impact,
    }
