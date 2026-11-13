# ===================================================================
# Multi-Stage Production Dockerfile for Seller Operations System
# ===================================================================
FROM python:3.12-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PORT=5000 \
    HOST=0.0.0.0

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create non-root system user for least privilege security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/exports && \
    chown -R appuser:appuser /app

USER appuser

# Expose standard container port
EXPOSE 5000

# Docker Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Production WSGI server launch
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]

