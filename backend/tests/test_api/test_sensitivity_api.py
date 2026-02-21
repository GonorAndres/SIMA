"""Tests for sensitivity router endpoints."""

import pytest


def test_mortality_shock(client):
    """THEORY: Positive mortality shock should increase premiums; negative should decrease."""
    response = client.post("/api/sensitivity/mortality-shock", json={
        "age": 40,
        "sum_assured": 1_000_000,
        "product_type": "whole_life",
        "factors": [-0.30, 0, 0.30],
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["factors"]) == 3
    assert len(data["premiums"]) == 3
    assert data["base_premium"] > 0
    # Negative shock -> lower premium, positive -> higher
    assert data["premiums"][0] < data["base_premium"]
    assert data["premiums"][2] > data["base_premium"]


def test_cross_country(client):
    """THEORY: Cross-country data should contain Mexico, USA, and Spain entries."""
    response = client.get("/api/sensitivity/cross-country")
    assert response.status_code == 200
    data = response.json()
    assert len(data["countries"]) == 3
    country_names = [c["country"] for c in data["countries"]]
    assert "Mexico" in country_names
    assert len(data["kt_profiles"]) == 3
    assert len(data["ax_profiles"]) == 3
    assert len(data["bx_profiles"]) == 3


def test_covid_comparison(client):
    """THEORY: Full-period drift should be less negative than pre-COVID (COVID slowed improvement)."""
    response = client.get("/api/sensitivity/covid-comparison")
    assert response.status_code == 200
    data = response.json()
    assert data["pre_covid"]["drift"] < 0
    assert data["full_period"]["drift"] < 0
    # Full period drift should be less negative (closer to 0) due to COVID
    assert data["full_period"]["drift"] > data["pre_covid"]["drift"]
    assert len(data["premium_impact"]) > 0
    # All COVID premium impacts should be positive (premiums increased)
    for impact in data["premium_impact"]:
        assert impact["pct_change"] > 0
