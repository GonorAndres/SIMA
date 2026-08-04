"""Tests for health check endpoint.

/api/health is the only thing the Cloud Run probe and scripts/validate_production.py
look at before traffic is cut over, so every field it publishes needs a test. It
previously returned {"status": "ok"} unconditionally and reported a single
`data_source` string driven only by the Mexican files -- which is how production
spent months serving synthetic USA and Spain mortality under the label "real".
"""

import pytest

from backend.api.services import precomputed


def test_health_check(client):
    """THEORY: Health endpoint returns status OK and engine module count."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine_modules"] == 13


def test_health_reports_every_loaded_pipeline(client):
    """
    THEORY: pipelines_loaded counts the fitted Lee-Carter models actually in
    memory -- 3 sexes for Mexico plus 3 for each of the two HMD countries.
    A literal here would go stale the moment a country is added, so it is
    counted from the cache.
    """
    data = client.get("/api/health").json()
    assert data["pipelines_loaded"] == 9
    assert data["pipelines_loaded"] == precomputed.count_loaded_pipelines()


def test_health_reports_provenance_per_dataset(client):
    """
    THEORY: a single collapsed label cannot express "Mexico is real but Spain is
    synthetic", which is the exact failure this endpoint exists to make visible.
    Every dataset the loader resolved must appear by name.
    """
    data = client.get("/api/health").json()
    sources = data["data_sources"]
    assert set(sources) == {"mexico", "cnsf", "cnsf_2013", "emssa_97", "usa", "spain"}
    valid = {
        precomputed.SOURCE_REAL,
        precomputed.SOURCE_SYNTHETIC,
        precomputed.SOURCE_MOCK,
        precomputed.SOURCE_MISSING,
    }
    assert set(sources.values()) <= valid

    # The legacy string is "real" only when every dataset is real, so it can
    # never claim more than the per-dataset dict behind it.
    if data["data_source"] == precomputed.SOURCE_REAL:
        assert all(v == precomputed.SOURCE_REAL for v in sources.values())


def test_health_reports_the_window_the_fit_actually_used(client):
    """
    THEORY: year_range is read off the loaded data, not written down. The footer
    renders its provenance badge from it, and it previously printed 1990-2024
    while every pipeline was fitted on 1990-2019.
    """
    data = client.get("/api/health").json()
    year_from, year_to = data["year_range"]
    assert year_from < year_to
    md = precomputed.get_mortality_data("unisex")
    assert [year_from, year_to] == [int(md.years[0]), int(md.years[-1])]


def test_health_returns_503_when_startup_loading_failed(client, monkeypatch):
    """
    THEORY: load_all() swallows its exception into _load_error, so before this
    branch existed a container where every pipeline failed to load still passed
    the Cloud Run health probe and then served 503s on every real endpoint.
    """
    monkeypatch.setattr(precomputed, "_load_error", "simulated startup failure")
    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["error"] == "simulated startup failure"


@pytest.mark.parametrize("supplied", ["ñ", "clave-ünicode", "ÿ"])
def test_non_ascii_proxy_secret_is_rejected_not_crashed(client, monkeypatch, supplied):
    """
    THEORY: secrets.compare_digest() raises TypeError on str operands holding
    non-ASCII characters. That TypeError escapes the middleware stack, outside
    every exception handler, as an unhandled 500 reachable with a single curl.
    The comparison is done on bytes so the answer is a plain 403.

    The header is sent as raw bytes because that is what a client actually puts
    on the wire; Starlette decodes header bytes with latin-1, which is why the
    middleware re-encodes with latin-1 to recover exactly what was sent.
    """
    from backend.api import main

    monkeypatch.setattr(main, "_proxy_secret", "a-real-secret")
    monkeypatch.setattr(main, "_proxy_secret_bytes", b"a-real-secret")
    response = client.get(
        "/api/health",
        headers={"X-SIMA-Proxy-Secret": supplied.encode("latin-1")},
    )
    assert response.status_code == 403
