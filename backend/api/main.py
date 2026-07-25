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
from backend.api.services.precomputed import get_data_source, load_all
from backend.engine.exceptions import (
    ActuarialValidationError,
    DataNotAvailableError,
    DataQualityError,
)

logger = logging.getLogger(__name__)


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
_logging_configured = logging.getLogger().handlers
if not _logging_configured:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

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
    """Health check endpoint."""
    return {
        "status": "ok",
        "engine_modules": 12,
        "version": "1.0.0",
        "data_source": get_data_source(),
    }


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
