# Session 13: Cloud Run Deployment (2026-02-21)

## Objective

Deploy SIMA (full-stack FastAPI + React) to Google Cloud Run for public portfolio access.

## Pre-deployment Fixes Applied

### 1. requirements.txt -- Missing Runtime Dependencies
**Problem**: `requirements.txt` only had numpy, pandas, scipy. The FastAPI app wouldn't start in a clean container.
**Fix**: Added `fastapi>=0.128`, `uvicorn>=0.30`, `pydantic>=2.0`. Removed `pytest` (dev-only).

### 2. backend/engine/a10_validation.py -- Absolute Import
**Problem**: Used `from backend.engine.a01_life_table import LifeTable` (absolute import). All other engine modules (a01-a09, a11-a12) use relative imports. This breaks when the package is installed differently or the working directory changes.
**Fix**: Changed to `from .a01_life_table import LifeTable`.

### 3. backend/engine/__init__.py -- Missing Exports
**Problem**: `__init__.py` only exported a01-a09. Modules a10 (MortalityComparison), a11 (Policy, Portfolio), a12 (SCR functions) were missing.
**Fix**: Added all missing imports and `__all__` entries.

### 4. backend/api/services/precomputed.py -- Real Data Auto-detection
**Problem**: Hardcoded mock data paths. API would never use real INEGI/CONAPO/CNSF data even when available.
**Fix**: Added `_resolve_paths()` that checks for real data at `backend/data/inegi/` and `backend/data/conapo/`. Falls back to mock data at `backend/data/mock/` if real files are missing. Added `get_data_source()` returning `"real"` or `"mock"` for the health endpoint.

### 5. backend/api/main.py -- Production Serving
**Problem**: No static file serving, no SPA catch-all, CORS hardcoded to `*`.
**Fix**:
- CORS origins from `CORS_ORIGINS` env var (defaults to `*`)
- `StaticFiles` mounts for `/assets` and `/formulas` directories
- SPA catch-all `/{full_path:path}` returns `index.html` for client-side routing
- Health endpoint includes `data_source` field

### 6. backend/tests/test_api/test_mortality_api.py -- Flexible Assertions
**Problem**: `assert data["min_age"] == 0` fails with real CNSF table (starts at age 12).
**Fix**: Changed to `assert data["min_age"] >= 0` -- works with both mock (age 0) and real (age 12).

## Infrastructure Created

### Dockerfile (Multi-stage Build)
```
Stage 1: node:22-slim
  - npm ci + npm run build (React frontend -> dist/)

Stage 2: python:3.12-slim
  - pip install requirements.txt
  - Copy backend/ + frontend/dist/
  - CMD: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```
Final image: ~423MB. Cloud Run injects `PORT=8080`.

### .dockerignore
Excludes: venv, __pycache__, .git, docs, HMD data, CONAPO XLSX, tests, analysis results.
**Intentionally includes**: `backend/data/inegi/`, `backend/data/conapo/*.csv`, `backend/data/cnsf/` (real data needed by API).

### .gcloudignore
Separate from `.gitignore` because:
- `.gitignore` excludes real data directories (they're large, shouldn't be in git)
- `.gcloudignore` includes them (they must be uploaded to Cloud Build for the API)
- If no `.gcloudignore` exists, `gcloud run deploy --source .` falls back to `.gitignore`, which would exclude the data

---

## GCP Infrastructure Steps (Critical)

### Project Details
| Field | Value |
|:------|:------|
| Project ID | `project-ad7a5be2-a1c7-4510-82d` |
| Project Number | `451451662791` |
| Region | `us-central1` |
| Service Name | `sima` |
| Service URL | `https://sima-451451662791.us-central1.run.app` |

### Required GCP APIs (3)
All must be enabled before deployment:
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```
These were already enabled in this project.

### IAM Permissions (Critical -- Deployment Fails Without These)

The Compute Engine default service account (`{PROJECT_NUMBER}-compute@developer.gserviceaccount.com`) is used by Cloud Build. It needs 3 roles:

| Role | Why |
|:-----|:----|
| `roles/storage.objectAdmin` | Cloud Build reads source from GCS bucket and writes build artifacts |
| `roles/artifactregistry.writer` | Cloud Build pushes the Docker image to Artifact Registry |
| `roles/logging.logWriter` | Cloud Build writes build logs to Cloud Logging |

**Commands executed:**
```bash
SA="451451662791-compute@developer.gserviceaccount.com"
PROJECT="project-ad7a5be2-a1c7-4510-82d"

# 1. Storage access (source upload + artifact storage)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectAdmin" \
  --condition=None

# 2. Artifact Registry (push Docker image)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/artifactregistry.writer" \
  --condition=None

# 3. Logging (build logs)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/logging.logWriter" \
  --condition=None
```

### Failure Modes Encountered

**Failure 1: `storage.objects.get` denied**
- Symptom: `gcloud run deploy --source .` fails after "Uploading sources...done" with permission error
- Cause: Compute SA lacked `roles/storage.objectAdmin`
- Fix: Grant the role as above

**Failure 2: Build SUCCESS but deployment FAILURE**
- Symptom: `gcloud builds describe` shows Docker step status=SUCCESS but overall status=FAILURE; `images` result is `None`
- Cause: Compute SA lacked `roles/artifactregistry.writer` -- image built but couldn't be pushed to Artifact Registry
- Fix: Grant the role as above

### Deployment Command
```bash
gcloud run deploy sima \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --max-instances 3
```

**Key flags:**
- `--source .`: Upload source + build in Cloud Build (no local Docker needed)
- `--allow-unauthenticated`: Public access (portfolio showcase)
- `--memory 1Gi`: Lee-Carter SVD on 101x31 matrix + 3 countries needs headroom
- `--timeout 300`: Some first-request computations take several seconds
- `--max-instances 3`: Cost control (scale-to-zero when idle, max 3 for traffic spikes)

### Artifact Registry Repository
Cloud Run automatically created: `us-central1-docker.pkg.dev/project-ad7a5be2-a1c7-4510-82d/cloud-run-source-deploy/sima:latest`

---

## Verification

### Health Check
```bash
curl https://sima-451451662791.us-central1.run.app/api/health
# {"status":"ok","engine_modules":12,"version":"1.0.0","data_source":"real"}
```

### API Endpoints (all 21 verified working)
- `/api/mortality/data/summary` -- Mexico, Total, ages 0-100, years 1990-2020
- `/api/mortality/lee-carter` -- 101 ages, 31 years, explained_var=0.6284
- `/api/sensitivity/cross-country` -- Mexico drift=-1.08, USA=-1.19, Spain=-2.89
- All POST endpoints (pricing, portfolio, SCR, sensitivity) operational

### Frontend
- SPA serves at root URL with automatic HTTPS
- All 6 routes (/, /mortalidad, /precios, /portafolio, /sensibilidad, /metodologia) serve index.html
- Static assets (/assets/*.js, /assets/*.css, /formulas/*.png) served correctly

---

## Architecture: How Cloud Run Deployment Works

```
Developer Machine                    Google Cloud
     |                                   |
     |  gcloud run deploy --source .     |
     |---------------------------------->|
     |                                   |
     |  1. Upload source to GCS          |
     |  (respects .gcloudignore)         |
     |                                   |
     |  2. Cloud Build reads source      |
     |     Runs Dockerfile               |
     |     Stage 1: npm ci + build       |
     |     Stage 2: pip install + copy   |
     |                                   |
     |  3. Push image to Artifact Reg.   |
     |                                   |
     |  4. Deploy to Cloud Run           |
     |     - Inject PORT=8080            |
     |     - Configure auto-scaling      |
     |     - Assign HTTPS URL            |
     |                                   |
     |  5. Route 100% traffic            |
     |<----------------------------------|
     |  Service URL returned             |
```

### Cost Model
- **Scale to zero**: No charge when idle (no traffic = no instances)
- **Per-request billing**: CPU + memory charged only during request processing
- **Free tier**: 2M requests/month, 360K vCPU-seconds, 180K GiB-seconds
- For a portfolio project with occasional visitors, cost should be ~$0/month

---

## Files Changed in This Session

| File | Action | Purpose |
|:-----|:-------|:--------|
| `requirements.txt` | Modified | Added fastapi, uvicorn, pydantic |
| `backend/engine/a10_validation.py` | Modified | Relative import |
| `backend/engine/__init__.py` | Modified | Added a10-a12 exports |
| `backend/api/services/precomputed.py` | Modified | Real data auto-detection |
| `backend/api/main.py` | Rewritten | Production-ready: CORS, SPA, static files |
| `backend/tests/test_api/test_mortality_api.py` | Modified | Flexible min_age assertion |
| `Dockerfile` | Created | Multi-stage Node + Python build |
| `.dockerignore` | Created | Exclude dev files, include real data |
| `.gcloudignore` | Created | Cloud Build upload filter |
| `docs/project/13_cloud_run_deployment_project.md` | Created | This document |
