"""
Celery application configuration for Government Scheme AI Assistant.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("govscheme")

# Load config from Django settings, using CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ─────────────────────────────────────────────
# Periodic Tasks (Celery Beat)
# ─────────────────────────────────────────────
app.conf.beat_schedule = {
    "nightly-rag-evaluation": {
        "task": "apps.analytics.tasks.run_nightly_rag_evaluation",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM
    },
    "weekly-log-cleanup": {
        "task": "apps.analytics.tasks.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Celery health check task."""
    print(f"Request: {self.request!r}")
