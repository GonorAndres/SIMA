# SIMA - Sistema Integral de Modelacion Actuarial
# Backend-only image. The React frontend is deployed separately to Cloudflare Pages.
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code + data
COPY backend/ ./backend/

# Cloud Run injects PORT (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

# Run as non-root for security
RUN groupadd -r sima && useradd -r -g sima sima
USER sima

# Single worker -- Cloud Run handles horizontal scaling
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}
