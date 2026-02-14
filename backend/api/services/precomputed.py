"""
Precomputed data service.

Loads mock data at application startup and caches the resulting objects
in module-level variables. This avoids re-parsing CSVs on every request.
"""

import sys
from pathlib import Path

# Engine imports require backend/ on the path
_backend_dir = str(Path(__file__).parent.parent.parent)
_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.engine.a01_life_table import LifeTable
from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a07_graduation import GraduatedRates
from backend.engine.a08_lee_carter import LeeCarter
from backend.engine.a09_projection import MortalityProjection

# Module-level cache
_mortality_data: MortalityData | None = None
_graduated: GraduatedRates | None = None
_lee_carter: LeeCarter | None = None
_projection: MortalityProjection | None = None
_cnsf_lt: LifeTable | None = None
_emssa_lt: LifeTable | None = None

# Paths to mock data
MOCK_DIR = Path(__file__).parent.parent.parent / "data" / "mock"
MOCK_DEATHS = str(MOCK_DIR / "mock_inegi_deaths.csv")
MOCK_POPULATION = str(MOCK_DIR / "mock_conapo_population.csv")
MOCK_CNSF = str(MOCK_DIR / "mock_cnsf_2000_i.csv")
MOCK_EMSSA = str(MOCK_DIR / "mock_emssa_2009.csv")


def load_all() -> None:
    """Load all precomputed data. Called once at startup."""
    global _mortality_data, _graduated, _lee_carter, _projection
    global _cnsf_lt, _emssa_lt

    # Load mortality data from mock INEGI/CONAPO
    _mortality_data = MortalityData.from_inegi(
        deaths_filepath=MOCK_DEATHS,
        population_filepath=MOCK_POPULATION,
        sex="Total",
        year_start=1990,
        year_end=2020,
        age_max=100,
    )

    # Graduate
    _graduated = GraduatedRates(
        _mortality_data,
        lambda_param=1e5,
        diff_order=2,
        weight_by_exposure=True,
    )

    # Fit Lee-Carter (no reestimation -- graduated data makes it problematic)
    _lee_carter = LeeCarter.fit(_graduated, reestimate_kt=False)

    # Project 30 years forward
    _projection = MortalityProjection(
        _lee_carter,
        horizon=30,
        n_simulations=500,
        random_seed=42,
    )

    # Load regulatory tables
    _cnsf_lt = LifeTable.from_regulatory_table(MOCK_CNSF, sex="male")
    _emssa_lt = LifeTable.from_regulatory_table(MOCK_EMSSA, sex="male")


def get_mortality_data() -> MortalityData:
    if _mortality_data is None:
        raise RuntimeError("Precomputed data not loaded. Call load_all() first.")
    return _mortality_data


def get_graduated() -> GraduatedRates:
    if _graduated is None:
        raise RuntimeError("Precomputed data not loaded. Call load_all() first.")
    return _graduated


def get_lee_carter() -> LeeCarter:
    if _lee_carter is None:
        raise RuntimeError("Precomputed data not loaded. Call load_all() first.")
    return _lee_carter


def get_projection() -> MortalityProjection:
    if _projection is None:
        raise RuntimeError("Precomputed data not loaded. Call load_all() first.")
    return _projection


def get_regulatory_lt(table_type: str = "cnsf", sex: str = "male") -> LifeTable:
    """Get a regulatory life table.

    For the API, we preload the male tables. If a different sex is requested,
    we load on-the-fly from the mock files.
    """
    if sex == "male":
        if table_type == "cnsf":
            if _cnsf_lt is None:
                raise RuntimeError("Precomputed data not loaded.")
            return _cnsf_lt
        elif table_type == "emssa":
            if _emssa_lt is None:
                raise RuntimeError("Precomputed data not loaded.")
            return _emssa_lt
        else:
            raise ValueError(f"Unknown table_type: {table_type}")
    else:
        filepath = MOCK_CNSF if table_type == "cnsf" else MOCK_EMSSA
        return LifeTable.from_regulatory_table(filepath, sex=sex)


def get_projected_life_table(year: int) -> LifeTable:
    """Get a life table projected to a specific year."""
    proj = get_projection()
    return proj.to_life_table(year=year, radix=100_000)
