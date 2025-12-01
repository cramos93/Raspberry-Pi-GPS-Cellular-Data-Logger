#!/bin/bash
LOG="/home/USERNAME/gps-tracker/docker_heal.log"

# Check container health
HEALTHY=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format '{{.Status}}' 2>/dev/null | grep -c healthy)

if [ "$HEALTHY" -lt "2" ]; then
    echo "$(date): Docker containers unhealthy, attempting recovery" >> $LOG
    
    # Get specific container status
    GPS_STATUS=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps gps-logger --format '{{.Status}}' 2>/dev/null | head -1)
    LTE_STATUS=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps lte-monitor --format '{{.Status}}' 2>/dev/null | head -1)
    
    # Send detailed notification
    curl -d "🔧 SYSTEM RECOVERY IN PROGRESS 🔧

CONTAINER STATUS:
- GPS Logger: ${GPS_STATUS:-Down}
- LTE Monitor: ${LTE_STATUS:-Down}

RECOVERY ACTIONS:
- Stopping all containers
- Restarting services
- Verifying GPS device
- Checking cellular modem

Stand by for status update." \
    https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
    
    # Fix Docker
    cd /home/USERNAME/gps-tracker
    docker compose down
    sleep 5
    docker compose up -d
    sleep 45
    
    # Check if fixed and notify
    HEALTHY_AFTER=$(docker compose ps --format '{{.Status}}' | grep -c healthy)
    if [ "$HEALTHY_AFTER" -eq "2" ]; then
        /home/USERNAME/gps-tracker/system_health_check.sh
        echo "$(date): Docker recovery successful" >> $LOG
    else
        curl -d "⚠️ RECOVERY PARTIAL

Some components still need attention.
Manual intervention may be required." \
        https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
        echo "$(date): Docker recovery incomplete" >> $LOG
    fi
fi
