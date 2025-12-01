#!/bin/bash
LOG="/home/USERNAME/gps-tracker/recovery.log"

# Function to fix specific issues
fix_docker() {
    echo "$(date): Restarting Docker containers" >> $LOG
    cd /home/USERNAME/gps-tracker
    docker compose down
    sleep 5
    docker compose up -d
    sleep 30
}

fix_network() {
    echo "$(date): Fixing network connection" >> $LOG
    # Try to reconnect to hotspot
    nmcli connection up phone-hotspot 2>/dev/null || \
    nmcli connection up uuid ccee2ceb-1cb9-44f2-95f1-c7eeff8f8809 2>/dev/null
    sleep 10
}

fix_qmi() {
    echo "$(date): Resetting cellular modem" >> $LOG
    # Stop ModemManager if running
    sudo systemctl stop ModemManager 2>/dev/null
    # USB reset modem
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/unbind 2>/dev/null
    sleep 5
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/bind 2>/dev/null
    sleep 15
}

fix_gps() {
    echo "$(date): Restarting GPS container" >> $LOG
    cd /home/USERNAME/gps-tracker
    docker compose restart gps-logger
    sleep 20
}

# Main recovery logic
perform_recovery() {
    # Check each component and fix if needed
    
    # 1. Check Docker containers
    CONTAINERS=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format '{{.Status}}' 2>/dev/null | grep -c healthy)
    if [ "$CONTAINERS" -lt "2" ]; then
        echo "$(date): Docker issue detected, attempting fix" >> $LOG
        fix_docker
    fi
    
    # 2. Check network
    if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        echo "$(date): Network issue detected, attempting fix" >> $LOG
        fix_network
    fi
    
    # 3. Check cellular modem
    if ! qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -q dBm; then
        echo "$(date): Cellular modem issue detected, attempting fix" >> $LOG
        fix_qmi
    fi
    
    # 4. Check if GPS is collecting data (should have new records in last 5 min)
    RECENT_GPS=$(sqlite3 /home/USERNAME/gps-data/gps_data.db \
        "SELECT COUNT(*) FROM gps_data WHERE timestamp > strftime('%s', 'now', '-5 minutes');" 2>/dev/null || echo "0")
    if [ "$RECENT_GPS" -eq "0" ]; then
        echo "$(date): GPS not collecting, attempting fix" >> $LOG
        fix_gps
    fi
    
    # Wait and check if fixes worked
    sleep 30
    
    # Run health check and notify status
    /home/USERNAME/gps-tracker/system_health_check.sh
}

# Run recovery
perform_recovery
