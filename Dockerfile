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

# Single worker -- Cloud Run handles horizontal scaling.
# Exec (JSON) form, and `exec` inside the sh -c wrapper, so uvicorn replaces
# the shell as PID 1 and receives Cloud Run's SIGTERM directly. Shell form
# would leave /bin/sh as PID 1 swallowing the signal (killed revisions).
# The sh -c wrapper exists only to expand ${PORT:-8080}.
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
