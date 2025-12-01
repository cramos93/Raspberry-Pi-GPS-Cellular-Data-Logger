#!/bin/bash
# Comprehensive Notification System for GPS Tracker

NOTIFICATION_URL="https://ntfy.sh/gps-tracker-YOUR-TOPIC"
DB="/home/USERNAME/gps-data/gps_data.db"
LOG="/home/USERNAME/gps-data/logs/notifications.log"

# Function to check system status
check_system_status() {
    local status="OPERATIONAL"
    local issues=""
    
    # Check containers
    GPS_CONTAINER=$(docker ps | grep -c gps-logger)
    LTE_CONTAINER=$(docker ps | grep -c lte-monitor)
    
    # Check GPS collection (allowing for gaps)
    RECENT_GPS=$(sqlite3 $DB "SELECT COUNT(*) FROM gps_data WHERE timestamp > datetime('now','-10 minutes');" 2>/dev/null || echo 0)
    
    # Check network
    NETWORK_OK=$(ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo 1 || echo 0)
    
    # Build status report
    if [ "$GPS_CONTAINER" -eq 1 ] && [ "$LTE_CONTAINER" -eq 1 ] && [ "$RECENT_GPS" -gt 0 ]; then
        echo "OPERATIONAL"
    else
        [ "$GPS_CONTAINER" -eq 0 ] && issues="GPS-Container "
        [ "$LTE_CONTAINER" -eq 0 ] && issues="${issues}LTE-Container "
        [ "$RECENT_GPS" -eq 0 ] && issues="${issues}GPS-Collection "
        [ "$NETWORK_OK" -eq 0 ] && issues="${issues}Network "
        echo "ISSUES: $issues"
    fi
}

# Function to send operational status
send_operational_status() {
    local gps_status="❌"
    local lte_status="❌"
    local collection_status="❌"
    local network_status="❌"
    
    docker ps | grep -q gps-logger && gps_status="✅"
    docker ps | grep -q lte-monitor && lte_status="✅"
    [ "$(sqlite3 $DB "SELECT COUNT(*) FROM gps_data WHERE timestamp > datetime('now','-10 minutes');" 2>/dev/null)" -gt 0 ] && collection_status="✅"
    ping -c 1 8.8.8.8 >/dev/null 2>&1 && network_status="✅"
    
    local total_records=$(sqlite3 $DB "SELECT COUNT(*) FROM gps_data;" 2>/dev/null)
    local latest_pos=$(sqlite3 $DB "SELECT latitude || ',' || longitude FROM gps_data ORDER BY id DESC LIMIT 1;" 2>/dev/null)
    
    curl -s -d "✅ SYSTEM FULLY OPERATIONAL ✅

SERVICE STATUS:
${gps_status} GPS Container
${lte_status} LTE Monitor  
${collection_status} Data Collection
${network_status} Network

STATISTICS:
📊 Total Records: ${total_records}
📍 Latest Position: ${latest_pos}
⏰ Status Time: $(date '+%Y-%m-%d %H:%M:%S')" \
    "$NOTIFICATION_URL" > /dev/null
    
    echo "$(date): Operational status sent" >> $LOG
}

# Function to send issue alert
send_issue_alert() {
    local issues="$1"
    
    curl -s -d "⚠️ SYSTEM ISSUE DETECTED ⚠️

AFFECTED COMPONENTS:
${issues}

ACTION: Self-healing will attempt recovery
TIME: $(date '+%Y-%m-%d %H:%M:%S')" \
    "$NOTIFICATION_URL" > /dev/null
    
    echo "$(date): Issue alert sent - $issues" >> $LOG
}

# Function to send self-healing notification
send_healing_notification() {
    local component="$1"
    
    curl -s -d "🔧 SELF-HEALING IN PROGRESS 🔧

COMPONENT: ${component}
ACTION: Restarting service
TIME: $(date '+%Y-%m-%d %H:%M:%S')" \
    "$NOTIFICATION_URL" > /dev/null
    
    echo "$(date): Self-healing notification sent - $component" >> $LOG
}

# Main execution based on parameter
case "$1" in
    "boot")
        sleep 60  # Wait for system to stabilize
        send_operational_status
        ;;
    "status")
        STATUS=$(check_system_status)
        if [[ "$STATUS" == "OPERATIONAL" ]]; then
            send_operational_status
        else
            send_issue_alert "${STATUS#ISSUES: }"
        fi
        ;;
    "healing")
        send_healing_notification "$2"
        ;;
    "recovered")
        send_operational_status
        ;;
    *)
        # Default monitoring mode
        STATUS=$(check_system_status)
        if [[ "$STATUS" != "OPERATIONAL" ]]; then
            send_issue_alert "${STATUS#ISSUES: }"
            # Attempt self-healing
            send_healing_notification "GPS Logger"
            cd /home/USERNAME/gps-tracker && docker compose restart gps-logger
            sleep 30
            NEW_STATUS=$(check_system_status)
            if [[ "$NEW_STATUS" == "OPERATIONAL" ]]; then
                send_operational_status
            fi
        fi
        ;;
esac
