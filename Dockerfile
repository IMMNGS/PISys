# Multi-stage Dockerfile for Patient Information System
# Production-optimized for Synology NAS deployment
#
# Usage:
#   docker build -t pisys-app:latest .
#   docker compose up -d

# ════════════════════════════════════════════════════════════════════════════
# Stage 1: Python dependencies builder
# ════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS python-builder

WORKDIR /build

# Install build tools needed for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip install --user --no-cache-dir \
    --no-warn-script-location \
    --requirement requirements.txt

# ════════════════════════════════════════════════════════════════════════════
# Stage 2: Frontend builder
# ════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy frontend code and dependencies
COPY frontend/package.json frontend/package-lock.json ./

# Install frontend dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy frontend source
COPY frontend ./

# Build React app for production
RUN npm run build

# ════════════════════════════════════════════════════════════════════════════
# Stage 3: Runtime environment
# ════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim

# Metadata
LABEL maintainer="PISYS Team"
LABEL description="Patient Information System - Production Container"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    FLASK_APP=run.py \
    PORT=8000

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend /app/backend
COPY frontend/dist /app/frontend/dist
COPY run.py gunicorn.conf.py ./
COPY .env.synology.example .env.example

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Create data directories
RUN mkdir -p /app/data/vcf /app/data/variant_uploads && \
    chown -R appuser:appuser /app/data

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Expose port
EXPOSE ${PORT}

# Run production server
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
