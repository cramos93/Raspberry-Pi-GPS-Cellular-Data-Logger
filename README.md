# Raspberry Pi GPS Data Logger
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

Continuous GPS logging system with motion analytics, geofence detection, and optional LTE/GSM metadata capture for Raspberry Pi 5.

## **1. Objectives**

### **Primary Objectives**
- Implement a GPS receiver system on a **Raspberry Pi 5** to record continuous location updates into a centralized database.  
- Calculate and log movement parameters such as **speed** and **heading** over time.  
- Define and enforce a **geofence** using a GeoJSON boundary file.  
- Trigger a **real-time notification** when the geofence is crossed.

### **Secondary Objective**
- **LTE/GSM Logging:** Integrate a cellular metadata capture module to enrich GPS records with LTE/GSM network context (Cell ID, signal strength, band, and registration state) using a **Sierra Wireless EM7565/EM7511** modem.  
  This allows correlation of spatial and signal data for contextualized geolocation analytics.

All modules are containerized for reproducible deployment and long-term unattended operation.

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

## Acknowledgments

Built for continuous vehicle tracking, asset monitoring, and geolocation analytics.
