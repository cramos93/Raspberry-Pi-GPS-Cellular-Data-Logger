#!/bin/bash
STATE_FILE="/tmp/network_down_time"
LOG="/home/USERNAME/gps-tracker/network.log"

# Check internet
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    # Internet is UP
    if [ -f "$STATE_FILE" ]; then
        # Was down, now recovered
        echo "$(date): Network recovered" >> $LOG
        rm -f "$STATE_FILE"
        
        # Send recovery notification
        curl -d "🟢 NETWORK RECOVERED 🟢

Internet connection restored.
All systems operational." \
        https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
    fi
else
    # Internet is DOWN
    if [ ! -f "$STATE_FILE" ]; then
        # First detection
        date +%s > "$STATE_FILE"
        echo "$(date): Network down detected" >> $LOG
    else
        # Check how long it's been down
        DOWN_SINCE=$(cat "$STATE_FILE")
        CURRENT=$(date +%s)
        DURATION=$((CURRENT - DOWN_SINCE))
        
        # Only alert after 10 minutes (600 seconds)
        if [ "$DURATION" -gt 600 ] && [ "$DURATION" -lt 660 ]; then
            curl -d "⚠️ NETWORK ISSUE (10+ min)

Internet disconnected for over 10 minutes.
GPS/GSM logging continues offline." \
            https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
        fi
        
        # Try to reconnect
        if [ "$DURATION" -gt 300 ]; then
            nmcli connection up phone-hotspot 2>/dev/null
        fi
    fi
fi
