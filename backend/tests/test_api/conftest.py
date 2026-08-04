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


_DATA_DIR = Path(__file__).parent.parent.parent / "data"
REAL_DEATHS = _DATA_DIR / "inegi" / "inegi_deaths.csv"
REAL_POP = _DATA_DIR / "conapo" / "conapo_population.csv"

# Most API tests assert structure and hold on either data source. A few assert
# a measured property of the real Mexican fit -- the size of the Spain
# improvement gap, the COVID slowdown -- and those are meaningless against the
# synthetic fixtures, which carry a planted constant drift and no pandemic.
# Marking them keeps CI honest instead of asserting facts its data cannot show.
real_data = pytest.mark.skipif(
    not (REAL_DEATHS.exists() and REAL_POP.exists()),
    reason="real INEGI/CONAPO files not present (they are gitignored; see DATA.md)",
)


@pytest.fixture(scope="module")
def client():
    """Create a test client with startup event (loads precomputed data)."""
    with TestClient(app) as c:
        yield c
