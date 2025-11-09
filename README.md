# Raspberry Pi GPS Data Logger
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

Continuous GPS logging system with motion analytics, geofence detection, and optional LTE/GSM metadata capture for Raspberry Pi 5.

## Features

- 🛰️ **Continuous GPS Tracking** - Log position, speed, heading, altitude from GlobalSat BU-353N
- 📊 **Motion Analytics** - Calculate speed and bearing using Haversine distance formulas
- 🗺️ **Geofence Detection** - Define boundaries with GeoJSON and get real-time alerts
- 🔔 **Push Notifications** - Instant alerts via ntfy.sh on geofence violations
- 📶 **LTE/GSM Metadata** (Optional) - Enrich GPS data with cellular network context
- 🐳 **Fully Containerized** - Docker Compose deployment for easy setup and portability
- 💾 **Flexible Storage** - SQLite for single-device or PostgreSQL for multi-device deployments

## Quick Start

### Prerequisites
- Raspberry Pi 5 with Raspberry Pi OS (Bookworm)
- GlobalSat BU-353N GPS Receiver (USB)
- Docker and Docker Compose installed

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/raspberry-pi-gps-logger.git
cd raspberry-pi-gps-logger

# Create configuration
cp config/config.env.example config/config.env
nano config/config.env  # Edit settings

# Build and start
docker compose build
docker compose up -d

# View logs
docker compose logs -f gps-logger
```

## Documentation

- 📖 [Architecture & Design](docs/ARCHITECTURE.md)
- 🚀 [Deployment Guide](docs/DEPLOYMENT.md)
- ⚙️ [Configuration Options](docs/CONFIGURATION.md)

## Hardware Requirements

- **Raspberry Pi 5** (8GB recommended)
- **GlobalSat BU-353N GPS Receiver** (USB, SiRF Star IV chipset)
- **Sierra Wireless EM7565/EM7511 LTE Modem** (Optional, for cellular metadata)

## Project Structure
```
├── src/                  # Python source code
├── config/               # Configuration files
├── data/                 # Database storage
├── logs/                 # Application logs
├── docs/                 # Documentation
└── docker-compose.yml    # Container orchestration
```

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built for continuous vehicle tracking, asset monitoring, and geolocation analytics.
