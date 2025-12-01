#!/usr/bin/env python3
import subprocess, json, sqlite3, time, logging, re
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

GPS_STALE_THRESHOLD_SECONDS = 30  # Only use GPS if less than 30 seconds old

def get_fresh_gps_or_none(db):
    """Get GPS coordinates ONLY if they're fresh (< 30 seconds old)"""
    try:
        cursor = db.execute(
            "SELECT timestamp, latitude, longitude, speed, heading, altitude "
            "FROM gps_data ORDER BY timestamp DESC LIMIT 1"
        )
        result = cursor.fetchone()
        
        if not result:
            return None
        
        gps_timestamp_str, lat, lon, speed, heading, altitude = result
        
        # Parse GPS timestamp
        gps_time = datetime.fromisoformat(gps_timestamp_str)
        current_time = datetime.now()
        age_seconds = (current_time - gps_time).total_seconds()
        
        if age_seconds < GPS_STALE_THRESHOLD_SECONDS:
            # GPS is FRESH - use it
            return (lat, lon, speed, heading, altitude)
        else:
            # GPS is STALE - don't use it
            logging.warning(f"GPS data is stale ({age_seconds:.0f}s old) - using NULL")
            return None
            
    except Exception as e:
        logging.error(f"Error checking GPS freshness: {e}")
        return None

def get_qmi_data():
    """Get cellular data using QMI commands"""
    data = {}

    try:
        # Get signal strength
        result = subprocess.run(['qmicli', '-d', '/dev/cdc-wdm0', '--nas-get-signal-strength'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = result.stdout
            lines = output.split('\n')
            current_section = None

            for line in lines:
                line_stripped = line.strip()

                if line_stripped in ['RSRP:', 'RSRQ:', 'SNR:', 'SINR (8):']:
                    current_section = line_stripped.rstrip(':')
                    continue

                if current_section and "'lte':" in line and ("dBm" in line or "dB" in line):
                    match = re.search(r"'(-?\d+\.?\d*)", line)
                    if match:
                        value = float(match.group(1))
                        if current_section in ['RSRP']:
                            data['rsrp'] = value
                        elif current_section in ['RSRQ']:
                            data['rsrq'] = value
                        elif current_section in ['SNR', 'SINR (8)']:
                            data['snr'] = value

        # Get cell info
        result = subprocess.run(['qmicli', '-d', '/dev/cdc-wdm0', '--nas-get-cell-location-info'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "Global Cell ID:" in line:
                    match = re.search(r"'(\d+)'", line)
                    if match: data['cell_id'] = match.group(1)
                elif "Physical Cell ID:" in line:
                    match = re.search(r"'(\d+)'", line)
                    if match: data['pci'] = int(match.group(1))
                elif "EUTRA Absolute RF Channel Number:" in line:
                    match = re.search(r"band (\d+)", line)
                    if match: data['band'] = f"B{match.group(1)}"

    except Exception as e:
        logging.error(f"QMI command failed: {e}")

    return data

def main():
    db = sqlite3.connect('/app/data/gps_data.db')

    while True:
        try:
            qmi_data = get_qmi_data()

            if qmi_data:
                # Get FRESH GPS or None
                gps = get_fresh_gps_or_none(db)

                if gps:
                    # GPS is fresh - use real coordinates
                    lat, lon, speed, heading, altitude = gps
                    logging.info(f"📡 Cell: {qmi_data.get('cell_id')} Band: {qmi_data.get('band')} "
                               f"RSRP: {qmi_data.get('rsrp')}dBm RSRQ: {qmi_data.get('rsrq')}dB "
                               f"SNR: {qmi_data.get('snr')}dB @ GPS: {lat:.5f},{lon:.5f}")
                else:
                    # GPS is stale or unavailable - use NULL
                    lat, lon, speed, heading, altitude = None, None, None, None, None
                    logging.info(f"📡 Cell: {qmi_data.get('cell_id')} Band: {qmi_data.get('band')} "
                               f"RSRP: {qmi_data.get('rsrp')}dBm RSRQ: {qmi_data.get('rsrq')}dB "
                               f"SNR: {qmi_data.get('snr')}dB @ GPS: STALE/UNAVAILABLE")

                # INSERT observation (with NULL if GPS is stale)
                db.execute("""INSERT INTO cell_observations
                    (ts, lat, lon, speed, heading, altitude, cell_id, pci, rsrp, rsrq, snr, band)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (int(time.time()), lat, lon, speed, heading, altitude,
                     qmi_data.get('cell_id'), qmi_data.get('pci'),
                     qmi_data.get('rsrp'), qmi_data.get('rsrq'), qmi_data.get('snr'), qmi_data.get('band')))
                db.commit()

            time.sleep(5)

        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
