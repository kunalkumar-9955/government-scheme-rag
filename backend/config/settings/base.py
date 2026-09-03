"""
Django settings — Base configuration
Government Scheme AI Assistant
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# ─────────────────────────────────────────────
# Base Paths
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────
SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ─────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

try:
    import django_extensions
    THIRD_PARTY_APPS.append("django_extensions")
except ImportError:
    pass

try:
    import storages
    THIRD_PARTY_APPS.append("storages")
except ImportError:
    pass

LOCAL_APPS = [
    "apps.authentication",
    "apps.users",
    "apps.documents",
    "apps.schemes",
    "apps.chat",
    "apps.eligibility",
    "apps.analytics",
    "apps.evaluation",
    "apps.admin_panel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─────────────────────────────────────────────
# Database — PostgreSQL + pgvector
# ─────────────────────────────────────────────
DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=config("DB_SSL_REQUIRE", default=False, cast=bool),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="govscheme_db"),
            "USER": config("POSTGRES_USER", default="govscheme_user"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="govscheme_pass"),
            "HOST": config("POSTGRES_HOST", default="localhost"),
            "PORT": config("POSTGRES_PORT", default="5432"),
            "OPTIONS": {
                "connect_timeout": 10,
                "sslmode": config("POSTGRES_SSLMODE", default="prefer"),
            },
            "CONN_MAX_AGE": 60,
        }
    }

# ─────────────────────────────────────────────
# Custom User Model
# ─────────────────────────────────────────────
AUTH_USER_MODEL = "authentication.CustomUser"

# ─────────────────────────────────────────────
# Password Validation
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ─────────────────────────────────────────────
# Internationalization
# ─────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────
# Static & Media Files
# ─────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Local Development Cache
# Redis is not required for local admin testing.
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "government-scheme-rag-local-cache",
    }
}

# Store Django sessions in PostgreSQL instead of Redis
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ─────────────────────────────────────────────
# Celery
# ─────────────────────────────────────────────
CELERY_BROKER_URL = REDIS_URL + "/0"
CELERY_RESULT_BACKEND = REDIS_URL + "/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_TASK_ROUTES = {
    "apps.documents.tasks.*": {"queue": "documents"},
    "apps.chat.tasks.*": {"queue": "rag"},
    "apps.analytics.tasks.*": {"queue": "evaluation"},
}

CELERY_BEAT_SCHEDULE = {
    "nightly-rag-evaluation": {
        "task": "apps.analytics.tasks.run_nightly_rag_evaluation",
        "schedule": "0 2 * * *",  # 2 AM daily
    },
    "weekly-log-cleanup": {
        "task": "apps.analytics.tasks.cleanup_old_logs",
        "schedule": "0 3 * * 0",  # Sunday 3 AM
    },
}

# ─────────────────────────────────────────────
# Django REST Framework
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_ANON_RATE", default="120/minute"),
        "user": config("THROTTLE_USER_RATE", default="600/minute"),
    },
}

# ─────────────────────────────────────────────
# JWT Configuration
# ─────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ─────────────────────────────────────────────
# CORS Configuration
# ─────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ─────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]
MAX_DOCUMENT_SIZE_MB = 50

# ─────────────────────────────────────────────
# MinIO / S3 Storage
# ─────────────────────────────────────────────
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = config("MINIO_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = config("MINIO_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = config("MINIO_BUCKET_NAME", default="govscheme-docs")
    AWS_S3_ENDPOINT_URL = config("MINIO_ENDPOINT_URL", default="http://minio:9000")
    AWS_S3_CUSTOM_DOMAIN = None
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    DOCUMENT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
else:
    DOCUMENT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ─────────────────────────────────────────────
# AI / LLM Configuration
# ─────────────────────────────────────────────
GOOGLE_API_KEY = config("GOOGLE_API_KEY", default="")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
COHERE_API_KEY = config("COHERE_API_KEY", default="")

# LLM Settings
LLM_PRIMARY_MODEL = config("LLM_PRIMARY_MODEL", default="gemini-1.5-pro")
LLM_FAST_MODEL = config("LLM_FAST_MODEL", default="gemini-2.0-flash-exp")
LLM_EMBEDDING_MODEL = config("LLM_EMBEDDING_MODEL", default="models/text-embedding-004")
LLM_MAX_TOKENS = config("LLM_MAX_TOKENS", default=2048, cast=int)
LLM_TEMPERATURE = config("LLM_TEMPERATURE", default=0.1, cast=float)

# RAG Settings
RAG_TOP_K_RETRIEVE = config("RAG_TOP_K_RETRIEVE", default=20, cast=int)
RAG_TOP_K_RERANK = config("RAG_TOP_K_RERANK", default=5, cast=int)
RAG_CHUNK_SIZE = config("RAG_CHUNK_SIZE", default=512, cast=int)
RAG_CHUNK_OVERLAP = config("RAG_CHUNK_OVERLAP", default=64, cast=int)
RAG_SIMILARITY_THRESHOLD = config("RAG_SIMILARITY_THRESHOLD", default=0.7, cast=float)

# Reranker Settings
RERANKER_MODEL = config("RERANKER_MODEL", default="BAAI/bge-reranker-v2-m3")
USE_RERANKER = config("USE_RERANKER", default=True, cast=bool)

# ─────────────────────────────────────────────
# API Documentation (drf-spectacular)
# ─────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Government Scheme AI Assistant API",
    "DESCRIPTION": "AI-powered RAG platform for government scheme discovery and eligibility evaluation.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
}

# ─────────────────────────────────────────────
# Email Configuration
# ─────────────────────────────────────────────
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@govscheme.ai")

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "rag": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
