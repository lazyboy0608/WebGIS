#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/webgis_backup_${TIMESTAMP}.sql"

echo "========================================================"
echo "  WebGIS PostGIS Database Backup Utility (Linux)"
echo "========================================================"
echo ""

mkdir -p "${BACKUP_DIR}"

echo "Backing up PostgreSQL / PostGIS database to:"
echo "${BACKUP_FILE}"
echo ""

docker exec webgis-postgis pg_dump -U postgres webgis > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Backup completed successfully!"
    ls -lh "${BACKUP_FILE}"
else
    echo "[ERROR] Backup failed. Make sure webgis-postgis container is running."
fi

echo ""
