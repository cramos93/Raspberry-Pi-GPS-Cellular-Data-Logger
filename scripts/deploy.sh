#!/bin/bash
# ============================================================================
# GPS/LTE Tracker - Enhanced Deployment Script
# Stores data on /mnt/nvme for performance and longevity
# ============================================================================

set -euo pipefail

PROJECT_DIR="$HOME/gps-tracker"
NVME_PATH="/mnt/nvme"

echo "============================================================"
echo "  GPS/LTE Tracker - Enhanced Deployment"
echo "============================================================"
echo ""

# Create project structure
echo "==> Creating project directories..."
mkdir -p "$PROJECT_DIR" "$PROJECT_DIR/config"
cd "$PROJECT_DIR"

# Ensure NVMe paths exist and are owned by user
echo "==> Setting up NVMe storage..."
sudo mkdir -p "$NVME_PATH" "$NVME_PATH/logs" "$NVME_PATH/backups"
sudo chown -R "$USER":"$USER" "$NVME_PATH"

# Check Docker installation
echo "==> Checking Docker..."
if ! command -v docker >/dev/null 2>&1; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in."
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

sudo systemctl enable --now docker

# Detect USB devices (prefer by-id for stability)
echo "==> Detecting USB devices..."
GPS_BYID=$(ls -1 /dev/serial/by-id/*Prolific* 2>/dev/null | head -n1 || echo "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0")
LTE_BYID=$(ls -1 /dev/serial/by-id/*Sierra* 2>/dev/null | head -n1 || echo "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0")

echo "GPS Device: $GPS_BYID"
echo "LTE Device: $LTE_BYID"

# Set QMI device permissions
if [ -e /dev/cdc-wdm0 ]; then
    sudo chmod 666 /dev/cdc-wdm0
    echo "QMI Device: /dev/cdc-wdm0 (permissions set)"
fi

echo ""
echo "==> Creating configuration files..."

# ============================================================================
# Create docker-compose.yml
# ============================================================================
cat > docker-compose.yml <<'COMPOSE_EOF'
version: '3.9'

services:
  gps-logger:
    build:
      context: .
      dockerfile: Dockerfile.gps
    container_name: rpi-gps-logger
    restart: unless-stopped
    devices:
      - ${GPS_DEVICE}:${GPS_DEVICE}
    volumes:
      - /mnt/nvme:/app/data
      - /mnt/nvme/logs:/app/logs
      - ./config:/app/config:ro
    environment:
      TZ: ${TZ}
      GPS_DEVICE: ${GPS_DEVICE}
      GPS_BAUD_RATE: "${GPS_BAUD_RATE}"
      DATABASE_PATH: /app/data/gps_data.db
      GEOFENCE_FILE: /app/config/virginia_counties.geojson
      NOTIFICATION_URL: ${NOTIFICATION_URL}
      LOG_LEVEL: ${LOG_LEVEL}
      GEOF_DEBOUNCE_COUNT: "${GEOF_DEBOUNCE_COUNT}"
      GEOF_MIN_MOVE_M: "${GEOF_MIN_MOVE_M}"
      SPEED_SMOOTH_ALPHA: "${SPEED_SMOOTH_ALPHA}"
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; sqlite3.connect('/app/data/gps_data.db').close()"]
      interval: 60s
      timeout: 10s
      retries: 3
    networks:
      - gps-network

  lte-monitor:
    build:
      context: .
      dockerfile: Dockerfile.lte
    container_name: rpi-lte-monitor
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/cdc-wdm0:/dev/cdc-wdm0
      - ${LTE_SERIAL_DEVICE}:${LTE_SERIAL_DEVICE}
    volumes:
      - /mnt/nvme:/app/data
      - /mnt/nvme/logs:/app/logs
    environment:
      TZ: ${TZ}
      MODEM_DEVICE: /dev/cdc-wdm0
      LTE_SERIAL_DEVICE: ${LTE_SERIAL_DEVICE}
      DATABASE_PATH: /app/data/gps_data.db
      LTE_POLL_INTERVAL: "${LTE_POLL_INTERVAL}"
      LOG_LEVEL: ${LOG_LEVEL}
      USE_QMI: "${USE_QMI}"
    healthcheck:
      test: ["CMD-SHELL", "qmicli -d /dev/cdc-wdm0 --get-wwan-iface >/dev/null 2>&1 || exit 0"]
      interval: 60s
      timeout: 10s
      retries: 3
    networks:
      - gps-network

networks:
  gps-network:
    driver: bridge
COMPOSE_EOF

# ============================================================================
# Create Dockerfile.gps
# ============================================================================
cat > Dockerfile.gps <<'DOCKERFILE_GPS_EOF'
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/config /app/data /app/logs

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gps_logger.py /app/gps_logger.py

ENV PYTHONUNBUFFERED=1
ENV GPS_DEVICE=/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_DEVICE_SERIAL-if00-port0
ENV DATABASE_PATH=/app/data/gps_data.db

CMD ["python", "-u", "/app/gps_logger.py"]
DOCKERFILE_GPS_EOF

# ============================================================================
# Create Dockerfile.lte
# ============================================================================
cat > Dockerfile.lte <<'DOCKERFILE_LTE_EOF'
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqmi-utils \
    libqmi-proxy \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/data /app/logs

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY lte_monitor.py /app/lte_monitor.py

ENV PYTHONUNBUFFERED=1
ENV MODEM_DEVICE=/dev/cdc-wdm0

CMD ["python", "-u", "/app/lte_monitor.py"]
DOCKERFILE_LTE_EOF

# ============================================================================
# Create requirements.txt
# ============================================================================
cat > requirements.txt <<'REQUIREMENTS_EOF'
pyserial>=3.5
geojson>=3.0.0
shapely>=2.0.0
requests>=2.31.0
REQUIREMENTS_EOF

# ============================================================================
# Create .env file
# ============================================================================
cat > .env <<ENV_EOF
# Notification URL - Get your topic from https://ntfy.sh
NOTIFICATION_URL=https://ntfy.sh/gps-tracker-rpi-$(hostname)

# Timezone
TZ=America/New_York

# Logging
LOG_LEVEL=INFO

# GPS Settings
GPS_DEVICE=$GPS_BYID
GPS_BAUD_RATE=4800

# LTE Settings
LTE_SERIAL_DEVICE=$LTE_BYID
LTE_POLL_INTERVAL=5
USE_QMI=true

# Correlation Settings
GPS_LOOKBACK_SEC=2

# Geofence Settings
GEOF_DEBOUNCE_COUNT=3
GEOF_MIN_MOVE_M=5
SPEED_SMOOTH_ALPHA=0.3
ENV_EOF

# ============================================================================
# Create Virginia counties geofence
# ============================================================================
cat > config/virginia_counties.geojson <<'GEOJSON_EOF'
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "YOUR_CITY County",
        "state": "Virginia",
        "county": "YOUR_CITY"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-78.051, 38.635], [-77.933, 38.635], [-77.815, 38.557],
          [-77.767, 38.468], [-77.715, 38.382], [-77.701, 38.289],
          [-77.782, 38.238], [-77.896, 38.215], [-78.024, 38.228],
          [-78.142, 38.289], [-78.189, 38.382], [-78.176, 38.468],
          [-78.118, 38.557], [-78.051, 38.635]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Fauquier County",
        "state": "Virginia",
        "county": "Fauquier"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-77.967, 38.945], [-77.715, 38.945], [-77.573, 38.857],
          [-77.526, 38.738], [-77.534, 38.635], [-77.598, 38.557],
          [-77.701, 38.468], [-77.815, 38.382], [-77.933, 38.289],
          [-78.071, 38.238], [-78.209, 38.263], [-78.327, 38.328],
          [-78.394, 38.419], [-78.401, 38.519], [-78.354, 38.612],
          [-78.261, 38.686], [-78.142, 38.751], [-78.024, 38.816],
          [-77.967, 38.945]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Prince William County",
        "state": "Virginia",
        "county": "Prince William"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-77.734, 38.945], [-77.465, 38.945], [-77.286, 38.857],
          [-77.186, 38.738], [-77.146, 38.612], [-77.166, 38.493],
          [-77.233, 38.393], [-77.340, 38.315], [-77.467, 38.276],
          [-77.594, 38.289], [-77.701, 38.328], [-77.781, 38.393],
          [-77.828, 38.486], [-77.855, 38.593], [-77.842, 38.699],
          [-77.795, 38.790], [-77.734, 38.945]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "YOUR_CITY County",
        "state": "Virginia",
        "county": "YOUR_CITY"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-77.573, 39.045], [-77.217, 39.032], [-77.047, 38.945],
          [-76.910, 38.818], [-76.843, 38.686], [-76.843, 38.541],
          [-76.896, 38.419], [-76.990, 38.315], [-77.120, 38.250],
          [-77.267, 38.224], [-77.414, 38.237], [-77.541, 38.289],
          [-77.648, 38.367], [-77.735, 38.467], [-77.795, 38.580],
          [-77.828, 38.699], [-77.822, 38.818], [-77.775, 38.932],
          [-77.681, 39.019], [-77.573, 39.045]
        ]]
      }
    }
  ]
}
GEOJSON_EOF

# ============================================================================
# Create backup script
# ============================================================================
cat > backup.sh <<'BACKUP_EOF'
#!/bin/bash
BACKUP_DIR="/mnt/nvme/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
if [ -f /mnt/nvme/gps_data.db ]; then
    sqlite3 /mnt/nvme/gps_data.db ".backup '$BACKUP_DIR/gps_data_$TIMESTAMP.db'"
    echo "Database backed up to: $BACKUP_DIR/gps_data_$TIMESTAMP.db"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "gps_data_*.db" -mtime +7 -delete
    echo "Old backups cleaned up (keeping 7 days)"
else
    echo "No database found to backup"
fi

# Show disk usage
echo ""
echo "Disk usage:"
du -sh /mnt/nvme/gps_data.db 2>/dev/null || echo "Database not yet created"
df -h /mnt/nvme
BACKUP_EOF

chmod +x backup.sh

# ============================================================================
# Create systemd service for auto-start
# ============================================================================
echo "==> Creating systemd service..."
sudo tee /etc/systemd/system/gps-tracker.service >/dev/null <<SERVICE_EOF
[Unit]
Description=GPS/LTE Tracker Docker Compose
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$USER
Environment="PATH=/usr/bin:/usr/local/bin"

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable gps-tracker.service

# ============================================================================
# Validate Python scripts exist
# ============================================================================
echo ""
echo "==> Validating Python scripts..."
MISSING_FILES=0

if [ ! -f "gps_logger.py" ]; then
    echo "❌ ERROR: gps_logger.py not found in $PROJECT_DIR"
    MISSING_FILES=1
fi

if [ ! -f "lte_monitor.py" ]; then
    echo "❌ ERROR: lte_monitor.py not found in $PROJECT_DIR"
    MISSING_FILES=1
fi

if [ $MISSING_FILES -eq 1 ]; then
    echo ""
    echo "============================================================"
    echo "  ⚠️  DEPLOYMENT INCOMPLETE"
    echo "============================================================"
    echo ""
    echo "Please copy the Python scripts to $PROJECT_DIR:"
    echo "  - gps_logger.py"
    echo "  - lte_monitor.py"
    echo ""
    echo "Then run: cd $PROJECT_DIR && ./deploy.sh"
    echo ""
    exit 1
fi

# ============================================================================
# Build and deploy
# ============================================================================
echo ""
echo "==> Building Docker containers..."
docker compose build

echo ""
echo "==> Starting services..."
docker compose up -d

# Wait a moment for services to start
sleep 3

echo ""
echo "============================================================"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "Service Status:"
docker compose ps
echo ""
echo "Storage Location: /mnt/nvme"
echo "  Database: /mnt/nvme/gps_data.db"
echo "  Logs:     /mnt/nvme/logs/"
echo ""
echo "Useful Commands:"
echo "  View all logs:     docker compose logs -f"
echo "  View GPS logs:     docker compose logs -f gps-logger"
echo "  View LTE logs:     docker compose logs -f lte-monitor"
echo "  Restart:           docker compose restart"
echo "  Stop:              docker compose down"
echo "  Backup database:   ./backup.sh"
echo "  Check data:        sqlite3 /mnt/nvme/gps_data.db 'SELECT COUNT(*) FROM gps_data'"
echo ""
echo "Auto-start on boot: ENABLED (systemd service installed)"
echo ""
echo "Checking for GPS fix (waiting 10 seconds)..."
sleep 10
echo ""
docker compose logs --tail=30 gps-logger

echo ""
echo "Edit .env to customize notification URL and other settings"
echo "Geofence: config/virginia_counties.geojson (4 counties loaded)"
