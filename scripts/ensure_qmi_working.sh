#!/bin/bash
LOG="/home/USERNAME/gps-tracker/qmi_startup.log"

echo "$(date): Ensuring QMI operational" >> $LOG

# Always stop ModemManager (it interferes with QMI)
sudo systemctl stop ModemManager 2>/dev/null
sudo systemctl disable ModemManager 2>/dev/null

# Wait for modem to stabilize
sleep 15

# Test QMI
if sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -q dBm; then
    echo "$(date): QMI working properly" >> $LOG
else
    echo "$(date): QMI not responding, resetting modem" >> $LOG
    # USB reset
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
    sleep 5
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/bind
    sleep 15
    
    # Test again
    if sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength 2>/dev/null | grep -q dBm; then
        echo "$(date): QMI working after reset" >> $LOG
    else
        echo "$(date): QMI still not working" >> $LOG
    fi
fi
