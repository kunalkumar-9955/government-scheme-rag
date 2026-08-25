#!/usr/bin/env bash
# ============================================================
# Government Scheme Platform — Database Restore Script
# Usage: ./restore_db.sh <path_to_backup.sql.gz>
# ============================================================

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "[-] Error: Please specify the backup file path to restore."
    echo "Usage: $0 /backups/govscheme_db_backup_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[-] Error: Backup file '${BACKUP_FILE}' does not exist."
    exit 1
fi

DB_NAME="${POSTGRES_DB:-govscheme_db}"
DB_USER="${POSTGRES_USER:-govscheme_user}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "[!] WARNING: This will restore database '${DB_NAME}' from ${BACKUP_FILE}."
echo "[+] Starting restore at $(date)..."

PGPASSWORD="${POSTGRES_PASSWORD}" gunzip -c "${BACKUP_FILE}" | psql \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --single-transaction

echo "[✓] Database restore completed successfully at $(date)."
