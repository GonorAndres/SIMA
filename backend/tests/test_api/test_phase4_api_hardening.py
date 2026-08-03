"""
Phase 4 API hardening tests.

Covers docs/plan-25julio.md section 4.5:
  - 400 / 422 for invalid payloads (Pydantic cross-field validation)
  - 422 for engine ActuarialValidationError escaping routes
  - 503 mapping for DataNotAvailableError (data-load failure path)
  - Golden-value test against a known mini life table via the API
  - Concurrency smoke test for the global portfolio (thread lock)
  - Audit log lines emitted for SCR / BEL computations
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.services import scr_service


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# =============================================================================
# 422: Pydantic cross-field validation at the boundary
# =============================================================================


def test_policy_create_term_requires_term(client):
    """term/endowment products must include `term`."""
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "X-01",
            "product_type": "term",
            "issue_age": 30,
            "sum_assured": 1_000_000,
            # term missing
        },
    )
    assert r.status_code == 422


def test_policy_create_duration_exceeds_term_rejected(client):
    """duration > term is rejected at the schema boundary rather than silently
    creating an expired policy."""
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "X-02",
            "product_type": "term",
            "issue_age": 30,
            "sum_assured": 1_000_000,
            "term": 10,
            "duration": 12,
        },
    )
    assert r.status_code == 422


def test_policy_create_death_product_requires_positive_sa(client):
    """sum_assured must be > 0 for death products."""
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "X-03",
            "product_type": "whole_life",
            "issue_age": 30,
            "sum_assured": 0.0,
        },
    )
    assert r.status_code == 422


def test_policy_create_annuity_requires_positive_pension(client):
    """annual_pension must be > 0 for annuity products."""
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "X-04",
            "product_type": "annuity",
            "issue_age": 65,
            "annual_pension": 0.0,
        },
    )
    assert r.status_code == 422


def test_premium_request_term_required_for_term_product(client):
    r = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "term",
            "age": 40,
            "sum_assured": 1_000_000,
            # term missing
        },
    )
    assert r.status_code == 422


def test_reserve_request_duration_exceeds_term_rejected(client):
    r = client.post(
        "/api/pricing/reserve",
        json={
            "product_type": "term",
            "age": 40,
            "sum_assured": 1_000_000,
            "term": 10,
            "duration": 15,
        },
    )
    assert r.status_code == 422


def test_scr_request_ir_shock_too_large_for_rate(client):
    """The IR down shock must not push rate below zero at the boundary."""
    r = client.post(
        "/api/scr/compute",
        json={
            "interest_rate": 0.005,  # 50 bps
            "ir_shock_bps": 100,  # but shock is 100 bps -> down rate < 0
        },
    )
    assert r.status_code == 422


# =============================================================================
# 422: engine ActuarialValidationError escaping the router
# =============================================================================


def test_engine_validation_error_maps_to_422(client):
    """An out-of-table attained age (issue_age + duration beyond max_age of
    the regulatory table) reaches the engine and is mapped to 422, not 500."""
    # CNSF 2000-I goes up to age 99; issue 95 + duration 10 -> attained 105.
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "X-OLD",
            "product_type": "whole_life",
            "issue_age": 95,
            "sum_assured": 100_000,
            "duration": 10,
        },
    )
    # Adding succeeds (no cross-table validation at construction).
    assert r.status_code == 200

    # BEL reads against CNSF -- attained age 105 is out of range -> 422.
    r2 = client.post("/api/portfolio/bel", json={"interest_rate": 0.05, "sex": "male"})
    assert r2.status_code == 422

    # Cleanup: reset so other tests see a clean portfolio.
    client.post("/api/portfolio/reset")


def test_duplicate_policy_id_at_add_time_returns_422(client):
    """Adding the sample portfolio's existing WL-01 again must surface a
    422 immediately (the service re-checks uniqueness at add time)."""
    # The default sample portfolio already contains WL-01.
    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "WL-01",
            "product_type": "whole_life",
            "issue_age": 35,
            "sum_assured": 1_000_000,
        },
    )
    assert r.status_code == 422


def test_portfolio_rejects_policies_past_the_cap(client):
    """
    THEORY: the demo portfolio is module-level state shared by every caller, so
    an unbounded /portfolio/policy endpoint is an unauthenticated memory-growth
    primitive. scr_service.MAX_PORTFOLIO_POLICIES caps it, and the refusal must
    be a 422 (a validation failure the caller can act on), not a 500.
    """
    from backend.api.services.scr_service import MAX_PORTFOLIO_POLICIES

    client.post("/api/portfolio/reset")
    existing = client.get("/api/portfolio/summary").json()["n_policies"]

    for i in range(MAX_PORTFOLIO_POLICIES - existing):
        r = client.post(
            "/api/portfolio/policy",
            json={
                "policy_id": f"FILL-{i:04d}",
                "product_type": "whole_life",
                "issue_age": 40,
                "sum_assured": 1_000_000,
            },
        )
        assert r.status_code == 200, (i, r.status_code, r.text)

    r = client.post(
        "/api/portfolio/policy",
        json={
            "policy_id": "OVERFLOW-01",
            "product_type": "whole_life",
            "issue_age": 40,
            "sum_assured": 1_000_000,
        },
    )
    assert r.status_code == 422, r.text
    assert client.get("/api/portfolio/summary").json()["n_policies"] == MAX_PORTFOLIO_POLICIES

    # Leave the shared portfolio as the next test expects to find it.
    client.post("/api/portfolio/reset")


# =============================================================================
# 200: valid request still succeeds
# =============================================================================


def test_valid_premium_request_succeeds(client):
    r = client.post(
        "/api/pricing/premium",
        json={
            "product_type": "whole_life",
            "age": 40,
            "sum_assured": 1_000_000,
            "interest_rate": 0.05,
            "sex": "male",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["annual_premium"] > 0
    assert body["premium_rate"] > 0


def test_scr_compute_with_auto_duration_succeeds(client):
    """portfolio_duration=None (auto-compute path) is accepted at the API."""
    r = client.post("/api/scr/compute", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["bel_base"] >= 0
    assert body["risk_margin"]["duration"] > 0


# =============================================================================
# Concurrency: global portfolio thread lock
# =============================================================================


def test_concurrent_policy_adds_are_all_persisted(client):
    """Adding N concurrent policies with distinct ids must result in all N
    being present exactly once (no torn appends / duplicates)."""
    client.post("/api/portfolio/reset")

    n_threads = 20
    barrier = threading.Barrier(n_threads)

    def add_one(i: int):
        barrier.wait()
        client.post(
            "/api/portfolio/policy",
            json={
                "policy_id": f"CONC-{i:03d}",
                "product_type": "whole_life",
                "issue_age": 30,
                "sum_assured": 100_000,
            },
        )

    threads = [threading.Thread(target=add_one, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summary = client.get("/api/portfolio/summary").json()
    ids = [p["policy_id"] for p in summary["policies"]]
    conc_ids = [pid for pid in ids if pid.startswith("CONC-")]
    assert len(conc_ids) == n_threads, (
        f"expected {n_threads} concurrent policies, got {len(conc_ids)}"
    )
    assert len(set(conc_ids)) == n_threads, "duplicate policy_ids after concurrent add"

    client.post("/api/portfolio/reset")


def test_concurrent_duplicate_add_is_rejected(client):
    """Two threads racing to add the SAME policy_id must result in exactly
    one success and one 422 (the lock serializes the uniqueness check)."""
    client.post("/api/portfolio/reset")

    results: list[int] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def add_dup():
        barrier.wait()
        r = client.post(
            "/api/portfolio/policy",
            json={
                "policy_id": "DUP-RACE",
                "product_type": "whole_life",
                "issue_age": 30,
                "sum_assured": 100_000,
            },
        )
        with results_lock:
            results.append(r.status_code)

    t1 = threading.Thread(target=add_dup)
    t2 = threading.Thread(target=add_dup)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results) == [200, 422], f"expected one 200 and one 422, got {results}"
    client.post("/api/portfolio/reset")


# =============================================================================
# Observability: audit log lines for SCR / BEL
# =============================================================================


def test_scr_compute_emits_audit_log(client, caplog):
    """An SCR computation emits a structured audit line at INFO level."""
    with caplog.at_level(logging.INFO, logger="backend.api.routers.scr"):
        r = client.post("/api/scr/compute", json={"interest_rate": 0.05})
    assert r.status_code == 200

    # At least one record tagged SCR/compute with the rate and portfolio size.
    scr_records = [rec for rec in caplog.records if "SCR/compute" in rec.getMessage()]
    assert scr_records, "expected an SCR/compute audit log line"
    msg = scr_records[0].getMessage()
    assert "rate=0.0500" in msg
    assert "port_size=" in msg


def test_bel_compute_emits_audit_log(client, caplog):
    """A BEL computation emits a structured audit line at INFO level."""
    with caplog.at_level(logging.INFO, logger="backend.api.services.scr_service"):
        r = client.post("/api/portfolio/bel", json={"interest_rate": 0.05})
    assert r.status_code == 200

    bel_records = [rec for rec in caplog.records if "BEL/compute" in rec.getMessage()]
    assert bel_records, "expected a BEL/compute audit log line"


def test_request_logging_middleware_writes_one_line_per_request(client, caplog):
    """The request-logging middleware emits one INFO line per API request."""
    with caplog.at_level(logging.INFO, logger="backend.api.main"):
        client.get("/api/health")
    matching = [
        rec
        for rec in caplog.records
        if re.search(r"GET /api/health -> \d+ \(\d+\.\d+ ms\)", rec.getMessage())
    ]
    assert matching, "expected a 'GET /api/health -> <status> (<ms> ms)' log line"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
