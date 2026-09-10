#!/bin/bash
set -e

echo "========================================================"
echo "  WebGIS PostGIS Database Restore Utility (Linux)"
echo "========================================================"
echo ""

if [ -z "$1" ]; then
    echo "Usage: ./restore_database.sh path/to/backup_file.sql"
    echo ""
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file does not exist: ${BACKUP_FILE}"
    exit 1
fi

echo "WARNING: This will overwrite existing data in webgis database!"
read -p "Are you sure you want to proceed? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Restoring database from ${BACKUP_FILE}..."
docker exec -i webgis-postgis psql -U postgres -d webgis < "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Database restored successfully!"
else
    echo "[ERROR] Restore failed."
fi

echo ""
