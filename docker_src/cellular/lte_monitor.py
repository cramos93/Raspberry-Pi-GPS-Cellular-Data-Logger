import os
import time
import sqlite3
import logging
import subprocess
import signal
import threading

# --- Logging setup ---
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "lte_monitor.log")),
    ],
)

# --- Config ---
DB_PATH = os.getenv("DATABASE_PATH", "/app/data/gps_data.db")
POLL = int(os.getenv("LTE_POLL_INTERVAL", "5"))
QMI_DEV = os.getenv("QMI_DEVICE", "/dev/cdc-wdm0")

stop = threading.Event()


def sigterm(*_):
    stop.set()


signal.signal(signal.SIGTERM, sigterm)


# --- DB setup ---
def db_init():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cell_observations(
            id INTEGER PRIMARY KEY,
            ts INTEGER,
            lat REAL,
            lon REAL,
            speed REAL,
            heading REAL,
            altitude REAL,
            cell_id TEXT,
            pci INTEGER,
            rsrp REAL,
            rsrq REAL,
            band TEXT,
            mcc TEXT,
            mnc TEXT,
            operator TEXT
        );
        """
    )
    con.commit()
    return con


def _pick(cols, candidates, default=None):
    for c in candidates:
        if c in cols:
            return c
    return default


def latest_gps(con):
    """
    Get the most recent GPS fix from gps_data.

    We do NOT assume any particular timestamp column.
    We just take the last inserted row (ORDER BY rowid DESC).
    """
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(gps_data)")]
    lat_col = _pick(cols, ["lat", "latitude"])
    lon_col = _pick(cols, ["lon", "longitude"])
    spd_col = _pick(cols, ["speed", "speed_mps", "speed_mph", "ground_speed"])
    hdg_col = _pick(cols, ["heading", "course", "bearing"])
    alt_col = _pick(cols, ["alt", "altitude", "altitude_m"])

    if not lat_col or not lon_col:
        logging.warning("gps_data missing lat/lon; cannot attach LTE fix")
        return None

    select_cols = [lat_col, lon_col]
    if spd_col:
        select_cols.append(spd_col)
    if hdg_col:
        select_cols.append(hdg_col)
    if alt_col:
        select_cols.append(alt_col)

    q = f"SELECT {', '.join(select_cols)} FROM gps_data ORDER BY rowid DESC LIMIT 1"
    row = cur.execute(q).fetchone()
    if not row:
        return None

    idx = 0
    lat = row[idx]
    lon = row[idx + 1]
    idx += 2

    speed = heading = altitude = None
    if spd_col and len(row) > idx:
        speed = row[idx]
        idx += 1
    if hdg_col and len(row) > idx:
        heading = row[idx]
        idx += 1
    if alt_col and len(row) > idx:
        altitude = row[idx]

    return {
        "ts": int(time.time()),
        "lat": lat,
        "lon": lon,
        "speed": speed,
        "heading": heading,
        "altitude": altitude,
    }


def _extract_number(fragment):
    """
    Best-effort helper to pull a float like -96 from substrings such as:
    "RSRP: '-96 dBm'" or "RSRP: -96 dBm"
    """
    try:
        frag = fragment.strip()
        if "'" in frag:
            frag = frag.split("'", 2)[1]
        return float(frag.split()[0])
    except Exception:
        return None


def parse_qmi():
    """
    Use qmicli to read LTE signal + basic serving info from /dev/cdc-wdm0.

    Requires:
      - libqmi-utils inside container (qmicli binary)
      - /dev/cdc-wdm0 passed into container
    """
    info = {
        "rsrp": None,
        "rsrq": None,
        "rssi": None,
        "snr": None,
        "band": None,
        "cell_id": None,
        "pci": None,
        "mcc": None,
        "mnc": None,
        "operator": None,
    }

    # 1) Signal info
    try:
        out = subprocess.check_output(
            ["qmicli", "-d", QMI_DEV, "--nas-get-signal-info"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        for line in out.splitlines():
            line = line.strip()
            if "RSSI:" in line:
                val = _extract_number(line.split("RSSI:", 1)[1])
                if val is not None:
                    info["rssi"] = val
            if "RSRP:" in line:
                val = _extract_number(line.split("RSRP:", 1)[1])
                if val is not None:
                    info["rsrp"] = val
            if "RSRQ:" in line:
                val = _extract_number(line.split("RSRQ:", 1)[1])
                if val is not None:
                    info["rsrq"] = val
            if "SNR:" in line:
                val = _extract_number(line.split("SNR:", 1)[1])
                if val is not None:
                    info["snr"] = val
    except FileNotFoundError:
        logging.warning("qmicli not found in container PATH; install libqmi-utils.")
        return info
    except Exception as e:
        logging.warning(f"qmicli signal query failed: {e}")

    # 2) Serving system info for MCC/MNC/operator (best-effort)
    try:
        out = subprocess.check_output(
            ["qmicli", "-d", QMI_DEV, "--nas-get-serving-system"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        for line in out.splitlines():
            line = line.strip()
            if "MCC:" in line and info["mcc"] is None:
                frag = line.split("MCC:", 1)[1]
                if "'" in frag:
                    info["mcc"] = frag.split("'", 2)[1].strip()
            if "MNC:" in line and info["mnc"] is None:
                frag = line.split("MNC:", 1)[1]
                if "'" in frag:
                    info["mnc"] = frag.split("'", 2)[1].strip()
            if "operator name:" in line and info["operator"] is None:
                frag = line.split("operator name:", 1)[1]
                if "'" in frag:
                    info["operator"] = frag.split("'", 2)[1].strip()
    except Exception as e:
        # Not fatal; we still have signal metrics if those worked
        logging.debug(f"qmicli serving-system query failed: {e}")

    # If we have any LTE-ish metrics, assume LTE band label if unknown
    if info["band"] is None and any(
        info[k] is not None for k in ("rsrp", "rsrq", "rssi", "snr")
    ):
        info["band"] = "LTE"

    return info


def main():
    logging.info(f"Starting LTE monitor via QMI (device {QMI_DEV})")
    con = db_init()

    while not stop.is_set():
        try:
            gps = latest_gps(con)
            if not gps:
                logging.debug("No recent GPS fix; skipping LTE sample")
                time.sleep(POLL)
                continue

            lte = parse_qmi()

            if any(lte.get(k) is not None for k in ("rsrp", "rsrq", "rssi", "band")):
                cur = con.cursor()
                cur.execute(
                    """
                    INSERT INTO cell_observations
                    (ts, lat, lon, speed, heading, altitude,
                     cell_id, pci, rsrp, rsrq, band, mcc, mnc, operator)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        gps["ts"],
                        gps["lat"],
                        gps["lon"],
                        gps.get("speed"),
                        gps.get("heading"),
                        gps.get("altitude"),
                        lte.get("cell_id"),
                        lte.get("pci"),
                        lte.get("rsrp"),
                        lte.get("rsrq"),
                        lte.get("band"),
                        lte.get("mcc"),
                        lte.get("mnc"),
                        lte.get("operator"),
                    ),
                )
                con.commit()
                logging.info(
                    "LTE sample: band=%s rsrp=%s rsrq=%s mcc=%s mnc=%s @ (%.5f,%.5f)"
                    % (
                        lte.get("band"),
                        lte.get("rsrp"),
                        lte.get("rsrq"),
                        lte.get("mcc"),
                        lte.get("mnc"),
                        gps["lat"],
                        gps["lon"],
                    )
                )
            else:
                logging.debug("No LTE signal metrics from qmicli; skipping insert")

            time.sleep(POLL)
        except Exception as e:
            logging.error(f"Error in LTE monitor loop: {e}")
            time.sleep(POLL)


if __name__ == "__main__":
    main()
