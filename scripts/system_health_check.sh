#!/bin/bash

# Function to check each component
check_health() {
    local failures=0
    local status_msg=""
    
    # Check containers
    CONTAINERS=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format '{{.Status}}' | grep -c healthy)
    if [ "$CONTAINERS" -eq "2" ]; then
        status_msg+="✅ Docker Containers: 2/2 healthy
"
    else
        status_msg+="❌ Docker Containers: $CONTAINERS/2 healthy
"
        failures=$((failures + 1))
    fi
    
    # Check GPS device
    if [ -e /dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0 ]; then
        status_msg+="✅ GPS Device: Connected
"
    else
        status_msg+="❌ GPS Device: Not found
"
        failures=$((failures + 1))
    fi
    
    # Check cellular modem
    if qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -q dBm; then
        SIGNAL=$(qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep "Network 'lte'" | head -1 | grep -o '[0-9]* dBm')
        status_msg+="✅ Cellular Modem: Online ($SIGNAL)
"
    else
        status_msg+="❌ Cellular Modem: Not responding
"
        failures=$((failures + 1))
    fi
    
    # Check network
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        status_msg+="✅ Internet: Connected
"
    else
        status_msg+="❌ Internet: Disconnected
"
        failures=$((failures + 1))
    fi
    
    # Check database
    if [ -f /home/USERNAME/gps-data/gps_data.db ]; then
        GPS_COUNT=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data;" 2>/dev/null)
        CELL_COUNT=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM cell_observations;" 2>/dev/null)
        status_msg+="✅ Database: $GPS_COUNT GPS, $CELL_COUNT Cell records
"
    else
        status_msg+="❌ Database: Not found
"
        failures=$((failures + 1))
    fi
    
    # Send notification based on status
    if [ "$failures" -eq 0 ]; then
        # ALL SYSTEMS GO! - Cleaner format with proper line breaks
        curl -d "🟢 ALL SYSTEMS OPERATIONAL 🟢

GPS/GSM LOGGER STATUS:
${status_msg}
Ready for mobile data collection!
Geofence active." \
        https://ntfy.sh/gps-tracker-YOUR-TOPIC
        
        echo "$(date): All systems healthy - notification sent" >> /home/USERNAME/gps-tracker/mobile_startup.log
    else
        # Some systems failed
        curl -d "⚠️ ISSUES DETECTED

GPS/GSM LOGGER STATUS:
${status_msg}
$failures component(s) need attention" \
        https://ntfy.sh/gps-tracker-YOUR-TOPIC
        
        echo "$(date): System issues detected - $failures failures" >> /home/USERNAME/gps-tracker/mobile_startup.log
    fi
    
    echo -e "$status_msg"
}

# Run the health check
check_health
