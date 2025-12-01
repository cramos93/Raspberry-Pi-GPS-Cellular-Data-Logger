#!/bin/bash

# Check for total system failure
FAILURES=0

# Critical checks
docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps | grep -q Up || FAILURES=$((FAILURES+1))
ping -c 1 8.8.8.8 > /dev/null 2>&1 || FAILURES=$((FAILURES+1))
[ -e /dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0 ] || FAILURES=$((FAILURES+1))

if [ "$FAILURES" -ge 2 ]; then
    # Multiple critical failures - send alert
    curl -d "🔴 CRITICAL SYSTEM FAILURE 🔴
    
Multiple components failed!
Automatic recovery in progress...
Check system if this persists." \
    https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
    
    # Attempt full system recovery
    /home/USERNAME/gps-tracker/mobile_startup.sh
fi
