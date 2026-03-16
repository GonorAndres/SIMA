#!/usr/bin/env python3
"""Post-deploy production validation script.

Validates that the deployed SIMA API returns actuarially reasonable values
for the Mexican insurance market. Uses only stdlib (no pip dependencies)
so it can run on any GitHub Actions runner.

Usage:
    python scripts/validate_production.py [BASE_URL]
    python scripts/validate_production.py https://sima-451451662791.us-central1.run.app

Exit code 0 = all tests pass, 1 = failures detected.
"""

import json
import sys
import urllib.request
import urllib.error

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://sima-451451662791.us-central1.run.app"
API = f"{BASE_URL}/api"

passed = 0
failed = 0
results = []


def get(path: str) -> dict:
    url = f"{API}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def post(path: str, body: dict = None) -> dict:
    url = f"{API}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def check(test_id: str, condition: bool, msg: str):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    results.append(f"  {status}  {test_id}: {msg}")
    print(f"  {'✓' if condition else '✗'}  {test_id}: {msg}")


# ── A: Health ──────────────────────────────────────────────

print("\n=== A: Health ===")
health = get("/health")
check("A1", health["data_source"] == "real", f"data_source={health['data_source']}")
check("A2", health["engine_modules"] == 12, f"engine_modules={health['engine_modules']}")

# ── B: Mortality Engine ────────────────────────────────────

print("\n=== B: Mortality Engine ===")
lc = get("/mortality/lee-carter?sex=unisex")
check("B1", 0.70 <= lc["explained_variance"] <= 0.90,
      f"explained_var={lc['explained_variance']:.4f} (expect 0.70-0.90)")
check("B2", -1.3 <= lc["drift"] <= -0.8,
      f"drift={lc['drift']:.4f} (expect -1.3 to -0.8)")
check("B3", lc["sigma"] > 0, f"sigma={lc['sigma']:.4f}")
check("B4", lc["validations"]["bx_sums_to_one"] and lc["validations"]["kt_sums_to_zero"],
      "LC identifiability constraints satisfied")

grad = get("/mortality/graduation?sex=unisex")
check("B5", grad["roughness_reduction"] > 0.50,
      f"roughness_reduction={grad['roughness_reduction']:.4f} (expect >0.50)")

proj = get("/mortality/projection?horizon=30&projection_year=2040&sex=unisex")
check("B6", len(proj["projected_years"]) == 30,
      f"projected_years length={len(proj['projected_years'])}")

# ── C: Pricing ─────────────────────────────────────────────

print("\n=== C: Pricing ===")
wl40 = post("/pricing/premium", {
    "product_type": "whole_life", "age": 40,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "sex": "male"
})
check("C1", 5_000 <= wl40["annual_premium"] <= 40_000,
      f"WL male 40 premium=${wl40['annual_premium']:,.0f} (expect $5K-$40K)")

term40 = post("/pricing/premium", {
    "product_type": "term", "age": 40,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "term": 20, "sex": "male"
})
check("C2", term40["annual_premium"] < wl40["annual_premium"],
      f"term(${term40['annual_premium']:,.0f}) < WL(${wl40['annual_premium']:,.0f})")

endow40 = post("/pricing/premium", {
    "product_type": "endowment", "age": 40,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "term": 20, "sex": "male"
})
check("C3", endow40["annual_premium"] > wl40["annual_premium"],
      f"endow(${endow40['annual_premium']:,.0f}) > WL(${wl40['annual_premium']:,.0f})")

ages_prems = []
for age in [20, 40, 60]:
    p = post("/pricing/premium", {
        "product_type": "whole_life", "age": age,
        "sum_assured": 1_000_000, "interest_rate": 0.05, "sex": "male"
    })["annual_premium"]
    ages_prems.append(p)
check("C4", ages_prems[0] < ages_prems[1] < ages_prems[2],
      f"P(20)=${ages_prems[0]:,.0f} < P(40)=${ages_prems[1]:,.0f} < P(60)=${ages_prems[2]:,.0f}")

male30 = post("/pricing/premium", {
    "product_type": "whole_life", "age": 30,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "sex": "male"
})["annual_premium"]
female30 = post("/pricing/premium", {
    "product_type": "whole_life", "age": 30,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "sex": "female"
})["annual_premium"]
check("C5", male30 > female30,
      f"male(${male30:,.0f}) > female(${female30:,.0f})")

# Cross-country
cc = post("/pricing/cross-country", {
    "product_type": "whole_life", "age": 40,
    "sum_assured": 1_000_000, "interest_rate": 0.05, "sex": "male"
})
entries = {e["country"]: e for e in cc["entries"]}
mx_p = entries["Mexico"]["annual_premium"]
usa_p = entries["Estados Unidos"]["annual_premium"]
spain_p = entries["España"]["annual_premium"]
check("C6", mx_p > usa_p > spain_p,
      f"MX(${mx_p:,.0f}) > USA(${usa_p:,.0f}) > Spain(${spain_p:,.0f})")

# ── D: SCR ─────────────────────────────────────────────────

print("\n=== D: SCR ===")
post("/portfolio/reset")
scr = post("/scr/defaults")
check("D1", scr["mortality"]["scr"] > 0, f"mort_scr=${scr['mortality']['scr']:,.0f}")
check("D2", scr["longevity"]["scr"] > 0, f"long_scr=${scr['longevity']['scr']:,.0f}")
check("D3", scr["interest_rate"]["scr"] > 0, f"ir_scr=${scr['interest_rate']['scr']:,.0f}")
check("D4", scr["catastrophe"]["scr"] > 0, f"cat_scr=${scr['catastrophe']['scr']:,.0f}")

agg = scr["total_aggregation"]
check("D5", agg["scr_aggregated"] < agg["sum_individual"],
      f"diversification: agg(${agg['scr_aggregated']:,.0f}) < sum(${agg['sum_individual']:,.0f})")
check("D6", scr["risk_margin"]["risk_margin"] > 0,
      f"risk_margin=${scr['risk_margin']['risk_margin']:,.0f}")
check("D7", scr["technical_provisions"] > scr["bel_base"],
      f"TP(${scr['technical_provisions']:,.0f}) > BEL(${scr['bel_base']:,.0f})")

ir_ratio = scr["interest_rate"]["scr"] / agg["scr_aggregated"]
check("D8", ir_ratio > 0.50,
      f"IR dominance: {ir_ratio:.1%} of total SCR (expect >50%)")

# ── E: Sensitivity ─────────────────────────────────────────

print("\n=== E: Sensitivity ===")
shock = post("/sensitivity/mortality-shock", {
    "age": 40, "sum_assured": 1_000_000,
    "product_type": "whole_life", "factors": [-0.30, 0, 0.30],
})
check("E1", shock["premiums"][2] > shock["premiums"][1] > shock["premiums"][0],
      f"shock ordering: +30%>${shock['premiums'][2]:,.0f} > base>${shock['premiums'][1]:,.0f} > -30%>${shock['premiums'][0]:,.0f}")

covid = get("/sensitivity/covid-comparison")
check("E2", covid["full_period"]["drift"] > covid["pre_covid"]["drift"],
      f"COVID drift: full({covid['full_period']['drift']:.3f}) > pre({covid['pre_covid']['drift']:.3f})")
all_positive = all(i["pct_change"] > 0 for i in covid["premium_impact"])
check("E3", all_positive, "All COVID premium impacts positive")

# ── Summary ────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"PRODUCTION VALIDATION: {passed} PASS, {failed} FAIL out of {passed+failed}")
print(f"{'='*50}")

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r.startswith("  FAIL"):
            print(f"  {r}")

sys.exit(1 if failed > 0 else 0)
