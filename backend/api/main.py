"""
SIMA API - Sistema Integral de Modelacion Actuarial
====================================================

FastAPI application that exposes the actuarial engine (a01-a12) via REST endpoints.

Startup:
    cd /home/andtega349/SIMA
    python -m uvicorn backend.api.main:app --reload

Docs:
    http://localhost:8000/docs
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend is importable
_project_dir = str(Path(__file__).parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from backend.api.services.precomputed import load_all
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

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(mortality.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(scr.router, prefix="/api")
app.include_router(sensitivity.router, prefix="/api")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "engine_modules": 12, "version": "1.0.0"}
