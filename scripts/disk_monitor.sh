#!/bin/bash
USAGE=$(df -h / | awk 'NR==2 {print substr($5,1,length($5)-1)}')
if [ $USAGE -gt 85 ]; then
    curl -d "⚠️ DISK SPACE WARNING: ${USAGE}% used!" https://ntfy.sh/gps-tracker-YOUR-TOPIC
fi
