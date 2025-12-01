#!/bin/bash
# Check if GPS is collecting data, restart if not
CURRENT=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data WHERE timestamp > strftime('%s', 'now', '-5 minutes');" 2>/dev/null || echo "0")

if [ "$CURRENT" -eq "0" ]; then
    echo "$(date): No recent GPS data, restarting containers" >> /home/USERNAME/gps-tracker/mobile_startup.log
    cd /home/USERNAME/gps-tracker
    docker compose restart gps-logger
fi
