# GPS/LTE Tracker - Enhanced Deployment Package

Complete Docker-based GPS and cellular network tracker for Raspberry Pi 5 with NVMe storage.

## Features

### GPS Tracking
- ✅ Comprehensive NMEA sentence parsing (GPGGA, GPRMC, GPGSA, GPGSV, GPVTG, GPGLL)
- ✅ Full satellite metadata (count, HDOP, VDOP, PDOP, fix quality)
- ✅ Motion analytics (speed, heading, climb rate, distance traveled)
- ✅ Exponential speed smoothing to reduce noise
- ✅ Minimum movement threshold to filter GPS drift

### Geofencing
- ✅ Multi-county geofence support (YOUR_CITY, Fauquier, Prince William, YOUR_CITY)
- ✅ Entry/exit detection with debouncing (prevents false triggers)
- ✅ Push notifications via ntfy.sh
- ✅ Independent tracking for each geofence region

### LTE/GSM Monitoring
- ✅ Cell tower information (Cell ID, PCI, TAC, LAC)
- ✅ Network identity (MCC, MNC, operator)
- ✅ Signal strength (RSSI, RSRP, RSRQ, SINR, RSSNR)
- ✅ Technology detection (LTE/UMTS/GSM)
- ✅ Band and frequency (EARFCN, bandwidth)
- ✅ Neighbor cell scanning
- ✅ Cell transition/handover logging
- ✅ Dual interface support (AT commands + QMI)

### Storage & Performance
- ✅ NVMe storage for performance and SD card longevity
- ✅ SQLite database with comprehensive indexing
- ✅ Automatic backup script
- ✅ Systemd service for auto-start on boot

## Quick Start

### Prerequisites
- Raspberry Pi 5 with Raspberry Pi OS (Bookworm)
- NVMe drive mounted at `/mnt/nvme`
- GlobalSat BU-353N GPS receiver (USB)
- Sierra Wireless EM7565/EM7511 LTE modem (optional)

### Installation

**Option 1: From Windows (PowerShell)**
```powershell
# Copy files to Raspberry Pi
scp deploy.sh pi@raspberrypi:/home/pi/gps-tracker/
scp gps_logger.py pi@raspberrypi:/home/pi/gps-tracker/
scp lte_monitor.py pi@raspberrypi:/home/pi/gps-tracker/

# SSH to Pi
ssh pi@raspberrypi
cd ~/gps-tracker
chmod +x deploy.sh
./deploy.sh
```

**Option 2: Direct on Raspberry Pi**
```bash
# Create directory and copy files
mkdir -p ~/gps-tracker
cd ~/gps-tracker

# Copy deploy.sh, gps_logger.py, lte_monitor.py here
# Then run:
chmod +x deploy.sh
./deploy.sh
```

## Configuration

### Environment Variables (.env)

The deployment script creates a `.env` file. Edit it to customize:

```bash
# Notification URL - Get topic from https://ntfy.sh
NOTIFICATION_URL=https://ntfy.sh/your-unique-topic

# Timezone
TZ=America/New_York

# GPS Settings
GPS_DEVICE=/dev/serial/by-id/usb-Prolific_...  # Auto-detected
GPS_BAUD_RATE=4800

# LTE Settings
LTE_SERIAL_DEVICE=/dev/serial/by-id/usb-Sierra_...  # Auto-detected
LTE_POLL_INTERVAL=5
USE_QMI=true

# Geofence Settings
GEOF_DEBOUNCE_COUNT=3      # Readings before triggering event
GEOF_MIN_MOVE_M=5          # Minimum movement in meters
SPEED_SMOOTH_ALPHA=0.3     # Speed smoothing factor (0-1)

# Logging
LOG_LEVEL=INFO
```

### Geofence Configuration

Edit `config/virginia_counties.geojson` to modify geofence boundaries. The default includes:
- YOUR_CITY County
- Fauquier County
- Prince William County
- YOUR_CITY County

### Notification Setup

1. Visit https://ntfy.sh
2. Choose a unique topic name (e.g., `gps-tracker-your-name-123`)
3. Update `NOTIFICATION_URL` in `.env`
4. Subscribe to your topic:
   - **Web**: Visit `https://ntfy.sh/your-topic`
   - **Mobile**: Download ntfy app, add subscription
   - **API**: `curl -d "test" ntfy.sh/your-topic`

## Usage

### Service Management

```bash
# View status
docker compose ps

# View all logs
docker compose logs -f

# View GPS logs only
docker compose logs -f gps-logger

# View LTE logs only
docker compose logs -f lte-monitor

# Restart services
docker compose restart

# Stop services
docker compose down

# Rebuild after changes
docker compose build
docker compose up -d
```

### Database Queries

```bash
# Enter database
sqlite3 /mnt/nvme/gps_data.db

# Count GPS records
SELECT COUNT(*) FROM gps_data;

# Recent GPS data
SELECT datetime(timestamp), latitude, longitude, speed, satellites_used 
FROM gps_data 
ORDER BY timestamp DESC 
LIMIT 10;

# Geofence events
SELECT datetime(timestamp), event_type, latitude, longitude 
FROM geofence_events 
ORDER BY timestamp DESC;

# Cell transitions
SELECT datetime(timestamp), from_cell_id, to_cell_id, to_technology, to_rsrp 
FROM cell_transitions 
ORDER BY timestamp DESC 
LIMIT 10;

# Average signal strength by cell
SELECT cell_id, AVG(rsrp) as avg_rsrp, COUNT(*) as readings 
FROM cellular_data 
GROUP BY cell_id 
ORDER BY avg_rsrp DESC;
```

### Backup & Maintenance

```bash
# Backup database
./backup.sh

# Check disk usage
df -h /mnt/nvme
du -sh /mnt/nvme/gps_data.db

# View backup history
ls -lh /mnt/nvme/backups/

# Restore from backup
cp /mnt/nvme/backups/gps_data_20250109_120000.db /mnt/nvme/gps_data.db
docker compose restart
```

### Auto-Start Service

The deployment automatically creates a systemd service:

```bash
# Check service status
sudo systemctl status gps-tracker

# Stop auto-start
sudo systemctl disable gps-tracker

# Enable auto-start
sudo systemctl enable gps-tracker

# Start immediately
sudo systemctl start gps-tracker

# View service logs
sudo journalctl -u gps-tracker -f
```

## Troubleshooting

### GPS Not Getting Fix

```bash
# Check device connection
ls -l /dev/ttyUSB* /dev/ttyACM*

# Test GPS directly (requires gpsd)
sudo gpsd /dev/ttyUSB0
cgps -s

# Check logs
docker compose logs --tail=100 gps-logger | grep -i satellite

# Ensure outdoor location with clear sky view
```

### LTE Modem Not Detected

```bash
# Check modem devices
ls -l /dev/cdc-wdm*
lsusb | grep Sierra

# Test QMI interface
qmicli -d /dev/cdc-wdm0 --nas-get-serving-system

# Check modem status
mmcli -L
mmcli -m 0

# Set permissions
sudo chmod 666 /dev/cdc-wdm0
```

### Container Won't Start

```bash
# Check detailed logs
docker compose logs gps-logger
docker compose logs lte-monitor

# Validate device paths in .env
cat .env | grep DEVICE

# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Database Issues

```bash
# Check database integrity
sqlite3 /mnt/nvme/gps_data.db "PRAGMA integrity_check;"

# Check database size
du -h /mnt/nvme/gps_data.db

# Vacuum database (reduce size)
sqlite3 /mnt/nvme/gps_data.db "VACUUM;"
```

## File Structure

```
~/gps-tracker/
├── deploy.sh                           # Deployment script
├── docker-compose.yml                  # Service orchestration
├── Dockerfile.gps                      # GPS logger container
├── Dockerfile.lte                      # LTE monitor container
├── requirements.txt                    # Python dependencies
├── .env                                # Configuration (edit this!)
├── gps_logger.py                       # GPS application
├── lte_monitor.py                      # LTE application
├── backup.sh                           # Database backup script
├── config/
│   └── virginia_counties.geojson       # Geofence boundaries
└── /mnt/nvme/
    ├── gps_data.db                     # SQLite database
    ├── logs/                           # Application logs
    └── backups/                        # Database backups
```

## Performance Tuning

### Geofence Debouncing
Increase if you get false triggers at boundaries:
```bash
GEOF_DEBOUNCE_COUNT=5  # Requires 5 consecutive readings
```

### Movement Filtering
Increase to ignore more GPS noise while stationary:
```bash
GEOF_MIN_MOVE_M=10  # Ignore movements under 10 meters
```

### Speed Smoothing
- Lower = more responsive (0.1-0.4)
- Higher = smoother, less noise (0.5-0.9)
```bash
SPEED_SMOOTH_ALPHA=0.5  # Balance between noise and responsiveness
```

### LTE Polling
Reduce to save power or increase for more frequent updates:
```bash
LTE_POLL_INTERVAL=10  # Check every 10 seconds
```

## Database Schema

### GPS Data
- Position (lat/lon/alt)
- Motion (speed, heading, climb rate)
- Satellites (count, HDOP, VDOP, PDOP)
- Fix information (quality, type, mode)
- Distance tracking

### Cellular Data
- Cell info (Cell ID, PCI, TAC, LAC)
- Network (MCC, MNC, operator)
- Signal (RSSI, RSRP, RSRQ, SINR)
- Technology (LTE/UMTS/GSM, band)
- Frequency (EARFCN, bandwidth)

### Geofence Events
- Entry/exit timestamps
- Location at crossing
- Speed and heading

### Neighbor Cells
- Nearby cell towers
- Signal strength comparison

### Cell Transitions
- Handover tracking
- Signal strength changes

## Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Verify device connections: `ls -l /dev/`
3. Check database: `sqlite3 /mnt/nvme/gps_data.db`
4. Review configuration: `cat .env`


## Resources

- GPS Parsing: NMEA 0183 standard
- Geofencing: Shapely library
- LTE Interface: QMI protocol
- Notifications: ntfy.sh

