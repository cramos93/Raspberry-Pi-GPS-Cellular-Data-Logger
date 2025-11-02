# **Raspberry Pi GPS–Cellular Data Logger**
### Dual-Interface GPS and LTE Metadata Logger for Contextualized Geolocation Analysis

---

## **1. Objective**

The goal of this project is to build an automated GPS logging platform using a Raspberry Pi to capture and timestamp location, speed, heading, and satellite telemetry — optionally enhanced with LTE modem data for cellular network context.

This system provides accurate, timestamp-based geospatial logging without reliance on GPSD, instead using direct serial reads for increased reliability and control.  
The platform is designed for continuous mobile operation and automatic startup on boot.

---

## **2. Project Design Overview**

### **Core Functionality**
- Continuously log **GPS NMEA data** (latitude, longitude, speed, heading, altitude, satellite count, and local timestamp) from a **BU-353N GPS puck**.
- Store logs in **CSV format** with **timestamped filenames** for each session.
- Execute automatically on boot using a **systemd service** for unattended operation.

### **Optional LTE / Cellular Integration**
- Interface with a **Sierra Wireless EM7565 (or EM7511)** LTE modem via USB.  
- Collect and log **cellular metadata** (Cell ID, MCC/MNC, signal strength, band, registration state).  
- Merge or correlate LTE data with GPS telemetry for **contextual mapping** and **coverage visualization**.

### **Architecture**
- **Raspberry Pi 5 (8 GB)** as the core compute and logging node.  
- **Python-based data acquisition scripts** running independently or alongside network scanners (e.g., Wi-Fi or SDR capture).  
- Optional **Docker integration** for modular deployment of separate GPS, LTE, and analysis containers.

---

## **3. Requirements**

### **Hardware**
- **Raspberry Pi 5 (8 GB)** with Raspberry Pi OS (Bookworm recommended)  
- **GlobalSat BU-353N GPS Receiver** (USB, SiRF Star IV)  
- **Sierra Wireless EM7565 / EM7511 LTE Module**  
  - With T-Mobile or AT&T SIM  
  - Configurable via `AT` commands or `qmicli`  
- *(Optional)* **Panda PAU09 Wi-Fi Adapter** for network survey expansion  

### **Software**
- **Python 3.x**
  - Libraries: `pyserial`, `csv`, `datetime`, `subprocess`, `os`, `re`
- **Systemd Service Configuration**
  - Auto-start GPS logger script on boot
- *(Optional)* **Docker & Docker Compose** for modular deployments  

---

## **4. Project Deliverables**

### **Python GPS Logger**
Script that directly reads and parses serial GPS data from `/dev/ttyUSB0` and logs to timestamped CSV files.

### **Systemd Service File**
Ensures GPS logging starts automatically on boot, runs continuously, and restarts if terminated.

### **LTE Metadata Script (Optional)**
Captures and parses `AT+` command responses or `qmicli` outputs for cellular diagnostics and tower data.

### **Data Output Example**
