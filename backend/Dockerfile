# Multi-stage Dockerfile for Talent Pool Screening Backend

# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/local -r requirements.txt


# Stage 2: Final Runtime Image
FROM python:3.11-slim

WORKDIR /app

# Create non-root app user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /install/local /usr/local

# Copy application code
COPY . /app

# Ensure writable temporary and report directories
RUN mkdir -p /app/tmp/reports && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Native Python urllib healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
