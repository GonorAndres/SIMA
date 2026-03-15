"""
Precomputed data service.

Loads mortality data at application startup and caches the resulting objects
in module-level variables. This avoids re-parsing CSVs on every request.

Data source priority:
    1. Real INEGI/CONAPO/CNSF data (if present in backend/data/{inegi,conapo,cnsf}/)
    2. Mock synthetic data (backend/data/mock/) as fallback

Sex-differentiated pipelines:
    Three full LC pipelines are loaded at startup (male, female, unisex/Total).
    INEGI sex values: "Hombres", "Mujeres", "Total".
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

# Mapping from API sex values to INEGI column names
SEX_TO_INEGI = {"male": "Hombres", "female": "Mujeres", "unisex": "Total"}

# Module-level cache: one pipeline per sex
_pipelines: dict[str, dict] = {}  # keyed by "male", "female", "unisex"
_cnsf_lt: LifeTable | None = None
_cnsf_2013_lt: LifeTable | None = None
_emssa_lt: LifeTable | None = None
_cnsf_lt_female: LifeTable | None = None
_cnsf_2013_lt_female: LifeTable | None = None
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
REAL_CNSF_2013 = DATA_DIR / "cnsf" / "cnsf_2013.csv"
REAL_EMSSA = DATA_DIR / "cnsf" / "emssa_2009.csv"

# Mock data paths (fallback)
MOCK_DEATHS = MOCK_DIR / "mock_inegi_deaths.csv"
MOCK_POPULATION = MOCK_DIR / "mock_conapo_population.csv"
MOCK_CNSF = MOCK_DIR / "mock_cnsf_2000_i.csv"
MOCK_EMSSA = MOCK_DIR / "mock_emssa_2009.csv"


def _resolve_paths() -> tuple[str, str, str, str | None, str, str]:
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
    cnsf_2013 = str(REAL_CNSF_2013) if REAL_CNSF_2013.exists() else None
    emssa = str(REAL_EMSSA) if REAL_EMSSA.exists() else str(MOCK_EMSSA)

    return deaths, population, cnsf, cnsf_2013, emssa, source


def _build_pipeline(deaths: str, population: str, inegi_sex: str) -> dict:
    """Build a full MortalityData -> Graduation -> LeeCarter -> Projection pipeline."""
    md = MortalityData.from_inegi(
        deaths_filepath=deaths,
        population_filepath=population,
        sex=inegi_sex,
        year_start=1990,
        year_end=2019,
        age_max=100,
    )
    grad = GraduatedRates(
        md,
        lambda_param=1e5,
        diff_order=2,
        weight_by_exposure=True,
    )
    lc = LeeCarter.fit(grad, reestimate_kt=False)
    proj = MortalityProjection(
        lc,
        horizon=30,
        n_simulations=500,
        random_seed=42,
    )
    return {
        "mortality_data": md,
        "graduated": grad,
        "lee_carter": lc,
        "projection": proj,
    }


def load_all() -> None:
    """Load all precomputed data. Called once at startup."""
    global _pipelines
    global _cnsf_lt, _cnsf_2013_lt, _emssa_lt
    global _cnsf_lt_female, _cnsf_2013_lt_female, _emssa_lt_female
    global _data_source, _load_error

    try:
        deaths, population, cnsf, cnsf_2013, emssa, _data_source = _resolve_paths()

        # Build one LC pipeline per sex
        for sex_key, inegi_sex in SEX_TO_INEGI.items():
            logger.info("Loading %s (%s) pipeline...", sex_key, inegi_sex)
            _pipelines[sex_key] = _build_pipeline(deaths, population, inegi_sex)

        # Load regulatory tables (both sexes)
        _cnsf_lt = LifeTable.from_regulatory_table(cnsf, sex="male")
        _emssa_lt = LifeTable.from_regulatory_table(emssa, sex="male")
        _cnsf_lt_female = LifeTable.from_regulatory_table(cnsf, sex="female")
        _emssa_lt_female = LifeTable.from_regulatory_table(emssa, sex="female")

        # CNSF 2013 (only available with real data, not in mock)
        if cnsf_2013 is not None:
            _cnsf_2013_lt = LifeTable.from_regulatory_table(cnsf_2013, sex="male")
            _cnsf_2013_lt_female = LifeTable.from_regulatory_table(cnsf_2013, sex="female")
            logger.info("CNSF 2013 regulatory table loaded.")

        _load_error = None
        logger.info(
            "Precomputed data loaded successfully (source: %s, pipelines: %s)",
            _data_source,
            list(_pipelines.keys()),
        )
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


def _get_pipeline(sex: str = "unisex") -> dict:
    """Get a sex-specific pipeline, defaulting to unisex (Total)."""
    if _load_error is not None:
        raise RuntimeError(f"Data loading failed at startup: {_load_error}")
    if sex not in _pipelines:
        raise ValueError(f"Unknown sex: {sex}. Valid: {list(_pipelines.keys())}")
    return _pipelines[sex]


def get_mortality_data(sex: str = "unisex") -> MortalityData:
    return _get_pipeline(sex)["mortality_data"]


def get_graduated(sex: str = "unisex") -> GraduatedRates:
    return _get_pipeline(sex)["graduated"]


def get_lee_carter(sex: str = "unisex") -> LeeCarter:
    return _get_pipeline(sex)["lee_carter"]


def get_projection(sex: str = "unisex") -> MortalityProjection:
    return _get_pipeline(sex)["projection"]


def get_data_source() -> str:
    """Return whether real or mock data is being used."""
    return _data_source


def get_regulatory_lt(table_type: str = "cnsf", sex: str = "male") -> LifeTable:
    """Get a regulatory life table (both sexes cached at startup)."""
    cache = {
        ("cnsf", "male"): _cnsf_lt,
        ("cnsf", "female"): _cnsf_lt_female,
        ("cnsf_2013", "male"): _cnsf_2013_lt,
        ("cnsf_2013", "female"): _cnsf_2013_lt_female,
        ("emssa", "male"): _emssa_lt,
        ("emssa", "female"): _emssa_lt_female,
    }
    key = (table_type, sex)
    if key not in cache:
        raise ValueError(f"Unknown table_type/sex: {table_type}/{sex}")
    lt = cache[key]
    return _check_loaded(lt, f"regulatory_lt({table_type}/{sex})")


def get_projected_life_table(year: int, sex: str = "unisex") -> LifeTable:
    """Get a life table projected to a specific year."""
    proj = get_projection(sex)
    return proj.to_life_table(year=year, radix=100_000)
