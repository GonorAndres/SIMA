"""
Precomputed data service.

Loads mortality data at application startup and caches the resulting objects
in module-level variables. This avoids re-parsing CSVs on every request.

Data source priority:
    1. Real INEGI/CONAPO/CNSF data (if present in backend/data/{inegi,conapo,cnsf}/)
    2. Mock synthetic data (backend/data/mock/) as fallback

Provenance is tracked per dataset (see get_data_source()) and combines the path
that was resolved with a content check of the file header, because "the file is
in the real-data directory" is not evidence that the file is real data.

Pipelines loaded at startup (9 total):
    Mexico:  male, female, unisex (INEGI/CONAPO)
    USA:     male, female, unisex (HMD)
    Spain:   male, female, unisex (HMD)
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
from backend.engine.exceptions import DataNotAvailableError

# Mapping from API sex values to data column names
SEX_TO_INEGI = {"male": "Hombres", "female": "Mujeres", "unisex": "Total"}
SEX_TO_HMD = {"male": "Male", "female": "Female", "unisex": "Total"}

# Module-level cache: one pipeline per sex (Mexico) + per (country, sex) (HMD)
_pipelines: dict[str, dict] = {}  # keyed by "male", "female", "unisex"
_hmd_pipelines: dict[tuple[str, str], dict] = {}  # keyed by ("usa", "male"), etc.
_cnsf_lt: LifeTable | None = None
# One table only: CNSF M 2013 is published MIXTA (unisex), so there is no
# female counterpart to cache -- see load_all().
_cnsf_2013_lt: LifeTable | None = None
_emssa_lt: LifeTable | None = None
_cnsf_lt_female: LifeTable | None = None
_emssa_lt_female: LifeTable | None = None
# Per-dataset provenance, keyed by dataset name ("mexico", "usa", "spain",
# "cnsf", "cnsf_2013", "emssa_97"). A single global label is not enough: until
# 2026-08-02 production reported "real" (driven only by the Mexican files)
# while USA and Spain were being served from synthetic Gompertz-Makeham curves
# sitting in the real-data directory.
_data_sources: dict[str, str] = {}
_load_error: str | None = None

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"

# Real data paths
REAL_DEATHS = DATA_DIR / "inegi" / "inegi_deaths.csv"
REAL_POPULATION = DATA_DIR / "conapo" / "conapo_population.csv"
REAL_CNSF = DATA_DIR / "cnsf" / "cnsf_2000_i.csv"
REAL_CNSF_2013 = DATA_DIR / "cnsf" / "cnsf_2013.csv"
# CUSF Anexo 14.2.4-a, "EMSSAH-97 / EMSSAM-97". There is no "EMSSA 2009" annex:
# the file that used to sit at backend/data/cnsf/emssa_2009.csv was a fabrication
# and was deleted on 2026-08-02. The published table is sex-differentiated and
# covers ages 15-110 only -- it prices working-life and pension obligations, so
# any consumer that assumes a table starting at age 0 must handle the offset.
REAL_EMSSA_97 = DATA_DIR / "cnsf" / "emssah_emssam_97.csv"

# Mock data paths (fallback)
MOCK_DEATHS = MOCK_DIR / "mock_inegi_deaths.csv"
MOCK_POPULATION = MOCK_DIR / "mock_conapo_population.csv"
MOCK_CNSF = MOCK_DIR / "mock_cnsf_2000_i.csv"
MOCK_EMSSA_97 = MOCK_DIR / "mock_emssa_97.csv"

# HMD data paths
REAL_HMD_DIR = DATA_DIR / "hmd"
MOCK_HMD_DIR = MOCK_DIR / "hmd"
HMD_COUNTRIES = ["usa", "spain"]

# Projection constants
PROJECTION_YEAR = 2029

# Provenance labels used by _classify() / get_data_source().
#   "real"      -- file on the real-data path, no synthetic marker in its header
#   "synthetic" -- file on the real-data path whose header says it was generated
#   "mock"      -- file served from backend/data/mock/ (the git-tracked CI
#                  fixtures; correct for CI, never valid for a published result)
#   "missing"   -- dataset not present, nothing loaded
SOURCE_REAL = "real"
SOURCE_SYNTHETIC = "synthetic"
SOURCE_MOCK = "mock"
SOURCE_MISSING = "missing"

# backend/scripts/generate_mock_hmd.py stamps "(synthetic mock data for CI
# testing)" into the second line of every file it writes; real HMD extracts
# carry "Last modified: ...;  Methods Protocol: v6 (2017)" instead. Two lines
# are enough to tell them apart, and a content check catches the failure a path
# check cannot: a synthetic file sitting in the real-data directory.
_SYNTHETIC_MARKERS = ("synthetic", "mock")


def _looks_synthetic(path: Path) -> bool:
    """True if the first two lines of `path` identify it as generated data."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            header = "".join(next(fh, "") for _ in range(2)).lower()
    except OSError as exc:
        # Provenance is diagnostic only -- an unreadable file will fail loudly
        # a few lines later when the engine tries to parse it.
        logger.warning("Provenance check could not read %s: %s", path, exc)
        return False
    return any(marker in header for marker in _SYNTHETIC_MARKERS)


def _classify(paths: list[Path], *, from_mock_dir: bool) -> str:
    """Label the provenance of the file(s) backing one dataset.

    Existence is checked before the mock branch on purpose: a deleted mock
    fallback must report "missing" here rather than "mock", otherwise health
    advertises a fixture that is not on disk and the failure only surfaces
    later as a parse error inside the engine.
    """
    if not paths or not all(p.exists() for p in paths):
        return SOURCE_MISSING
    if from_mock_dir:
        return SOURCE_MOCK
    return SOURCE_SYNTHETIC if any(_looks_synthetic(p) for p in paths) else SOURCE_REAL


def _resolve_paths() -> tuple[str, str, str, str | None, str, dict[str, str]]:
    """Resolve data file paths: prefer real data, fall back to mock.

    Returns the resolved paths plus a per-dataset provenance dict, so the
    health endpoint can report exactly which files each pipeline was built on.
    """
    sources: dict[str, str] = {}

    if REAL_DEATHS.exists() and REAL_POPULATION.exists():
        deaths = str(REAL_DEATHS)
        population = str(REAL_POPULATION)
        sources["mexico"] = _classify([REAL_DEATHS, REAL_POPULATION], from_mock_dir=False)
    else:
        deaths = str(MOCK_DEATHS)
        population = str(MOCK_POPULATION)
        sources["mexico"] = _classify([MOCK_DEATHS, MOCK_POPULATION], from_mock_dir=True)

    cnsf_is_real = REAL_CNSF.exists()
    cnsf = str(REAL_CNSF) if cnsf_is_real else str(MOCK_CNSF)
    sources["cnsf"] = _classify(
        [REAL_CNSF] if cnsf_is_real else [MOCK_CNSF], from_mock_dir=not cnsf_is_real
    )

    cnsf_2013 = str(REAL_CNSF_2013) if REAL_CNSF_2013.exists() else None
    # No mock fallback exists for CNSF 2013: absent means the tab is unavailable.
    sources["cnsf_2013"] = (
        _classify([REAL_CNSF_2013], from_mock_dir=False) if cnsf_2013 else SOURCE_MISSING
    )

    emssa_is_real = REAL_EMSSA_97.exists()
    emssa = str(REAL_EMSSA_97) if emssa_is_real else str(MOCK_EMSSA_97)
    sources["emssa_97"] = _classify(
        [REAL_EMSSA_97] if emssa_is_real else [MOCK_EMSSA_97], from_mock_dir=not emssa_is_real
    )

    logger.info(
        "Data path resolution: mexico=%s, deaths=%s, population=%s",
        sources["mexico"],
        deaths,
        population,
    )
    if sources["mexico"] != SOURCE_REAL:
        logger.warning(
            "REAL DATA NOT FOUND. Expected: %s and %s. Falling back to mock.",
            REAL_DEATHS,
            REAL_POPULATION,
        )

    return deaths, population, cnsf, cnsf_2013, emssa, sources


def _fit_pipeline(md: MortalityData) -> dict:
    """Graduate, fit Lee-Carter, and project from a MortalityData object."""
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


def _build_inegi_pipeline(deaths: str, population: str, inegi_sex: str) -> dict:
    """Build pipeline from INEGI/CONAPO data."""
    md = MortalityData.from_inegi(
        deaths_filepath=deaths,
        population_filepath=population,
        sex=inegi_sex,
        year_start=1990,
        year_end=2019,
        age_max=100,
    )
    return _fit_pipeline(md)


def _resolve_hmd_dir(country: str) -> tuple[str, str]:
    """Resolve HMD data directory: prefer real, fall back to mock.

    Returns (data_dir, provenance). `data_dir` is the *parent* of the country
    folder because MortalityData.from_hmd() joins country itself. Provenance is
    read from the file headers, not from the directory name, so a generated
    file left in backend/data/hmd/ is reported as "synthetic" rather than
    passing itself off as real HMD.
    """
    real_dir = REAL_HMD_DIR / country
    mock_dir = MOCK_HMD_DIR / country
    real_files = sorted(real_dir.glob("*.txt")) if real_dir.exists() else []
    if real_files:
        source = _classify(real_files, from_mock_dir=False)
        if source == SOURCE_SYNTHETIC:
            logger.warning(
                "HMD %s: files in %s are SYNTHETIC (header says so), not real HMD data.",
                country,
                real_dir,
            )
        else:
            logger.info("HMD %s: using real data from %s", country, real_dir)
        return str(real_dir.parent), source
    logger.warning(
        "HMD %s: real data not found at %s (exists=%s, files=%s). Falling back to mock.",
        country,
        real_dir,
        real_dir.exists(),
        list(real_dir.glob("*")) if real_dir.exists() else "dir_missing",
    )
    return str(mock_dir.parent), SOURCE_MOCK


def _build_hmd_pipeline(data_dir: str, country: str, hmd_sex: str) -> dict:
    """Build pipeline from HMD data."""
    md = MortalityData.from_hmd(
        data_dir=data_dir,
        country=country,
        sex=hmd_sex,
        year_min=1990,
        year_max=2019,
        age_max=100,
    )
    return _fit_pipeline(md)


def load_all() -> None:
    """Load all precomputed data. Called once at startup."""
    global _pipelines, _hmd_pipelines
    global _cnsf_lt, _cnsf_2013_lt, _emssa_lt
    global _cnsf_lt_female, _emssa_lt_female
    global _load_error

    try:
        # Clear first, then rebuild. A reload that fails partway must not leave
        # /api/health reporting status="error" next to a stale pipelines_loaded=9
        # and a half-populated provenance dict -- the health endpoint would then
        # be asserting something it cannot know.
        _pipelines.clear()
        _hmd_pipelines.clear()
        _data_sources.clear()
        _cnsf_lt = _cnsf_2013_lt = _emssa_lt = None
        _cnsf_lt_female = _emssa_lt_female = None

        deaths, population, cnsf, cnsf_2013, emssa, sources = _resolve_paths()
        _data_sources.update(sources)

        # Build one LC pipeline per sex (Mexico via INEGI/CONAPO)
        for sex_key, inegi_sex in SEX_TO_INEGI.items():
            logger.info("Loading Mexico %s (%s) pipeline...", sex_key, inegi_sex)
            _pipelines[sex_key] = _build_inegi_pipeline(deaths, population, inegi_sex)

        # Build HMD pipelines for USA and Spain (3 sexes each)
        for country in HMD_COUNTRIES:
            hmd_dir, _data_sources[country] = _resolve_hmd_dir(country)
            for sex_key, hmd_sex in SEX_TO_HMD.items():
                logger.info("Loading %s %s (%s) pipeline...", country, sex_key, hmd_sex)
                _hmd_pipelines[(country, sex_key)] = _build_hmd_pipeline(hmd_dir, country, hmd_sex)

        # Load regulatory tables (both sexes)
        _cnsf_lt = LifeTable.from_regulatory_table(cnsf, sex="male")
        _emssa_lt = LifeTable.from_regulatory_table(emssa, sex="male")
        _cnsf_lt_female = LifeTable.from_regulatory_table(cnsf, sex="female")
        _emssa_lt_female = LifeTable.from_regulatory_table(emssa, sex="female")

        # CNSF 2013 (only available with real data, not in mock).
        # CUSF Anexo 5.3.3-a publishes this table as "CNSFM 2013 - experiencia
        # demografica de mortalidad MIXTA (hombres y mujeres)": one q_x column,
        # ages 0-110, no official sex split. So it is loaded once, as unisex.
        # Reading it with sex="male"/"female" returned the same numbers (the two
        # columns are copies of the published value) but emitted a UserWarning on
        # every startup and presented a mixed table as if it were sexed.
        if cnsf_2013 is not None:
            _cnsf_2013_lt = LifeTable.from_regulatory_table(cnsf_2013, sex="unisex")
            logger.info("CNSF M 2013 (mixta) regulatory table loaded.")

        _load_error = None
        logger.info(
            "Precomputed data loaded successfully (sources: %s, "
            "Mexico pipelines: %s, HMD pipelines: %s)",
            _data_sources,
            list(_pipelines.keys()),
            list(_hmd_pipelines.keys()),
        )
    except Exception as exc:
        _load_error = str(exc)
        logger.error("Failed to load precomputed data: %s", exc, exc_info=True)


def _check_loaded(obj, name: str):
    """Check that precomputed data loaded successfully."""
    if _load_error is not None:
        raise DataNotAvailableError(
            f"Data loading failed at startup: {_load_error}",
            field=name,
            constraint="data files present and loadable at startup",
        )
    if obj is None:
        raise DataNotAvailableError(
            f"{name} not loaded. Call load_all() first.",
            field=name,
            constraint="load_all() invoked during application lifespan",
        )
    return obj


def _get_pipeline(sex: str = "unisex") -> dict:
    """Get a sex-specific pipeline, defaulting to unisex (Total)."""
    if _load_error is not None:
        raise DataNotAvailableError(
            f"Data loading failed at startup: {_load_error}",
            field=sex,
            constraint="data files present and loadable at startup",
        )
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


def get_data_source() -> dict[str, str]:
    """Return per-dataset provenance, keyed by dataset name.

    Keys: "mexico", "usa", "spain", "cnsf", "cnsf_2013", "emssa_97". Values are
    one of SOURCE_REAL / SOURCE_SYNTHETIC / SOURCE_MOCK / SOURCE_MISSING.
    Empty until load_all() has run.
    """
    return dict(_data_sources)


def get_data_source_label() -> str:
    """Collapse per-dataset provenance into the single legacy string.

    The /api/health `data_source` field predates per-dataset provenance and is
    consumed by the frontend footer and scripts/validate_production.py, so it
    keeps its string shape: "real" only when *every* loaded dataset is real,
    "mixed" when some are and some are not, otherwise the shared label.
    """
    if not _data_sources:
        return "unknown"
    distinct = {s for s in _data_sources.values() if s != SOURCE_MISSING}
    if not distinct:
        return SOURCE_MISSING
    if len(distinct) == 1:
        return distinct.pop()
    return "mixed"


def get_load_error() -> str | None:
    """Return the startup load failure message, or None if loading succeeded."""
    return _load_error


def count_loaded_pipelines() -> int:
    """Number of fitted Lee-Carter pipelines currently cached (Mexico + HMD)."""
    return len(_pipelines) + len(_hmd_pipelines)


def get_fitted_year_range() -> list[int] | None:
    """First and last calendar year of the fitted window, or None if unloaded.

    Read off the loaded Mexican data rather than restated as a literal: the
    footer used to print "1990-2024" while every pipeline was in fact fitted on
    1990-2019. Returned by /api/health so a single call is enough to render the
    provenance badge.
    """
    pipeline = _pipelines.get("unisex")
    if pipeline is None:
        return None
    years = pipeline["mortality_data"].years
    return [int(years[0]), int(years[-1])]


def get_regulatory_lt(table_type: str = "cnsf", sex: str = "male") -> LifeTable:
    """Get a regulatory life table (both sexes cached at startup).

    CNSF M 2013 is published MIXTA, so both sex values resolve to the same
    table. That is not a shortcut: the annex publishes no sex split, and
    returning a "female" variant that is byte-identical to the "male" one would
    be a more honest failure than inventing a difference, but a less honest one
    than saying so here.
    """
    cache = {
        ("cnsf", "male"): _cnsf_lt,
        ("cnsf", "female"): _cnsf_lt_female,
        ("cnsf_2013", "male"): _cnsf_2013_lt,
        ("cnsf_2013", "female"): _cnsf_2013_lt,
        ("cnsf_2013", "unisex"): _cnsf_2013_lt,
        ("emssa_97", "male"): _emssa_lt,
        ("emssa_97", "female"): _emssa_lt_female,
    }
    key = (table_type, sex)
    if key not in cache:
        raise ValueError(f"Unknown table_type/sex: {table_type}/{sex}")
    lt = cache[key]
    return _check_loaded(lt, f"regulatory_lt({table_type}/{sex})")


def get_projected_life_table(year: int = PROJECTION_YEAR, sex: str = "unisex") -> LifeTable:
    """Get a Mexico life table projected to a specific year."""
    proj = get_projection(sex)
    return proj.to_life_table(year=year, radix=100_000)


def get_hmd_pipeline(country: str, sex: str = "unisex") -> dict:
    """Get a HMD country pipeline by country and sex."""
    if _load_error is not None:
        raise DataNotAvailableError(
            f"Data loading failed at startup: {_load_error}",
            field=f"{country}/{sex}",
            constraint="data files present and loadable at startup",
        )
    key = (country, sex)
    if key not in _hmd_pipelines:
        raise ValueError(
            f"Unknown country/sex: {country}/{sex}. Valid: {list(_hmd_pipelines.keys())}"
        )
    return _hmd_pipelines[key]


def get_hmd_lee_carter(country: str, sex: str = "unisex") -> LeeCarter:
    """Get Lee-Carter model for a HMD country."""
    return get_hmd_pipeline(country, sex)["lee_carter"]


def get_hmd_projected_life_table(
    country: str, year: int = PROJECTION_YEAR, sex: str = "unisex"
) -> LifeTable:
    """Get a HMD country life table projected to a specific year."""
    proj = get_hmd_pipeline(country, sex)["projection"]
    return proj.to_life_table(year=year, radix=100_000)
