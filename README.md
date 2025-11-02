# **Raspberry Pi GPS–Cellular Data Logger**
### Continuous GPS Logging, Motion Analytics, and Geofence Event Detection — with Optional LTE/GSM Contextual Metadata

---

## **1. Objectives**

### **Primary Objectives**
- Implement a GPS receiver system on a **Raspberry Pi 5** to record continuous location updates into a centralized database.
- Calculate and log movement parameters such as **speed** and **heading** over time.
- Define and enforce a **geofence** using a GeoJSON boundary file.
- Trigger a **real-time notification** when the geofence is crossed.

### **Secondary Objective (Optional)**
- **LTE/GSM Logging:** Integrate a cellular metadata capture module to enrich GPS records with LTE/GSM network context (Cell ID, signal strength, band, and registration state) using a **Sierra Wireless EM7565/EM7511** modem.  
  This enables correlation of spatial and signal data for contextualized geolocation analytics.

**Note:** The geofence is a configurable variable and not the defining objective of the project.

All modules are containerized for reproducible deployment and long-term unattended operation.

---

## **2. Project Design Overview**

### **Core Functionality**
- Continuously log **GPS NMEA sentences** from a **BU-353N GPS puck** connected via USB.  
- Parse and store **latitude, longitude, timestamp, altitude, speed, and heading** in a structured database.  
- Compute movement metrics using delta position and Haversine-based distance calculations.  
- Execute automatically on boot using a **systemd service** or **Docker container**.

### **Geofence and Notification Logic**
- Load a **GeoJSON file** defining the geofence polygon or radius boundary.  
- Continuously validate current position against the geofence area.  
- Log **entry and exit events** with timestamps in the database.  
- Trigger a **real-time notification** (e.g., via ntfy.sh) upon boundary violation.

### **— Optional: LTE/GSM Metadata Capture**
- Interface with a **Sierra Wireless EM7565/EM7511 LTE modem** through AT or QMI commands.  
- Record contextual **cellular metrics**, including:  
  - Cell ID  
  - MCC/MNC (Mobile Country & Network Code)  
  - RSRP (Signal Strength in dBm)  
  - LTE Band / Radio Access Type  
- Associate LTE metadata with each GPS timestamp for environmental context and future signal-coverage mapping.  

### **Data Architecture**
1. **Ingestion Layer** — GPS and LTE data collection through serial interfaces.  
2. **Analytics Layer** — Movement computation (speed, heading, bearing).  
3. **Persistence Layer** — Time-series data storage (SQLite/PostgreSQL).  
4. **Geofence Layer** — Spatial boundary validation using Shapely and GeoJSON.  
5. **Notification Layer** — REST-based event trigger to external services.  
6. **Container Layer** — All components modularized and orchestrated via Docker Compose.  
7. **— Optional: Cellular Context Layer** — Secondary ingestion pipeline for LTE/GSM network metrics.

---

## **3. Requirements**

### **Hardware**
- **Raspberry Pi 5 (8 GB)** with Raspberry Pi OS (Bookworm)  
- **GlobalSat BU-353N GPS Receiver (USB, SiRF Star IV)**  
- **— Optional:** Sierra Wireless EM7565 / EM7511 LTE Modem (USB interface)  
- **— Optional:** Panda PAU09 Wi-Fi Adapter for future survey expansion  

### **Software**
- **Python 3.x**
  - Libraries: `pyserial`, `gps`, `geojson`, `shapely`, `pyproj`, `sqlite3`, `requests`, `datetime`, `re`  
- **Database:** SQLite (default) or PostgreSQL  
- **Docker & Docker Compose** for containerized deployment  
- **Notification Service:** ntfy or equivalent push API  

---

<div align="center">

### **System Architecture Diagram**

```mermaid
graph TB
    %% -------------------- HARDWARE --------------------
    subgraph HW["🔧 HARDWARE LAYER"]
        GPS[📡 GPS Receiver<br/>BU-353N<br/><i>Hardware</i>]
        LTE[📶 LTE Modem<br/>EM7565<br/><i>Hardware · Optional</i>]
    end

    GPS -->|USB/NMEA| PI{{"🖥️ RASPBERRY PI 5<br/>Central Processing Unit<br/><i>Software Runtime</i>"}}
    LTE -.->|USB/AT| PI

    %% -------------------- SOFTWARE --------------------
    subgraph SW["💾 SOFTWARE LAYER"]
        direction TB
        PARSE[🧮 GPS Parser &<br/>Movement Calculator]
        CORE["⚙️ CORE PROCESSING<br/>📍 Location Tracking<br/>⚡ Speed Calculation<br/>🧭 Heading Analysis<br/>📊 Parameter Logging"]
        DB[(🗄️ Time-Series Database<br/>SQLite / PostgreSQL)]
        META[📱 LTE/GSM Metadata Collector<br/><i>Optional</i>]
    end

    PI --> PARSE
    PI -.-> META
    PARSE --> CORE
    CORE -->|Primary Data Flow| DB
    META -.->|Cell Data| DB

    %% -------------------- OPTIONAL FEATURES --------------------
    subgraph OPT["📌 OPTIONAL FEATURES"]
        FENCE[🧭 Geofence Validator<br/>GeoJSON · Optional]
        NOTIFY[📨 Push Notification<br/>ntfy.sh · Optional]
    end

    DB -.->|Feature Branch| FENCE
    FENCE -.->|On Violation| NOTIFY

    %% -------------------- DATA EXPORTS --------------------
    subgraph EXPORTS["📤 DATA VISUALIZATION EXPORTS"]
        direction TB
        CSV[📊 Formatted CSV<br/>for Charts & Dashboards]
        GEO[🗺️ GeoJSON Feature Collection<br/>for Mapping / Visualization]
    end

    DB -->|Export| CSV
    DB -->|Export| GEO

    %% -------------------- STYLES --------------------
    style HW fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style SW fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style OPT fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style EXPORTS fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

    style PI fill:#4caf50,stroke:#1b5e20,stroke-width:4px
    style CORE fill:#ffd54f,stroke:#f57c00,stroke-width:3px
    style DB fill:#ffb74d,stroke:#e64a19,stroke-width:2px

    style GPS fill:#90caf9,stroke:#1565c0,stroke-width:2px
    style LTE fill:#b0bec5,stroke:#455a64,stroke-width:1px,stroke-dasharray: 5 5
    style META fill:#ce93d8,stroke:#6a1b9a,stroke-width:1px,stroke-dasharray: 5 5
    style FENCE fill:#bcaaa4,stroke:#5d4037,stroke-width:1px,stroke-dasharray: 5 5
    style NOTIFY fill:#bcaaa4,stroke:#5d4037,stroke-width:1px,stroke-dasharray: 5 5
