#!/bin/bash
# Geofence Boundary Monitoring

DB="/home/USERNAME/gps-data/gps_data.db"
STATE_FILE="/tmp/geofence_state"
NOTIFICATION_URL="https://ntfy.sh/gps-tracker-YOUR-TOPIC"

# Get current geofence status from GPS logger
CURRENT_STATUS=$(docker compose exec gps-logger python3 -c "
import json
import sqlite3

db = sqlite3.connect('/app/data/gps_data.db')
cursor = db.cursor()
cursor.execute('SELECT latitude, longitude FROM gps_data ORDER BY id DESC LIMIT 1')
result = cursor.fetchone()

if result:
    lat, lon = result
    # Check if in YOUR_CITY County (simplified check - you may need to adjust)
    in_culpeper = (lat > 38.3 and lat < 38.7 and lon > -78.2 and lon < -77.6)
    print('INSIDE' if in_culpeper else 'OUTSIDE')
" 2>/dev/null)

# Read previous state
PREVIOUS_STATUS=$(cat $STATE_FILE 2>/dev/null || echo "UNKNOWN")

# Check for boundary crossing
if [ "$CURRENT_STATUS" != "$PREVIOUS_STATUS" ] && [ "$PREVIOUS_STATUS" != "UNKNOWN" ]; then
    LAST_POS=$(sqlite3 $DB "SELECT latitude || ',' || longitude FROM gps_data ORDER BY id DESC LIMIT 1;" 2>/dev/null)
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ "$CURRENT_STATUS" = "OUTSIDE" ]; then
        curl -s -d "🚨 BOUNDARY VIOLATION 🚨

EVENT: LEFT YOUR_CITY County Geofence
TIME: ${TIMESTAMP}
LAST POSITION: ${LAST_POS}

Vehicle has exited monitored area!" \
        "$NOTIFICATION_URL" > /dev/null
    else
        curl -s -d "✅ BOUNDARY RE-ENTRY ✅

EVENT: ENTERED YOUR_CITY County Geofence  
TIME: ${TIMESTAMP}
POSITION: ${LAST_POS}

Vehicle has returned to monitored area!" \
        "$NOTIFICATION_URL" > /dev/null
    fi
fi

# Save current state
echo "$CURRENT_STATUS" > $STATE_FILE
