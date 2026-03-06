#!/usr/bin/env bash
# Backup analytics SQLite database to a dated file.
# Usage: ./scripts/backup/backup-analytics.sh [source_path] [backup_dir]
set -euo pipefail

SRC="${1:-apps/api/data/analytics.db}"
BACKUP_DIR="${2:-backups/analytics}"
DATE=$(date +%Y%m%d_%H%M%S)

if [ ! -f "$SRC" ]; then
    echo "Source database not found: $SRC"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$SRC" "$BACKUP_DIR/analytics_${DATE}.db"
echo "Backed up to $BACKUP_DIR/analytics_${DATE}.db"

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/analytics_*.db 2>/dev/null | tail -n +31 | xargs -r rm --
echo "Cleanup complete. $(ls "$BACKUP_DIR"/analytics_*.db 2>/dev/null | wc -l) backups retained."
