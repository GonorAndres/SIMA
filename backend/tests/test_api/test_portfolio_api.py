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

    response = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "TEST-01",
            "product_type": "whole_life",
            "issue_age": 30,
            "sum_assured": 500_000,
            "duration": 0,
        },
    )
    assert response.status_code == 200

    updated = client.get("/api/portfolio/summary").json()
    assert updated["n_policies"] == initial["n_policies"] + 1


def test_reset_portfolio(client):
    """THEORY: Reset should restore the sample 12-policy portfolio."""
    response = client.post("/api/portfolio/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["n_policies"] == 12


def test_portfolio_is_per_session(client):
    """THEORY: two callers get independent portfolios.

    The portfolio used to be one module-level object shared by every request,
    so a second visitor adding a policy moved the first visitor's BEL and SCR.
    Each caller now gets a session cookie keying its own portfolio.
    """
    from fastapi.testclient import TestClient

    from backend.api.main import app

    # Two clients, each with its own cookie jar -> two sessions.
    with TestClient(app) as alice, TestClient(app) as bob:
        alice.post("/api/portfolio/reset")
        bob.post("/api/portfolio/reset")

        baseline = bob.get("/api/portfolio/summary").json()["n_policies"]

        added = alice.post(
            "/api/portfolio/policy",
            json={
                "policy_id": "SESSION-ISOLATION-01",
                "product_type": "whole_life",
                "issue_age": 40,
                "sum_assured": 1_000_000,
            },
        )
        assert added.status_code == 200

        assert alice.get("/api/portfolio/summary").json()["n_policies"] == baseline + 1
        # Bob must not see Alice's policy.
        assert bob.get("/api/portfolio/summary").json()["n_policies"] == baseline
        bob_ids = [p["policy_id"] for p in bob.get("/api/portfolio/summary").json()["policies"]]
        assert "SESSION-ISOLATION-01" not in bob_ids


def test_session_cookie_is_set_and_reused(client):
    """THEORY: the API mints a session cookie once and honours it thereafter."""
    from fastapi.testclient import TestClient

    from backend.api.main import app

    with TestClient(app) as c:
        first = c.get("/api/portfolio/summary")
        assert "sima_session" in first.cookies or "sima_session" in c.cookies
        sid = c.cookies.get("sima_session")
        assert sid and sid.isalnum()

        c.get("/api/portfolio/summary")
        # The id must be stable across requests, otherwise every call would
        # silently start a fresh portfolio.
        assert c.cookies.get("sima_session") == sid
