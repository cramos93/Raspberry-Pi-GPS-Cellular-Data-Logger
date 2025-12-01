#!/bin/bash
# Wait for boot to complete
sleep 120

# Test if modem responds
if ! timeout 5 qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength > /dev/null 2>&1; then
    echo "$(date): Modem not responding, resetting USB" >> /home/USERNAME/modem_reset.log
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
    sleep 5
    echo '2-1' | sudo tee /sys/bus/usb/drivers/usb/bind
fi
