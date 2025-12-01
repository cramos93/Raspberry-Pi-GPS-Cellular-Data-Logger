#!/usr/bin/env python3
import os
import sqlite3
import json
from datetime import datetime

import requests
from shapely.geometry import Point, shape

DB_PATH = '/home/USERNAME/gps-data/gps_data.db'
GEOFENCE_FILE = '/home/USERNAME/gps-tracker/geofence/virginia_counties.geojson'
NTFY_URL = 'https://ntfy.sh/gps-tracker-YOUR-TOPIC'
STATE_FILE = '/tmp/culpeper_state.txt'

FENCE_LABEL = 'YOUR_CITY County'

def load_culpeper_polygon():
    """Load the YOUR_CITY County polygon from the GeoJSON file."""
    with open(GEOFENCE_FILE, 'r') as f:
        data = json.load(f)
    for feature in data.get("features", []):
        props = feature.get("properties", {}) or {}
        name = props.get("name") or props.get("NAME") or ""
        if "YOUR_CITY" in name:
            return shape(feature["geometry"])
    return None

def get_latest_fix(conn):
    """Return the latest GPS row as (id, ts, lat, lon) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, latitude, longitude "
        "FROM gps_data ORDER BY id DESC LIMIT 1;"
    )
    row = cur.fetchone()
    return row if row else None

def get_prev_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return None

def set_prev_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            f.write(state)
    except Exception:
        pass

def table_has_fence_name(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(geofence_events);")
    cols = [r[1] for r in cur.fetchall()]
    return "fence_name" in cols

def insert_geofence_event(conn, ts, event_type, lat, lon, fence_name=None):
    cur = conn.cursor()
    if fence_name is not None and table_has_fence_name(conn):
        cur.execute(
            "INSERT INTO geofence_events "
            "(timestamp, event_type, fence_name, latitude, longitude) "
            "VALUES (?, ?, ?, ?, ?);",
            (ts, event_type, fence_name, lat, lon),
        )
    else:
        cur.execute(
            "INSERT INTO geofence_events "
            "(timestamp, event_type, latitude, longitude) "
            "VALUES (?, ?, ?, ?);",
            (ts, event_type, lat, lon),
        )
    conn.commit()

def send_ntfy(event_type, ts, lat, lon):
    icon = "🚨" if event_type == "EXIT" else "✅"
    action = "LEFT" if event_type == "EXIT" else "ENTERED"
    msg = (
        f"{icon} {action} {FENCE_LABEL}\n"
        f"Time: {ts}\n"
        f"Position: {lat:.5f}, {lon:.5f}"
    )
    try:
        requests.post(NTFY_URL, data=msg.encode("utf-8"), timeout=5)
        print(f"NOTIFICATION SENT: {action} {FENCE_LABEL}")
    except Exception as e:
        print(f"NTFY error: {e}")

def main():
    polygon = load_culpeper_polygon()
    if polygon is None:
        print("ERROR: Could not load YOUR_CITY County polygon!")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        latest = get_latest_fix(conn)
        if latest is None:
            print("No GPS data yet.")
            return

        row_id, ts, lat, lon = latest
        point = Point(float(lon), float(lat))
        inside = polygon.contains(point)

        current_state = "inside" if inside else "outside"
        prev_state = get_prev_state()

        print(
            f"[{datetime.now().isoformat(timespec='seconds')}] "
            f"Position: {lat:.5f}, {lon:.5f} - {current_state.upper()} {FENCE_LABEL}"
        )

        # First run: just record state, no event
        if prev_state is None:
            set_prev_state(current_state)
            print(f"Initial state recorded: {current_state}")
            return

        # No change -> nothing to do
        if prev_state == current_state:
            return

        # BOUNDARY CROSSING!
        event_type = "ENTER" if current_state == "inside" else "EXIT"
        insert_geofence_event(conn, ts, event_type, lat, lon, FENCE_LABEL)
        send_ntfy(event_type, ts, lat, lon)
        set_prev_state(current_state)

        print(f"GEOFENCE EVENT: {event_type} {FENCE_LABEL} @ {ts}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
