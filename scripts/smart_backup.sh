#!/bin/bash
# Backup database only when significant changes occur

DB_PATH="/home/USERNAME/gps-data/gps_data.db"
BACKUP_DIR="/home/USERNAME/gps-data/backups"
LAST_SIZE_FILE="/tmp/last_db_size"

current_size=$(stat -c%s "$DB_PATH")
last_size=$(cat "$LAST_SIZE_FILE" 2>/dev/null || echo "0")

# Only backup if database grew by more than 100KB
size_diff=$((current_size - last_size))

if [ $size_diff -gt 102400 ]; then
    timestamp=$(date +%Y%m%d_%H%M%S)
    cp "$DB_PATH" "$BACKUP_DIR/gps_data_${timestamp}.db"
    echo "$current_size" > "$LAST_SIZE_FILE"
    echo "$(date): Backup created (grew by $(($size_diff/1024))KB)"
    
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/gps_data_*.db | tail -n +11 | xargs rm -f 2>/dev/null
fi
