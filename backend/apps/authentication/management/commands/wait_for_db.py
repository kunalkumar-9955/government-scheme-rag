"""
apps/authentication/management/commands/wait_for_db.py
Custom management command to wait for DB to be ready (used in Docker entrypoint).
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Wait for the database to be available."

    def handle(self, *args, **options):
        self.stdout.write("Waiting for database connection...")
        db_conn = None
        attempts = 0
        max_attempts = 30

        while not db_conn and attempts < max_attempts:
            try:
                db_conn = connections["default"]
                db_conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database is available!"))
                return
            except OperationalError:
                attempts += 1
                self.stdout.write(f"Database unavailable, waiting... (attempt {attempts}/{max_attempts})")
                time.sleep(2)

        self.stdout.write(self.style.ERROR("Database did not become available after max retries."))
        raise SystemExit(1)
