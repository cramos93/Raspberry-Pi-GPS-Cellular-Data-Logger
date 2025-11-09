# Raspberry Pi GPS Data Logger

![License](https://img.shields.io/badge/license-MIT-blue.svg)
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
