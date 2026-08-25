from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


# ── Health Check ─────────────────────────────────────────────
def health_check(request):
    """
    GET /api/v1/health/
    Returns a simple status response. Used by Docker, load balancers,
    and the frontend to verify the backend is reachable.
    """
    from django.db import connection
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "connected" if db_ok else "unreachable",
            "version": "1.0.0",
            "phase": "1",
        },
        status=status_code,
    )


# ── API v1 URL Patterns ──────────────────────────────────────
api_v1_patterns = [
    # Health check — always first, no auth required
    path("health/", health_check, name="health-check"),

    # Authentication
    path("auth/", include("apps.authentication.urls")),

    # User profiles
    path("users/", include("apps.users.urls")),

    # Government Schemes & Data Management
    path("schemes/", include("apps.schemes.urls")),

    # Document Ingestion & Management
    path("documents/", include("apps.documents.urls")),

    # Eligibility Evaluation Engine
    path("eligibility/", include("apps.eligibility.urls")),

    # AI Chatbot & RAG Assistant
    path("chat/", include("apps.chat.urls")),

    # Analytics & RAG Evaluation Metrics
    path("analytics/", include("apps.analytics.urls")),

    # Dedicated RAG Evaluation System
    path("evaluation/", include("apps.evaluation.urls")),

    # API Schema & Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
