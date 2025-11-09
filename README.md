#!/usr/bin/env python3
"""
Raspberry Pi GPS Data Logger
Continuous GPS logging with motion analytics and geofence detection
"""

import serial
import time
import sqlite3
import json
import requests
import os
import logging
from datetime import datetime
from math import radians, cos, sin, asin, sqrt, atan2, degrees
from pathlib import Path
import re

try:
    from shapely.geometry import Point, shape
    import geojson
    GEOFENCE_AVAILABLE = True
except ImportError:
    GEOFENCE_AVAILABLE = False
    print("Warning: shapely/geojson not available. Geofence features disabled.")


class GPSLogger:
    """Main GPS logging application with motion analytics and geofencing"""
    
    def __init__(self, config=None):
        """Initialize GPS logger with configuration"""
        self.config = config or self.load_config()
        self.setup_logging()
        self.db_path = self.config.get('database_path', '/app/data/gps_data.db')
        self.gps_device = self.config.get('gps_device', '/dev/ttyUSB0')
        self.gps_baud = self.config.get('gps_baud_rate', 4800)
        
        # Initialize components
        self.serial_conn = None
        self.db_conn = None
        self.geofence = None
        self.inside_geofence = None
        self.last_position = None
        
        # Setup database
        self.setup_database()
        
        # Load geofence if available
        if GEOFENCE_AVAILABLE:
            self.load_geofence()
    
    def load_config(self):
        """Load configuration from environment variables"""
        return {
            'database_path': os.getenv('DATABASE_PATH', '/app/data/gps_data.db'),
            'gps_device': os.getenv('GPS_DEVICE', '/dev/ttyUSB0'),
            'gps_baud_rate': int(os.getenv('GPS_BAUD_RATE', '4800')),
            'gps_timeout': int(os.getenv('GPS_TIMEOUT', '10')),
            'geofence_file': os.getenv('GEOFENCE_FILE', '/app/config/geofence.geojson'),
            'geofence_check_interval': int(os.getenv('GEOFENCE_CHECK_INTERVAL', '5')),
            'notification_url': os.getenv('NOTIFICATION_URL', ''),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/app/logs/gps_logger.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_database(self):
        """Initialize SQLite database with required tables"""
        try:
            # Create data directory if it doesn't exist
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            
            # GPS data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gps_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    speed REAL,
                    heading REAL,
                    satellites INTEGER,
                    hdop REAL,
                    fix_quality INTEGER
                )
            ''')
            
            # Geofence events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geofence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON gps_data(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_geofence_timestamp 
                ON geofence_events(timestamp)
            ''')
            
            self.db_conn.commit()
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Database setup error: {e}")
            raise
    
    def load_geofence(self):
        """Load geofence boundary from GeoJSON file"""
        if not GEOFENCE_AVAILABLE:
            self.logger.warning("Geofence features not available (shapely/geojson not installed)")
            return
        
        geofence_file = self.config.get('geofence_file')
        if not geofence_file or not os.path.exists(geofence_file):
            self.logger.warning(f"Geofence file not found: {geofence_file}")
            return
        
        try:
            with open(geofence_file, 'r') as f:
                geojson_data = geojson.load(f)
            
            # Support both Feature and FeatureCollection
            if geojson_data['type'] == 'FeatureCollection':
                self.geofence = shape(geojson_data['features'][0]['geometry'])
            elif geojson_data['type'] == 'Feature':
                self.geofence = shape(geojson_data['geometry'])
            else:
                self.geofence = shape(geojson_data)
            
            self.logger.info(f"Geofence loaded from {geofence_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading geofence: {e}")
    
    def connect_gps(self):
        """Connect to GPS receiver via serial port"""
        try:
            self.serial_conn = serial.Serial(
                self.gps_device,
                baudrate=self.gps_baud,
                timeout=self.config.get('gps_timeout', 10)
            )
            self.logger.info(f"Connected to GPS at {self.gps_device}")
            return True
        except Exception as e:
            self.logger.error(f"GPS connection error: {e}")
            return False
    
    def parse_nmea_sentence(self, sentence):
        """Parse NMEA sentence and extract GPS data"""
        try:
            if not sentence.startswith('$'):
                return None
            
            parts = sentence.strip().split(',')
            sentence_type = parts[0]
            
            # Parse GPGGA (Global Positioning System Fix Data)
            if sentence_type == '$GPGGA':
                return self.parse_gpgga(parts)
            
            # Parse GPRMC (Recommended Minimum Specific GPS/Transit Data)
            elif sentence_type == '$GPRMC':
                return self.parse_gprmc(parts)
            
        except Exception as e:
            self.logger.debug(f"Error parsing NMEA: {e}")
        
        return None
    
    def parse_gpgga(self, parts):
        """Parse GPGGA NMEA sentence"""
        try:
            if len(parts) < 15 or not parts[2] or not parts[4]:
                return None
            
            # Convert latitude
            lat_deg = float(parts[2][:2])
            lat_min = float(parts[2][2:])
            latitude = lat_deg + (lat_min / 60.0)
            if parts[3] == 'S':
                latitude = -latitude
            
            # Convert longitude
            lon_deg = float(parts[4][:3])
            lon_min = float(parts[4][3:])
            longitude = lon_deg + (lon_min / 60.0)
            if parts[5] == 'W':
                longitude = -longitude
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'latitude': latitude,
                'longitude': longitude,
                'altitude': float(parts[9]) if parts[9] else None,
                'satellites': int(parts[7]) if parts[7] else None,
                'hdop': float(parts[8]) if parts[8] else None,
                'fix_quality': int(parts[6]) if parts[6] else 0
            }
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPGGA parse error: {e}")
            return None
    
    def parse_gprmc(self, parts):
        """Parse GPRMC NMEA sentence"""
        try:
            if len(parts) < 12 or not parts[3] or not parts[5] or parts[2] != 'A':
                return None
            
            # Convert latitude
            lat_deg = float(parts[3][:2])
            lat_min = float(parts[3][2:])
            latitude = lat_deg + (lat_min / 60.0)
            if parts[4] == 'S':
                latitude = -latitude
            
            # Convert longitude
            lon_deg = float(parts[5][:3])
            lon_min = float(parts[5][3:])
            longitude = lon_deg + (lon_min / 60.0)
            if parts[6] == 'W':
                longitude = -longitude
            
            # Speed in knots to km/h
            speed = float(parts[7]) * 1.852 if parts[7] else None
            
            # Track angle (heading)
            heading = float(parts[8]) if parts[8] else None
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'latitude': latitude,
                'longitude': longitude,
                'speed': speed,
                'heading': heading
            }
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPRMC parse error: {e}")
            return None
    
    def calculate_movement_metrics(self, current_pos):
        """Calculate speed and heading from position changes"""
        if not self.last_position:
            self.last_position = current_pos
            return current_pos
        
        # Calculate distance using Haversine formula
        distance = self.haversine_distance(
            self.last_position['latitude'],
            self.last_position['longitude'],
            current_pos['latitude'],
            current_pos['longitude']
        )
        
        # Calculate time difference
        try:
            last_time = datetime.fromisoformat(self.last_position['timestamp'])
            curr_time = datetime.fromisoformat(current_pos['timestamp'])
            time_diff = (curr_time - last_time).total_seconds()
            
            if time_diff > 0:
                # Calculate speed (km/h)
                if 'speed' not in current_pos or current_pos['speed'] is None:
                    current_pos['speed'] = (distance / time_diff) * 3600
                
                # Calculate heading
                if 'heading' not in current_pos or current_pos['heading'] is None:
                    current_pos['heading'] = self.calculate_bearing(
                        self.last_position['latitude'],
                        self.last_position['longitude'],
                        current_pos['latitude'],
                        current_pos['longitude']
                    )
        except Exception as e:
            self.logger.debug(f"Movement calculation error: {e}")
        
        self.last_position = current_pos
        return current_pos
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula (in km)"""
        R = 6371  # Earth radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two points"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        x = sin(dlon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        
        bearing = atan2(x, y)
        bearing = degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def check_geofence(self, latitude, longitude):
        """Check if position is inside geofence and log events"""
        if not self.geofence or not GEOFENCE_AVAILABLE:
            return
        
        try:
            point = Point(longitude, latitude)
            is_inside = self.geofence.contains(point)
            
            # Detect boundary crossing
            if self.inside_geofence is not None and self.inside_geofence != is_inside:
                event_type = "ENTRY" if is_inside else "EXIT"
                self.log_geofence_event(event_type, latitude, longitude)
                self.send_notification(event_type, latitude, longitude)
            
            self.inside_geofence = is_inside
            
        except Exception as e:
            self.logger.error(f"Geofence check error: {e}")
    
    def log_geofence_event(self, event_type, latitude, longitude):
        """Log geofence crossing event to database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO geofence_events (timestamp, event_type, latitude, longitude)
                VALUES (?, ?, ?, ?)
            ''', (datetime.utcnow().isoformat(), event_type, latitude, longitude))
            self.db_conn.commit()
            
            self.logger.info(f"Geofence {event_type} at ({latitude}, {longitude})")
            
        except Exception as e:
            self.logger.error(f"Error logging geofence event: {e}")
    
    def send_notification(self, event_type, latitude, longitude):
        """Send push notification for geofence event"""
        notification_url = self.config.get('notification_url')
        if not notification_url:
            return
        
        try:
            message = f"Geofence {event_type}: Location ({latitude:.6f}, {longitude:.6f})"
            
            requests.post(
                notification_url,
                data=message.encode('utf-8'),
                headers={'Title': f'GPS Alert - Geofence {event_type}'},
                timeout=5
            )
            
            self.logger.info(f"Notification sent: {message}")
            
        except Exception as e:
            self.logger.error(f"Notification error: {e}")
    
    def save_gps_data(self, gps_data):
        """Save GPS data to database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO gps_data 
                (timestamp, latitude, longitude, altitude, speed, heading, 
                 satellites, hdop, fix_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                gps_data['timestamp'],
                gps_data['latitude'],
                gps_data['longitude'],
                gps_data.get('altitude'),
                gps_data.get('speed'),
                gps_data.get('heading'),
                gps_data.get('satellites'),
                gps_data.get('hdop'),
                gps_data.get('fix_quality', 0)
            ))
            self.db_conn.commit()
            
        except Exception as e:
            self.logger.error(f"Database save error: {e}")
    
    def run(self):
        """Main GPS logging loop"""
        self.logger.info("Starting GPS logger...")
        
        if not self.connect_gps():
            self.logger.error("Failed to connect to GPS. Exiting.")
            return
        
        record_count = 0
        
        try:
            while True:
                try:
                    # Read NMEA sentence
                    line = self.serial_conn.readline().decode('ascii', errors='ignore')
                    
                    if not line:
                        continue
                    
                    # Parse GPS data
                    gps_data = self.parse_nmea_sentence(line)
                    
                    if gps_data:
                        # Calculate movement metrics
                        gps_data = self.calculate_movement_metrics(gps_data)
                        
                        # Save to database
                        self.save_gps_data(gps_data)
                        
                        # Check geofence
                        self.check_geofence(gps_data['latitude'], gps_data['longitude'])
                        
                        record_count += 1
                        
                        if record_count % 60 == 0:  # Log every 60 records
                            self.logger.info(
                                f"Logged {record_count} records. "
                                f"Current: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f} "
                                f"Speed: {gps_data.get('speed', 0):.1f} km/h"
                            )
                
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    self.logger.error(f"Loop error: {e}")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("Shutting down GPS logger...")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.serial_conn:
            self.serial_conn.close()
        if self.db_conn:
            self.db_conn.close()
        self.logger.info("GPS logger stopped")


if __name__ == '__main__':
    logger = GPSLogger()
    logger.run()
