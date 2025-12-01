#!/bin/bash
# Check if Tailscale is connected
if ! tailscale status | grep -q "100.0.0.1"; then
    echo "$(date): Tailscale disconnected, attempting reconnect"
    sudo tailscale down
    sudo tailscale up --accept-routes --accept-dns=false
fi

# Check if we have internet (via LTE or WiFi)
if ! ping -c 1 -W 5 8.8.8.8 > /dev/null 2>&1; then
    echo "$(date): No internet, restarting networking"
    sudo systemctl restart NetworkManager
fi
