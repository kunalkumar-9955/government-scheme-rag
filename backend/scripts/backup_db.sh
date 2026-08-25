#!/usr/bin/env bash
# ============================================================
# Government Scheme Platform — Automated Database Backup Script
# Usage: ./backup_db.sh [backup_dir]
# Creates compressed pg_dump snapshot including pgvector tables.
# ============================================================

set -euo pipefail

BACKUP_DIR="${1:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/govscheme_db_backup_${TIMESTAMP}.sql.gz"

DB_NAME="${POSTGRES_DB:-govscheme_db}"
DB_USER="${POSTGRES_USER:-govscheme_user}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"

mkdir -p "${BACKUP_DIR}"

echo "[+] Starting PostgreSQL + pgvector database backup for ${DB_NAME} at $(date)"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_FILE}"

echo "[✓] Backup completed successfully: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

# Retention: Keep backups for 30 days, purge older
find "${BACKUP_DIR}" -name "govscheme_db_backup_*.sql.gz" -type f -mtime +30 -delete
echo "[✓] Purged backups older than 30 days."
