#!/usr/bin/env python3
import sqlite3
import requests
from datetime import datetime

DB_PATH = '/home/USERNAME/gps-data/gps_data.db'
NTFY_URL = 'https://ntfy.sh/gps-tracker-YOUR-TOPIC'
STATE_FILE = '/tmp/last_geofence_state.txt'

# YOUR_CITY County approximate boundaries
LAT_MIN, LAT_MAX = 38.3, 38.73
LON_MIN, LON_MAX = -78.17, -77.64

def is_in_culpeper(lat, lon):
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest position
    cursor.execute('SELECT latitude, longitude FROM gps_data ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    if not result:
        return
    
    lat, lon = result
    current_inside = is_in_culpeper(lat, lon)
    
    # Read previous state
    try:
        with open(STATE_FILE, 'r') as f:
            was_inside = f.read().strip() == 'INSIDE'
    except:
        was_inside = None
    
    # Detect crossing
    if was_inside is not None:
        if was_inside and not current_inside:
            msg = f"🚨 LEFT YOUR_CITY County\nPosition: {lat:.5f}, {lon:.5f}"
            requests.post(NTFY_URL, data=msg)
            print(f"ALERT SENT: {msg}")
            
            # Log to database
            cursor.execute('''INSERT INTO geofence_events 
                           (timestamp, event_type, latitude, longitude) 
                           VALUES (datetime('now'), 'EXIT', ?, ?)''', (lat, lon))
            conn.commit()
            
        elif not was_inside and current_inside:
            msg = f"✅ ENTERED YOUR_CITY County\nPosition: {lat:.5f}, {lon:.5f}"
            requests.post(NTFY_URL, data=msg)
            print(f"ALERT SENT: {msg}")
            
            cursor.execute('''INSERT INTO geofence_events 
                           (timestamp, event_type, latitude, longitude) 
                           VALUES (datetime('now'), 'ENTER', ?, ?)''', (lat, lon))
            conn.commit()
    
    # Save state
    with open(STATE_FILE, 'w') as f:
        f.write('INSIDE' if current_inside else 'OUTSIDE')
    
    conn.close()
    print(f"Checked: {lat:.5f}, {lon:.5f} - {'INSIDE' if current_inside else 'OUTSIDE'}")

if __name__ == '__main__':
    main()
