"""Django settings — Development"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use console email backend in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Enable Browsable API in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Detailed logging in dev
LOGGING["root"]["level"] = "DEBUG"
