#!/bin/bash
# Simple GPS Tracker Monitor - Post-Debug Version
LOG="/home/USERNAME/gps-data/logs/monitor.log"

# Check if containers are running
GPS_RUNNING=$(docker ps | grep -c gps-logger)
LTE_RUNNING=$(docker ps | grep -c lte-monitor)

# Check if GPS is collecting data
BEFORE=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data;" 2>/dev/null || echo 0)
sleep 30
AFTER=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data;" 2>/dev/null || echo 0)

# Only act if there's a real problem
if [ "$GPS_RUNNING" -eq 0 ] || [ "$((AFTER - BEFORE))" -eq 0 ]; then
    echo "$(date): Issue detected - GPS:$GPS_RUNNING, New records:$((AFTER - BEFORE))" >> "$LOG"
    cd /home/USERNAME/gps-tracker
    docker compose restart gps-logger
    curl -s -d "🔧 GPS Logger restarted - check status" https://ntfy.sh/gps-tracker-YOUR-TOPIC > /dev/null
fi
