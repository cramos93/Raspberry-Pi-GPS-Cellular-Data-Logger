#!/bin/bash
BACKUP_DIR="/mnt/nvme/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
if [ -f /mnt/nvme/gps_data.db ]; then
    sqlite3 /mnt/nvme/gps_data.db ".backup '$BACKUP_DIR/gps_data_$TIMESTAMP.db'"
    echo "Database backed up to: $BACKUP_DIR/gps_data_$TIMESTAMP.db"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "gps_data_*.db" -mtime +7 -delete
    echo "Old backups cleaned up (keeping 7 days)"
else
    echo "No database found to backup"
fi

# Show disk usage
echo ""
echo "Disk usage:"
du -sh /mnt/nvme/gps_data.db 2>/dev/null || echo "Database not yet created"
df -h /mnt/nvme
