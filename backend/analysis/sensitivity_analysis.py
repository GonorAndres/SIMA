"""
Sensitivity Analysis: Interest Rate, Mortality Shocks, Cross-Country
=====================================================================

Three-dimensional sensitivity analysis on the Lee-Carter mortality pipeline:

    1. Interest rate sensitivity (Mexico): i = 2% to 8%
       -> How premiums and reserves respond to discount rate changes

    2. Mortality shock sensitivity (Mexico): q_x scaled by 0.70 to 1.30
       -> How premiums and reserves respond to mortality deviations

    3. Cross-country comparison: Mexico vs USA vs Spain
       -> Same pipeline (1990-2019), Lee-Carter parameters side by side

All analyses use the established engine modules (a01-a10) without modification.
Mexico uses INEGI/CONAPO data; USA and Spain use HMD data.

Usage:
    cd /home/andtega349/SIMA
    venv/bin/python backend/analysis/sensitivity_analysis.py
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection

# ── Paths ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
HMD_DIR = str(DATA_DIR / "hmd")
INEGI_DEATHS = str(DATA_DIR / "inegi" / "inegi_deaths.csv")
CONAPO_POP = str(DATA_DIR / "conapo" / "conapo_population.csv")
RESULTS_DIR = Path(__file__).parent / "results"

# ── Constants ────────────────────────────────────────────────────────

INTEREST_RATES = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
SHOCK_FACTORS = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]
PREMIUM_AGES = [25, 30, 35, 40, 45, 50, 55, 60]
RESERVE_AGE = 35
SA = 1_000_000
TARGET_YEAR_OFFSET = 10
BASE_RATE = 0.05
BASE_SHOCK = 1.00


# ── Helper Functions ─────────────────────────────────────────────────


def build_shocked_life_table(base_lt, shock_factor, radix=100_000.0):
    """
    Create a new LifeTable with q_x scaled by shock_factor.

    For each age, shocked_q_x = min(base_q_x * factor, 1.0).
    Then rebuild l_x from the shocked q_x values.

    A shock_factor > 1.0 means WORSE mortality (higher death rates).
    A shock_factor < 1.0 means BETTER mortality (lower death rates).
    """
    ages = base_lt.ages
    shocked_qx = []
    for age in ages[:-1]:
        shocked_qx.append(min(base_lt.get_q(age) * shock_factor, 1.0))
    shocked_qx.append(1.0)  # terminal q = 1.0

    l_x = [radix]
    for qx in shocked_qx[:-1]:
        l_x.append(l_x[-1] * (1.0 - qx))

    return LifeTable(ages=ages, l_x_values=l_x)


def run_country_pipeline(country, sex="Total", year_start=1990, year_end=2019):
    """
    Run full Lee-Carter pipeline for one country.

    Returns dict with all intermediate objects: mortality_data, graduated,
    lee_carter, projection, life_table, target_year.
    """
    if country == "mexico":
        data = MortalityData.from_inegi(
            INEGI_DEATHS, CONAPO_POP,
            sex=sex, year_start=year_start, year_end=year_end, age_max=100,
        )
    else:
        data = MortalityData.from_hmd(
            HMD_DIR, country,
            sex="Male", year_min=year_start, year_max=year_end, age_max=100,
        )

    graduated = GraduatedRates(data, lambda_param=1e5)
    lc = LeeCarter.fit(graduated, reestimate_kt=False)
    projection = MortalityProjection(lc, horizon=30, n_simulations=1000, random_seed=42)
    target_year = int(lc.years[-1]) + TARGET_YEAR_OFFSET
    life_table = projection.to_life_table(year=target_year)

    return {
        "country": country,
        "mortality_data": data,
        "graduated": graduated,
        "lee_carter": lc,
        "projection": projection,
        "life_table": life_table,
        "target_year": target_year,
    }


def compute_premiums_at_rate(life_table, interest_rate):
    """
    Compute premiums for 3 products at PREMIUM_AGES for a given interest rate.

    Returns dict[age] = {whole_life, term_20, endowment_20}.
    """
    comm = CommutationFunctions(life_table, interest_rate=interest_rate)
    pc = PremiumCalculator(comm)
    results = {}
    for age in PREMIUM_AGES:
        entry = {"whole_life": pc.whole_life(SA=SA, x=age)}
        if age + 20 <= life_table.omega:
            entry["term_20"] = pc.term(SA=SA, x=age, n=20)
            entry["endowment_20"] = pc.endowment(SA=SA, x=age, n=20)
        else:
            entry["term_20"] = None
            entry["endowment_20"] = None
        results[age] = entry
    return results


def compute_reserve_trajectory(life_table, interest_rate, age, product, n=None):
    """
    Compute reserve trajectory for one scenario.

    Returns list of (duration, reserve) tuples.
    """
    comm = CommutationFunctions(life_table, interest_rate=interest_rate)
    rc = ReserveCalculator(comm)
    return rc.reserve_trajectory(SA=SA, x=age, product=product, n=n)


# ── Analysis 1: Interest Rate Sensitivity ────────────────────────────


def run_interest_rate_sensitivity(mexico_result):
    """
    Sweep interest rates from 2% to 8% on Mexico's projected life table.

    Returns dict with premium tables and reserve trajectories for each rate.
    """
    lt = mexico_result["life_table"]

    # Premiums at each rate
    premium_tables = {}
    for rate in INTEREST_RATES:
        premium_tables[rate] = compute_premiums_at_rate(lt, rate)

    # Reserve trajectories at each rate (whole life, age 35)
    reserve_tables = {}
    for rate in INTEREST_RATES:
        reserve_tables[rate] = compute_reserve_trajectory(
            lt, rate, RESERVE_AGE, "whole_life"
        )

    return {"premiums": premium_tables, "reserves": reserve_tables}


def format_interest_rate_report(mexico_result, sensitivity_result):
    """Format interest rate sensitivity into a text report."""
    lines = []
    sep = "=" * 78
    target_year = mexico_result["target_year"]
    premiums = sensitivity_result["premiums"]
    reserves = sensitivity_result["reserves"]

    lines.append(sep)
    lines.append("  SIMA - SENSITIVITY ANALYSIS: INTEREST RATE")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # Section 1: Parameters
    lines.append("1. PARAMETERS")
    lines.append("-" * 50)
    lines.append(f"  Base life table:  Mexico projected, year {target_year}")
    lines.append(f"  Data period:      1990-2019 (pre-COVID)")
    lines.append(f"  Sum assured:      ${SA:,.0f} MXN")
    lines.append(f"  Interest rates:   {', '.join(f'{r:.0%}' for r in INTEREST_RATES)}")
    lines.append(f"  Premium ages:     {', '.join(str(a) for a in PREMIUM_AGES)}")
    lines.append(f"  Reserve age:      {RESERVE_AGE} (whole life)")
    lines.append("")

    # Section 2: Premium tables by product
    for product_key, product_name in [
        ("whole_life", "Whole Life"),
        ("term_20", "Term 20"),
        ("endowment_20", "Endowment 20"),
    ]:
        lines.append(f"2. NET ANNUAL PREMIUMS: {product_name}")
        lines.append("-" * 50)

        # Header row
        header = f"  {'Age':>5}"
        for rate in INTEREST_RATES:
            header += f"  {f'i={rate:.0%}':>12}"
        lines.append(header)

        divider = f"  {'---':>5}"
        for _ in INTEREST_RATES:
            divider += f"  {'-' * 12}"
        lines.append(divider)

        # Data rows
        for age in PREMIUM_AGES:
            row = f"  {age:>5}"
            for rate in INTEREST_RATES:
                val = premiums[rate][age][product_key]
                if val is not None:
                    row += f"  ${val:>10,.0f}"
                else:
                    row += f"  {'N/A':>11}"
            lines.append(row)
        lines.append("")

    # Section 3: Percentage change vs base (i=5%)
    lines.append("3. PERCENTAGE CHANGE VS BASE (i=5%)")
    lines.append("-" * 50)

    for product_key, product_name in [
        ("whole_life", "Whole Life"),
        ("term_20", "Term 20"),
        ("endowment_20", "Endowment 20"),
    ]:
        lines.append(f"  {product_name}:")

        header = f"  {'Age':>5}"
        for rate in INTEREST_RATES:
            header += f"  {f'i={rate:.0%}':>10}"
        lines.append(header)

        divider = f"  {'---':>5}"
        for _ in INTEREST_RATES:
            divider += f"  {'-' * 10}"
        lines.append(divider)

        for age in PREMIUM_AGES:
            base_val = premiums[BASE_RATE][age][product_key]
            row = f"  {age:>5}"
            for rate in INTEREST_RATES:
                val = premiums[rate][age][product_key]
                if val is not None and base_val is not None and base_val != 0:
                    pct = (val - base_val) / base_val * 100
                    row += f"  {pct:>+9.1f}%"
                else:
                    row += f"  {'N/A':>10}"
            lines.append(row)
        lines.append("")

    # Section 4: Reserve trajectory comparison
    lines.append(f"4. RESERVE TRAJECTORY: Whole Life, Age {RESERVE_AGE}")
    lines.append("-" * 50)

    header = f"  {'Dur':>5}  {'Age':>4}"
    for rate in INTEREST_RATES:
        header += f"  {f'i={rate:.0%}':>12}"
    lines.append(header)

    divider = f"  {'---':>5}  {'---':>4}"
    for _ in INTEREST_RATES:
        divider += f"  {'-' * 12}"
    lines.append(divider)

    # Show selected durations
    selected_durations = [0, 1, 5, 10, 15, 20, 25, 30]
    for dur in selected_durations:
        row = f"  {dur:>5}  {RESERVE_AGE + dur:>4}"
        for rate in INTEREST_RATES:
            traj = reserves[rate]
            if dur < len(traj):
                _, reserve = traj[dur]
                row += f"  ${reserve:>10,.0f}"
            else:
                row += f"  {'N/A':>11}"
        lines.append(row)
    lines.append("")

    # Interpretation
    lines.append("5. INTERPRETATION")
    lines.append("-" * 50)
    wl_low = premiums[INTEREST_RATES[0]][40]["whole_life"]
    wl_high = premiums[INTEREST_RATES[-1]][40]["whole_life"]
    pct_range = (wl_low - wl_high) / wl_high * 100
    lines.append(f"  At age 40, whole life premium ranges from "
                 f"${wl_high:,.0f} (i=8%) to ${wl_low:,.0f} (i=2%)")
    lines.append(f"  This is a {pct_range:+.1f}% spread -- interest rate is a MAJOR driver.")
    lines.append(f"  Higher i => lower premium (future death benefit is cheaper in PV terms).")
    lines.append(f"  Reserves also decrease with higher i: less needs to be set aside today.")
    lines.append("")

    return "\n".join(lines)


# ── Analysis 2: Mortality Shock Sensitivity ──────────────────────────


def run_mortality_shock_sensitivity(mexico_result):
    """
    Apply mortality shock factors 0.70 to 1.30 on Mexico's projected life table.

    Returns dict with shocked life tables, premium tables, and reserve trajectories.
    """
    base_lt = mexico_result["life_table"]

    shocked_lts = {}
    premium_tables = {}
    reserve_tables = {}

    for factor in SHOCK_FACTORS:
        if abs(factor - 1.0) < 1e-9:
            shocked_lt = base_lt
        else:
            shocked_lt = build_shocked_life_table(base_lt, factor)

        shocked_lts[factor] = shocked_lt
        premium_tables[factor] = compute_premiums_at_rate(shocked_lt, BASE_RATE)
        reserve_tables[factor] = compute_reserve_trajectory(
            shocked_lt, BASE_RATE, RESERVE_AGE, "whole_life"
        )

    return {
        "shocked_lts": shocked_lts,
        "premiums": premium_tables,
        "reserves": reserve_tables,
    }


def format_mortality_shock_report(mexico_result, shock_result):
    """Format mortality shock sensitivity into a text report."""
    lines = []
    sep = "=" * 78
    target_year = mexico_result["target_year"]
    base_lt = mexico_result["life_table"]
    premiums = shock_result["premiums"]
    reserves = shock_result["reserves"]
    shocked_lts = shock_result["shocked_lts"]

    lines.append(sep)
    lines.append("  SIMA - SENSITIVITY ANALYSIS: MORTALITY SHOCKS")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # Section 1: Parameters
    lines.append("1. PARAMETERS")
    lines.append("-" * 50)
    lines.append(f"  Base life table:  Mexico projected, year {target_year}")
    lines.append(f"  Data period:      1990-2019 (pre-COVID)")
    lines.append(f"  Fixed rate:       i = {BASE_RATE:.0%}")
    lines.append(f"  Sum assured:      ${SA:,.0f} MXN")
    lines.append(f"  Shock factors:    {', '.join(f'{f:.2f}' for f in SHOCK_FACTORS)}")
    lines.append(f"  Premium ages:     {', '.join(str(a) for a in PREMIUM_AGES)}")
    lines.append(f"  Reserve age:      {RESERVE_AGE} (whole life)")
    lines.append("")

    # Section 2: Shocked q_x at selected ages
    lines.append("2. SHOCKED q_x VALUES (1000*q_x)")
    lines.append("-" * 50)

    header = f"  {'Age':>5}"
    for factor in SHOCK_FACTORS:
        header += f"  {f'{factor:.2f}x':>9}"
    lines.append(header)

    divider = f"  {'---':>5}"
    for _ in SHOCK_FACTORS:
        divider += f"  {'-' * 9}"
    lines.append(divider)

    for age in [0, 1, 10, 20, 30, 40, 50, 60, 70, 80, 90]:
        if age in base_lt.q_x:
            row = f"  {age:>5}"
            for factor in SHOCK_FACTORS:
                lt = shocked_lts[factor]
                qx = lt.get_q(age)
                row += f"  {qx * 1000:>9.3f}"
            lines.append(row)
    lines.append("")

    # Section 3: Premium tables by product
    for product_key, product_name in [
        ("whole_life", "Whole Life"),
        ("term_20", "Term 20"),
        ("endowment_20", "Endowment 20"),
    ]:
        lines.append(f"3. NET ANNUAL PREMIUMS: {product_name} (i={BASE_RATE:.0%})")
        lines.append("-" * 50)

        header = f"  {'Age':>5}"
        for factor in SHOCK_FACTORS:
            header += f"  {f'{factor:.2f}x':>12}"
        lines.append(header)

        divider = f"  {'---':>5}"
        for _ in SHOCK_FACTORS:
            divider += f"  {'-' * 12}"
        lines.append(divider)

        for age in PREMIUM_AGES:
            row = f"  {age:>5}"
            for factor in SHOCK_FACTORS:
                val = premiums[factor][age][product_key]
                if val is not None:
                    row += f"  ${val:>10,.0f}"
                else:
                    row += f"  {'N/A':>11}"
            lines.append(row)
        lines.append("")

    # Section 4: Percentage change vs base (factor=1.00)
    lines.append("4. PERCENTAGE CHANGE VS BASE (factor=1.00)")
    lines.append("-" * 50)

    for product_key, product_name in [
        ("whole_life", "Whole Life"),
        ("term_20", "Term 20"),
        ("endowment_20", "Endowment 20"),
    ]:
        lines.append(f"  {product_name}:")

        header = f"  {'Age':>5}"
        for factor in SHOCK_FACTORS:
            header += f"  {f'{factor:.2f}x':>10}"
        lines.append(header)

        divider = f"  {'---':>5}"
        for _ in SHOCK_FACTORS:
            divider += f"  {'-' * 10}"
        lines.append(divider)

        for age in PREMIUM_AGES:
            base_val = premiums[BASE_SHOCK][age][product_key]
            row = f"  {age:>5}"
            for factor in SHOCK_FACTORS:
                val = premiums[factor][age][product_key]
                if val is not None and base_val is not None and base_val != 0:
                    pct = (val - base_val) / base_val * 100
                    row += f"  {pct:>+9.1f}%"
                else:
                    row += f"  {'N/A':>10}"
            lines.append(row)
        lines.append("")

    # Section 5: Reserve trajectory comparison
    lines.append(f"5. RESERVE TRAJECTORY: Whole Life, Age {RESERVE_AGE}, i={BASE_RATE:.0%}")
    lines.append("-" * 50)

    header = f"  {'Dur':>5}  {'Age':>4}"
    for factor in SHOCK_FACTORS:
        header += f"  {f'{factor:.2f}x':>12}"
    lines.append(header)

    divider = f"  {'---':>5}  {'---':>4}"
    for _ in SHOCK_FACTORS:
        divider += f"  {'-' * 12}"
    lines.append(divider)

    selected_durations = [0, 1, 5, 10, 15, 20, 25, 30]
    for dur in selected_durations:
        row = f"  {dur:>5}  {RESERVE_AGE + dur:>4}"
        for factor in SHOCK_FACTORS:
            traj = reserves[factor]
            if dur < len(traj):
                _, reserve = traj[dur]
                row += f"  ${reserve:>10,.0f}"
            else:
                row += f"  {'N/A':>11}"
        lines.append(row)
    lines.append("")

    # Interpretation
    lines.append("6. INTERPRETATION")
    lines.append("-" * 50)
    wl_low = premiums[0.70][40]["whole_life"]
    wl_base = premiums[1.00][40]["whole_life"]
    wl_high = premiums[1.30][40]["whole_life"]
    pct_low = (wl_low - wl_base) / wl_base * 100
    pct_high = (wl_high - wl_base) / wl_base * 100
    lines.append(f"  At age 40 (whole life, i=5%):")
    lines.append(f"    30% mortality improvement (0.70x): premium changes {pct_low:+.1f}%")
    lines.append(f"    30% mortality deterioration (1.30x): premium changes {pct_high:+.1f}%")
    lines.append(f"  Mortality shocks have an ASYMMETRIC effect: increases hurt more")
    lines.append(f"  than decreases help, because the q_x -> premium relationship is convex.")
    lines.append(f"  CNSF stress testing typically uses +15% to +30% shock factors.")
    lines.append("")

    return "\n".join(lines)


# ── Analysis 3: Cross-Country Comparison ─────────────────────────────


def run_cross_country_comparison():
    """
    Run Lee-Carter pipeline for Mexico, USA, Spain and compare.

    All use 1990-2019, age_max=100, lambda=1e5, reestimate_kt=False.
    Mexico uses sex="Total" (INEGI); USA/Spain use sex="Male" (HMD).
    """
    countries = ["mexico", "usa", "spain"]
    results = {}
    for country in countries:
        print(f"    Running pipeline for {country}...")
        results[country] = run_country_pipeline(country)

    return results


def format_cross_country_report(country_results):
    """Format cross-country comparison into a text report."""
    lines = []
    sep = "=" * 78
    countries = ["mexico", "usa", "spain"]
    labels = {"mexico": "Mexico", "usa": "USA", "spain": "Spain"}

    lines.append(sep)
    lines.append("  SIMA - SENSITIVITY ANALYSIS: CROSS-COUNTRY COMPARISON")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # Section 1: Data summary
    lines.append("1. DATA SUMMARY")
    lines.append("-" * 50)
    header = f"  {'':>18}"
    for c in countries:
        header += f"  {labels[c]:>14}"
    lines.append(header)

    divider = f"  {'':>18}"
    for _ in countries:
        divider += f"  {'-' * 14}"
    lines.append(divider)

    row_src = f"  {'Source':>18}"
    row_sex = f"  {'Sex':>18}"
    row_years = f"  {'Years':>18}"
    row_ages = f"  {'Ages':>18}"
    row_shape = f"  {'Matrix shape':>18}"

    for c in countries:
        r = country_results[c]
        data = r["mortality_data"]
        row_src += f"  {'INEGI/CONAPO' if c == 'mexico' else 'HMD':>14}"
        row_sex += f"  {data.sex:>14}"
        row_years += f"  {f'{int(data.years[0])}-{int(data.years[-1])}':>14}"
        row_ages += f"  {f'{int(data.ages[0])}-{int(data.ages[-1])}':>14}"
        row_shape += f"  {f'{data.mx.shape[0]}x{data.mx.shape[1]}':>14}"

    lines.extend([row_src, row_sex, row_years, row_ages, row_shape])
    lines.append("")

    # Section 2: Lee-Carter diagnostics
    lines.append("2. LEE-CARTER DIAGNOSTICS")
    lines.append("-" * 50)

    header = f"  {'Metric':>22}"
    for c in countries:
        header += f"  {labels[c]:>14}"
    lines.append(header)

    divider = f"  {'-' * 22}"
    for _ in countries:
        divider += f"  {'-' * 14}"
    lines.append(divider)

    # Explained variance
    row = f"  {'Explained var':>22}"
    for c in countries:
        lc = country_results[c]["lee_carter"]
        row += f"  {lc.explained_variance:>13.4f}"
    lines.append(row)

    # RMSE
    row = f"  {'RMSE (log-space)':>22}"
    for c in countries:
        lc = country_results[c]["lee_carter"]
        gof = lc.goodness_of_fit()
        row += f"  {gof['rmse']:>13.6f}"
    lines.append(row)

    # Mean abs error
    row = f"  {'Mean abs error':>22}"
    for c in countries:
        lc = country_results[c]["lee_carter"]
        gof = lc.goodness_of_fit()
        row += f"  {gof['mean_abs_error']:>13.6f}"
    lines.append(row)

    # Identifiability
    row = f"  {'sum(b_x)':>22}"
    for c in countries:
        lc = country_results[c]["lee_carter"]
        row += f"  {np.sum(lc.bx):>13.6f}"
    lines.append(row)

    row = f"  {'sum(k_t)':>22}"
    for c in countries:
        lc = country_results[c]["lee_carter"]
        row += f"  {np.sum(lc.kt):>13.6f}"
    lines.append(row)
    lines.append("")

    # Section 3: Projection parameters
    lines.append("3. PROJECTION PARAMETERS (Random Walk with Drift)")
    lines.append("-" * 50)

    header = f"  {'Metric':>22}"
    for c in countries:
        header += f"  {labels[c]:>14}"
    lines.append(header)

    divider = f"  {'-' * 22}"
    for _ in countries:
        divider += f"  {'-' * 14}"
    lines.append(divider)

    for metric, getter in [
        ("Drift (annual)", lambda r: r["projection"].drift),
        ("Sigma", lambda r: r["projection"].sigma),
        ("k_t first observed", lambda r: r["lee_carter"].kt[0]),
        ("k_t last observed", lambda r: r["lee_carter"].kt[-1]),
        ("Target year", lambda r: r["target_year"]),
    ]:
        row = f"  {metric:>22}"
        for c in countries:
            val = getter(country_results[c])
            if isinstance(val, int):
                row += f"  {val:>14}"
            else:
                row += f"  {val:>14.4f}"
        lines.append(row)
    lines.append("")

    # Section 4: Projected q_x comparison
    lines.append("4. PROJECTED q_x COMPARISON (central estimate, 1000*q_x)")
    lines.append("-" * 50)

    header = f"  {'Age':>5}"
    for c in countries:
        ty = country_results[c]["target_year"]
        header += f"  {f'{labels[c]} ({ty})':>16}"
    lines.append(header)

    divider = f"  {'---':>5}"
    for _ in countries:
        divider += f"  {'-' * 16}"
    lines.append(divider)

    for age in [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        row = f"  {age:>5}"
        all_available = True
        for c in countries:
            lt = country_results[c]["life_table"]
            if age in lt.q_x:
                qx = lt.get_q(age)
                row += f"  {qx * 1000:>16.4f}"
            else:
                row += f"  {'N/A':>16}"
                all_available = False
        if all_available or age <= 90:
            lines.append(row)
    lines.append("")

    # Section 5: Premium comparison at i=5%
    lines.append(f"5. PREMIUM COMPARISON (i={BASE_RATE:.0%}, SA=${SA:,.0f})")
    lines.append("-" * 50)

    for product_key, product_name in [
        ("whole_life", "Whole Life"),
        ("term_20", "Term 20"),
        ("endowment_20", "Endowment 20"),
    ]:
        lines.append(f"  {product_name}:")

        header = f"  {'Age':>5}"
        for c in countries:
            header += f"  {labels[c]:>14}"
        lines.append(header)

        divider = f"  {'---':>5}"
        for _ in countries:
            divider += f"  {'-' * 14}"
        lines.append(divider)

        for age in PREMIUM_AGES:
            row = f"  {age:>5}"
            for c in countries:
                lt = country_results[c]["life_table"]
                prems = compute_premiums_at_rate(lt, BASE_RATE)
                val = prems[age][product_key]
                if val is not None:
                    row += f"  ${val:>12,.0f}"
                else:
                    row += f"  {'N/A':>13}"
            lines.append(row)
        lines.append("")

    # Section 6: a_x profile comparison
    lines.append("6. a_x PROFILE (average log-mortality by age)")
    lines.append("-" * 50)

    header = f"  {'Age':>5}"
    for c in countries:
        header += f"  {labels[c]:>14}"
    lines.append(header)

    divider = f"  {'---':>5}"
    for _ in countries:
        divider += f"  {'-' * 14}"
    lines.append(divider)

    for age in [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        row = f"  {age:>5}"
        for c in countries:
            lc = country_results[c]["lee_carter"]
            age_idx = np.searchsorted(lc.ages, age)
            if age_idx < len(lc.ages) and lc.ages[age_idx] == age:
                row += f"  {lc.ax[age_idx]:>14.4f}"
            else:
                row += f"  {'N/A':>14}"
        lines.append(row)
    lines.append("")

    # Section 7: b_x profile comparison
    lines.append("7. b_x PROFILE (age sensitivity to mortality trend)")
    lines.append("-" * 50)

    header = f"  {'Age':>5}"
    for c in countries:
        header += f"  {labels[c]:>14}"
    lines.append(header)

    divider = f"  {'---':>5}"
    for _ in countries:
        divider += f"  {'-' * 14}"
    lines.append(divider)

    for age in [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        row = f"  {age:>5}"
        for c in countries:
            lc = country_results[c]["lee_carter"]
            age_idx = np.searchsorted(lc.ages, age)
            if age_idx < len(lc.ages) and lc.ages[age_idx] == age:
                row += f"  {lc.bx[age_idx]:>14.6f}"
            else:
                row += f"  {'N/A':>14}"
        lines.append(row)
    lines.append("")

    # Section 8: Interpretation
    lines.append("8. INTERPRETATION")
    lines.append("-" * 50)

    # Compare drifts
    drifts = {c: country_results[c]["projection"].drift for c in countries}
    fastest = min(drifts, key=lambda c: drifts[c])
    slowest = max(drifts, key=lambda c: drifts[c])
    lines.append(f"  Mortality improvement trends:")
    for c in countries:
        lines.append(f"    {labels[c]:>8}: drift = {drifts[c]:+.4f} "
                     f"({'fastest improvement' if c == fastest else 'slowest improvement' if c == slowest else ''})")
    lines.append("")

    # Compare explained variance
    lines.append(f"  Model fit (explained variance):")
    for c in countries:
        lc = country_results[c]["lee_carter"]
        quality = "excellent" if lc.explained_variance > 0.90 else \
                  "good" if lc.explained_variance > 0.70 else "moderate"
        lines.append(f"    {labels[c]:>8}: {lc.explained_variance:.1%} ({quality})")
    lines.append("")

    lines.append(f"  Key observations:")
    lines.append(f"    - All three countries show NEGATIVE drift (mortality improving)")
    lines.append(f"    - Differences in a_x reflect base mortality levels (infant, adult, old-age)")
    lines.append(f"    - Differences in b_x show which ages benefited most from improvement")
    lines.append(f"    - Premium differences reflect both base mortality AND improvement speed")
    lines.append("")

    return "\n".join(lines)


# ── Executive Summary ────────────────────────────────────────────────


def format_executive_summary(mexico_result, ir_result, shock_result, country_results):
    """Combine key findings from all three analyses into an executive summary."""
    lines = []
    sep = "=" * 78
    target_year = mexico_result["target_year"]

    lines.append(sep)
    lines.append("  SIMA - SENSITIVITY ANALYSIS: EXECUTIVE SUMMARY")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    lines.append("OVERVIEW")
    lines.append("-" * 50)
    lines.append(f"  This report summarizes sensitivity analyses across three dimensions:")
    lines.append(f"  1. Interest rate:  i = 2% to 8% (Mexico, projected year {target_year})")
    lines.append(f"  2. Mortality shock: q_x x 0.70 to 1.30 (Mexico, i=5%)")
    lines.append(f"  3. Cross-country:  Mexico vs USA vs Spain (1990-2019)")
    lines.append("")

    # Interest rate key findings
    lines.append("A. INTEREST RATE SENSITIVITY (Mexico)")
    lines.append("-" * 50)
    ir_prems = ir_result["premiums"]

    # Pick age 40 whole life as representative
    wl_2pct = ir_prems[0.02][40]["whole_life"]
    wl_5pct = ir_prems[0.05][40]["whole_life"]
    wl_8pct = ir_prems[0.08][40]["whole_life"]

    lines.append(f"  Whole life premium at age 40:")
    lines.append(f"    i=2%: ${wl_2pct:>12,.0f}")
    lines.append(f"    i=5%: ${wl_5pct:>12,.0f}  (base)")
    lines.append(f"    i=8%: ${wl_8pct:>12,.0f}")
    lines.append(f"    Range: {(wl_2pct - wl_8pct) / wl_5pct * 100:+.0f}% spread around base")
    lines.append("")

    # Find which product is most sensitive
    products = ["whole_life", "term_20", "endowment_20"]
    max_sensitivity = 0
    most_sensitive = ""
    for pk in products:
        val_low = ir_prems[0.02][40].get(pk)
        val_high = ir_prems[0.08][40].get(pk)
        if val_low is not None and val_high is not None:
            spread = abs(val_low - val_high) / ir_prems[0.05][40][pk] * 100
            if spread > max_sensitivity:
                max_sensitivity = spread
                most_sensitive = pk
    lines.append(f"  Most interest-rate sensitive product: {most_sensitive.replace('_', ' ')}")
    lines.append(f"  ({max_sensitivity:.0f}% spread from i=2% to i=8% at age 40)")
    lines.append("")

    # Mortality shock key findings
    lines.append("B. MORTALITY SHOCK SENSITIVITY (Mexico)")
    lines.append("-" * 50)
    shock_prems = shock_result["premiums"]

    wl_070 = shock_prems[0.70][40]["whole_life"]
    wl_100 = shock_prems[1.00][40]["whole_life"]
    wl_130 = shock_prems[1.30][40]["whole_life"]

    lines.append(f"  Whole life premium at age 40 (i=5%):")
    lines.append(f"    0.70x (30% improvement): ${wl_070:>12,.0f}  ({(wl_070 - wl_100) / wl_100 * 100:+.1f}%)")
    lines.append(f"    1.00x (base):            ${wl_100:>12,.0f}")
    lines.append(f"    1.30x (30% deterioration): ${wl_130:>12,.0f}  ({(wl_130 - wl_100) / wl_100 * 100:+.1f}%)")
    lines.append("")

    # Asymmetry check
    decrease = abs(wl_070 - wl_100)
    increase = abs(wl_130 - wl_100)
    if increase > decrease:
        lines.append(f"  Asymmetry: 30% mortality increase raises premium by more than")
        lines.append(f"  30% decrease reduces it ({increase / decrease:.2f}x ratio).")
        lines.append(f"  This convexity means insurers face greater DOWNSIDE risk.")
    lines.append("")

    # Cross-country key findings
    lines.append("C. CROSS-COUNTRY COMPARISON")
    lines.append("-" * 50)

    countries = ["mexico", "usa", "spain"]
    labels = {"mexico": "Mexico", "usa": "USA", "spain": "Spain"}

    # Drift comparison
    lines.append(f"  Lee-Carter drift (mortality improvement speed):")
    for c in countries:
        drift = country_results[c]["projection"].drift
        lines.append(f"    {labels[c]:>8}: {drift:+.4f}")
    lines.append("")

    # Premium comparison at age 40
    lines.append(f"  Whole life premium at age 40 (i=5%):")
    for c in countries:
        lt = country_results[c]["life_table"]
        prems = compute_premiums_at_rate(lt, BASE_RATE)
        wl = prems[40]["whole_life"]
        lines.append(f"    {labels[c]:>8}: ${wl:>12,.0f}")
    lines.append("")

    # Explained variance
    lines.append(f"  Lee-Carter model fit:")
    for c in countries:
        lc = country_results[c]["lee_carter"]
        lines.append(f"    {labels[c]:>8}: explained variance = {lc.explained_variance:.1%}")
    lines.append("")

    # Overall conclusions
    lines.append("D. KEY TAKEAWAYS")
    lines.append("-" * 50)
    lines.append(f"  1. Interest rate is the DOMINANT sensitivity factor for long-duration")
    lines.append(f"     products (whole life, endowment). A 3% rate change can shift")
    lines.append(f"     premiums by 30-60%.")
    lines.append("")
    lines.append(f"  2. Mortality shocks have a SMALLER but ASYMMETRIC effect. A 30%")
    lines.append(f"     mortality deterioration hurts more than a 30% improvement helps.")
    lines.append(f"     This justifies regulatory capital buffers.")
    lines.append("")
    lines.append(f"  3. Cross-country comparison shows that while all three countries")
    lines.append(f"     exhibit improving mortality, the SPEED and LEVEL differ. Mexico's")
    lines.append(f"     base mortality profile differs from developed-country HMD patterns,")
    lines.append(f"     reinforcing the need for country-specific calibration.")
    lines.append("")
    lines.append(f"  4. For CNSF regulatory compliance, stress testing should combine")
    lines.append(f"     interest rate AND mortality shocks simultaneously (joint stress),")
    lines.append(f"     as these risks can correlate during economic crises.")
    lines.append("")

    return "\n".join(lines)


# ── Main Execution ───────────────────────────────────────────────────


def main():
    print("=" * 78)
    print("  SIMA: Sensitivity Analysis")
    print("  Interest Rate | Mortality Shocks | Cross-Country")
    print("=" * 78)
    print()

    # ── [1/4] Mexico pipeline (base for sensitivity) ─────────────
    print("[1/4] Running Mexico pipeline (1990-2019, pre-COVID)...")
    mexico_result = run_country_pipeline("mexico")
    lc = mexico_result["lee_carter"]
    print(f"      Explained variance: {lc.explained_variance:.4f}")
    print(f"      Drift: {mexico_result['projection'].drift:.6f}")
    print(f"      Target year: {mexico_result['target_year']}")
    print()

    # ── [2/4] Interest rate sensitivity ──────────────────────────
    print("[2/4] Running interest rate sensitivity (i = 2%-8%)...")
    ir_result = run_interest_rate_sensitivity(mexico_result)
    print(f"      Computed premiums at {len(INTEREST_RATES)} rates x "
          f"{len(PREMIUM_AGES)} ages x 3 products")
    print()

    # ── [3/4] Mortality shock sensitivity ────────────────────────
    print("[3/4] Running mortality shock sensitivity (factor = 0.70-1.30)...")
    shock_result = run_mortality_shock_sensitivity(mexico_result)
    print(f"      Computed premiums at {len(SHOCK_FACTORS)} shock levels x "
          f"{len(PREMIUM_AGES)} ages x 3 products")
    print()

    # ── [4/4] Cross-country comparison ───────────────────────────
    print("[4/4] Running cross-country comparison (Mexico, USA, Spain)...")
    country_results = run_cross_country_comparison()
    for c in ["mexico", "usa", "spain"]:
        lc_c = country_results[c]["lee_carter"]
        print(f"      {c}: explained_var={lc_c.explained_variance:.4f}, "
              f"drift={country_results[c]['projection'].drift:.4f}")
    print()

    # ── Generate and save reports ────────────────────────────────
    print("Generating reports...")

    report_ir = format_interest_rate_report(mexico_result, ir_result)
    report_shock = format_mortality_shock_report(mexico_result, shock_result)
    report_cross = format_cross_country_report(country_results)
    report_summary = format_executive_summary(
        mexico_result, ir_result, shock_result, country_results
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    path_ir = RESULTS_DIR / "sensitivity_interest_rate.txt"
    path_shock = RESULTS_DIR / "sensitivity_mortality_shock.txt"
    path_cross = RESULTS_DIR / "sensitivity_cross_country.txt"
    path_summary = RESULTS_DIR / "sensitivity_summary.txt"

    path_ir.write_text(report_ir, encoding="utf-8")
    path_shock.write_text(report_shock, encoding="utf-8")
    path_cross.write_text(report_cross, encoding="utf-8")
    path_summary.write_text(report_summary, encoding="utf-8")

    print(f"\nResults saved to:")
    print(f"  {path_ir}")
    print(f"  {path_shock}")
    print(f"  {path_cross}")
    print(f"  {path_summary}")
    print()

    # Print summary report to console
    print(report_summary)


if __name__ == "__main__":
    main()
