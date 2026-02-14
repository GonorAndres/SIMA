"""Shared fixtures for API tests."""

import sys
from pathlib import Path

import pytest

# Ensure project root is on the path
project_dir = str(Path(__file__).parent.parent.parent.parent)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from fastapi.testclient import TestClient
from backend.api.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client with startup event (loads precomputed data)."""
    with TestClient(app) as c:
        yield c
