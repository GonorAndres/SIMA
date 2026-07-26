# Agent Notes for SIMA

## Project

- **Name:** SIMA — Sistema Integral de Modelación Actuarial
- **Purpose:** End-to-end actuarial modeling platform for life insurance under Mexican regulation (LISF/CUSF).
- **Stack:** Python 3.12 + FastAPI/Pydantic v2 backend; React 19 + TypeScript + Vite frontend; Docker + Google Cloud Run deployment.

## Current Branch

- **Active branch:** `25julio`
- **Goal:** Harden the backend actuarial engine before opening a PR to `main`.

## Active Plan

The canonical implementation plan is in:

```
docs/plan-25julio.md
```

Always read this file at the start of a new session. It contains the prioritized phases, open decisions, and resume instructions.

## Quick Commands

```bash
# Run backend tests
pytest backend/tests/

# Start API server
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Start frontend dev server
cd frontend && npm run dev
```

## Notes

- Do not commit to `main` directly.
- Keep commits on `25julio` incremental and phase-focused.
- Before large changes, confirm the open decisions listed in `docs/plan-25julio.md`.
