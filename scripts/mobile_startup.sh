#!/bin/bash
LOG="/home/USERNAME/gps-tracker/mobile_startup.log"
echo "===========================================" >> $LOG
echo "$(date): Mobile startup initiated" >> $LOG

check_gps_container() {
    if ! docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps | grep -q "healthy"; then
        echo "$(date): Starting GPS containers" >> $LOG
        cd /home/USERNAME/gps-tracker && docker compose up -d
        sleep 30
    fi
}

check_cellular_collection() {
    # Clear any stale locks
    rm -f /tmp/collect_cellular.lock 2>/dev/null
    
    # Kill any stuck processes
    pkill -f collect_cellular_v2.sh 2>/dev/null
    sleep 2
    
    # Start fresh
    /home/USERNAME/gps-tracker/collect_cellular_v2.sh &
    echo "$(date): Cellular collection started" >> $LOG
}

check_network() {
    if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        echo "$(date): Connecting to phone hotspot" >> $LOG
        nmcli connection up phone-hotspot 2>/dev/null
    fi
}

verify_data_collection() {
    INITIAL_COUNT=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data;" 2>/dev/null || echo "0")
    sleep 10
    FINAL_COUNT=$(sqlite3 /home/USERNAME/gps-data/gps_data.db "SELECT COUNT(*) FROM gps_data;" 2>/dev/null || echo "0")
    
    if [ "$FINAL_COUNT" -gt "$INITIAL_COUNT" ]; then
        echo "$(date): ✓ GPS data collection verified" >> $LOG
    else
        echo "$(date): ⚠ WARNING: No new GPS data!" >> $LOG
    fi
}

# Main execution
sleep 60
# Ensure QMI is working first
/home/USERNAME/gps-tracker/ensure_qmi_working.sh

check_gps_container
check_cellular_collection
check_network
verify_data_collection

echo "$(date): Mobile startup complete" >> $LOG
echo "$(date): Containers: $(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format 'table {{.Status}}' | grep -c Up)" >> $LOG

# Send health status notification
/home/USERNAME/gps-tracker/system_health_check.sh

