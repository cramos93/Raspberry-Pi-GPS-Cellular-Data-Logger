# **Raspberry Pi GPS Data Logger**
### Continuous GPS Logging, Motion Analytics, and Geofence Event Detection — with Optional LTE/GSM Contextual Metadata

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/-RaspberryPi-C51A4A?logo=Raspberry-Pi)

---

## **📋 Table of Contents**
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [Geofencing](#geofencing)
- [LTE/GSM Monitoring](#ltegsm-monitoring-optional)
- [Data Export](#data-export)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## **Overview**

A production-grade GPS vehicle tracking system for Raspberry Pi 5 that records continuous location updates, calculates motion parameters, and monitors geofence boundaries with real-time notifications. Optional LTE/GSM cellular metadata integration provides enriched spatial and signal correlation data.

**Core Objectives:**
- Implement continuous GPS logging with NMEA parsing
- Calculate movement parameters (speed, heading, distance)
- Define and enforce geofence boundaries with GeoJSON
- Trigger real-time notifications on boundary crossings
- *(Optional)* Capture LTE/GSM cellular metadata for signal analysis

---

## **System Architecture**
```mermaid
