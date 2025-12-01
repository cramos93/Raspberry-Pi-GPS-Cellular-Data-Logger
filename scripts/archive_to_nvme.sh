#!/bin/bash
# Periodically archive old data to NVMe (if available)
# System continues working even if NVMe fails

if mountpoint -q /mnt/nvme; then
    mkdir -p /mnt/nvme/gps-archives
    
    # Archive database records older than 30 days
    timestamp=$(date +%Y%m%d)
    
    sqlite3 /home/USERNAME/gps-data/gps_data.db << SQL
ATTACH DATABASE '/mnt/nvme/gps-archives/archive_${timestamp}.db' AS archive;
CREATE TABLE IF NOT EXISTS archive.gps_data AS SELECT * FROM main.gps_data WHERE 0;
INSERT INTO archive.gps_data SELECT * FROM main.gps_data 
  WHERE timestamp < datetime('now', '-30 days');
SQL
    
    echo "$(date): Archived old records to NVMe"
else
    echo "$(date): NVMe not available, skipping archive (OK)"
fi
