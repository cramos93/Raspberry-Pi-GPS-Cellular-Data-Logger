#!/bin/bash
# Check if GPS is actually receiving data
if ! timeout 10 cat /dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0 | grep -q '$GP'; then
    echo "$(date): GPS not responding, restarting container"
    docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml restart gps-logger
fi
