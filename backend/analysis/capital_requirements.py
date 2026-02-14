"""
Capital Requirements Analysis: SCR under CNSF / Solvency II
=============================================================

Computes the full Solvency Capital Requirement (RCS) for a sample
Mexican insurance portfolio using the Solvency II standard formula.

Risk modules:
    1. Mortality:   +15% permanent q_x shock (death products)
    2. Longevity:   -20% permanent q_x shock (annuity products)
    3. Interest Rate: +/- 100 bps parallel shift (all products)
    4. Catastrophe: +35% one-year spike (death products, COVID-calibrated)

Aggregation:
    - Life underwriting: 3x3 correlation matrix (Solvency II Art. 136)
    - Total: life + market with rho = 0.25

Output:
    backend/analysis/results/capital_requirements_report.txt

Usage:
    cd /home/andtega349/SIMA
    venv/bin/python backend/analysis/capital_requirements.py
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection
from backend.engine.a11_portfolio import (
    Portfolio,
    Policy,
    compute_policy_bel,
    create_sample_portfolio,
)
from backend.engine.a12_scr import (
    compute_scr_mortality,
    compute_scr_longevity,
    compute_scr_interest_rate,
    compute_scr_catastrophe,
    aggregate_scr_life,
    aggregate_scr_total,
    compute_risk_margin,
    compute_solvency_ratio,
    run_full_scr,
    LIFE_CORR,
)

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
INEGI_DEATHS = str(DATA_DIR / "inegi" / "inegi_deaths.csv")
CONAPO_POP = str(DATA_DIR / "conapo" / "conapo_population.csv")
RESULTS_DIR = Path(__file__).parent / "results"

# ── Constants ────────────────────────────────────────────────────────
INTEREST_RATE = 0.05
TARGET_YEAR_OFFSET = 10
PORTFOLIO_DURATION = 15.0
COC_RATE = 0.06
CAPITAL_LEVELS = [1_000_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000]


# ── Helper: Load Mexico Life Table ───────────────────────────────────

def load_mexico_life_table():
    """
    Run Lee-Carter pipeline on Mexico (1990-2019, pre-COVID) and
    project to target year.

    Returns (life_table, target_year, lee_carter, projection).
    """
    data = MortalityData.from_inegi(
        INEGI_DEATHS, CONAPO_POP,
        sex="Total", year_start=1990, year_end=2019, age_max=100,
    )
    graduated = GraduatedRates(data, lambda_param=1e5)
    lc = LeeCarter.fit(graduated, reestimate_kt=False)
    projection = MortalityProjection(lc, horizon=30, n_simulations=1000, random_seed=42)
    target_year = int(lc.years[-1]) + TARGET_YEAR_OFFSET
    life_table = projection.to_life_table(year=target_year)

    return life_table, target_year, lc, projection


# ── Report Formatting ────────────────────────────────────────────────

def format_report(
    portfolio, life_table, target_year, lc, projection, full_result
):
    """Format the full SCR report as text."""
    lines = []
    sep = "=" * 78
    sub_sep = "-" * 50

    mort = full_result["mortality"]
    long = full_result["longevity"]
    ir = full_result["interest_rate"]
    cat = full_result["catastrophe"]
    life_agg = full_result["life_aggregation"]
    total_agg = full_result["total_aggregation"]
    rm = full_result["risk_margin"]
    bel_breakdown = full_result["bel_breakdown"]

    # ── Header ───────────────────────────────────────────────────
    lines.append(sep)
    lines.append("  SIMA - CAPITAL REQUIREMENTS: SCR UNDER CNSF / SOLVENCY II")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(sep)
    lines.append("")

    # ── Section 1: Portfolio Summary ─────────────────────────────
    lines.append("1. PORTFOLIO SUMMARY")
    lines.append(sub_sep)
    lines.append(f"  Total policies: {len(portfolio)}")
    lines.append(f"  Death products: {len(portfolio.death_products)}")
    lines.append(f"  Annuity products: {len(portfolio.annuity_products)}")
    lines.append("")

    lines.append(f"  {'ID':>6} {'Type':>12} {'Issue':>6} {'Att':>5} "
                 f"{'Dur':>4} {'SA/Pension':>14} {'n':>3}")
    lines.append(f"  {'-'*6} {'-'*12} {'-'*6} {'-'*5} {'-'*4} {'-'*14} {'-'*3}")
    for p in portfolio.policies:
        amount = f"${p.SA:>12,.0f}" if p.is_death_product else f"${p.annual_pension:>8,.0f}/yr"
        n_str = str(p.n) if p.n else "--"
        lines.append(
            f"  {p.policy_id:>6} {p.product_type:>12} {p.issue_age:>6} "
            f"{p.attained_age:>5} {p.duration:>4} {amount:>14} {n_str:>3}"
        )
    lines.append("")

    total_sa = sum(p.SA for p in portfolio.death_products)
    total_pension = sum(p.annual_pension for p in portfolio.annuity_products)
    lines.append(f"  Total sum assured:    ${total_sa:>14,.0f} MXN")
    lines.append(f"  Total annual pension: ${total_pension:>14,.0f} MXN/yr")
    lines.append("")

    # ── Section 2: Baseline BEL Decomposition ────────────────────
    lines.append("2. BASELINE BEL DECOMPOSITION")
    lines.append(sub_sep)
    lines.append(f"  Interest rate: {INTEREST_RATE:.1%}")
    lines.append(f"  Life table: Mexico projected, year {target_year} (pre-COVID)")
    lines.append("")

    breakdown = full_result.get("_breakdown_detail")
    if breakdown is None:
        breakdown = portfolio.compute_bel_breakdown(life_table, INTEREST_RATE)

    lines.append(f"  {'ID':>6} {'Type':>12} {'Att Age':>8} {'BEL':>16}")
    lines.append(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*16}")
    for entry in breakdown:
        lines.append(
            f"  {entry['policy_id']:>6} {entry['product_type']:>12} "
            f"{entry['attained_age']:>8} ${entry['bel']:>14,.2f}"
        )
    lines.append("")

    death_bel = bel_breakdown["death_bel"]
    annuity_bel = bel_breakdown["annuity_bel"]
    total_bel = bel_breakdown["total_bel"]
    lines.append(f"  Death product BEL:   ${death_bel:>14,.2f}")
    lines.append(f"  Annuity product BEL: ${annuity_bel:>14,.2f}")
    lines.append(f"  Total BEL:           ${total_bel:>14,.2f}")
    lines.append("")

    # ── Section 3: Mortality Risk SCR ────────────────────────────
    lines.append("3. MORTALITY RISK SCR")
    lines.append(sub_sep)
    lines.append(f"  Shock: +{mort['shock']:.0%} permanent q_x increase")
    lines.append(f"  Affected: {len(portfolio.death_products)} death products only")
    lines.append(f"  Regulatory basis: Solvency II standard formula (99.5% VaR)")
    lines.append("")
    lines.append(f"  BEL base (death):     ${mort['bel_base']:>14,.2f}")
    lines.append(f"  BEL stressed (death): ${mort['bel_stressed']:>14,.2f}")
    lines.append(f"  SCR_mortality:        ${mort['scr']:>14,.2f}")
    if mort['bel_base'] > 0:
        lines.append(f"  Impact: +{(mort['scr']/mort['bel_base'])*100:.1f}% of death BEL")
    lines.append("")

    # ── Section 4: Longevity Risk SCR ────────────────────────────
    lines.append("4. LONGEVITY RISK SCR")
    lines.append(sub_sep)
    lines.append(f"  Shock: -{long['shock']:.0%} permanent q_x decrease")
    lines.append(f"  Affected: {len(portfolio.annuity_products)} annuity products only")
    lines.append(f"  Rationale: Lower mortality = longer life = more pension payments")
    lines.append("")
    lines.append(f"  BEL base (annuity):     ${long['bel_base']:>14,.2f}")
    lines.append(f"  BEL stressed (annuity): ${long['bel_stressed']:>14,.2f}")
    lines.append(f"  SCR_longevity:          ${long['scr']:>14,.2f}")
    if long['bel_base'] > 0:
        lines.append(f"  Impact: +{(long['scr']/long['bel_base'])*100:.1f}% of annuity BEL")
    lines.append("")

    # ── Section 5: Interest Rate Risk SCR ────────────────────────
    lines.append("5. INTEREST RATE RISK SCR")
    lines.append(sub_sep)
    lines.append(f"  Shock: +/- 100 bps parallel shift")
    lines.append(f"  Affected: ALL products ({len(portfolio)} policies)")
    lines.append(f"  Base rate: {INTEREST_RATE:.2%} -> "
                 f"Up: {ir['rate_up']:.2%}, Down: {ir['rate_down']:.2%}")
    lines.append("")
    lines.append(f"  BEL base:   ${ir['bel_base']:>14,.2f}  (i={INTEREST_RATE:.1%})")
    lines.append(f"  BEL up:     ${ir['bel_up']:>14,.2f}  (i={ir['rate_up']:.1%})")
    lines.append(f"  BEL down:   ${ir['bel_down']:>14,.2f}  (i={ir['rate_down']:.1%})")
    lines.append(f"  SCR_ir:     ${ir['scr']:>14,.2f}")

    dominant = "DOWN" if (ir['bel_down'] - ir['bel_base']) >= (ir['bel_up'] - ir['bel_base']) else "UP"
    lines.append(f"  Dominant scenario: {dominant} (lower rates => higher PV of obligations)")
    lines.append("")

    # ── Section 6: Catastrophe Risk SCR ──────────────────────────
    lines.append("6. CATASTROPHE RISK SCR (COVID-CALIBRATED)")
    lines.append(sub_sep)
    lines.append(f"  Shock: +{(cat['cat_shock_factor']-1)*100:.0f}% one-year mortality spike")
    lines.append(f"  Affected: {len(portfolio.death_products)} death products only")
    lines.append(f"  Calibration: COVID-19 impact on Mexican mortality (INEGI/CONAPO)")
    lines.append(f"    - Pre-COVID k_t drift: -1.076/year")
    lines.append(f"    - COVID k_t reversal: ~6.76 units above trend")
    lines.append(f"    - Conservative factor: {cat['cat_shock_factor']:.2f}x")
    lines.append("")
    lines.append(f"  SCR_catastrophe:    ${cat['scr']:>14,.2f}")
    lines.append("")

    if "details" in cat and cat["details"]:
        lines.append(f"  Per-policy catastrophe impact:")
        lines.append(f"  {'ID':>6} {'Age':>5} {'q_base':>10} {'q_shock':>10} "
                     f"{'delta_q':>10} {'Extra Claim':>14}")
        lines.append(f"  {'-'*6} {'-'*5} {'-'*10} {'-'*10} {'-'*10} {'-'*14}")
        for d in cat["details"]:
            lines.append(
                f"  {d['policy_id']:>6} {d['attained_age']:>5} "
                f"{d['q_base']:>10.6f} {d['q_shocked']:>10.6f} "
                f"{d['delta_q']:>10.6f} ${d['extra_claim']:>12,.2f}"
            )
        lines.append("")

    # ── Section 7: Life Underwriting Aggregation ─────────────────
    lines.append("7. LIFE UNDERWRITING AGGREGATION")
    lines.append(sub_sep)
    lines.append("  Correlation matrix (Solvency II Article 136):")
    lines.append(f"              {'Mort':>10} {'Long':>10} {'Cat':>10}")
    labels = ["Mort", "Long", "Cat"]
    for i, label in enumerate(labels):
        row = f"  {label:>10}"
        for j in range(3):
            row += f"  {LIFE_CORR[i,j]:>8.2f}"
        lines.append(row)
    lines.append("")

    lines.append(f"  Individual SCR components:")
    lines.append(f"    SCR_mortality:       ${mort['scr']:>14,.2f}")
    lines.append(f"    SCR_longevity:       ${long['scr']:>14,.2f}")
    lines.append(f"    SCR_catastrophe:     ${cat['scr']:>14,.2f}")
    lines.append(f"    Sum (undiversified): ${life_agg['sum_individual']:>14,.2f}")
    lines.append("")
    lines.append(f"  Aggregated SCR_life:   ${life_agg['scr_life']:>14,.2f}")
    lines.append(f"  Diversification:       ${life_agg['diversification_benefit']:>14,.2f}")
    lines.append(f"  Diversification pct:   {life_agg['diversification_pct']:>13.1f}%")
    lines.append("")

    # ── Section 8: Total SCR Aggregation ─────────────────────────
    lines.append("8. TOTAL SCR AGGREGATION (Life + Market)")
    lines.append(sub_sep)
    lines.append(f"  SCR_life:              ${total_agg['scr_life']:>14,.2f}")
    lines.append(f"  SCR_ir (market):       ${total_agg['scr_ir']:>14,.2f}")
    lines.append(f"  Correlation rho:       {total_agg['rho']:>14.2f}")
    lines.append(f"  Sum (undiversified):   ${total_agg['sum_individual']:>14,.2f}")
    lines.append("")
    lines.append(f"  SCR_total:             ${total_agg['scr_total']:>14,.2f}")
    lines.append(f"  Diversification:       ${total_agg['diversification_benefit']:>14,.2f}")
    lines.append("")

    # ── Section 9: Risk Margin ───────────────────────────────────
    lines.append("9. RISK MARGIN (Margen de Riesgo)")
    lines.append(sub_sep)
    lines.append(f"  Cost-of-Capital rate:  {rm['coc_rate']:.0%}")
    lines.append(f"  Portfolio duration:    {rm['duration']:.0f} years")
    lines.append(f"  Discount rate:         {INTEREST_RATE:.1%}")
    lines.append(f"  Annuity factor:        {rm['annuity_factor']:.4f}")
    lines.append(f"  SCR_total:             ${total_agg['scr_total']:>14,.2f}")
    lines.append("")
    lines.append(f"  Risk Margin (MdR):     ${rm['risk_margin']:>14,.2f}")
    lines.append(f"  Formula: MdR = CoC x SCR x annuity_factor")
    lines.append(f"           = {rm['coc_rate']:.2f} x "
                 f"{total_agg['scr_total']:,.0f} x {rm['annuity_factor']:.4f}")
    lines.append("")

    # ── Section 10: Technical Provisions ─────────────────────────
    lines.append("10. TECHNICAL PROVISIONS (Reservas Tecnicas)")
    lines.append(sub_sep)
    tp = full_result["technical_provisions"]
    lines.append(f"  BEL (Mejor Estimacion):    ${full_result['bel_base']:>14,.2f}")
    lines.append(f"  Risk Margin (MdR):         ${rm['risk_margin']:>14,.2f}")
    lines.append(f"  ----------------------------------------")
    lines.append(f"  Technical Provisions (TP):  ${tp:>14,.2f}")
    lines.append("")

    # ── Section 11: Solvency Ratio ───────────────────────────────
    lines.append("11. SOLVENCY RATIO AT MULTIPLE CAPITAL LEVELS")
    lines.append(sub_sep)
    lines.append(f"  SCR_total: ${total_agg['scr_total']:>14,.2f}")
    lines.append("")
    lines.append(f"  {'Capital (MXN)':>18} {'Ratio':>8} {'Status':>12}")
    lines.append(f"  {'-'*18} {'-'*8} {'-'*12}")

    for capital in CAPITAL_LEVELS:
        sol = compute_solvency_ratio(capital, total_agg["scr_total"])
        status = "SOLVENT" if sol["is_solvent"] else "INSOLVENT"
        if sol["ratio"] >= 2.0:
            status = "VERY STRONG"
        elif sol["ratio"] >= 1.5:
            status = "STRONG"
        lines.append(
            f"  ${capital:>16,.0f} {sol['ratio_pct']:>7.1f}% {status:>12}"
        )
    lines.append("")
    lines.append(f"  CNSF minimum: 100% (Indice de Solvencia >= 1.0)")
    lines.append(f"  Best practice: 150-200%")
    lines.append("")

    # ── Section 12: SCR Decomposition Summary ────────────────────
    lines.append("12. SCR DECOMPOSITION SUMMARY")
    lines.append(sub_sep)

    components = [
        ("Mortality risk", mort["scr"]),
        ("Longevity risk", long["scr"]),
        ("Catastrophe risk", cat["scr"]),
        ("Interest rate risk", ir["scr"]),
    ]
    total_undiv = sum(c[1] for c in components)

    lines.append(f"  {'Component':>22} {'SCR':>14} {'% of Total':>12} {'% Undiv':>10}")
    lines.append(f"  {'-'*22} {'-'*14} {'-'*12} {'-'*10}")
    for name, scr in components:
        pct_total = (scr / total_agg["scr_total"] * 100) if total_agg["scr_total"] > 0 else 0
        pct_undiv = (scr / total_undiv * 100) if total_undiv > 0 else 0
        lines.append(f"  {name:>22} ${scr:>12,.2f} {pct_total:>11.1f}% {pct_undiv:>9.1f}%")

    lines.append(f"  {'-'*22} {'-'*14}")
    lines.append(f"  {'Sum (undiversified)':>22} ${total_undiv:>12,.2f}")
    lines.append(f"  {'Life aggregation':>22} ${life_agg['scr_life']:>12,.2f}")
    lines.append(f"  {'Total SCR':>22} ${total_agg['scr_total']:>12,.2f}")
    lines.append(f"  {'Diversification saved':>22} ${(total_undiv - total_agg['scr_total']):>12,.2f}")
    lines.append("")

    # ── Interpretation ───────────────────────────────────────────
    lines.append("INTERPRETATION")
    lines.append(sub_sep)

    # Identify largest risk
    largest_name, largest_scr = max(components, key=lambda x: x[1])
    lines.append(f"  Largest risk component: {largest_name} "
                 f"(${largest_scr:,.0f})")
    lines.append("")

    lines.append("  Key observations:")
    lines.append(f"  1. Interest rate risk is typically the LARGEST component because it")
    lines.append(f"     affects ALL products (every discounted cash flow changes).")
    lines.append(f"  2. Mortality and longevity risks offset partially (rho = -0.25),")
    lines.append(f"     creating a {life_agg['diversification_pct']:.1f}% "
                 f"diversification benefit in the life module.")
    lines.append(f"  3. The catastrophe module uses COVID-calibrated shocks (+35%),")
    lines.append(f"     which is specific to the Mexican mortality experience.")
    lines.append(f"  4. Technical provisions = BEL + MdR ensures the insurer can")
    lines.append(f"     transfer the portfolio to a third party if needed.")
    lines.append(f"  5. The diversification benefit rewards insurers for writing")
    lines.append(f"     BOTH death products and annuities (natural hedge).")
    lines.append("")

    return "\n".join(lines)


# ── Main Execution ───────────────────────────────────────────────────

def main():
    print("=" * 78)
    print("  SIMA: Capital Requirements (SCR)")
    print("  Solvency II / CNSF Standard Formula")
    print("=" * 78)
    print()

    # ── [1/6] Load Mexico life table ─────────────────────────────
    print("[1/6] Loading Mexico life table (1990-2019, pre-COVID, projected)...")
    life_table, target_year, lc, projection = load_mexico_life_table()
    print(f"      Explained variance: {lc.explained_variance:.4f}")
    print(f"      Drift: {projection.drift:.6f}")
    print(f"      Target year: {target_year}")
    print()

    # ── [2/6] Build sample portfolio ─────────────────────────────
    print("[2/6] Building sample portfolio (12 policies)...")
    portfolio = create_sample_portfolio()
    print(f"      Death products: {len(portfolio.death_products)}")
    print(f"      Annuity products: {len(portfolio.annuity_products)}")
    print()

    # ── [3/6] Compute baseline BEL ───────────────────────────────
    print("[3/6] Computing baseline BEL...")
    bel_types = portfolio.compute_bel_by_type(life_table, INTEREST_RATE)
    print(f"      Death BEL:   ${bel_types['death_bel']:>14,.2f}")
    print(f"      Annuity BEL: ${bel_types['annuity_bel']:>14,.2f}")
    print(f"      Total BEL:   ${bel_types['total_bel']:>14,.2f}")
    print()

    # ── [4/6] Compute 4 individual SCR components ────────────────
    print("[4/6] Computing individual SCR components...")
    full_result = run_full_scr(
        portfolio, life_table, INTEREST_RATE,
        portfolio_duration=PORTFOLIO_DURATION,
        coc_rate=COC_RATE,
    )
    print(f"      SCR_mortality:   ${full_result['mortality']['scr']:>14,.2f}")
    print(f"      SCR_longevity:   ${full_result['longevity']['scr']:>14,.2f}")
    print(f"      SCR_interest:    ${full_result['interest_rate']['scr']:>14,.2f}")
    print(f"      SCR_catastrophe: ${full_result['catastrophe']['scr']:>14,.2f}")
    print()

    # ── [5/6] Aggregate ──────────────────────────────────────────
    life_agg = full_result["life_aggregation"]
    total_agg = full_result["total_aggregation"]
    print("[5/6] Aggregating...")
    print(f"      SCR_life (aggregated): ${life_agg['scr_life']:>14,.2f}")
    print(f"      Diversification:       {life_agg['diversification_pct']:.1f}%")
    print(f"      SCR_total:             ${total_agg['scr_total']:>14,.2f}")
    print()

    # ── [6/6] Risk margin and technical provisions ───────────────
    rm = full_result["risk_margin"]
    tp = full_result["technical_provisions"]
    print("[6/6] Risk margin and technical provisions...")
    print(f"      Risk margin (MdR): ${rm['risk_margin']:>14,.2f}")
    print(f"      Tech provisions:   ${tp:>14,.2f}")
    print()

    # ── Generate and save report ─────────────────────────────────
    print("Generating report...")
    report = format_report(
        portfolio, life_table, target_year, lc, projection, full_result
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "capital_requirements_report.txt"
    report_path.write_text(report, encoding="utf-8")

    print(f"\nResults saved to: {report_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
