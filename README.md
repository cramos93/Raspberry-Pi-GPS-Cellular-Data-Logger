# Raspberry Pi GPS Data Logger
### Continuous GPS Logging, Motion Analytics, and Geofence Event Detection — with Optional LTE/GSM Contextual Metadata

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/-RaspberryPi-C51A4A?logo=Raspberry-Pi)
![Docker](https://img.shields.io/badge/docker-27.x-2496ED?logo=docker)

---

## Objectives

### Primary Objectives
- Implement a GPS receiver system on a **Raspberry Pi 5** to record continuous location updates into a centralized database
- Calculate and log movement parameters such as **speed** and **heading** over time
- Define and enforce a **geofence** using a GeoJSON boundary file
- Trigger a **real-time notification** when the geofence is crossed

### Secondary Objective
- **LTE/GSM Logging:** Integrate a cellular metadata capture module to enrich GPS records with LTE/GSM network context (Cell ID, signal strength, band, and registration state) using a **Sierra Wireless EM7565/EM7511** modem

This allows correlation of spatial and signal data for contextualized geolocation analytics.

**All modules are containerized for reproducible deployment and long-term unattended operation.**

---

## Project Design Overview

### Core Functionality
- Continuously log **GPS NMEA sentences** from a USB GPS receiver connected via USB
- Parse and store **latitude, longitude, timestamp, altitude, speed, and heading** in a structured database
- Compute movement metrics using delta position and Haversine-based distance calculations
- Execute automatically on boot using a **systemd service** or **Docker container**

### Geofence and Notification Logic
- Load a **GeoJSON** file defining the geofence polygon or radius boundary
- Continuously validate current position against the geofence area
- Log **entry and exit events** with timestamps in the database
- Trigger a **real-time notification** (e.g., via ntfy.sh) upon boundary violation

### Optional: LTE/GSM Metadata Capture
- Interface with a **Sierra Wireless EM7565/EM7511 LTE modem** through AT or QMI commands
- Record contextual **cellular metrics**, including:
  - Cell ID
  - MCC/MNC (Mobile Country & Network Code)
  - RSRP (Signal Strength in dBm)
  - LTE Band / Radio Access Type
- Associate LTE metadata with each GPS timestamp for environmental context and future signal-coverage mapping

---

## System Architecture

```mermaid
graph TB
    %% ---------- Hardware ----------
    GPS["📡 GPS Receiver<br/>USB NMEA Device<br/><i>Hardware</i>"]
    LTE["📶 LTE Modem EM7565/EM7511<br/><i>Hardware · Optional</i>"]
    GPS -->|USB/NMEA| PI{{"💻 RASPBERRY PI 5<br/>Central Processing Unit<br/><i>Software Runtime</i>"}}
    LTE -.->|USB/AT or QMI| PI
    %% ---------- Software Ingest ----------
    PI ==>|Primary Path| PARSE["⚙️ GPS Parser &<br/>Movement Calculator"]
    PI -.->|"Optional Path"| META["📡 LTE/GSM Metadata<br/>Parser & Collector"]
    %% ---------- Core Processing (hexagonal symbol, unique) ----------
    PARSE ==> CORE{{"🎯 CORE PROCESSING ENGINE<br/>━━━━━━━━━━━━━━<br/>📍 Location Tracking<br/>⚡ Speed Calculation<br/>🧭 Heading Analysis<br/>📶 Cellular Logging (LTE/GSM)<br/>📊 Parameter Logging<br/>━━━━━━━━━━━━━━"}}
    META -.->|"Cell Metrics Processing"| CORE
    %% ---------- Database & Outputs ----------
    CORE ==>|Primary Data Flow| DB[("💾 Time-Series Database<br/>SQLite / PostgreSQL")]
    DB -->|"Export"| FILES["📁 File Outputs<br/>CSV / GeoJSON<br/>Merged GPS + Cellular Data"]
    %% ---------- Geofence & Notification (optional feature branch) ----------
    DB -.->|"Feature Branch"| FENCE["🗺️ Geofence Validator<br/>GeoJSON · Optional"]
    FENCE -.->|"On Violation"| NOTIFY["🔔 Push Notification<br/>ntfy.sh · Optional"]
    %% ---------- Styles ----------
    %% Hardware = Grey; Export = Light Blue
    classDef hardware fill:#e0e0e0,stroke:#424242,stroke-width:2px,color:#000
    classDef hardwareOpt fill:#eeeeee,stroke:#616161,stroke-width:2px,stroke-dasharray:5 5,color:#555
    classDef central fill:#4caf50,stroke:#1b5e20,stroke-width:4px,color:#000
    classDef core fill:#ffe082,stroke:#f9a825,stroke-width:3px,color:#000
    classDef software fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef softwareOpt fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray:5 5,color:#666
    classDef database fill:#ffb74d,stroke:#e64a19,stroke-width:2px,color:#000
    classDef export fill:#bbdefb,stroke:#1565c0,stroke-width:2px,color:#000
    classDef optional fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,stroke-dasharray:5 5,color:#666
    %% ---------- Assign Classes ----------
    class GPS hardware
    class LTE hardwareOpt
    class PI central
    class PARSE software
    class META softwareOpt
    class CORE core
    class DB database
    class FILES export
    class FENCE,NOTIFY optional
```

### Architecture Summary

The system follows a **seven-layer architecture** designed for reliability and autonomous operation:

**Layer 1 - Hardware:** GPS receiver and optional LTE modem connect via USB to the Raspberry Pi 5, providing raw NMEA sentences and cellular metrics.

**Layer 2 - Operating System:** Ubuntu 24.04 LTS manages device interfaces and provides systemd service orchestration for automatic startup and recovery.

**Layer 3 - Container Infrastructure:** Docker Compose isolates three services (GPS logger, LTE monitor, API server) with independent health checks and restart policies.

**Layer 4 - Application Services:** Python 3.12 applications parse NMEA data, calculate motion parameters, validate geofence boundaries, and collect cellular metadata.

**Layer 5 - Data Persistence:** SQLite with Write-Ahead Logging (WAL) provides crash-resistant storage, surviving hard power loss without corruption.

**Layer 6 - Monitoring & Recovery:** Self-healing mechanisms detect failures and restart containers within 30 seconds, with automated backups and integrity checks.

**Layer 7 - Network & Communication:** REST API provides programmatic access, web dashboard enables visualization, and ntfy.sh sends real-time geofence alerts.

---

## System Features & Data Flow

```mermaid
graph TB
    subgraph INPUTS["📡 DATA INGESTION"]
        direction TB
        GPS_IN["<b>GPS Receiver</b><br/>━━━━━━━━━━━━━━━<br/>📍 NMEA 0183 Protocol<br/>🔄 1 Hz Update Rate<br/>📊 Position & Timestamp<br/>🛰️ Satellite Count & HDOP<br/>━━━━━━━━━━━━━━━<br/><i>src/gps/gps_logger.py</i>"]
        
        LTE_IN["<b>LTE/GSM Monitor</b><br/>━━━━━━━━━━━━━━━<br/>📶 QMI Protocol<br/>📡 Cell ID & MCC/MNC<br/>📊 RSRP, RSRQ, SNR<br/>📻 LTE Band Detection<br/>━━━━━━━━━━━━━━━<br/><i>src/cellular/lte_monitor.py</i><br/><b>Optional</b>"]
    end
    
    subgraph PROCESSING["⚙️ REAL-TIME ANALYTICS"]
        direction TB
        PARSE_P["<b>NMEA Parser</b><br/>━━━━━━━━━━━━━━━<br/>🔍 Sentence Validation<br/>📐 Coordinate Extraction<br/>🧮 Data Type Conversion<br/>━━━━━━━━━━━━━━━<br/><i>src/gps/nmea_parser.py</i>"]
        
        MOTION_P["<b>Motion Analytics</b><br/>━━━━━━━━━━━━━━━<br/>⚡ Speed Calculation<br/>🧭 Heading/Bearing<br/>📏 Haversine Distance<br/>🎯 Movement Detection<br/>━━━━━━━━━━━━━━━<br/><i>src/gps/movement_calc.py</i>"]
        
        FENCE_P["<b>Geofence Engine</b><br/>━━━━━━━━━━━━━━━<br/>🗺️ GeoJSON Boundary Load<br/>📍 Point-in-Polygon Test<br/>🚪 Entry/Exit Detection<br/>⏱️ Event Timestamping<br/>━━━━━━━━━━━━━━━<br/><i>src/geofence/monitor.py</i>"]
    end
    
    subgraph PERSISTENCE["💾 DATA PERSISTENCE"]
        direction TB
        DB_P["<b>SQLite Database</b><br/>━━━━━━━━━━━━━━━<br/>📊 Time-Series Storage<br/>✍️ Write-Ahead Logging<br/>🔒 ACID Transactions<br/>📇 Indexed Queries<br/>━━━━━━━━━━━━━━━<br/><i>database/schema.sql</i>"]
        
        BACKUP_P["<b>Backup System</b><br/>━━━━━━━━━━━━━━━<br/>🕐 Daily Snapshots<br/>✅ Integrity Checks<br/>🔄 Auto-Recovery<br/>━━━━━━━━━━━━━━━<br/><i>scripts/backup.sh</i>"]
        
        EXPORT_P["<b>Export Utilities</b><br/>━━━━━━━━━━━━━━━<br/>📄 CSV Format<br/>🗺️ GeoJSON Tracks<br/>🔗 API Access<br/>━━━━━━━━━━━━━━━<br/><i>api/export_handler.py</i>"]
    end
    
    subgraph INTERFACE["🌐 USER INTERFACE"]
        direction TB
        API_I["<b>REST API</b><br/>━━━━━━━━━━━━━━━<br/>⚡ FastAPI Framework<br/>📖 Swagger Docs<br/>🔍 Query Endpoints<br/>📊 Statistics API<br/>━━━━━━━━━━━━━━━<br/><i>api/api_server.py</i>"]
        
        DASH_I["<b>Web Dashboard</b><br/>━━━━━━━━━━━━━━━<br/>🗺️ Leaflet.js Maps<br/>📈 Real-Time Tracking<br/>📊 Quality Metrics<br/>🎨 Interactive UI<br/>━━━━━━━━━━━━━━━<br/><i>api/dashboard/index.html</i>"]
        
        NOTIFY_I["<b>Push Notifications</b><br/>━━━━━━━━━━━━━━━<br/>🔔 Geofence Alerts<br/>⚠️ System Events<br/>📱 ntfy.sh Integration<br/>━━━━━━━━━━━━━━━<br/><i>scripts/notification_mgr.sh</i>"]
    end
    
    %% Primary Data Flow (GPS - Required)
    GPS_IN ==>|"NMEA Stream"| PARSE_P
    PARSE_P ==>|"Parsed Coordinates"| MOTION_P
    PARSE_P ==>|"Position Data"| FENCE_P
    MOTION_P ==>|"GPS + Metrics"| DB_P
    FENCE_P ==>|"Position + Events"| DB_P
    
    %% Optional LTE Flow
    LTE_IN -.->|"Cell Metrics"| DB_P
    
    %% Database Operations
    DB_P ==>|"Continuous Backup"| BACKUP_P
    DB_P ==>|"Data Access"| EXPORT_P
    DB_P ==>|"Query Interface"| API_I
    
    %% User Interface Outputs
    API_I ==>|"REST Endpoints"| DASH_I
    FENCE_P ==>|"Boundary Events"| NOTIFY_I
    
    %% Annotations
    GPS_IN -.->|"USB /dev/ttyUSB0"| PARSE_P
    LTE_IN -.->|"QMI /dev/cdc-wdm0"| DB_P
    
    %% Styling
    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    classDef processStyle fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000
    classDef storageStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000
    classDef interfaceStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:3px,color:#000
    classDef optionalStyle fill:#fafafa,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray: 5 5,color:#666
    
    class GPS_IN inputStyle
    class LTE_IN optionalStyle
    class PARSE_P,MOTION_P,FENCE_P processStyle
    class DB_P,BACKUP_P,EXPORT_P storageStyle
    class API_I,DASH_I,NOTIFY_I interfaceStyle
    
    %% Subgraph Styling
    style INPUTS fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style PROCESSING fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style PERSISTENCE fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style INTERFACE fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

### Data Architecture Layers

The system processes data through seven distinct architectural layers:

**1. Ingestion Layer** — GPS and LTE data collection through USB serial interfaces, providing raw NMEA sentences and cellular metrics.

**2. Analytics Layer** — Real-time computation of movement parameters (speed, heading, bearing) using Haversine formulas and position deltas.

**3. Persistence Layer** — Time-series data storage in SQLite with Write-Ahead Logging for crash resistance and ACID transaction guarantees.

**4. Geofence Layer** — Spatial boundary validation using Shapely point-in-polygon algorithms against GeoJSON-defined boundaries.

**5. Notification Layer** — REST-based event triggers to external services (ntfy.sh) when geofence violations or system events occur.

**6. Container Layer** — All components modularized and orchestrated via Docker Compose with independent health checks and restart policies.

**7. Cellular Context Layer** *(Optional)* — Secondary ingestion pipeline for LTE/GSM network metrics, enriching GPS records with cellular context.

### Feature Layer Details

#### 📡 Data Ingestion Layer
Primary input sources for real-time geolocation data collection.

| Component | Purpose | Technology | Status |
|-----------|---------|------------|--------|
| GPS Receiver | Continuous position tracking | NMEA 0183 @ 4800 baud | ✅ Required |
| LTE Monitor | Cellular network metadata | QMI protocol via libqmi | ⚠️ Optional |

#### ⚙️ Real-Time Analytics Layer
Processes raw sensor data into actionable intelligence and events.

| Component | Purpose | Algorithm | Output |
|-----------|---------|-----------|--------|
| NMEA Parser | Decode GPS sentences | Regex + validation | Structured coordinates |
| Motion Analytics | Calculate movement | Haversine formula | Speed, heading, distance |
| Geofence Engine | Boundary validation | Point-in-polygon (Shapely) | Entry/exit events |

#### 💾 Data Persistence Layer
Reliable, crash-resistant storage with automated maintenance.

| Component | Purpose | Technology | Frequency |
|-----------|---------|------------|-----------|
| SQLite Database | Time-series storage | WAL mode + FULL sync | Continuous |
| Backup System | Data redundancy | Automated snapshots | Daily @ 3 AM |
| Export Utilities | Data extraction | CSV/GeoJSON converters | On-demand |

**Database Tables:** `gps_data` (position, speed, heading) · `cell_observations` (LTE metrics) · `geofence_events` (boundary crossings)


#### 🌐 User Interface Layer
Access points for data visualization, querying, and alerting.

| Component | Purpose | Framework | Access |
|-----------|---------|-----------|--------|
| REST API | Programmatic access | FastAPI + Uvicorn | Port 8000 |
| Web Dashboard | Visual tracking | Leaflet.js + HTML5 | `http://[pi]:8000` |
| Push Notifications | Real-time alerts | ntfy.sh | Mobile/Desktop |

**API Endpoints:** `/api/gps/latest` · `/api/gps/track` · `/api/stats/summary` · `/docs` (Swagger)


### Data Flow Summary

```
GPS Receiver → NMEA Parser → Motion Analytics → SQLite Database → REST API → Dashboard
                          ↓                                      ↓
                    Geofence Engine → Push Notifications    Export Tools
                    
LTE Modem → Cell Metrics → SQLite Database (optional path)
```

**Flow Characteristics:**
- **Primary Path** (solid lines): Required GPS data pipeline from sensor to storage to user interface
- **Optional Path** (dashed lines): LTE metadata enhancement for cellular context correlation
- **Real-Time Processing**: <1 second latency from GPS fix to database commit
- **Crash Resilient**: WAL mode protects against corruption during sudden power loss
- **Self-Healing**: Automatic container restart on failure with <30 second recovery time

---

## Feature Priorities

#### 🔴 Mission Critical (P0) - Primary Objectives
Core GPS tracking and geofence alerting capabilities.

| Feature | Description | Implementation |
|---------|-------------|----------------|
| 📍 **GPS Position Logging** | Continuous NMEA parsing and coordinate extraction | `src/gps/gps_logger.py` |
| ⚡ **Speed/Heading Calc** | Haversine-based motion analytics from position deltas | `src/gps/movement_calc.py` |
| 🗺️ **Geofence Detection** | Point-in-polygon validation against GeoJSON boundaries | `src/geofence/monitor.py` |
| 🔔 **Push Notifications** | Real-time alerts via ntfy.sh on boundary violations | `scripts/notification_mgr.sh` |

#### 🟡 Enhanced Capabilities (P1) - Secondary Objectives
Cellular metadata collection and data access interfaces.

| Feature | Description | Implementation |
|---------|-------------|----------------|
| 📶 **LTE/GSM Metadata** | Cell ID, RSRP, RSRQ, band logging via QMI protocol | `src/cellular/lte_monitor.py` |
| 🌐 **REST API** | FastAPI endpoints for data access and statistics | `api/api_server.py` |
| 📊 **Dashboard Viz** | Interactive Leaflet.js map with real-time tracking | `api/dashboard/` |
| 📄 **Data Export** | CSV/GeoJSON export utilities for external analysis | `api/export_handler.py` |

#### 🔵 Infrastructure (P2) - Reliability Foundation
System-level capabilities ensuring autonomous operation.

| Feature | Description | Implementation |
|---------|-------------|----------------|
| 🐳 **Docker Containers** | Modular service isolation and orchestration | `docker-compose.yml` |
| 💾 **Auto Backups** | Daily database snapshots with integrity checks | `scripts/backup.sh` |
| 🔄 **Self-Healing** | Automatic container restart on failure (<30s recovery) | Health checks + systemd |
| 💥 **Crash Tolerance** | SQLite WAL + ext4 optimization for hard shutdowns | System configuration |

---

## Hardware Requirements

### Core Components

| Component | Model/Specification | Details |
|-----------|---------------------|---------|
| **Single Board Computer** | Raspberry Pi 5 (8GB RAM) | ARM Cortex-A76 quad-core @ 2.4GHz<br/>8GB LPDDR4X-4267 SDRAM<br/>Dual 4Kp60 HDMI display output<br/>2× USB 3.0, 2× USB 2.0 ports<br/>Gigabit Ethernet, WiFi 6, Bluetooth 5.0 |
| **Primary Storage** | SanDisk 128GB microSD Card | Class 10, UHS-I (U3)<br/>Formatted ext4 with optimizations<br/>`noatime,commit=60,data=ordered` |
| **Power Supply** | Official Raspberry Pi 27W USB-C | 5.1V / 5A output<br/>Vehicle adapter: 12V DC to USB-C |
| **Enclosure** | Raspberry Pi 5 Case | Passive cooling recommended<br/>Ventilation for continuous operation |

### GPS Hardware

| Component | Specification |
|-----------|---------------|
| **GPS Receiver** | USB GPS with Prolific PL2303 chipset |
| **Protocol** | NMEA 0183 |
| **Baud Rate** | 4800 |
| **Chipset** | SiRF Star IV or equivalent |
| **Update Rate** | 1 Hz (1 position/second) |
| **Cold Start** | 45-60 seconds |
| **Accuracy** | 2.5m CEP (typical) |
| **Satellites** | GPS + GLONASS support |
| **Antenna** | Active GPS antenna (recommended for vehicle) |
| **Device Path** | `/dev/ttyUSB0`<br/>Symlink: `/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_*` |
| **Connection** | USB 2.0/3.0 |
| **Fix Requirements** | 4+ satellites for 2D fix<br/>5+ satellites for 3D fix with altitude |

### LTE/GSM Hardware *(Optional)*

| Component | Specification |
|-----------|---------------|
| **Modem** | Sierra Wireless EM7511 |
| **Form Factor** | M.2 3042 (requires USB adapter) |
| **Interface** | USB 3.0 via M.2 to USB adapter |
| **Carrier** | T-Mobile (tested), unlocked for other carriers |
| **Bands** | LTE: B2, B4, B5, B7, B12, B13, B25, B26, B41, B66, B71<br/>UMTS/HSPA+: B1, B2, B4, B5, B8 |
| **Protocols** | QMI (primary), AT commands (secondary) |
| **QMI Device** | `/dev/cdc-wdm0` |
| **AT Interface** | `/dev/ttyUSB2` |
| **Data Collection** | Cell ID, MCC/MNC, PCI, RSRP, RSRQ, SNR, LTE Band |

### Optional Components

| Component | Purpose | Notes |
|-----------|---------|-------|
| **NVMe SSD** | Long-term archive storage | 256GB+ recommended<br/>Requires PCIe HAT for Pi 5<br/>Not critical for operation |
| **External GPS Antenna** | Improved GPS reception | SMA connector, active antenna<br/>Useful for vehicle installations |
| **LTE Antenna** | Enhanced cellular signal | Dual antenna for EM7511<br/>Improves signal in weak coverage areas |
| **UPS/Battery Pack** | Graceful shutdown buffer | Prevents data loss on power cut<br/>5-10 minute runtime sufficient |

### Tested Configuration

This system has been validated in production deployment:

- **Operating System**: Ubuntu 24.04 LTS (64-bit)
- **Kernel**: Linux 6.8+
- **Docker**: 27.x
- **Python**: 3.12
- **Deployment**: Mobile vehicle installation
- **Runtime**: 24/7 continuous operation
- **Environment**: Hard shutdown tolerance (no graceful power-off)

---

## Docker Architecture

### Container Orchestration Overview

```mermaid
graph TB
    subgraph BOOT["⚡ System Boot Sequence"]
        USB["usb-reset-boot.service<br/>Reset USB devices"]
        MAIN["gps-tracker.service<br/>Start Docker Compose"]
        USB --> MAIN
    end
    
    subgraph COMPOSE["🐳 Docker Compose Stack"]
        direction LR
        
        GPS["📡 rpi-gps-logger<br/>━━━━━━━━━━<br/>GPS collection<br/>NMEA parsing<br/>Motion analytics<br/><br/>Health: 30s<br/>Restart: unless-stopped"]
        
        LTE["📶 rpi-lte-monitor<br/>━━━━━━━━━━<br/>LTE metadata<br/>QMI interface<br/><br/>Health: 60s<br/>Restart: unless-stopped<br/><i>Privileged · Optional</i>"]
        
        API["🌐 gps-api-server<br/>━━━━━━━━━━<br/>FastAPI + Uvicorn<br/>Dashboard<br/>Data export<br/><br/>Health: 30s<br/>Restart: unless-stopped<br/>Port: 8000"]
    end
    
    subgraph STORAGE["💾 Persistent Storage"]
        DATA["./data/<br/>GPS SQLite database"]
        LTE_DATA["./lte-data/<br/>LTE SQLite database"]
        CONFIG["./config/<br/>GeoJSON, YAML"]
        LOGS["/var/log/gps-tracker/<br/>Application logs"]
    end
    
    subgraph HW["🔌 Hardware Devices"]
        GPS_DEV["/dev/ttyUSB0<br/>GPS receiver"]
        LTE_DEV["/dev/cdc-wdm0<br/>LTE modem"]
    end
    
    subgraph EXT["🌐 External Services"]
        BROWSER["Web Browser<br/>:8000"]
        NTFY["ntfy.sh<br/>gps-tracker-YOUR-TOPIC"]
    end
    
    %% Boot flow
    MAIN ==> COMPOSE
    
    %% Device connections
    GPS_DEV --> GPS
    LTE_DEV -.-> LTE
    
    %% Volume access
    GPS <-->|RW| DATA
    GPS -->|RO| CONFIG
    GPS -->|WO| LOGS
    
    LTE <-->|RW| LTE_DATA
    LTE -->|WO| LOGS
    
    API -->|RO| DATA
    API -->|RO| CONFIG
    
    %% External access
    API ==> BROWSER
    GPS -.-> NTFY
    
    %% Styling
    classDef bootStyle fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef containerStyle fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    classDef optionalStyle fill:#fafafa,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray:5 5
    classDef storageStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef hwStyle fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef extStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    
    class USB,MAIN bootStyle
    class GPS,API containerStyle
    class LTE optionalStyle
    class DATA,LTE_DATA,CONFIG,LOGS storageStyle
    class GPS_DEV,LTE_DEV hwStyle
    class BROWSER,NTFY extStyle
```

### Container Details

```mermaid
graph LR
    subgraph GPS_CONTAINER["📡 rpi-gps-logger Container"]
        direction TB
        GPS_CODE["<b>Application Code</b><br/>src/gps/gps_logger.py<br/>src/gps/nmea_parser.py<br/>src/gps/movement_calc.py"]
        GPS_ENV["<b>Environment</b><br/>Python 3.12<br/>pyserial, shapely"]
        GPS_MOUNT["<b>Mounts</b><br/>./data → /app/data (RW)<br/>./config → /app/config (RO)"]
        GPS_DEV_LINK["<b>Device</b><br/>/dev/ttyUSB0"]
        
        GPS_CODE --> GPS_ENV
        GPS_ENV --> GPS_MOUNT
        GPS_ENV --> GPS_DEV_LINK
    end
    
    subgraph LTE_CONTAINER["📶 rpi-lte-monitor Container (Optional)"]
        direction TB
        LTE_CODE["<b>Application Code</b><br/>src/cellular/lte_monitor.py<br/>src/cellular/qmi_interface.py"]
        LTE_ENV["<b>Environment</b><br/>Python 3.12<br/>libqmi, AT commands<br/><b>Privileged mode</b>"]
        LTE_MOUNT["<b>Mounts</b><br/>./lte-data → /app/data (RW)<br/>/dev → /dev (full access)"]
        LTE_DEV_LINK["<b>Network</b><br/>host mode"]
        
        LTE_CODE --> LTE_ENV
        LTE_ENV --> LTE_MOUNT
        LTE_ENV --> LTE_DEV_LINK
    end
    
    subgraph API_CONTAINER["🌐 gps-api-server Container"]
        direction TB
        API_CODE["<b>Application Code</b><br/>api/api_server.py<br/>api/export_handler.py<br/>api/dashboard/"]
        API_ENV["<b>Environment</b><br/>FastAPI + Uvicorn<br/>Leaflet.js, Pandas"]
        API_MOUNT["<b>Mounts</b><br/>./data → /app/data (RO)<br/>./config → /app/config (RO)"]
        API_PORT["<b>Exposed Port</b><br/>8000:8000"]
        
        API_CODE --> API_ENV
        API_ENV --> API_MOUNT
        API_ENV --> API_PORT
    end
    
    style GPS_CONTAINER fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style LTE_CONTAINER fill:#fafafa,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray:5 5
    style API_CONTAINER fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

### Architecture Components

| Component | Purpose | Restart Policy | Privileges |
|-----------|---------|----------------|------------|
| **usb-reset-boot.service** | Initializes USB devices on boot | One-shot | Root |
| **gps-tracker.service** | Orchestrates Docker Compose | Always restart | Root |
| **rpi-gps-logger** | Primary GPS data collection | `unless-stopped` | Standard |
| **rpi-lte-monitor** | Secondary cellular metadata | `unless-stopped` | Privileged (QMI) |
| **gps-api-server** | REST API and web dashboard | `unless-stopped` | Standard |

### Volume Mappings

| Host Path | Container Path | Access | Purpose |
|-----------|---------------|--------|---------|
| `./data` | `/app/data` | RW (GPS), RO (API) | GPS SQLite database |
| `./lte-data` | `/app/data` | RW (LTE only) | LTE SQLite database |
| `./config` | `/app/config` | RO (GPS, API) | GeoJSON boundaries, YAML config |
| `/var/log/gps-tracker` | Host logs | WO (GPS, LTE) | Application logs |

### Device Passthrough

| Host Device | Container | Mode | Purpose |
|-------------|-----------|------|---------|
| `/dev/ttyUSB0` | rpi-gps-logger | Standard | GPS NMEA data stream |
| `/dev/cdc-wdm0` | rpi-lte-monitor | Privileged + host network | QMI protocol access |

### Container Stack

```yaml
services:
  gps-logger:
    # Primary Task: GPS Data Collection
    # - Parses NMEA sentences
    # - Calculates speed and heading
    # - Writes to SQLite database
    devices: [GPS_DEVICE]
    restart: unless-stopped
    
  lte-monitor:
    # Secondary Task: Cellular Metadata Collection
    # - Collects signal metrics via QMI
    # - Logs Cell ID, RSRP, RSRQ, Band
    # - Requires ModemManager masked
    privileged: true
    restart: unless-stopped
    
  api-server:
    # Provides REST API and dashboard
    # - FastAPI endpoints
    # - Real-time map visualization
    # - Data export utilities
    ports: ["8000:8000"]
    restart: unless-stopped
```

**Health Checks:**
- GPS Logger: Database connectivity every 30s
- LTE Monitor: QMI device check every 60s
- API Server: HTTP endpoint check every 30s

**Auto-Recovery:**
- Containers restart automatically on failure
- Systemd service restarts Docker Compose
- Recovery time: <30 seconds

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/Raspberry-Pi-GPS-Cellular-Data-Logger.git
cd Raspberry-Pi-GPS-Cellular-Data-Logger

# 2. Configure environment
cp .env.example .env
nano .env  # Edit GPS_DEVICE path and other settings

# 3. Configure geofence (optional)
cp config/geofence.example.geojson config/geofence.geojson
# Edit coordinates using geojson.io or text editor

# 4. Deploy containers
docker compose up -d

# 5. Verify operation
docker ps
docker logs rpi-gps-logger --follow

# 6. Access dashboard
# Open browser: http://[raspberry-pi-ip]:8000
```

**Initial Setup Checklist:**
- [ ] GPS device connected and visible at `/dev/ttyUSB0`
- [ ] `.env` file configured with correct device paths
- [ ] Docker and Docker Compose installed
- [ ] Port 8000 available for API server
- [ ] (Optional) LTE modem connected at `/dev/cdc-wdm0`
- [ ] (Optional) Geofence boundary defined in `config/geofence.geojson`

---

## Database Schema

### gps_data (Primary Table)
```sql
CREATE TABLE gps_data (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude REAL,
    speed REAL,
    heading REAL,
    satellites INTEGER,
    hdop REAL,
    fix_quality INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### cell_observations (LTE Metadata - Optional)
```sql
CREATE TABLE cell_observations (
    id INTEGER PRIMARY KEY,
    ts INTEGER NOT NULL,
    cell_id TEXT,
    rsrp REAL,
    rsrq REAL,
    snr REAL,
    band TEXT,
    pci INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### geofence_events (Boundary Crossings)
```sql
CREATE TABLE geofence_events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    fence_name TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Database Configuration:**
- Mode: WAL (Write-Ahead Logging)
- Sync: FULL
- Location: `./data/gps_data.db`

---

## System Resilience

### Hard Shutdown Tolerance
The system is designed for mobile vehicle deployment where power can be cut without warning:

- **SQLite WAL Mode:** Protects against corruption during sudden power loss
- **Filesystem Optimization:** `ext4` with `noatime,commit=60,data=ordered`
- **RAM Logging:** Active logs in tmpfs, synced every 15 minutes
- **USB Reset Service:** Ensures devices initialize properly on boot

**Result:** Survives hard power loss mid-write without data corruption

### Self-Healing Mechanisms
- Container auto-restart on failure
- Health monitoring every 15 minutes
- Database integrity checks hourly
- Automatic backup restoration
- Recovery time: <30 seconds

### SD Card Longevity
- RAM-based logging (90% write reduction)
- Smart backups (only on changes)
- `noatime` mount option
- **Result:** Years of lifespan vs. months

---

## Geofencing

### Task Implementation
1. **Define Boundary:** Create GeoJSON file with polygon coordinates
2. **Load Configuration:** Geofence monitor reads boundary at startup
3. **Continuous Validation:** Check GPS position every 60 seconds
4. **Event Detection:** Log entry/exit when boundary is crossed
5. **Trigger Notification:** Send push alert via ntfy.sh

### GeoJSON Configuration
```json
{
  "type": "Feature",
  "properties": {"name": "Home Zone"},
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-77.0369, 38.8951],
      [-77.0369, 38.9051],
      [-77.0269, 38.9051],
      [-77.0269, 38.8951],
      [-77.0369, 38.8951]
    ]]
  }
}
```

Save to: `config/geofence.geojson`

**Create boundaries easily:** Use [geojson.io](https://geojson.io) to draw and export polygons

### Testing Your Geofence
```bash
# Check geofence events
docker exec rpi-gps-logger sqlite3 /app/data/gps_data.db \
  "SELECT * FROM geofence_events ORDER BY timestamp DESC LIMIT 10;"

# Monitor in real-time
docker logs rpi-gps-logger --follow | grep -i geofence
```

---

## REST API

### Base URL
```
http://[raspberry-pi-ip]:8000
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Interactive dashboard |
| `GET /docs` | Swagger API documentation |
| `GET /api/gps/latest` | Latest GPS position |
| `GET /api/gps/track` | GPS track (GeoJSON) |
| `GET /api/stats/summary` | System statistics |
| `GET /api/analysis/track-quality` | GPS quality metrics |

### Example: Latest Position
```bash
curl http://[raspberry-pi-ip]:8000/api/gps/latest | jq
```

```json
{
  "latitude": 39.1234,
  "longitude": -78.5678,
  "altitude": 125.5,
  "speed": 45.2,
  "heading": 135.0,
  "satellites": 8,
  "timestamp": "2025-11-24T10:30:00Z"
}
```

---

## System Services

### Systemd Integration

**Main Service:** `gps-tracker.service`
```ini
[Unit]
Description=GPS Tracker Service
After=docker.service network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/gps-tracker
ExecStart=/usr/bin/docker compose up
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**USB Reset Service:** `usb-reset-boot.service`
- Resets USB devices on boot
- Ensures GPS and modem initialize correctly
- Runs before main service starts

**Enable auto-start:**
```bash
sudo systemctl enable gps-tracker.service
sudo systemctl start gps-tracker.service
```

---

## Monitoring

### Health Checks
- Container health: Every 30-60 seconds
- System health: Every 15 minutes
- Database integrity: Hourly + on boot
- Disk space: Every 6 hours

### Automated Backups
- Daily at 3 AM
- Retention: Last 10 backups
- Location: `./backups/`

### Notifications
Push alerts via [ntfy.sh](https://ntfy.sh):
- Geofence boundary crossings (primary objective)
- System startup
- Container failures
- Low disk space warnings

**Configure:** Set your ntfy.sh topic in `.env` file

---

## Troubleshooting

### GPS Not Collecting Data

**Symptom:** No GPS records in database

```bash
# Check USB device
ls -la /dev/ttyUSB*

# Test GPS output directly
cat /dev/ttyUSB0
# Should see NMEA sentences like: $GPGGA,123519,4807.038,N,01131.000,E...

# Check container logs
docker logs rpi-gps-logger --tail 50

# Restart GPS container
docker restart rpi-gps-logger
```

**Common causes:**
- GPS device not connected or wrong path in `.env`
- GPS needs clear sky view (satellite acquisition takes 5-10 minutes)
- Wrong baud rate (try 9600 if 4800 doesn't work)
- USB power issues (try different port)

### LTE Monitor Not Working

**Symptom:** No cellular data in database

```bash
# Check QMI device
ls -la /dev/cdc-wdm0

# Verify ModemManager is masked (it conflicts with QMI)
systemctl is-active ModemManager
# Should show: inactive

# Test QMI manually
qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength

# Check container logs
docker logs rpi-lte-monitor --tail 50
```

**Common causes:**
- ModemManager running (conflicts with direct QMI access)
- LTE modem not properly initialized
- Insufficient privileges (container needs `privileged: true`)

### Dashboard Not Accessible

**Symptom:** Cannot reach http://[pi-ip]:8000

```bash
# Check if API container is running
docker ps | grep gps-api-server

# Check port binding
netstat -tuln | grep 8000

# Check API logs
docker logs gps-api-server --tail 50

# Restart API container
docker restart gps-api-server
```

**Common causes:**
- Firewall blocking port 8000
- Wrong IP address (check with `hostname -I`)
- Container failed to start (check logs)

### Database Corruption After Power Loss

**Symptom:** "database disk image is malformed"

```bash
# Check database integrity
sqlite3 /path/to/gps_data.db "PRAGMA integrity_check;"

# Restore from backup
cp ./backups/gps_data_backup_YYYYMMDD.db ./data/gps_data.db

# If no backup, attempt recovery
sqlite3 /path/to/gps_data.db ".recover" | sqlite3 recovered.db
```

**Prevention:**
- System already configured for crash resistance (WAL mode, optimized filesystem)
- Ensure SD card is high-quality (Class 10, UHS-I recommended)
- Consider UPS/battery backup for graceful shutdown

### GPS Loses Satellite Lock While Driving

**Symptom:** GPS works initially, then stops logging

```bash
# Check satellite count degradation
sqlite3 ./data/gps_data.db \
  "SELECT timestamp, satellites_used, fix_type 
   FROM gps_data 
   ORDER BY timestamp DESC 
   LIMIT 20;"
```

**Common causes:**
- GPS antenna blocked or poorly positioned
- Heavy tree cover or urban canyon (buildings)
- GPS receiver overheating
- USB cable/connection issue

**Solutions:**
- Use external GPS antenna with roof mount
- Ensure antenna has clear sky view
- Check USB cable quality and connections

---

## Project Structure & Documentation

```
raspberry-pi-gps-cellular-logger/
│
├── 📦 Container Configuration
│   ├── docker-compose.yml          Service orchestration
│   ├── Dockerfile.gps              GPS logger container
│   ├── Dockerfile.lte              LTE monitor container
│   ├── Dockerfile.api              API server container
│   └── .env                        Environment variables
│
├── 🐍 Source Code
│   ├── src/
│   │   ├── gps/
│   │   │   ├── gps_logger.py       GPS data collector
│   │   │   ├── nmea_parser.py      NMEA sentence parser
│   │   │   └── movement_calc.py    Motion analytics
│   │   ├── cellular/
│   │   │   ├── lte_monitor.py      LTE signal monitor (optional)
│   │   │   └── qmi_interface.py    QMI protocol handler
│   │   └── geofence/
│   │       └── geofence_monitor.py Boundary validator
│   │
│   └── api/
│       ├── api_server.py           FastAPI REST server
│       ├── export_handler.py       Data export utilities
│       └── dashboard/
│           └── index.html          Web dashboard
│
├── ⚙️ Configuration
│   ├── config/
│   │   ├── config.yaml.example     Configuration template
│   │   └── geofence.geojson        Boundary definitions
│   │
│   └── database/
│       └── schema.sql              SQLite schema
│
├── 🔧 System Scripts
│   ├── scripts/
│   │   ├── install.sh              System installation
│   │   ├── usb_reset.sh            USB device reset
│   │   ├── backup.sh               Database backup
│   │   └── notification_mgr.sh     Push notification handler
│   │
│   └── systemd/
│       ├── gps-tracker.service     Main service
│       └── usb-reset-boot.service  Boot USB reset
│
└── 📚 Documentation
    └── README.md                   This file
```

### Documentation Overview

This project includes comprehensive inline documentation and configuration examples to get started quickly.

#### 🚀 Quick Start Resources
- **docker-compose.yml** - Multi-container orchestration with health checks and volume mappings
- **.env.example** - Environment variable template with GPS device paths and settings
- **config.example.yaml** - System configuration reference with all available options
- **geofence.example.geojson** - Sample boundary polygon for geofencing setup

#### 📦 Container Configuration
- **Dockerfile.gps** - GPS logger image build specification with Python 3.12 and dependencies
- **Dockerfile.lte** - LTE monitor image (optional) with QMI protocol support
- **Dockerfile.api** - FastAPI REST API server image with dashboard assets

#### 🔧 System Integration
- **systemd/gps-tracker.service** - Main service definition for automatic startup
- **systemd/usb-reset-boot.service** - USB device initialization service
- **scripts/usb_reset.sh** - USB device reset utility for reliable boot
- **scripts/backup.sh** - Automated database backup with integrity checks

#### 💾 Database Architecture
- **database/schema.sql** - Complete SQLite schema with indexes
  - `gps_data` table: Position, speed, heading, satellite metrics
  - `cell_observations` table: LTE signal strength, cell towers, bands
  - `geofence_events` table: Boundary crossing timestamps and locations

#### 🐍 Source Code Structure
```
src/
├── gps/
│   ├── gps_logger.py          # NMEA parsing and GPS data collection
│   ├── nmea_parser.py          # Sentence validation and coordinate extraction
│   └── movement_calc.py        # Haversine-based speed/heading analytics
├── cellular/
│   ├── lte_monitor.py          # QMI protocol cellular metadata collection
│   └── qmi_interface.py        # Low-level QMI command interface
└── geofence/
    └── geofence_monitor.py     # Point-in-polygon boundary validation
```

#### 🌐 API & Dashboard
- **api/api_server.py** - FastAPI REST endpoints with Swagger documentation
- **api/export_handler.py** - CSV and GeoJSON export utilities
- **api/dashboard/index.html** - Interactive Leaflet.js map interface

#### ⚙️ Configuration Management
All configuration is centralized in `config/config.yaml`:
- GPS device path and baud rate
- LTE modem settings (optional)
- Geofence boundary files
- Notification URLs (ntfy.sh)
- Database paths
- Logging levels

See inline comments in example files for detailed configuration options.

---

## Acknowledgments

Built for production deployment on Raspberry Pi 5 with emphasis on reliability, autonomous operation, and hard shutdown tolerance. Tested in mobile vehicle environments with continuous 24/7 operation.

**Status**: Production-Ready  
**Last Updated**: 30 November 2025

---

## License

Free & Public Use
