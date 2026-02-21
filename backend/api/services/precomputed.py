"""
Precomputed data service.

Loads mortality data at application startup and caches the resulting objects
in module-level variables. This avoids re-parsing CSVs on every request.

Data source priority:
    1. Real INEGI/CONAPO/CNSF data (if present in backend/data/{inegi,conapo,cnsf}/)
    2. Mock synthetic data (backend/data/mock/) as fallback
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

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
_cnsf_lt_female: LifeTable | None = None
_emssa_lt_female: LifeTable | None = None
_data_source: str = "unknown"
_load_error: str | None = None

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"

# Real data paths
REAL_DEATHS = DATA_DIR / "inegi" / "inegi_deaths.csv"
REAL_POPULATION = DATA_DIR / "conapo" / "conapo_population.csv"
REAL_CNSF = DATA_DIR / "cnsf" / "cnsf_2000_i.csv"
REAL_EMSSA = DATA_DIR / "cnsf" / "emssa_2009.csv"

# Mock data paths (fallback)
MOCK_DEATHS = MOCK_DIR / "mock_inegi_deaths.csv"
MOCK_POPULATION = MOCK_DIR / "mock_conapo_population.csv"
MOCK_CNSF = MOCK_DIR / "mock_cnsf_2000_i.csv"
MOCK_EMSSA = MOCK_DIR / "mock_emssa_2009.csv"


def _resolve_paths() -> tuple[str, str, str, str, str]:
    """Resolve data file paths: prefer real data, fall back to mock."""
    if REAL_DEATHS.exists() and REAL_POPULATION.exists():
        deaths = str(REAL_DEATHS)
        population = str(REAL_POPULATION)
        source = "real"
    else:
        deaths = str(MOCK_DEATHS)
        population = str(MOCK_POPULATION)
        source = "mock"

    cnsf = str(REAL_CNSF) if REAL_CNSF.exists() else str(MOCK_CNSF)
    emssa = str(REAL_EMSSA) if REAL_EMSSA.exists() else str(MOCK_EMSSA)

    return deaths, population, cnsf, emssa, source


def load_all() -> None:
    """Load all precomputed data. Called once at startup."""
    global _mortality_data, _graduated, _lee_carter, _projection
    global _cnsf_lt, _emssa_lt, _cnsf_lt_female, _emssa_lt_female
    global _data_source, _load_error

    try:
        deaths, population, cnsf, emssa, _data_source = _resolve_paths()

        # Load mortality data from INEGI/CONAPO
        _mortality_data = MortalityData.from_inegi(
            deaths_filepath=deaths,
            population_filepath=population,
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

        # Load regulatory tables (both sexes)
        _cnsf_lt = LifeTable.from_regulatory_table(cnsf, sex="male")
        _emssa_lt = LifeTable.from_regulatory_table(emssa, sex="male")
        _cnsf_lt_female = LifeTable.from_regulatory_table(cnsf, sex="female")
        _emssa_lt_female = LifeTable.from_regulatory_table(emssa, sex="female")

        _load_error = None
        logger.info("Precomputed data loaded successfully (source: %s)", _data_source)
    except Exception as exc:
        _load_error = str(exc)
        logger.error("Failed to load precomputed data: %s", exc, exc_info=True)


def _check_loaded(obj, name: str):
    """Check that precomputed data loaded successfully."""
    if _load_error is not None:
        raise RuntimeError(f"Data loading failed at startup: {_load_error}")
    if obj is None:
        raise RuntimeError(f"{name} not loaded. Call load_all() first.")
    return obj


def get_mortality_data() -> MortalityData:
    return _check_loaded(_mortality_data, "MortalityData")


def get_graduated() -> GraduatedRates:
    return _check_loaded(_graduated, "GraduatedRates")


def get_lee_carter() -> LeeCarter:
    return _check_loaded(_lee_carter, "LeeCarter")


def get_projection() -> MortalityProjection:
    return _check_loaded(_projection, "MortalityProjection")


def get_data_source() -> str:
    """Return whether real or mock data is being used."""
    return _data_source


def get_regulatory_lt(table_type: str = "cnsf", sex: str = "male") -> LifeTable:
    """Get a regulatory life table (both sexes cached at startup)."""
    cache = {
        ("cnsf", "male"): _cnsf_lt,
        ("cnsf", "female"): _cnsf_lt_female,
        ("emssa", "male"): _emssa_lt,
        ("emssa", "female"): _emssa_lt_female,
    }
    key = (table_type, sex)
    if key not in cache:
        raise ValueError(f"Unknown table_type/sex: {table_type}/{sex}")
    lt = cache[key]
    return _check_loaded(lt, f"regulatory_lt({table_type}/{sex})")


def get_projected_life_table(year: int) -> LifeTable:
    """Get a life table projected to a specific year."""
    proj = get_projection()
    return proj.to_life_table(year=year, radix=100_000)
