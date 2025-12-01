#!/bin/bash
# Check database integrity on boot and periodically

DB_PATH="/home/USERNAME/gps-data/gps_data.db"
BACKUP_PATH="/home/USERNAME/gps-data/backups"

check_db() {
    sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1
}

result=$(check_db)

if [[ "$result" != "ok" ]]; then
    echo "$(date): Database corruption detected!"
    
    # Try to recover from WAL
    sqlite3 "$DB_PATH" "PRAGMA wal_checkpoint(RESTART);" 2>&1
    
    # Check again
    result=$(check_db)
    
    if [[ "$result" != "ok" ]]; then
        echo "$(date): Recovery failed, restoring from backup"
        # Restore latest backup
        latest_backup=$(ls -t $BACKUP_PATH/gps_data_*.db 2>/dev/null | head -1)
        if [ -n "$latest_backup" ]; then
            cp "$latest_backup" "$DB_PATH"
            echo "$(date): Restored from $latest_backup"
        fi
    fi
fi
