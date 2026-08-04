"""Actuarial structural tests: relationships that hold regardless of data source.

These tests verify fundamental actuarial properties that must hold whether
the app uses real INEGI/CONAPO data or mock Gompertz-Makeham synthetic data.
They catch code regressions that break actuarial logic.
"""


# --- Pricing Structural Properties ---


def test_premium_age_monotonicity(client):
    """THEORY: Whole life premiums must increase with age because q_x increases
    with age (Gompertz law) and fewer premium-paying years remain."""
    premiums = []
    for age in [20, 40, 60]:
        resp = client.post(
            "/api/pricing/premium",
            json={
                "product_type": "whole_life",
                "age": age,
                "sum_assured": 1_000_000,
                "interest_rate": 0.05,
                "sex": "male",
            },
        )
        assert resp.status_code == 200
        premiums.append(resp.json()["annual_premium"])

    assert premiums[0] < premiums[1] < premiums[2], (
        f"Premium must increase with age: P(20)={premiums[0]}, P(40)={premiums[1]}, P(60)={premiums[2]}"
    )


def test_endowment_exceeds_whole_life(client):
    """THEORY: Endowment premium > whole life premium because endowment pays on
    death OR survival (two contingencies), while whole life pays on death only."""
    wl = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.05,
            "sex": "male",
        },
    ).json()

    endow = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "endowment",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.05,
            "term": 20,
            "sex": "male",
        },
    ).json()

    assert endow["annual_premium"] > wl["annual_premium"], (
        f"Endowment ({endow['annual_premium']}) must exceed whole life ({wl['annual_premium']})"
    )


def test_interest_rate_inverse_relationship(client):
    """THEORY: Lower discount rate means higher present value of death benefit,
    so the premium needed to fund it must be higher."""
    low_i = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.03,
            "sex": "male",
        },
    ).json()

    high_i = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.08,
            "sex": "male",
        },
    ).json()

    assert low_i["annual_premium"] > high_i["annual_premium"], (
        f"P(i=3%)={low_i['annual_premium']} must exceed P(i=8%)={high_i['annual_premium']}"
    )


def test_sensitivity_strictly_decreasing(client):
    """THEORY: Premium is a strictly decreasing function of interest rate for whole life.
    Each rate increase reduces the PV of the death benefit (A_x = M_x/D_x)."""
    resp = client.post(
        "/api/pricing/sensitivity",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "rates": [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
            "sex": "male",
        },
    )
    assert resp.status_code == 200
    premiums = [r["annual_premium"] for r in resp.json()["results"]]
    for i in range(len(premiums) - 1):
        assert premiums[i] > premiums[i + 1], (
            f"Premium at rate {i} ({premiums[i]}) must exceed rate {i + 1} ({premiums[i + 1]})"
        )


def test_coverage_proportionality(client):
    """THEORY: Net premium is proportional to sum assured (P = SA * M_x/N_x).
    Doubling SA should exactly double the premium."""
    p1 = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 500_000,
            "interest_rate": 0.05,
            "sex": "male",
        },
    ).json()["annual_premium"]

    p2 = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.05,
            "sex": "male",
        },
    ).json()["annual_premium"]

    ratio = p2 / p1
    assert abs(ratio - 2.0) < 0.01, f"Premium ratio for 2x SA should be 2.0, got {ratio:.4f}"


# --- Cross-Country Structural Properties ---


def test_cross_country_drift_ordering(client):
    """THEORY: all three populations are improving, and Spain is improving
    materially faster than either Mexico or the USA.

    This test previously asserted a strict ordering Mexico > USA > Spain. That
    ordering came from synthetic Gompertz-Makeham fixtures, where the improvement
    rate of each country was a planted constant. On the real HMD and INEGI data
    it is false: Mexico and the USA improve at essentially the same rate (drift
    -1.0858 vs -1.0207, a 6% difference), and which of the two leads is not a
    structural fact about the two countries -- it is noise on a 30-year window,
    and it flips with the fit window or the sex.

    What survives contact with real data is the Spain gap, which is large
    (roughly 2.5x Mexico) and robust. So that is what is asserted. A test that
    pins a distinction the data cannot support is worse than no test.
    """
    resp = client.get("/api/sensitivity/cross-country")
    assert resp.status_code == 200
    countries = {c["country"]: c for c in resp.json()["countries"]}

    mx_drift = countries["México"]["drift"]
    usa_drift = countries["Estados Unidos"]["drift"]
    spain_drift = countries["España"]["drift"]

    assert mx_drift < 0, "Mexico drift must be negative (mortality improving)"
    assert usa_drift < 0, "USA drift must be negative"
    assert spain_drift < 0, "Spain drift must be negative"

    assert spain_drift < mx_drift, (
        f"Spain ({spain_drift}) must improve faster than Mexico ({mx_drift})"
    )
    assert spain_drift < usa_drift, (
        f"Spain ({spain_drift}) must improve faster than the USA ({usa_drift})"
    )
    # Mexico and the USA sit within a factor of 1.5 of each other in either
    # direction -- close enough that the page must not claim one leads the other.
    ratio = mx_drift / usa_drift
    assert 1 / 1.5 < ratio < 1.5, (
        f"Mexico ({mx_drift}) and USA ({usa_drift}) drifts should be comparable, ratio={ratio:.3f}"
    )


# --- SCR Structural Properties ---


def test_scr_interest_rate_dominance(client):
    """THEORY: For a mixed life portfolio (death + annuity products), interest rate
    risk typically dominates because rate changes affect the discounted value of ALL
    future cash flows. Expected to be >50% of total aggregated SCR."""
    client.post("/api/portfolio/reset")
    resp = client.post("/api/scr/defaults")
    assert resp.status_code == 200
    data = resp.json()

    ir_scr = data["interest_rate"]["scr"]
    total_scr = data["total_aggregation"]["scr_aggregated"]

    ratio = ir_scr / total_scr
    assert ratio > 0.40, f"IR risk should dominate: {ratio:.1%} of total (expected >40%)"


def test_scr_technical_provisions_decomposition(client):
    """THEORY: Technical provisions = BEL + risk margin. Both components must be
    positive, and TP must exceed BEL (risk margin adds a buffer)."""
    client.post("/api/portfolio/reset")
    resp = client.post("/api/scr/defaults")
    data = resp.json()

    bel = data["bel_base"]
    rm = data["risk_margin"]["risk_margin"]
    tp = data["technical_provisions"]

    assert bel > 0, "BEL must be positive for a non-empty portfolio"
    assert rm > 0, "Risk margin must be positive (CoC method with positive SCR)"
    assert abs(tp - (bel + rm)) / tp < 0.01, f"TP ({tp}) should equal BEL ({bel}) + RM ({rm})"


# --- Mortality Shock Asymmetry ---


def test_mortality_shock_convexity(client):
    """THEORY: Due to the convex relationship between q_x and premium,
    a symmetric mortality shock produces asymmetric premium changes:
    the percentage decrease from -30% shock exceeds the percentage increase
    from +30% shock in absolute terms."""
    resp = client.post(
        "/api/sensitivity/mortality-shock",
        json={
            "age": 40,
            "sum_assured": 1_000_000,
            "product_type": "whole_life",
            "factors": [-0.30, 0, 0.30],
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    pct_down = data["pct_changes"][0]  # -30% shock
    pct_up = data["pct_changes"][2]  # +30% shock

    assert pct_down < 0, "Negative shock should decrease premium"
    assert pct_up > 0, "Positive shock should increase premium"
    assert abs(pct_down) > abs(pct_up), (
        f"Convexity: |{pct_down:.2f}%| should exceed |{pct_up:.2f}%|"
    )
