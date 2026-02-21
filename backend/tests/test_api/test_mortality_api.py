"""Tests for mortality router endpoints."""

import pytest


def test_data_summary(client):
    """THEORY: Loaded mock data should report Mexico/Total with correct shape."""
    response = client.get("/api/mortality/data/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "Mexico"
    assert data["sex"] == "Total"
    assert data["age_range"][0] == 0
    assert data["age_range"][1] == 100
    assert data["mx_min"] > 0


def test_lee_carter_params(client):
    """THEORY: Lee-Carter parameters should satisfy identifiability constraints."""
    response = client.get("/api/mortality/lee-carter")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ax"]) == len(data["ages"])
    assert len(data["bx"]) == len(data["ages"])
    assert len(data["kt"]) == len(data["years"])
    assert data["explained_variance"] > 0.5
    assert data["validations"]["bx_sums_to_one"]
    assert data["validations"]["kt_sums_to_zero"]


def test_projection(client):
    """THEORY: Projection should produce negative drift (mortality improving)."""
    response = client.get("/api/mortality/projection?horizon=20&projection_year=2040")
    assert response.status_code == 200
    data = response.json()
    assert data["drift"] < 0
    assert data["sigma"] > 0
    assert len(data["kt_central"]) == 20
    assert data["life_table"] is not None
    assert data["life_table"]["min_age"] == 0


def test_life_table_cnsf(client):
    """THEORY: CNSF regulatory table should have valid q_x across 50+ ages."""
    response = client.get("/api/mortality/life-table?table_type=cnsf&sex=male")
    assert response.status_code == 200
    data = response.json()
    # Real CNSF starts at age 12; mock at 0. Both are valid.
    assert data["min_age"] >= 0
    assert len(data["ages"]) > 50
    assert all(0 <= q <= 1 for q in data["q_x"])


def test_life_table_emssa(client):
    """THEORY: EMSSA regulatory table should also be loadable."""
    response = client.get("/api/mortality/life-table?table_type=emssa&sex=male")
    assert response.status_code == 200
    data = response.json()
    assert data["min_age"] >= 0
    assert len(data["q_x"]) > 50


def test_validation(client):
    """THEORY: Validation should compute ratio and RMSE against regulatory table."""
    response = client.get("/api/mortality/validation?projection_year=2040&table_type=cnsf")
    assert response.status_code == 200
    data = response.json()
    assert data["rmse"] >= 0
    assert data["mean_ratio"] > 0
    assert len(data["ages"]) > 0
    assert len(data["qx_ratios"]) == len(data["ages"])


def test_graduation(client):
    """THEORY: Graduation should reduce roughness -- graduated rates are smoother than raw."""
    response = client.get("/api/mortality/graduation")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ages"]) > 0
    assert len(data["raw_mx"]) == len(data["ages"])
    assert len(data["graduated_mx"]) == len(data["ages"])
    assert data["roughness_reduction"] > 0
    assert data["roughness_graduated"] < data["roughness_raw"]


def test_surface(client):
    """THEORY: Mortality surface should be a 2D matrix (ages x years) of log rates."""
    response = client.get("/api/mortality/surface")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ages"]) > 0
    assert len(data["years"]) > 0
    assert len(data["log_mx"]) == len(data["ages"])
    assert len(data["log_mx"][0]) == len(data["years"])


def test_diagnostics(client):
    """THEORY: Lee-Carter diagnostics should report fit quality metrics."""
    response = client.get("/api/mortality/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["rmse"] >= 0
    assert data["explained_variance"] > 0.5
    assert len(data["residuals_sample"]) > 0
