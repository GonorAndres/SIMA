# SIMA - Sistema Integral de Modelacion Actuarial
# Multi-stage Docker build: Node (frontend) + Python (backend + serving)

# -- Stage 1: Build React frontend ------------------------------------------
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# -- Stage 2: Python runtime ------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code + data
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Cloud Run injects PORT (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

# Run as non-root for security
RUN groupadd -r sima && useradd -r -g sima sima
USER sima

# Single worker -- Cloud Run handles horizontal scaling
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}
