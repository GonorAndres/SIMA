"""
SIMA API - Sistema Integral de Modelacion Actuarial
====================================================

FastAPI application that exposes the actuarial engine (a01-a12) via REST endpoints.
Serves both the API and the React frontend from a single process.

Local dev:
    cd /home/andtega349/sima
    python -m uvicorn backend.api.main:app --reload

Production (Cloud Run):
    uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import os
import secrets
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure backend is importable
_project_dir = str(Path(__file__).parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.api.routers import mortality, portfolio, pricing, scr, sensitivity
from backend.api.services.precomputed import (
    count_loaded_pipelines,
    get_data_source,
    get_data_source_label,
    get_fitted_year_range,
    get_load_error,
    load_all,
)
from backend.engine.exceptions import (
    ActuarialValidationError,
    DataNotAvailableError,
    DataQualityError,
)

logger = logging.getLogger(__name__)

# Engine modules present on disk (a01_life_table.py ... a12_scr.py), counted
# once at import so /api/health reports a fact rather than a literal that
# silently goes stale when a module is added or removed.
ENGINE_MODULE_COUNT = len(list((Path(__file__).parent.parent / "engine").glob("a[0-9][0-9]_*.py")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load precomputed data at startup."""
    load_all()
    yield


app = FastAPI(
    title="SIMA - Sistema Integral de Modelacion Actuarial",
    description=(
        "REST API for actuarial calculations: mortality modeling (Lee-Carter), "
        "premium pricing (equivalence principle), reserve valuation (prospective method), "
        "and solvency capital requirements (SCR) under the Solvency II / CNSF framework.\n\n"
        "**Note on /portfolio endpoints:** the demo portfolio is module-level state "
        "shared across all requests; concurrent callers will see each other's mutations. "
        "Per-user / per-session portfolios are planned for a future phase."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
# In production, Cloud Run captures stdout. A simple iso8601 format is good
# enough for now; structured JSON logging can be added later if needed.
#
# stream=sys.stdout is load-bearing: logging.basicConfig defaults to stderr,
# and Cloud Run tags everything written to stderr as severity=ERROR. Without
# it every INFO line (request log, data-path resolution) shows up in Cloud
# Logging as an error and real failures become impossible to spot.
_logging_configured = logging.getLogger().handlers
if not _logging_configured:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )

# Route warnings.warn() through logging (py.warnings logger) instead of stderr,
# so engine warnings (e.g. Whittaker-Henderson graduation diagnostics) inherit
# the handler above and land at WARNING severity rather than ERROR.
logging.captureWarnings(True)

# CORS -- configurable via environment variable, defaults to permissive for same-origin
_cors_raw = os.environ.get("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_proxy_secret = os.environ.get("SIMA_PROXY_SECRET", "")
# Compare as bytes: secrets.compare_digest() raises TypeError on str operands
# holding non-ASCII characters, and that TypeError would escape the middleware
# stack (outside every exception handler) as an unhandled 500 reachable with a
# single curl carrying one non-ASCII byte in the header. Starlette decodes raw
# header bytes with latin-1, so re-encoding with latin-1 recovers exactly the
# bytes the client sent; the environment secret is real text, hence utf-8.
_proxy_secret_bytes = _proxy_secret.encode("utf-8", "surrogateescape")


@app.middleware("http")
async def require_pages_proxy(request: Request, call_next):
    """Reject direct API calls when a Pages proxy secret is configured."""
    if _proxy_secret and request.url.path.startswith("/api"):
        supplied_secret = request.headers.get("X-SIMA-Proxy-Secret", "")
        supplied_bytes = supplied_secret.encode("latin-1", "surrogateescape")
        if not secrets.compare_digest(supplied_bytes, _proxy_secret_bytes):
            return JSONResponse(
                status_code=403,
                content={"detail": "API access is restricted to the SIMA frontend."},
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Request-logging / timing middleware.

    Records one structured log line per request with method, path, status,
    and duration in milliseconds. SCR / BEL computation endpoints additionally
    have their key inputs logged in the route handlers themselves
    (see routers/scr.py and routers/portfolio.py) for auditability.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000.0
    # Skip the static SPA catch-all and assets to keep logs focused on API.
    path = request.url.path
    if path.startswith("/api") or path == "/api/health":
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
    return response


# ---------------------------------------------------------------------------
# Backstop exception handlers
# ---------------------------------------------------------------------------
# These guarantee that engine domain errors never leak as an unstructured
# 500 even if a route handler omits its own try/except. Routes also catch
# these explicitly for a richer detail payload; the backstops are a safety
# net for dependencies (e.g. lifespan, shared services) that run before the
# route body.


@app.exception_handler(ActuarialValidationError)
async def actuarial_validation_exception_handler(
    request: Request, exc: ActuarialValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content=exc.to_dict())


@app.exception_handler(DataQualityError)
async def data_quality_exception_handler(request: Request, exc: DataQualityError) -> JSONResponse:
    return JSONResponse(status_code=422, content=exc.to_dict())


@app.exception_handler(DataNotAvailableError)
async def data_not_available_exception_handler(
    request: Request, exc: DataNotAvailableError
) -> JSONResponse:
    return JSONResponse(status_code=503, content=exc.to_dict())


@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(
    request: Request, exc: FileNotFoundError
) -> JSONResponse:
    logger.warning("FileNotFoundError serving %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "error": "FileNotFoundError",
            "message": "Required data file is unavailable.",
        },
    )


# Register API routers (must come before static file mounts)
app.include_router(mortality.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(scr.router, prefix="/api")
app.include_router(sensitivity.router, prefix="/api")


@app.get("/api/health")
def health_check():
    """Health check endpoint.

    Reports 503 when startup data loading failed. Previously this returned
    {"status": "ok"} unconditionally -- load_all() swallows its exception into
    _load_error, so a container where every pipeline failed to load still
    passed the Cloud Run health probe and served 503s on every real endpoint.

    `data_source` keeps its legacy single-string shape (frontend footer,
    scripts/validate_production.py); `data_sources` carries the per-dataset
    provenance that the collapsed label cannot express.

    `year_range` is the window the pipelines were actually fitted on, read off
    the loaded data rather than written down. It is here so the footer can
    render its provenance badge from this one call: it previously had to fire a
    second request at /mortality/data/summary just to learn the year range, and
    if that second call failed the attribution paragraph still rendered while
    pointing at a badge that was not on the page.
    """
    load_error = get_load_error()
    payload = {
        "status": "error" if load_error else "ok",
        # Count of engine modules actually importable (a01..a12), not a literal.
        "engine_modules": ENGINE_MODULE_COUNT,
        # Fitted Lee-Carter pipelines currently cached: 3 Mexico + 3 per HMD country.
        "pipelines_loaded": count_loaded_pipelines(),
        "version": "1.0.0",
        "data_source": get_data_source_label(),
        "data_sources": get_data_source(),
        "year_range": get_fitted_year_range(),
    }
    if load_error:
        payload["error"] = load_error
        return JSONResponse(status_code=503, content=payload)
    return payload


# --- Static frontend serving (production) ---
# Serve the built React SPA from frontend/dist/ if it exists.
# In development, the Vite dev server handles this instead.
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    # Mount static asset directories with specific paths
    assets_dir = FRONTEND_DIR / "assets"
    formulas_dir = FRONTEND_DIR / "formulas"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if formulas_dir.exists():
        app.mount("/formulas", StaticFiles(directory=str(formulas_dir)), name="formulas")

    # Serve other static files (vite.svg, etc.) and SPA catch-all
    _FRONTEND_RESOLVED = FRONTEND_DIR.resolve()

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA catch-all: serve static files or index.html for client-side routing."""
        file_path = (FRONTEND_DIR / full_path).resolve()
        # Containment check: prevent path traversal outside frontend dist
        if not str(file_path).startswith(str(_FRONTEND_RESOLVED)):
            return FileResponse(str(FRONTEND_DIR / "index.html"))
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
