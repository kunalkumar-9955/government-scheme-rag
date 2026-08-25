"""
config/settings/phase1.py — Phase 1 Development Settings
-------------------------------------------------------
Overrides base.py for Phase 1 (Foundation only).
Key differences from base.py:
  - Uses local memory cache (no Redis required)
  - Disables Celery / Beat
  - Registers ONLY the apps needed for Phase 1
  - Uses console email backend
  - Relaxed CORS for local development
"""
from .base import *  # noqa: F401, F403
import os

# ── Debug ──
DEBUG = True
ALLOWED_HOSTS = ["*"]

# ── Phase 1 Installed Apps ─────────────────────────────────
# Only register apps that have working models + migrations.
# RAG, Chat, Documents etc. are added in later phases.
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

LOCAL_APPS = [
    "apps.authentication",
    "apps.users",
    "apps.schemes",
    "apps.documents",
    "apps.eligibility",
    "apps.chat",
    "apps.analytics",
    "apps.evaluation",
]

ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".docx", ".doc", ".html", ".htm", ".txt"]
MAX_DOCUMENT_SIZE_MB = 50
RAG_CHUNK_SIZE = 512
RAG_CHUNK_OVERLAP = 64
LLM_EMBEDDING_MODEL = "models/text-embedding-004"
GOOGLE_API_KEY = "mock-google-api-key"

# ── RAG Retrieval Settings ──────────────────────────────────
RAG_TOP_K_RETRIEVE = 20          # How many chunks to retrieve before reranking
RAG_TOP_K_RERANK = 5             # How many chunks to keep after reranking
RAG_SIMILARITY_THRESHOLD = 0.0   # Min cosine score for dense results (0 = no filter in tests)

# ── Reranker ────────────────────────────────────────────────
USE_RERANKER = False             # Disabled in Phase 1 (model not installed)
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# ── LLM Models ──────────────────────────────────────────────
LLM_PRIMARY_MODEL = "gemini-1.5-pro"
LLM_FAST_MODEL = "gemini-2.0-flash-exp"
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.1

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Local Memory Cache (no Redis needed in Phase 1) ────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "govscheme-phase1",
    }
}

# Sessions via DB (no Redis needed)
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = None

# ── Disable Celery ──────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True   # Tasks run inline, synchronously
CELERY_BEAT_SCHEDULE = {}

# ── Email: Print to console ─────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── CORS: Allow all origins in local dev ───────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ── Password hashers: only PBKDF2 for fast dev ─────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ── Logging: DEBUG level ────────────────────────────────────
LOGGING["root"]["level"] = "DEBUG"  # type: ignore[index]
