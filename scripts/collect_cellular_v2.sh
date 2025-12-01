#!/bin/bash

# Locking mechanism to prevent concurrent access
LOCKFILE="/tmp/cellular_collection.lock"
exec 200>$LOCKFILE
if ! flock -n 200; then
    echo "$(date): Another instance running, skipping" >> /home/USERNAME/gps-data/logs/cellular_collection.log
    exit 0
fi

# Configuration
DB_PATH="/home/USERNAME/gps-data/gps_data.db"
LOG_FILE="/home/USERNAME/gps-data/logs/cellular_collection.log"
RAW_DATA="/home/USERNAME/gps-data/logs/cellular_raw.txt"

mkdir -p /home/USERNAME/gps-data/logs
TIMESTAMP=$(date +%s)

# Collect QMI data with timeout
SIGNAL_DATA=$(timeout 3 qmicli -d /dev/cdc-wdm0 -p --nas-get-signal-strength 2>/dev/null)
CELL_DATA=$(timeout 3 qmicli -d /dev/cdc-wdm0 -p --nas-get-cell-location-info 2>/dev/null)

# Parse signal strength
RSRP=$(echo "$SIGNAL_DATA" | grep -A1 "RSRP:" | grep "lte" | sed -n "s/.*Network 'lte': '\(-*[0-9]*\).*/\1/p")
RSRQ=$(echo "$SIGNAL_DATA" | grep -A1 "RSRQ:" | grep "lte" | sed -n "s/.*Network 'lte': '\(-*[0-9]*\).*/\1/p")

# Parse cell info
CELL_ID=$(echo "$CELL_DATA" | grep "Global Cell ID:" | sed -n "s/.*'\([0-9]*\)'.*/\1/p")
PCI=$(echo "$CELL_DATA" | grep "Physical Cell ID:" | head -1 | sed -n "s/.*'\([0-9]*\)'.*/\1/p")
BAND=$(echo "$CELL_DATA" | grep "EUTRA.*band" | head -1 | sed -n "s/.*band \([0-9]*\).*/B\1/p")

# Get GPS and insert to database
if [ -f "$DB_PATH" ]; then
    GPS_DATA=$(sqlite3 "$DB_PATH" "SELECT latitude, longitude, speed, heading, altitude FROM gps_data ORDER BY timestamp DESC LIMIT 1;" 2>/dev/null)
    IFS='|' read -r LAT LON SPEED HEADING ALTITUDE <<< "$GPS_DATA"
    
    if [ ! -z "$CELL_ID" ] || [ ! -z "$RSRP" ]; then
        sqlite3 "$DB_PATH" "INSERT INTO cell_observations (ts, lat, lon, speed, heading, altitude, cell_id, pci, rsrp, rsrq, band) VALUES ($TIMESTAMP, $LAT, $LON, $SPEED, $HEADING, $ALTITUDE, '$CELL_ID', $PCI, $RSRP, $RSRQ, '$BAND');" 2>/dev/null
        echo "$(date): Cell=$CELL_ID Band=$BAND RSRP=$RSRP" >> $LOG_FILE
    fi
fi

echo "$TIMESTAMP|$CELL_ID|$PCI|$BAND|$RSRP|$RSRQ" >> $RAW_DATA
LOG_FILE=/home/USERNAME/gps-data/logs/cellular_collection.log
