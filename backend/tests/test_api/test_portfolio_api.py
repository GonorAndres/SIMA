"""Tests for portfolio router endpoints."""

import pytest


def test_portfolio_summary(client):
    """THEORY: Default sample portfolio has 12 policies (9 death + 3 annuity)."""
    # Reset to ensure clean state
    client.post("/api/portfolio/reset")

    response = client.get("/api/portfolio/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["n_policies"] == 12
    assert data["n_death"] == 9
    assert data["n_annuity"] == 3
    assert data["total_sum_assured"] > 0
    assert data["total_annual_pension"] > 0


def test_portfolio_bel(client):
    """THEORY: Total BEL should be positive for in-force portfolio."""
    client.post("/api/portfolio/reset")
    response = client.post("/api/portfolio/bel", json={"interest_rate": 0.05})
    assert response.status_code == 200
    data = response.json()
    assert data["total_bel"] > 0
    assert data["annuity_bel"] > 0
    assert len(data["breakdown"]) == 12


def test_add_policy(client):
    """THEORY: Adding a policy should increase portfolio size."""
    client.post("/api/portfolio/reset")
    initial = client.get("/api/portfolio/summary").json()

    response = client.post("/api/portfolio/policy", json={
        "policy_id": "TEST-01",
        "product_type": "whole_life",
        "issue_age": 30,
        "sum_assured": 500_000,
        "duration": 0,
    })
    assert response.status_code == 200

    updated = client.get("/api/portfolio/summary").json()
    assert updated["n_policies"] == initial["n_policies"] + 1


def test_reset_portfolio(client):
    """THEORY: Reset should restore the sample 12-policy portfolio."""
    response = client.post("/api/portfolio/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["n_policies"] == 12
