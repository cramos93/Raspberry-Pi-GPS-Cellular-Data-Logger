# **Raspberry Pi GPS–Cellular Data Logger**
### Continuous GPS Logging, Motion Analytics, and Geofence Event Detection — with Optional LTE/GSM Contextual Metadata

---

## **1. Objective**

The purpose of this project is to design and implement an **automated GPS telemetry system** on a **Raspberry Pi 5** that continuously records positional data, computes movement parameters (speed and heading), and enforces a **geofence boundary** defined by a GeoJSON file.  
When a boundary is crossed, the system generates a **real-time push notification**.  

— **Optional Objective:**  
Integrate a **cellular metadata capture module** to enrich GPS records with LTE/GSM network context (Cell ID, signal strength, band, and registration state) using a **Sierra Wireless EM7565/EM7511** modem.  
This allows correlation of spatial and signal data for contextualized geolocation analytics.  

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

### **System Architecture Diagram**

If the diagram does not render automatically, refer to the static version below:  
![System Architecture Diagram](docs/system_architecture.png)

```mermaid
graph TD
    %% ===== Hardware Layer =====
    subgraph Hardware
        A[BU-353N GPS Receiver] --> B[Raspberry Pi 5]
        C[Sierra Wireless EM7565 LTE Modem — Optional] -.-> B
    end

    %% ===== Software Layer =====
    subgraph Software
        B --> D[GPS Parser and Movement Calculator]
        D --> F[Database Layer (SQLite / PostgreSQL)]
        F --> G[Geofence Validator (GeoJSON Boundary)]
        G --> H[Notification Service (ntfy.sh)]
        B -.-> E[LTE/GSM Metadata Collector — Optional]
        E -.-> F
    end

    %% ===== Styling =====
    style Hardware fill:#eaf4ff,stroke:#84a9ff,stroke-width:1px
    style Software fill:#f9f9f9,stroke:#999,stroke-width:1px
    classDef dashed stroke-dasharray: 4,3;
    class C,E dashed;
