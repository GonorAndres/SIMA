"""Tests for health check endpoint."""


def test_health_check(client):
    """THEORY: Health endpoint returns status OK and engine module count."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine_modules"] == 12
