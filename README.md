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
  This allows correlation of spatial and signal data for contextualized geolocation analytics.

All modules are containerized for reproducible deployment and long-term unattended operation.

---

## **2. Project Design Overview**

### **Core Functionality**
- Continuously log **GPS NMEA sentences** from a **BU-353N GPS puck** connected via USB.  
- Parse and store **latitude, longitude, timestamp, altitude, speed, and heading** in a structured database.  
- Compute movement metrics using delta-position and Haversine-based distance calculations.  
- Execute automatically on boot using a **systemd service** or **Docker container**.

### **Geofence and Notification Logic**
- Load a **GeoJSON** file defining the geofence polygon or radius boundary.  
- Continuously validate current position against the geofence area.  
- Log **entry and exit events** with timestamps in the database.  
- Trigger a **real-time notification** (e.g., via ntfy.sh) upon boundary violation.

### **Optional LTE/GSM Metadata Capture**
- Interface with a **Sierra Wireless EM7565/EM7511** LTE modem through AT or QMI commands.  
- Record contextual cellular metrics including Cell ID, MCC/MNC, RSRP, and LTE Band.  
- Associate LTE metadata with each GPS timestamp for future signal-coverage mapping.  

---

### **System Architecture Diagram**

```mermaid
graph TB
    %% ---------- Hardware ----------
    GPS["🔌 GPS Receiver<br/>BU-353N<br/><i>Hardware</i>"]
    LTE["📶 LTE Modem EM7565<br/><i>Hardware · Optional</i>"]

    GPS -->|USB/NMEA| PI{{"💻 RASPBERRY PI 5<br/>Central Processing Unit<br/><i>Software Runtime</i>"}}
    LTE -.->|USB/AT| PI

    %% ---------- Software Ingest ----------
    PI --> PARSE["⚙️ GPS Parser &<br/>Movement Calculator"]
    PI -.-> META["📡 LTE/GSM Metadata<br/>Parser & Collector · Optional"]

    %% ---------- Encapsulated Core Processing Hub ----------
    PARSE ==> CORE["🧠 <b>CORE PROCESSING MODULE</b><br/>━━━━━━━━━━━━━━━━━━━<br/>📍 Location Tracking<br/>⚡ Speed Calculation<br/>🧭 Heading Analysis<br/>📶 Cellular Logging (LTE/GSM)<br/>📊 Parameter Logging<br/>━━━━━━━━━━━━━━━━━━━<br/><i>Unified Telemetry & Signal Analytics Engine</i>"]

    META -.->|"Cell Metrics Input"| CORE
    CORE ==>|"Primary Data Flow"| DB[("💾 Time-Series Database<br/>SQLite / PostgreSQL")]
    DB -->|"Export"| FILES["📁 File Outputs<br/>CSV / GeoJSON<br/>Merged GPS + Cellular Data"]
    DB -.->|"Feature Branch"| FENCE["🗺️ Geofence Validator<br/>GeoJSON · Optional"]
    FENCE -.->|"On Violation"| NOTIFY["🔔 Push Notification<br/>ntfy.sh · Optional"]

    %% ---------- Styles ----------
    classDef hardware fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef hardwareOpt fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,stroke-dasharray:5 5,color:#666
    classDef central fill:#4caf50,stroke:#1b5e20,stroke-width:4px
    classDef core fill:#fff8e1,stroke:#f57c00,stroke-width:3px
    classDef database fill:#ffb74d,stroke:#e64a19,stroke-width:2px
    classDef software fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef softwareOpt fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray:5 5,color:#666
    classDef optional fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,stroke-dasharray:5 5,color:#666

    class GPS hardware
    class LTE hardwareOpt
    class PI central
    class PARSE software
    class META softwareOpt
    class CORE core
    class DB database
    class FILES software
    class FENCE,NOTIFY optional
