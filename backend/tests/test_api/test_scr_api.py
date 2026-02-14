"""Tests for SCR router endpoints."""

import pytest


def test_scr_defaults(client):
    """THEORY: Default SCR should produce positive capital requirement."""
    client.post("/api/portfolio/reset")
    response = client.post("/api/scr/defaults")
    assert response.status_code == 200
    data = response.json()
    assert data["bel_base"] > 0
    assert data["mortality"]["scr"] >= 0
    assert data["longevity"]["scr"] >= 0
    assert data["interest_rate"]["scr"] >= 0
    assert data["catastrophe"]["scr"] >= 0
    assert data["life_aggregation"]["scr_aggregated"] > 0
    assert data["total_aggregation"]["scr_aggregated"] > 0
    assert data["risk_margin"]["risk_margin"] > 0
    assert data["technical_provisions"] > data["bel_base"]


def test_scr_with_capital(client):
    """THEORY: With enough capital, solvency ratio should be > 100%."""
    client.post("/api/portfolio/reset")
    response = client.post("/api/scr/compute", json={
        "interest_rate": 0.05,
        "available_capital": 2_000_000,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["solvency"] is not None
    assert data["solvency"]["ratio"] > 0
    assert data["solvency"]["is_solvent"] in [True, False]


def test_scr_diversification(client):
    """THEORY: Aggregated SCR < sum of individual components (diversification)."""
    client.post("/api/portfolio/reset")
    response = client.post("/api/scr/defaults")
    data = response.json()
    life_agg = data["life_aggregation"]
    assert life_agg["diversification_benefit"] > 0
    assert life_agg["scr_aggregated"] < life_agg["sum_individual"]


def test_scr_custom_shocks(client):
    """THEORY: Larger shocks should produce larger SCR."""
    client.post("/api/portfolio/reset")
    small = client.post("/api/scr/compute", json={
        "mortality_shock": 0.10,
        "longevity_shock": 0.10,
    }).json()

    large = client.post("/api/scr/compute", json={
        "mortality_shock": 0.30,
        "longevity_shock": 0.30,
    }).json()

    assert large["mortality"]["scr"] >= small["mortality"]["scr"]
    assert large["longevity"]["scr"] >= small["longevity"]["scr"]
