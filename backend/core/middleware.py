"""
core/middleware.py — Request logging, security headers
"""
import time
import logging
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Logs every request with duration, method, path, status, and request ID.
    Injects X-Request-ID header for tracing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        start_time = time.monotonic()

        response = self.get_response(request)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        user_id = request.user.id if request.user.is_authenticated else "anon"

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            },
        )

        response["X-Request-ID"] = request_id
        return response
