"""
GPS/LTE Analytics API Server
Provides REST endpoints for frontend dashboard with anomaly detection
"""

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import math
from contextlib import contextmanager

app = FastAPI(
    title="GPS/LTE Analytics API",
    description="Real-time GPS tracking with anomaly detection",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path (read-only)
DB_PATH = "/app/data/gps_data.db"

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ============================================================
# CORE DATA ENDPOINTS
# ============================================================

@app.get("/")
def root():
    """API health check"""
    return {
        "status": "online",
        "api": "GPS/LTE Analytics",
        "version": "1.0.0",
        "endpoints": [
            "/api/gps/latest",
            "/api/gps/track",
            "/api/stats/summary",
            "/api/analysis/anomalies",
            "/api/analysis/track-quality"
        ]
    }

@app.get("/api/gps/latest")
def get_latest_gps():
    """Get most recent GPS position"""
    with get_db() as conn:
        cursor = conn.cursor()
        result = cursor.execute("""
            SELECT 
                latitude, longitude, altitude,
                speed, heading,
                timestamp, utc_time,
                satellites_used, satellites_visible,
                hdop, vdop, pdop,
                fix_type, fix_quality,
                geofence, geofence_status
            FROM gps_data
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()
        
        if result:
            return dict(result)
        return {"error": "No GPS data available"}

@app.get("/api/gps/track")
def get_gps_track(
    hours: int = Query(24, description="Hours of history to retrieve"),
    limit: int = Query(1000, description="Maximum number of points")
):
    """Get GPS track for map display"""
    with get_db() as conn:
        cursor = conn.cursor()
        results = cursor.execute("""
            SELECT 
                latitude, longitude, altitude,
                speed, heading,
                timestamp,
                satellites_used,
                hdop, fix_type
            FROM gps_data
            WHERE timestamp > datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (hours, limit)).fetchall()
        
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row["longitude"], row["latitude"]]
                    },
                    "properties": {
                        "timestamp": row["timestamp"],
                        "speed": row["speed"],
                        "heading": row["heading"],
                        "altitude": row["altitude"],
                        "satellites": row["satellites_used"],
                        "hdop": row["hdop"],
                        "fix_type": row["fix_type"]
                    }
                }
                for row in results
            ]
        }

@app.get("/api/stats/summary")
def get_summary_stats():
    """Get dashboard summary statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # GPS stats
        gps_stats = cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(datetime(timestamp)) as first_record,
                MAX(datetime(timestamp)) as last_record,
                AVG(speed) as avg_speed,
                MAX(speed) as max_speed,
                AVG(satellites_used) as avg_satellites,
                AVG(hdop) as avg_hdop
            FROM gps_data
        """).fetchone()
        
        # LTE stats
        lte_stats = cursor.execute("""
            SELECT 
                COUNT(*) as total_observations,
                AVG(rsrp) as avg_rsrp,
                AVG(rsrq) as avg_rsrq,
                COUNT(DISTINCT band) as unique_bands
            FROM cell_observations
        """).fetchone()
        
        # Recent stats (last 24 hours)
        recent_stats = cursor.execute("""
            SELECT 
                COUNT(*) as records_24h,
                SUM(distance_traveled) as distance_24h,
                AVG(speed) as avg_speed_24h
            FROM gps_data
            WHERE timestamp > datetime('now', '-24 hours')
        """).fetchone()
        
        return {
            "gps": dict(gps_stats) if gps_stats else {},
            "lte": dict(lte_stats) if lte_stats else {},
            "recent": dict(recent_stats) if recent_stats else {}
        }

# ============================================================
# ANOMALY DETECTION ENDPOINTS
# ============================================================

@app.get("/api/analysis/anomalies")
def detect_anomalies(hours: int = Query(24, description="Hours to analyze")):
    """
    Detect GPS anomalies:
    - Spoofing (position jumps, impossible speeds)
    - Jamming (satellite loss, signal degradation)
    - Quality issues (poor HDOP, fix loss)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get GPS data for analysis
        data = cursor.execute("""
            SELECT 
                id, timestamp, latitude, longitude, altitude,
                speed, heading,
                satellites_used, hdop, vdop,
                fix_type, fix_quality
            FROM gps_data
            WHERE timestamp > datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        """, (hours,)).fetchall()
        
        anomalies = []
        prev_row = None
        
        for row in data:
            row_dict = dict(row)
            
            if prev_row:
                # Check for position jumps (possible spoofing)
                distance = haversine_distance(
                    prev_row["latitude"], prev_row["longitude"],
                    row["latitude"], row["longitude"]
                )
                
                time_diff = (datetime.fromisoformat(row["timestamp"]) - 
                           datetime.fromisoformat(prev_row["timestamp"])).total_seconds()
                
                if time_diff > 0:
                    # Detect impossible speeds (>200 mph = 322 km/h)
                    implied_speed_mps = distance / time_diff  # meters per second
                    implied_speed_mph = implied_speed_mps * 2.237  # convert to mph
                    
                    if implied_speed_mph > 200:
                        anomalies.append({
                            "type": "spoofing_suspected",
                            "severity": "high",
                            "timestamp": row["timestamp"],
                            "latitude": row["latitude"],
                            "longitude": row["longitude"],
                            "reason": f"Impossible speed: {implied_speed_mph:.0f} mph",
                            "details": {
                                "distance_meters": distance,
                                "time_seconds": time_diff,
                                "implied_speed_mph": implied_speed_mph
                            }
                        })
                    
                    # Detect teleportation (>1 km jump in <5 seconds)
                    if distance > 1000 and time_diff < 5:
                        anomalies.append({
                            "type": "position_jump",
                            "severity": "critical",
                            "timestamp": row["timestamp"],
                            "latitude": row["latitude"],
                            "longitude": row["longitude"],
                            "reason": f"Position jump: {distance:.0f}m in {time_diff:.1f}s",
                            "details": {
                                "distance_meters": distance,
                                "time_seconds": time_diff
                            }
                        })
            
            # Detect jamming (satellite loss)
            if row["satellites_used"] is not None and row["satellites_used"] == 0:
                anomalies.append({
                    "type": "jamming_suspected",
                    "severity": "high",
                    "timestamp": row["timestamp"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "reason": "Complete satellite loss (0 satellites)",
                    "details": {
                        "satellites": row["satellites_used"],
                        "hdop": row["hdop"]
                    }
                })
            
            # Detect poor accuracy (high HDOP)
            if row["hdop"] is not None and row["hdop"] > 10:
                anomalies.append({
                    "type": "poor_accuracy",
                    "severity": "medium",
                    "timestamp": row["timestamp"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "reason": f"Poor GPS accuracy (HDOP: {row['hdop']:.1f})",
                    "details": {
                        "hdop": row["hdop"],
                        "satellites": row["satellites_used"]
                    }
                })
            
            # Detect fix degradation (3D -> 2D)
            if (prev_row and 
                prev_row["fix_type"] == "3D" and 
                row["fix_type"] in ["2D", "No Fix"]):
                anomalies.append({
                    "type": "fix_degradation",
                    "severity": "medium",
                    "timestamp": row["timestamp"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "reason": f"Fix degraded: 3D -> {row['fix_type']}",
                    "details": {
                        "prev_fix": prev_row["fix_type"],
                        "current_fix": row["fix_type"],
                        "satellites": row["satellites_used"]
                    }
                })
            
            prev_row = row_dict
        
        return {
            "total_anomalies": len(anomalies),
            "anomalies": anomalies,
            "summary": {
                "spoofing_events": len([a for a in anomalies if "spoofing" in a["type"]]),
                "jamming_events": len([a for a in anomalies if "jamming" in a["type"]]),
                "position_jumps": len([a for a in anomalies if a["type"] == "position_jump"]),
                "accuracy_issues": len([a for a in anomalies if a["type"] == "poor_accuracy"]),
                "fix_degradations": len([a for a in anomalies if a["type"] == "fix_degradation"])
            }
        }

@app.get("/api/analysis/track-quality")
def analyze_track_quality(hours: int = Query(24, description="Hours to analyze")):
    """Analyze overall GPS track quality"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        quality_metrics = cursor.execute("""
            SELECT 
                COUNT(*) as total_fixes,
                AVG(satellites_used) as avg_satellites,
                MIN(satellites_used) as min_satellites,
                MAX(satellites_used) as max_satellites,
                AVG(hdop) as avg_hdop,
                AVG(vdop) as avg_vdop,
                AVG(pdop) as avg_pdop,
                SUM(CASE WHEN fix_type = '3D' THEN 1 ELSE 0 END) as fixes_3d,
                SUM(CASE WHEN fix_type = '2D' THEN 1 ELSE 0 END) as fixes_2d,
                SUM(CASE WHEN fix_type = 'No Fix' THEN 1 ELSE 0 END) as fixes_none,
                SUM(CASE WHEN satellites_used >= 6 THEN 1 ELSE 0 END) as good_fixes,
                SUM(CASE WHEN hdop < 5 THEN 1 ELSE 0 END) as accurate_fixes
            FROM gps_data
            WHERE timestamp > datetime('now', '-' || ? || ' hours')
        """, (hours,)).fetchone()
        
        metrics = dict(quality_metrics)
        
        # Calculate quality score (0-100)
        total = metrics["total_fixes"]
        if total > 0:
            score = (
                (metrics["fixes_3d"] / total) * 40 +  # 40% weight on 3D fixes
                (metrics["good_fixes"] / total) * 30 +  # 30% weight on satellite count
                (metrics["accurate_fixes"] / total) * 30  # 30% weight on accuracy
            )
            metrics["quality_score"] = round(score, 1)
            metrics["quality_rating"] = (
                "Excellent" if score >= 90 else
                "Good" if score >= 75 else
                "Fair" if score >= 50 else
                "Poor"
            )
        else:
            metrics["quality_score"] = 0
            metrics["quality_rating"] = "No Data"
        
        return metrics

@app.get("/api/lte/heatmap")
def get_lte_heatmap(hours: int = Query(24, description="Hours of data")):
    """Get LTE signal strength heatmap data"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        results = cursor.execute("""
            SELECT 
                lat as latitude,
                lon as longitude,
                rsrp,
                rsrq,
                band,
                operator
            FROM cell_observations
            WHERE ts > strftime('%s', 'now', '-' || ? || ' hours')
            AND lat IS NOT NULL
            AND lon IS NOT NULL
            ORDER BY ts DESC
            LIMIT 1000
        """, (hours,)).fetchall()
        
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row["longitude"], row["latitude"]]
                    },
                    "properties": {
                        "rsrp": row["rsrp"],
                        "rsrq": row["rsrq"],
                        "band": row["band"],
                        "operator": row["operator"],
                        "signal_quality": (
                            "Excellent" if row["rsrp"] and row["rsrp"] > -80 else
                            "Good" if row["rsrp"] and row["rsrp"] > -90 else
                            "Fair" if row["rsrp"] and row["rsrp"] > -100 else
                            "Poor"
                        )
                    }
                }
                for row in results
            ]
        }

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in meters"""
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Serve static dashboard
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Mount dashboard directory
dashboard_path = "/app/dashboard"
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path), name="dashboard")
    
    @app.get("/")
    async def read_root():
        # Redirect to dashboard
        return FileResponse(os.path.join(dashboard_path, "index.html"))

