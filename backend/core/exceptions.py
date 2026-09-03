"""
core/exceptions.py — Standardized API error responses
"""
import logging
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns consistent JSON error structure:
    {
        "success": false,
        "error": {
            "code": "...",
            "message": "...",
            "details": {...}
        }
    }
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "success": False,
            "error": {
                "code": _get_error_code(response.status_code),
                "message": _extract_message(response.data),
                "details": response.data if not isinstance(response.data, str) else {},
            },
        }
        response.data = error_payload
        return response

    # Handle Django exceptions not caught by DRF
    if isinstance(exc, Http404):
        return Response(
            {"success": False, "error": {"code": "NOT_FOUND", "message": "Resource not found."}},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, PermissionDenied):
        return Response(
            {"success": False, "error": {"code": "FORBIDDEN", "message": "You do not have permission."}},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, ValidationError):
        return Response(
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle Django Database Errors
    from django.db import DatabaseError
    if isinstance(exc, DatabaseError):
        logger.exception("Database error occurred: %s", exc)
        return Response(
            {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Database error: {str(exc)}. Please check database connectivity and migrations.",
                    "details": {"exception": exc.__class__.__name__, "info": str(exc)},
                },
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Unhandled server error
    logger.exception("Unhandled exception: %s", exc)
    err_str = str(exc) if str(exc) else "An unexpected error occurred."
    return Response(
        {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": err_str,
                "details": {"exception": exc.__class__.__name__, "info": str(exc)},
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_code(status_code: int) -> str:
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
    }
    return codes.get(status_code, f"HTTP_{status_code}")


def _extract_message(data) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return data[0] if data else "Error"
    if isinstance(data, dict):
        for key in ("detail", "message", "non_field_errors"):
            if key in data:
                val = data[key]
                return val[0] if isinstance(val, list) else str(val)
        first_val = next(iter(data.values()), "Error")
        return first_val[0] if isinstance(first_val, list) else str(first_val)
    return "An error occurred"


class APIError(Exception):
    """Base custom API exception for app-level raises."""

    def __init__(self, message: str, code: str = "API_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class DocumentProcessingError(APIError):
    def __init__(self, message: str):
        super().__init__(message, code="DOCUMENT_PROCESSING_ERROR", status_code=422)


class RAGError(APIError):
    def __init__(self, message: str):
        super().__init__(message, code="RAG_ERROR", status_code=500)


class EligibilityError(APIError):
    def __init__(self, message: str):
        super().__init__(message, code="ELIGIBILITY_ERROR", status_code=400)
