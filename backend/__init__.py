"""
Backend package init — expose Celery app for Django to auto-discover.
"""
from .celery_app import app as celery_app

__all__ = ("celery_app",)
