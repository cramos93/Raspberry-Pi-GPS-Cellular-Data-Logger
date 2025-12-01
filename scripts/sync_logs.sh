#!/bin/bash
# Sync RAM logs to SD periodically
rsync -a /var/log/gps-tracker/ /home/USERNAME/gps-data/logs/ 2>/dev/null
