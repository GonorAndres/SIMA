"""
SIMA API - Sistema Integral de Modelacion Actuarial
====================================================

FastAPI application that exposes the actuarial engine (a01-a12) via REST endpoints.
Serves both the API and the React frontend from a single process.

Local dev:
    cd /home/andtega349/SIMA
    python -m uvicorn backend.api.main:app --reload

Production (Cloud Run):
    uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure backend is importable
_project_dir = str(Path(__file__).parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.api.services.precomputed import load_all, get_data_source
from backend.api.routers import mortality, pricing, portfolio, scr, sensitivity


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
        "and solvency capital requirements (SCR) under the Solvency II / CNSF framework."
    ),
    version="1.0.0",
    lifespan=lifespan,
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
