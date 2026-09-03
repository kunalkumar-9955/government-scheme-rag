# ============================================================
# Government Scheme AI Assistant — Django Backend
# Multi-stage Docker build for production efficiency
# ============================================================

FROM python:3.12-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── Dependencies Stage ──
FROM base AS deps

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ── Final Stage ──
FROM deps AS production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs && \
    chown -R appuser:appuser /app

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

USER appuser

EXPOSE 8000

# Default command: Migrate, Seed Demo Accounts, and Start Gunicorn on dynamic PORT
CMD ["sh", "-c", "python manage.py migrate --settings=config.settings.production && python manage.py seed_users --settings=config.settings.production || true && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --threads 2 --worker-class sync --worker-tmp-dir /dev/shm --timeout 120 --keep-alive 5 --log-level info --access-logfile - --error-logfile -"]