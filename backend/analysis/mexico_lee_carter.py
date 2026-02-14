"""
Lee-Carter Pipeline on Real Mexican Mortality Data
====================================================

Runs the full mortality modeling pipeline on real INEGI/CONAPO data:
    1. Load deaths + population -> MortalityData
    2. Graduate with Whittaker-Henderson -> GraduatedRates
    3. Fit Lee-Carter (a_x, b_x, k_t) via SVD + k_t re-estimation
    4. Project 30 years forward with RWD
    5. Compare projected life tables against 4 regulatory tables
    6. Compute insurance premiums from projected mortality

Two parallel analyses:
    A. Pre-COVID (1990-2019): clean baseline, no pandemic distortion
    B. Full period (1990-2024): includes COVID-19 spike (2020-2021)

Usage:
    cd /home/andtega349/SIMA
    venv/bin/python backend/analysis/mexico_lee_carter.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure imports work from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a10_validation import MortalityComparison

# ── Paths ───────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"

INEGI_DEATHS = str(DATA_DIR / "inegi" / "inegi_deaths.csv")
CONAPO_POP = str(DATA_DIR / "conapo" / "conapo_population.csv")

REGULATORY_TABLES = {
    "CNSF 2000-I (M)": (str(DATA_DIR / "cnsf" / "cnsf_2000_i.csv"), "male"),
    "CNSF 2000-I (F)": (str(DATA_DIR / "cnsf" / "cnsf_2000_i.csv"), "female"),
    "CNSF 2000-G (M)": (str(DATA_DIR / "cnsf" / "cnsf_2000_g.csv"), "male"),
    "CNSF 2000-G (F)": (str(DATA_DIR / "cnsf" / "cnsf_2000_g.csv"), "female"),
    "CNSFM 2013":      (str(DATA_DIR / "cnsf" / "cnsf_2013.csv"), "male"),
    "EMSSA 2009 (M)":  (str(DATA_DIR / "cnsf" / "emssa_2009.csv"), "male"),
    "EMSSA 2009 (F)":  (str(DATA_DIR / "cnsf" / "emssa_2009.csv"), "female"),
}

RESULTS_DIR = Path(__file__).parent / "results"

# ── Pipeline Functions ──────────────────────────────────────────────


def load_mexican_data(year_end, sex="Total"):
    """Load INEGI deaths + CONAPO population into MortalityData."""
    return MortalityData.from_inegi(
        deaths_filepath=INEGI_DEATHS,
        population_filepath=CONAPO_POP,
        sex=sex,
        year_start=1990,
        year_end=year_end,
        age_max=100,
    )


def run_pipeline(mortality_data, horizon=30):
    """Graduate -> Lee-Carter -> Project. Returns all intermediate objects.

    Uses reestimate_kt=False because Whittaker-Henderson graduation
    changes the mortality surface (smooths mx), so the re-estimation
    equation sum(E_x * exp(a_x + b_x*k_t)) = sum(D_x) cannot be
    satisfied exactly -- the graduated rates don't reproduce raw deaths.
    The SVD-estimated k_t is preferred here; it minimizes log-space error
    which is consistent with the Lee-Carter log-bilinear formulation.
    """
    graduated = GraduatedRates(mortality_data, lambda_param=1e5)
    lc = LeeCarter.fit(graduated, reestimate_kt=False)
    projection = MortalityProjection(lc, horizon=horizon, n_simulations=1000, random_seed=42)
    return graduated, lc, projection


def compare_against_regulatory(projection, target_year):
    """Compare projected life table vs all regulatory tables."""
    projected_lt = projection.to_life_table(year=target_year)

    comparisons = {}
    for name, (filepath, sex) in REGULATORY_TABLES.items():
        try:
            reg_lt = LifeTable.from_regulatory_table(filepath, sex=sex)
            comp = MortalityComparison(projected_lt, reg_lt, name=name)
            comparisons[name] = comp
        except (ValueError, FileNotFoundError) as e:
            comparisons[name] = f"SKIPPED: {e}"

    return projected_lt, comparisons


def compute_premiums(life_table, interest_rate=0.05):
    """Compute sample premiums for standard products."""
    comm = CommutationFunctions(life_table, interest_rate=interest_rate)
    pc = PremiumCalculator(comm)

    results = {}
    for age in [25, 30, 35, 40, 45, 50, 55, 60]:
        entry = {"whole_life": pc.whole_life(SA=1_000_000, x=age)}

        if age + 20 <= life_table.omega:
            entry["term_20"] = pc.term(SA=1_000_000, x=age, n=20)
            entry["endowment_20"] = pc.endowment(SA=1_000_000, x=age, n=20)
        else:
            entry["term_20"] = None
            entry["endowment_20"] = None

        results[age] = entry

    return results


# ── Report Formatting ───────────────────────────────────────────────


def format_report(analysis_name, mortality_data, lc, projection, projected_lt,
                  comparisons, premiums):
    """Build a complete text report for one analysis."""
    lines = []
    sep = "=" * 72

    # Header
    lines.append(sep)
    lines.append(f"  SIMA - Lee-Carter Analysis: {analysis_name}")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # ── Section 1: Data Summary ─────────────────────────────────────
    lines.append("1. DATA SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Source:       INEGI deaths + CONAPO population")
    lines.append(f"  Sex:          Total (both sexes combined)")
    lines.append(f"  Years:        {int(mortality_data.years[0])}-{int(mortality_data.years[-1])} "
                 f"({len(mortality_data.years)} years)")
    lines.append(f"  Ages:         {int(mortality_data.ages[0])}-{int(mortality_data.ages[-1])} "
                 f"({len(mortality_data.ages)} ages)")
    lines.append(f"  Matrix shape: {mortality_data.mx.shape} (ages x years)")
    lines.append("")

    # ── Section 2: Lee-Carter Diagnostics ───────────────────────────
    lines.append("2. LEE-CARTER MODEL DIAGNOSTICS")
    lines.append("-" * 40)

    gof = lc.goodness_of_fit()
    validation = lc.validate()

    lines.append(f"  Explained variance:  {lc.explained_variance:.4f} ({lc.explained_variance*100:.1f}%)")
    lines.append(f"  RMSE (log-space):    {gof['rmse']:.6f}")
    lines.append(f"  Max abs error:       {gof['max_abs_error']:.6f}")
    lines.append(f"  Mean abs error:      {gof['mean_abs_error']:.6f}")
    lines.append("")
    lines.append(f"  Constraints:")
    lines.append(f"    sum(b_x) = 1:  {'PASS' if validation['bx_sums_to_one'] else 'FAIL'} "
                 f"(actual: {np.sum(lc.bx):.10f})")
    lines.append(f"    sum(k_t) = 0:  {'PASS' if validation['kt_sums_to_zero'] else 'FAIL'} "
                 f"(actual: {np.sum(lc.kt):.10f})")
    lines.append(f"    No NaN:        {'PASS' if validation['no_nan'] else 'FAIL'}")
    lines.append(f"    Var > 50%:     {'PASS' if validation['explained_var_reasonable'] else 'FAIL'}")
    lines.append("")

    # ── Section 3: Projection Parameters ────────────────────────────
    lines.append("3. MORTALITY PROJECTION (Random Walk with Drift)")
    lines.append("-" * 40)

    proj_val = projection.validate()

    lines.append(f"  Horizon:          {projection.horizon} years "
                 f"({int(projection.projected_years[0])}-{int(projection.projected_years[-1])})")
    lines.append(f"  Simulations:      {projection.n_simulations}")
    lines.append(f"  Drift (annual):   {projection.drift:.6f}")
    lines.append(f"  Sigma:            {projection.sigma:.6f}")
    lines.append(f"  k_t last observed: {lc.kt[-1]:.4f} (year {int(lc.years[-1])})")
    lines.append(f"  k_t central end:   {projection.kt_central[-1]:.4f} "
                 f"(year {int(projection.projected_years[-1])})")
    lines.append("")
    lines.append(f"  Drift interpretation:")
    if projection.drift < 0:
        lines.append(f"    Negative drift => mortality is IMPROVING over time")
        lines.append(f"    Annual improvement rate ~ {abs(projection.drift):.4f} "
                     f"in k_t units")
    else:
        lines.append(f"    Positive/zero drift => mortality NOT improving (unusual)")
        lines.append(f"    This may indicate COVID distortion in the data")
    lines.append("")

    # k_t time series (selected years)
    lines.append("  k_t time series (observed):")
    step = max(1, len(lc.years) // 8)
    for i in range(0, len(lc.years), step):
        lines.append(f"    {int(lc.years[i])}: {lc.kt[i]:>10.4f}")
    if (len(lc.years) - 1) % step != 0:
        lines.append(f"    {int(lc.years[-1])}: {lc.kt[-1]:>10.4f}")
    lines.append("")

    # ── Section 4: Projected Life Table ─────────────────────────────
    target_year = int(projection.projected_years[9])  # 10 years out
    lines.append(f"4. PROJECTED LIFE TABLE (year {target_year}, central estimate)")
    lines.append("-" * 40)
    lines.append(f"  Age range: {projected_lt.min_age}-{projected_lt.max_age}")
    lines.append(f"  Radix (l_0): {projected_lt.l_x[projected_lt.min_age]:,.0f}")
    lines.append("")
    lines.append(f"  {'Age':>5}  {'l_x':>12}  {'q_x':>10}  {'1000*q_x':>10}")
    lines.append(f"  {'---':>5}  {'---':>12}  {'---':>10}  {'--------':>10}")
    for age in [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        if age in projected_lt.l_x:
            lx = projected_lt.l_x[age]
            qx = projected_lt.q_x[age]
            lines.append(f"  {age:>5}  {lx:>12,.1f}  {qx:>10.6f}  {qx*1000:>10.4f}")
    lines.append("")

    # ── Section 5: Regulatory Comparisons ───────────────────────────
    lines.append("5. REGULATORY TABLE COMPARISONS")
    lines.append("-" * 40)
    lines.append(f"  Projected year: {target_year} (central estimate)")
    lines.append("")

    # Table header
    header = f"  {'Table':<22} {'Ages':>6} {'RMSE(20-80)':>12} {'Mean Ratio':>11} {'Min Ratio':>10} {'Max Ratio':>10}"
    lines.append(header)
    lines.append(f"  {'-'*21}  {'-'*5}  {'-'*11}  {'-'*10}  {'-'*9}  {'-'*9}")

    for name, comp in comparisons.items():
        if isinstance(comp, str):
            lines.append(f"  {name:<22} {comp}")
            continue

        s = comp.summary()
        n_ages = s["n_ages"]
        rmse = s["rmse"]
        mean_r = s["mean_ratio"]
        min_r = s["min_ratio"]
        max_r = s["max_ratio"]
        lines.append(
            f"  {name:<22} {n_ages:>6} {rmse:>12.6f} {mean_r:>11.4f} {min_r:>10.4f} {max_r:>10.4f}"
        )
    lines.append("")

    # Detailed ratios for EMSSA 2009 (M) -- the primary benchmark
    emssa_key = "EMSSA 2009 (M)"
    if emssa_key in comparisons and not isinstance(comparisons[emssa_key], str):
        comp = comparisons[emssa_key]
        lines.append(f"  Detailed q_x ratios vs {emssa_key} (projected/regulatory):")
        ratios = comp.qx_ratio()
        ages = comp.overlap_ages[:-1]
        lines.append(f"  {'Age':>5}  {'Proj q_x':>12}  {'Reg q_x':>12}  {'Ratio':>8}")
        lines.append(f"  {'---':>5}  {'--------':>12}  {'-------':>12}  {'-----':>8}")
        for i, age in enumerate(ages):
            if age % 10 == 0 or age < 5:
                pq = projected_lt.get_q(age)
                rq = comp.regulatory.get_q(age)
                lines.append(f"  {age:>5}  {pq:>12.6f}  {rq:>12.6f}  {ratios[i]:>8.4f}")
        lines.append("")

    # ── Section 6: Insurance Premiums ───────────────────────────────
    lines.append("6. NET ANNUAL PREMIUMS (SA = $1,000,000 MXN, i = 5%)")
    lines.append("-" * 40)
    lines.append(f"  Based on projected life table for year {target_year}")
    lines.append("")

    header_p = f"  {'Age':>5}  {'Whole Life':>14}  {'Term 20':>14}  {'Endowment 20':>14}"
    lines.append(header_p)
    lines.append(f"  {'---':>5}  {'-'*14}  {'-'*14}  {'-'*14}")

    for age in sorted(premiums.keys()):
        p = premiums[age]
        wl = f"${p['whole_life']:>12,.2f}"
        t20 = f"${p['term_20']:>12,.2f}" if p['term_20'] is not None else f"{'N/A':>13}"
        e20 = f"${p['endowment_20']:>12,.2f}" if p['endowment_20'] is not None else f"{'N/A':>13}"
        lines.append(f"  {age:>5}  {wl}  {t20}  {e20}")
    lines.append("")

    # ── Section 7: Confidence Intervals ─────────────────────────────
    lines.append("7. CONFIDENCE INTERVALS (90% CI from 1000 simulations)")
    lines.append("-" * 40)

    central_lt, optimistic_lt, pessimistic_lt = projection.to_life_table_with_ci(
        year=target_year
    )

    lines.append(f"  q_x at selected ages for year {target_year}:")
    lines.append(f"  {'Age':>5}  {'Optimistic':>12}  {'Central':>12}  {'Pessimistic':>12}")
    lines.append(f"  {'---':>5}  {'----------':>12}  {'-------':>12}  {'-----------':>12}")
    for age in [30, 40, 50, 60, 70, 80]:
        if age in central_lt.q_x and age in optimistic_lt.q_x and age in pessimistic_lt.q_x:
            q_c = central_lt.get_q(age)
            q_o = optimistic_lt.get_q(age)
            q_p = pessimistic_lt.get_q(age)
            lines.append(f"  {age:>5}  {q_o:>12.6f}  {q_c:>12.6f}  {q_p:>12.6f}")
    lines.append("")

    return "\n".join(lines)


def format_covid_comparison(report_pre, report_full,
                            lc_pre, lc_full,
                            proj_pre, proj_full,
                            premiums_pre, premiums_full):
    """Build side-by-side COVID impact comparison."""
    lines = []
    sep = "=" * 72

    lines.append(sep)
    lines.append("  SIMA - COVID-19 IMPACT COMPARISON")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # ── Drift comparison ────────────────────────────────────────────
    lines.append("1. LEE-CARTER PARAMETER COMPARISON")
    lines.append("-" * 50)
    lines.append(f"  {'Metric':<30} {'Pre-COVID':>14} {'Full':>14} {'Diff':>14}")
    lines.append(f"  {'-'*29}  {'-'*13}  {'-'*13}  {'-'*13}")

    lines.append(f"  {'Explained variance':<30} "
                 f"{lc_pre.explained_variance:>13.4f}  "
                 f"{lc_full.explained_variance:>13.4f}  "
                 f"{lc_full.explained_variance - lc_pre.explained_variance:>+13.4f}")

    gof_pre = lc_pre.goodness_of_fit()
    gof_full = lc_full.goodness_of_fit()
    lines.append(f"  {'RMSE (log-space)':<30} "
                 f"{gof_pre['rmse']:>13.6f}  "
                 f"{gof_full['rmse']:>13.6f}  "
                 f"{gof_full['rmse'] - gof_pre['rmse']:>+13.6f}")

    lines.append(f"  {'k_t drift (annual)':<30} "
                 f"{proj_pre.drift:>13.6f}  "
                 f"{proj_full.drift:>13.6f}  "
                 f"{proj_full.drift - proj_pre.drift:>+13.6f}")

    lines.append(f"  {'k_t sigma':<30} "
                 f"{proj_pre.sigma:>13.6f}  "
                 f"{proj_full.sigma:>13.6f}  "
                 f"{proj_full.sigma - proj_pre.sigma:>+13.6f}")

    lines.append(f"  {'k_t last observed':<30} "
                 f"{lc_pre.kt[-1]:>13.4f}  "
                 f"{lc_full.kt[-1]:>13.4f}  "
                 f"{lc_full.kt[-1] - lc_pre.kt[-1]:>+13.4f}")
    lines.append("")

    lines.append("  Interpretation:")
    drift_diff = proj_full.drift - proj_pre.drift
    if drift_diff > 0:
        lines.append(f"    Including COVID years makes the drift {abs(drift_diff):.6f} LESS negative")
        lines.append(f"    (mortality improvement appears slower when COVID spike is included)")
    else:
        lines.append(f"    Including COVID years makes the drift {abs(drift_diff):.6f} MORE negative")
    lines.append("")

    # ── Premium comparison ──────────────────────────────────────────
    lines.append("2. PREMIUM IMPACT (SA = $1,000,000 MXN, i = 5%)")
    lines.append("-" * 50)
    lines.append(f"  Whole Life Annual Premiums:")
    lines.append(f"  {'Age':>5}  {'Pre-COVID':>14}  {'Full':>14}  {'Diff':>14}  {'% Change':>10}")
    lines.append(f"  {'---':>5}  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*10}")

    for age in sorted(premiums_pre.keys()):
        p_pre = premiums_pre[age]["whole_life"]
        p_full = premiums_full[age]["whole_life"]
        diff = p_full - p_pre
        pct = (diff / p_pre) * 100 if p_pre != 0 else 0.0
        lines.append(
            f"  {age:>5}  ${p_pre:>12,.2f}  ${p_full:>12,.2f}  "
            f"${diff:>+12,.2f}  {pct:>+9.2f}%"
        )
    lines.append("")

    # Term premiums
    lines.append(f"  Term 20 Annual Premiums:")
    lines.append(f"  {'Age':>5}  {'Pre-COVID':>14}  {'Full':>14}  {'Diff':>14}  {'% Change':>10}")
    lines.append(f"  {'---':>5}  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*10}")

    for age in sorted(premiums_pre.keys()):
        t_pre = premiums_pre[age].get("term_20")
        t_full = premiums_full[age].get("term_20")
        if t_pre is not None and t_full is not None:
            diff = t_full - t_pre
            pct = (diff / t_pre) * 100 if t_pre != 0 else 0.0
            lines.append(
                f"  {age:>5}  ${t_pre:>12,.2f}  ${t_full:>12,.2f}  "
                f"${diff:>+12,.2f}  {pct:>+9.2f}%"
            )
    lines.append("")

    # ── k_t trajectory comparison ───────────────────────────────────
    lines.append("3. k_t TRAJECTORY COMPARISON")
    lines.append("-" * 50)

    # Find overlapping years
    pre_years = set(lc_pre.years.astype(int))
    full_years = set(lc_full.years.astype(int))
    overlap_years = sorted(pre_years & full_years)

    lines.append(f"  {'Year':>6}  {'k_t (pre-COVID)':>16}  {'k_t (full)':>16}  {'Difference':>12}")
    lines.append(f"  {'----':>6}  {'-'*16}  {'-'*16}  {'-'*12}")

    step = max(1, len(overlap_years) // 10)
    for i in range(0, len(overlap_years), step):
        year = overlap_years[i]
        kt_pre_idx = np.searchsorted(lc_pre.years.astype(int), year)
        kt_full_idx = np.searchsorted(lc_full.years.astype(int), year)
        kp = lc_pre.kt[kt_pre_idx]
        kf = lc_full.kt[kt_full_idx]
        lines.append(f"  {year:>6}  {kp:>16.4f}  {kf:>16.4f}  {kf - kp:>+12.4f}")

    # Show COVID years in full model
    covid_years = sorted(full_years - pre_years)
    if covid_years:
        lines.append("")
        lines.append(f"  COVID-era years (only in full model):")
        for year in covid_years:
            idx = np.searchsorted(lc_full.years.astype(int), year)
            lines.append(f"  {year:>6}  {'---':>16}  {lc_full.kt[idx]:>16.4f}")
    lines.append("")

    return "\n".join(lines)


# ── Main Execution ──────────────────────────────────────────────────


def main():
    print("=" * 72)
    print("  SIMA: Lee-Carter Pipeline on Real Mexican Mortality Data")
    print("=" * 72)
    print()

    # Determine target year for comparisons: 10 years after last observed
    # Pre-COVID: last year 2019 -> projection starts 2020 -> target 2030
    # Full: last year 2024 -> projection starts 2025 -> target 2035
    TARGET_YEAR_PRE = 2030
    TARGET_YEAR_FULL = 2035

    # ── Analysis A: Pre-COVID (1990-2019) ───────────────────────────
    print("[A] Loading Mexican mortality data (1990-2019, pre-COVID)...")
    data_pre = load_mexican_data(year_end=2019)
    print(f"    Loaded: {data_pre.mx.shape[0]} ages x {data_pre.mx.shape[1]} years")

    print("[A] Running pipeline: Graduate -> Lee-Carter -> Project...")
    grad_pre, lc_pre, proj_pre = run_pipeline(data_pre, horizon=30)
    print(f"    Explained variance: {lc_pre.explained_variance:.4f}")
    print(f"    Drift: {proj_pre.drift:.6f}, Sigma: {proj_pre.sigma:.6f}")

    print(f"[A] Comparing vs regulatory tables (target year {TARGET_YEAR_PRE})...")
    lt_pre, comp_pre = compare_against_regulatory(proj_pre, target_year=TARGET_YEAR_PRE)

    print("[A] Computing premiums...")
    prem_pre = compute_premiums(lt_pre)

    report_pre = format_report(
        f"Pre-COVID (1990-2019) -> {TARGET_YEAR_PRE}",
        data_pre, lc_pre, proj_pre, lt_pre, comp_pre, prem_pre
    )
    print("[A] Pre-COVID analysis complete.")
    print()

    # ── Analysis B: Full period (1990-2024) ─────────────────────────
    print("[B] Loading Mexican mortality data (1990-2024, full period)...")
    data_full = load_mexican_data(year_end=2024)
    print(f"    Loaded: {data_full.mx.shape[0]} ages x {data_full.mx.shape[1]} years")

    print("[B] Running pipeline: Graduate -> Lee-Carter -> Project...")
    grad_full, lc_full, proj_full = run_pipeline(data_full, horizon=30)
    print(f"    Explained variance: {lc_full.explained_variance:.4f}")
    print(f"    Drift: {proj_full.drift:.6f}, Sigma: {proj_full.sigma:.6f}")

    print(f"[B] Comparing vs regulatory tables (target year {TARGET_YEAR_FULL})...")
    lt_full, comp_full = compare_against_regulatory(proj_full, target_year=TARGET_YEAR_FULL)

    print("[B] Computing premiums...")
    prem_full = compute_premiums(lt_full)

    report_full = format_report(
        f"Full Period (1990-2024) -> {TARGET_YEAR_FULL}",
        data_full, lc_full, proj_full, lt_full, comp_full, prem_full
    )
    print("[B] Full period analysis complete.")
    print()

    # ── COVID Comparison ────────────────────────────────────────────
    print("[C] Building COVID impact comparison...")
    report_covid = format_covid_comparison(
        report_pre, report_full,
        lc_pre, lc_full,
        proj_pre, proj_full,
        prem_pre, prem_full,
    )
    print("[C] Comparison complete.")
    print()

    # ── Save Results ────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    path_pre = RESULTS_DIR / "mexico_pre_covid_2019.txt"
    path_full = RESULTS_DIR / "mexico_full_2024.txt"
    path_covid = RESULTS_DIR / "mexico_covid_comparison.txt"

    path_pre.write_text(report_pre, encoding="utf-8")
    path_full.write_text(report_full, encoding="utf-8")
    path_covid.write_text(report_covid, encoding="utf-8")

    print(f"Results saved to:")
    print(f"  {path_pre}")
    print(f"  {path_full}")
    print(f"  {path_covid}")
    print()

    # ── Print Reports ───────────────────────────────────────────────
    print(report_pre)
    print()
    print(report_full)
    print()
    print(report_covid)


if __name__ == "__main__":
    main()
