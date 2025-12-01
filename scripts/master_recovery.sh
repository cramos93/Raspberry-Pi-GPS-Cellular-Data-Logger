#!/bin/bash
LOG="/home/USERNAME/gps-tracker/master_recovery.log"
RECOVERY_NOTIFIED="/tmp/recovery_notified"

perform_recovery() {
    local recovery_needed=0
    local issues_found=""
    
    # Check all components
    DOCKER_HEALTHY=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format '{{.Status}}' 2>/dev/null | grep -c healthy)
    QMI_OK=$(qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -c dBm)
    GPS_DEVICE=$([ -e /dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0 ] && echo 1 || echo 0)
    
    # Determine what needs fixing
    if [ "$DOCKER_HEALTHY" -lt "2" ]; then
        recovery_needed=1
        issues_found+="❌ Docker Containers: $DOCKER_HEALTHY/2 healthy
"
    fi
    
    if [ "$QMI_OK" -eq "0" ]; then
        recovery_needed=1
        issues_found+="❌ Cellular Modem: Not responding
"
    fi
    
    if [ "$GPS_DEVICE" -eq "0" ]; then
        recovery_needed=1
        issues_found+="❌ GPS Device: Not found
"
    fi
    
    if [ "$recovery_needed" -eq "1" ]; then
        # Send detailed recovery notification
        if [ ! -f "$RECOVERY_NOTIFIED" ]; then
            curl -d "🔧 AUTO-RECOVERY INITIATED 🔧

ISSUES DETECTED:
${issues_found}
ACTIONS:
- Restarting Docker containers
- Resetting cellular modem
- Reconnecting GPS device

Will notify when complete." \
            https://ntfy.sh/gps-tracker-YOUR-TOPIC 2>/dev/null
            
            touch "$RECOVERY_NOTIFIED"
        fi
        
        echo "$(date): Starting recovery process" >> $LOG
        
        # Fix Docker if needed
        if [ "$DOCKER_HEALTHY" -lt "2" ]; then
            echo "$(date): Fixing Docker containers" >> $LOG
            cd /home/USERNAME/gps-tracker
            docker compose restart
            sleep 30
        fi
        
        # Fix QMI if needed
        if [ "$QMI_OK" -eq "0" ]; then
            echo "$(date): Fixing cellular modem" >> $LOG
            sudo systemctl stop ModemManager 2>/dev/null
            echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/unbind 2>/dev/null
            sleep 5
            echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/bind 2>/dev/null
            sleep 15
        fi
        
        # Verify everything is fixed
        sleep 20
        DOCKER_FIXED=$(docker compose -f /home/USERNAME/gps-tracker/docker-compose.yml ps --format '{{.Status}}' 2>/dev/null | grep -c healthy)
        QMI_FIXED=$(qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -c dBm)
        
        if [ "$DOCKER_FIXED" -eq "2" ] && [ "$QMI_FIXED" -gt "0" ]; then
            echo "$(date): Recovery successful" >> $LOG
            rm -f "$RECOVERY_NOTIFIED"
            /home/USERNAME/gps-tracker/system_health_check.sh
        fi
    fi
}

perform_recovery
