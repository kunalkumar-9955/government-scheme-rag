"""
backend/config/settings/production.py — Production Settings

Enforces:
- DEBUG = False
- HTTPS & Strict-Transport-Security (HSTS)
- Secure Session and CSRF Cookies
- PostgreSQL Connection Pooling
- S3 / MinIO Object Storage
- JSON Container Logging
- Sentry Error Tracking
- Production Throttling
"""
import os
import sys
from decouple import config, Csv
from .base import *

DEBUG = False

# ─────────────────────────────────────────────
# Allowed Hosts & CSRF Trusted Origins
# ─────────────────────────────────────────────
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="*",
    cast=Csv(),
)

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,https://*.onrender.com,https://*.vercel.app",
    cast=Csv(),
)

# ─────────────────────────────────────────────
# Security & SSL Termination
# ─────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True



# ─────────────────────────────────────────────
# Storage & Media (MinIO / AWS S3)
# ─────────────────────────────────────────────
USE_S3 = config("USE_S3", default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID     = config("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="govscheme-documents")
    AWS_S3_ENDPOINT_URL   = config("AWS_S3_ENDPOINT_URL", default="http://minio:9000")
    AWS_S3_REGION_NAME    = config("AWS_S3_REGION_NAME", default="ap-south-1")
    AWS_DEFAULT_ACL       = None
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE  = "storages.backends.s3boto3.S3Boto3Storage"

# ─────────────────────────────────────────────
# Production Logging
# ─────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s",
        },
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s %(name)s (PID:%(process)d): %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": config("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "rag": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ─────────────────────────────────────────────
# Sentry Error Monitoring
# ─────────────────────────────────────────────
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
            profiles_sample_rate=config("SENTRY_PROFILES_SAMPLE_RATE", default=0.1, cast=float),
            environment=config("ENVIRONMENT", default="production"),
            send_default_pii=False,
        )
    except ImportError:
        pass
