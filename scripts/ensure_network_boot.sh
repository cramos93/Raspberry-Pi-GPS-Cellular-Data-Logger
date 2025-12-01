#!/bin/bash
LOG="/home/USERNAME/gps-tracker/network_boot.log"
MAX_ATTEMPTS=20
ATTEMPT=0

echo "$(date): Network boot script started" >> $LOG

# Wait for WiFi to be available
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Check if already connected
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        echo "$(date): Network connected on attempt $ATTEMPT" >> $LOG
        exit 0
    fi
    
    # Scan for hotspot
    if nmcli device wifi list | grep -q "YOUR_HOTSPOT"; then
        echo "$(date): Hotspot detected, connecting..." >> $LOG
        nmcli connection up "YOUR_HOTSPOT" 2>/dev/null && break
    else
        echo "$(date): Hotspot not visible yet (attempt $ATTEMPT)" >> $LOG
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    sleep 15
done

# Final check
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "$(date): Successfully connected" >> $LOG
else
    echo "$(date): Failed to connect after $MAX_ATTEMPTS attempts" >> $LOG
fi
