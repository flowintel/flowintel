#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_DIR="/opt/flowintel/backups/daily"
DB_NAME="flowintel"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/flowintel/backups/backup.log"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Flowintel backup"

# Stop Flowintel
log "Stopping Flowintel"
systemctl stop flowintel

# Backup database
log "Backing up database"
if sudo -u postgres pg_dump "$DB_NAME" | gzip > "${BACKUP_DIR}/flowintel_db_${TIMESTAMP}.sql.gz"; then
    DB_SIZE=$(du -h "${BACKUP_DIR}/flowintel_db_${TIMESTAMP}.sql.gz" | cut -f1)
    log "Database backup completed: ${DB_SIZE}"
else
    log "ERROR: Database backup failed"
    systemctl start flowintel
    exit 1
fi

# Backup file system
log "Backing up file system"
cd /opt/flowintel
if tar -czf "${BACKUP_DIR}/flowintel_files_${TIMESTAMP}.tar.gz" \
    --exclude='flowintel/__pycache__' \
    --exclude='flowintel/**/__pycache__' \
    flowintel/; then
    FILES_SIZE=$(du -h "${BACKUP_DIR}/flowintel_files_${TIMESTAMP}.tar.gz" | cut -f1)
    log "File system backup completed: ${FILES_SIZE}"
else
    log "ERROR: File system backup failed"
    systemctl start flowintel
    exit 1
fi

# Start Flowintel
log "Starting Flowintel"
systemctl start flowintel

# Remove old backups
log "Removing backups older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -name "flowintel_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "flowintel_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

log "Backup completed successfully"