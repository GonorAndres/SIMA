"""Tests for pricing router endpoints."""

import pytest


def test_whole_life_premium(client):
    """THEORY: Whole life premium should be positive and less than SA."""
    response = client.post("/api/pricing/premium", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["annual_premium"] > 0
    assert data["annual_premium"] < 1_000_000
    assert data["premium_rate"] > 0
    assert data["premium_rate"] < 1


def test_term_premium(client):
    """THEORY: Term premium < whole life premium (covers less)."""
    wl = client.post("/api/pricing/premium", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
    }).json()

    term = client.post("/api/pricing/premium", json={
        "product_type": "term",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
        "term": 20,
    }).json()

    assert term["annual_premium"] < wl["annual_premium"]


def test_endowment_premium(client):
    """THEORY: Endowment premium > term premium (pays on death OR survival)."""
    term = client.post("/api/pricing/premium", json={
        "product_type": "term",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
        "term": 20,
    }).json()

    endow = client.post("/api/pricing/premium", json={
        "product_type": "endowment",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
        "term": 20,
    }).json()

    assert endow["annual_premium"] > term["annual_premium"]


def test_reserve_trajectory(client):
    """THEORY: Reserve at t=0 should be ~0 (equivalence principle)."""
    response = client.post("/api/pricing/reserve", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["trajectory"]) > 0
    assert abs(data["trajectory"][0]["reserve"]) < 1.0


def test_commutation_values(client):
    """THEORY: Commutation values should satisfy D_x > 0, N_x > D_x."""
    response = client.get("/api/pricing/commutation?age=40&interest_rate=0.05")
    assert response.status_code == 200
    data = response.json()
    assert data["D_x"] > 0
    assert data["N_x"] > data["D_x"]
    assert data["C_x"] > 0
    assert data["M_x"] > 0
    assert 0 < data["A_x"] < 1
    assert data["a_due_x"] > 1


def test_sensitivity(client):
    """THEORY: Higher interest rate should produce lower whole life premium."""
    response = client.post("/api/pricing/sensitivity", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "rates": [0.02, 0.05, 0.08],
    })
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 3
    # Higher rate -> lower premium
    assert results[0]["annual_premium"] > results[1]["annual_premium"]
    assert results[1]["annual_premium"] > results[2]["annual_premium"]


def test_premium_sex_parameter(client):
    """THEORY: Sex parameter should be echoed back and produce valid premiums for all values."""
    for sex in ["male", "female", "unisex"]:
        resp = client.post("/api/pricing/premium", json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.05,
            "sex": sex,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sex"] == sex
        assert data["annual_premium"] > 0
        assert data["annual_premium"] < 1_000_000


def test_premium_unisex_uses_projected(client):
    """THEORY: Unisex premium uses the projected LC life table (Total population).
    It should differ from male/female regulatory-table premiums since it comes
    from a completely different data source (Lee-Carter projection vs CNSF table)."""
    male = client.post("/api/pricing/premium", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
        "sex": "male",
    }).json()

    unisex = client.post("/api/pricing/premium", json={
        "product_type": "whole_life",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
        "sex": "unisex",
    }).json()

    assert unisex["sex"] == "unisex"
    assert unisex["annual_premium"] > 0
    # Unisex comes from projected LC table, male from CNSF regulatory table:
    # they should be different (different data sources)
    assert unisex["annual_premium"] != male["annual_premium"]


def test_invalid_product_type(client):
    """THEORY: Unknown product type should return 422 (Pydantic Literal validation)."""
    response = client.post("/api/pricing/premium", json={
        "product_type": "unknown_product",
        "age": 40,
        "sum_assured": 1_000_000,
        "interest_rate": 0.05,
    })
    assert response.status_code == 422
