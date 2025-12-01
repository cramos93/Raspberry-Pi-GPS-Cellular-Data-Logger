#!/usr/bin/env python3
"""
GPS Data Logger - Complete Implementation
Logs GPS data with full metadata including position, motion analytics, and satellite info
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
    """Complete GPS logging with motion analytics and geofencing"""
    
    def __init__(self, config=None):
        """Initialize GPS logger"""
        self.config = config or self.load_config()
        self.setup_logging()
        self.db_path = self.config.get('database_path', '/app/data/gps_data.db')
        self.gps_device = self.config.get('gps_device', '/dev/ttyUSB0')
        self.gps_baud = self.config.get('gps_baud_rate', 4800)
        
        # State tracking
        self.serial_conn = None
        self.db_conn = None
        self.geofence = None
        self.geofence_states = {}  # Track state for each geofence region
        self.last_position = None
        self.total_distance = 0.0
        
        # GPS data accumulator for merging NMEA sentences
        self.current_gps_data = {}
        self.last_merge_time = None
        
        self.setup_database()
        
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
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'merge_timeout': float(os.getenv('GPS_MERGE_TIMEOUT', '2.0')),
            # Enhanced features
            'geof_debounce_count': int(os.getenv('GEOF_DEBOUNCE_COUNT', '3')),
            'geof_min_move_m': float(os.getenv('GEOF_MIN_MOVE_M', '5.0')),
            'speed_smooth_alpha': float(os.getenv('SPEED_SMOOTH_ALPHA', '0.3'))
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        
        # Create logs directory if it doesn't exist
        log_dir = Path('/app/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
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
        """Initialize SQLite database with comprehensive GPS tracking tables"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            
            # Main GPS data table with all metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gps_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    utc_time TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    speed REAL,
                    heading REAL,
                    climb_rate REAL,
                    satellites_used INTEGER,
                    satellites_visible INTEGER,
                    hdop REAL,
                    vdop REAL,
                    pdop REAL,
                    fix_quality INTEGER,
                    fix_type TEXT,
                    mode TEXT,
                    distance_traveled REAL,
                    total_distance REAL,
                    magnetic_variation REAL,
                    geoid_height REAL,
                    dgps_age REAL,
                    dgps_station_id TEXT
                )
            ''')
            
            # Satellite information table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS satellite_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gps_data_id INTEGER,
                    timestamp TEXT NOT NULL,
                    satellite_prn INTEGER,
                    elevation INTEGER,
                    azimuth INTEGER,
                    snr INTEGER,
                    used_in_fix INTEGER,
                    FOREIGN KEY (gps_data_id) REFERENCES gps_data(id)
                )
            ''')
            
            # Geofence events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geofence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed REAL,
                    heading REAL
                )
            ''')
            
            # Trip summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trip_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_distance REAL,
                    max_speed REAL,
                    avg_speed REAL,
                    duration_seconds INTEGER,
                    start_lat REAL,
                    start_lon REAL,
                    end_lat REAL,
                    end_lon REAL
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gps_timestamp ON gps_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gps_location ON gps_data(latitude, longitude)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_satellite_timestamp ON satellite_info(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_geofence_timestamp ON geofence_events(timestamp)')
            
            self.db_conn.commit()
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Database setup error: {e}")
            raise
    
    def load_geofence(self):
        """Load geofence boundaries from GeoJSON file (supports multiple polygons)"""
        if not GEOFENCE_AVAILABLE:
            self.logger.warning("Geofence features not available")
            return
        
        geofence_file = self.config.get('geofence_file')
        if not geofence_file or not os.path.exists(geofence_file):
            self.logger.info(f"No geofence file found at {geofence_file}")
            return
        
        try:
            with open(geofence_file, 'r') as f:
                geojson_data = geojson.load(f)
            
            # Handle FeatureCollection (multiple counties)
            if geojson_data['type'] == 'FeatureCollection':
                # Store list of geofences with names
                self.geofence = []
                for feature in geojson_data['features']:
                    geom = shape(feature['geometry'])
                    name = feature.get('properties', {}).get('name', 'Unknown')
                    county = feature.get('properties', {}).get('county', 'Unknown')
                    self.geofence.append({
                        'name': name,
                        'county': county,
                        'geometry': geom
                    })
                self.logger.info(f"Loaded {len(self.geofence)} geofence regions from {geofence_file}")
                for fence in self.geofence:
                    self.logger.info(f"  - {fence['name']}")
            
            # Handle single Feature
            elif geojson_data['type'] == 'Feature':
                geom = shape(geojson_data['geometry'])
                name = geojson_data.get('properties', {}).get('name', 'Geofence')
                self.geofence = [{'name': name, 'county': name, 'geometry': geom}]
                self.logger.info(f"Geofence loaded: {name}")
            
            # Handle raw geometry
            else:
                geom = shape(geojson_data)
                self.geofence = [{'name': 'Geofence', 'county': 'Geofence', 'geometry': geom}]
                self.logger.info(f"Geofence loaded from {geofence_file}")
            
            # Initialize tracking for each geofence
            self.geofence_states = {fence['county']: None for fence in self.geofence}
            
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
            self.logger.info(f"Connected to GPS at {self.gps_device} @ {self.gps_baud} baud")
            return True
        except Exception as e:
            self.logger.error(f"GPS connection error: {e}")
            return False
    
    def parse_nmea_sentence(self, sentence):
        """Parse NMEA sentences and accumulate GPS data"""
        try:
            if not sentence.startswith('$'):
                return None
            
            # Calculate checksum if present
            if '*' in sentence:
                msg, checksum = sentence.split('*')
                calc_checksum = 0
                for char in msg[1:]:  # Skip the $
                    calc_checksum ^= ord(char)
                if int(checksum.strip(), 16) != calc_checksum:
                    self.logger.debug(f"Checksum failed for: {sentence}")
                    return None
            
            parts = sentence.strip().split(',')
            sentence_type = parts[0]
            
            # Parse different NMEA sentence types
            if sentence_type in ['$GPGGA', '$GNGGA']:
                self.parse_gpgga(parts)
            elif sentence_type in ['$GPRMC', '$GNRMC']:
                self.parse_gprmc(parts)
            elif sentence_type in ['$GPGSA', '$GNGSA']:
                self.parse_gpgsa(parts)
            elif sentence_type in ['$GPGSV', '$GNGSV']:
                self.parse_gpgsv(parts)
            elif sentence_type in ['$GPVTG', '$GNVTG']:
                self.parse_gpvtg(parts)
            elif sentence_type in ['$GPGLL', '$GNGLL']:
                self.parse_gpgll(parts)
            
            # Check if we should merge and save accumulated data
            return self.check_and_merge_data()
            
        except Exception as e:
            self.logger.debug(f"Error parsing NMEA: {e}")
        
        return None
    
    def parse_gpgga(self, parts):
        """Parse GPGGA - Global Positioning System Fix Data"""
        try:
            if len(parts) < 15:
                return
            
            # UTC Time
            if parts[1]:
                utc_time = parts[1]
                self.current_gps_data['utc_time'] = f"{utc_time[:2]}:{utc_time[2:4]}:{utc_time[4:]}"
            
            # Position
            if parts[2] and parts[4]:
                lat_deg = float(parts[2][:2])
                lat_min = float(parts[2][2:])
                latitude = lat_deg + (lat_min / 60.0)
                if parts[3] == 'S':
                    latitude = -latitude
                
                lon_deg = float(parts[4][:3])
                lon_min = float(parts[4][3:])
                longitude = lon_deg + (lon_min / 60.0)
                if parts[5] == 'W':
                    longitude = -longitude
                
                self.current_gps_data['latitude'] = latitude
                self.current_gps_data['longitude'] = longitude
            
            # Fix quality
            if parts[6]:
                self.current_gps_data['fix_quality'] = int(parts[6])
            
            # Satellites
            if parts[7]:
                self.current_gps_data['satellites_used'] = int(parts[7])
            
            # HDOP
            if parts[8]:
                self.current_gps_data['hdop'] = float(parts[8])
            
            # Altitude
            if parts[9]:
                self.current_gps_data['altitude'] = float(parts[9])
            
            # Geoid height
            if parts[11]:
                self.current_gps_data['geoid_height'] = float(parts[11])
            
            # DGPS data
            if len(parts) > 13 and parts[13]:
                self.current_gps_data['dgps_age'] = float(parts[13])
            if len(parts) > 14 and parts[14]:
                dgps_id = parts[14].split('*')[0]  # Remove checksum
                self.current_gps_data['dgps_station_id'] = dgps_id
                
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPGGA parse error: {e}")
    
    def parse_gprmc(self, parts):
        """Parse GPRMC - Recommended Minimum Specific GPS/Transit Data"""
        try:
            if len(parts) < 12:
                return
            
            # Check status
            if parts[2] != 'A':  # A = Active, V = Void
                return
            
            # UTC Time
            if parts[1]:
                utc_time = parts[1]
                self.current_gps_data['utc_time'] = f"{utc_time[:2]}:{utc_time[2:4]}:{utc_time[4:]}"
            
            # Position
            if parts[3] and parts[5]:
                lat_deg = float(parts[3][:2])
                lat_min = float(parts[3][2:])
                latitude = lat_deg + (lat_min / 60.0)
                if parts[4] == 'S':
                    latitude = -latitude
                
                lon_deg = float(parts[5][:3])
                lon_min = float(parts[5][3:])
                longitude = lon_deg + (lon_min / 60.0)
                if parts[6] == 'W':
                    longitude = -longitude
                
                self.current_gps_data['latitude'] = latitude
                self.current_gps_data['longitude'] = longitude
            
            # Speed (knots to km/h)
            if parts[7]:
                self.current_gps_data['speed'] = float(parts[7]) * 1.852
            
            # Track angle (heading)
            if parts[8]:
                self.current_gps_data['heading'] = float(parts[8])
            
            # Magnetic variation
            if len(parts) > 10 and parts[10]:
                mag_var = float(parts[10])
                if len(parts) > 11 and parts[11] and 'W' in parts[11]:
                    mag_var = -mag_var
                self.current_gps_data['magnetic_variation'] = mag_var
                
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPRMC parse error: {e}")
    
    def parse_gpgsa(self, parts):
        """Parse GPGSA - GPS DOP and Active Satellites"""
        try:
            if len(parts) < 18:
                return
            
            # Mode (M=Manual, A=Automatic)
            if parts[1]:
                self.current_gps_data['mode'] = parts[1]
            
            # Fix type (1=No fix, 2=2D, 3=3D)
            if parts[2]:
                fix_type = int(parts[2])
                self.current_gps_data['fix_type'] = ['No Fix', 'No Fix', '2D', '3D'][fix_type] if fix_type <= 3 else 'Unknown'
            
            # PDOP, HDOP, VDOP
            if parts[15]:
                self.current_gps_data['pdop'] = float(parts[15])
            if parts[16]:
                self.current_gps_data['hdop'] = float(parts[16])
            if parts[17]:
                vdop = parts[17].split('*')[0]  # Remove checksum
                self.current_gps_data['vdop'] = float(vdop)
                
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPGSA parse error: {e}")
    
    def parse_gpgsv(self, parts):
        """Parse GPGSV - GPS Satellites in View"""
        try:
            if len(parts) < 4:
                return
            
            # Total number of satellites in view
            if parts[3]:
                self.current_gps_data['satellites_visible'] = int(parts[3])
            
            # Store satellite details (we could parse individual satellite data here)
            # This would require tracking multiple GPGSV messages
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPGSV parse error: {e}")
    
    def parse_gpvtg(self, parts):
        """Parse GPVTG - Track Made Good and Ground Speed"""
        try:
            if len(parts) < 10:
                return
            
            # True track
            if parts[1]:
                self.current_gps_data['heading'] = float(parts[1])
            
            # Speed in km/h
            if parts[7]:
                self.current_gps_data['speed'] = float(parts[7])
                
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPVTG parse error: {e}")
    
    def parse_gpgll(self, parts):
        """Parse GPGLL - Geographic Position"""
        try:
            if len(parts) < 8:
                return
            
            # Check status
            if parts[6] != 'A':  # A = Active, V = Void
                return
            
            # Position
            if parts[1] and parts[3]:
                lat_deg = float(parts[1][:2])
                lat_min = float(parts[1][2:])
                latitude = lat_deg + (lat_min / 60.0)
                if parts[2] == 'S':
                    latitude = -latitude
                
                lon_deg = float(parts[3][:3])
                lon_min = float(parts[3][3:])
                longitude = lon_deg + (lon_min / 60.0)
                if parts[4] == 'W':
                    longitude = -longitude
                
                self.current_gps_data['latitude'] = latitude
                self.current_gps_data['longitude'] = longitude
            
            # UTC Time
            if parts[5]:
                utc_time = parts[5]
                self.current_gps_data['utc_time'] = f"{utc_time[:2]}:{utc_time[2:4]}:{utc_time[4:]}"
                
        except (ValueError, IndexError) as e:
            self.logger.debug(f"GPGLL parse error: {e}")
    
    def check_and_merge_data(self):
        """Check if enough time has passed and merge accumulated GPS data"""
        current_time = time.time()
        
        # If we have position data and enough time has passed, merge and return
        if 'latitude' in self.current_gps_data and 'longitude' in self.current_gps_data:
            if self.last_merge_time is None or (current_time - self.last_merge_time) >= self.config['merge_timeout']:
                merged_data = self.current_gps_data.copy()
                merged_data['timestamp'] = datetime.utcnow().isoformat()
                
                self.current_gps_data = {}
                self.last_merge_time = current_time
                
                return merged_data
        
        return None
    
    def calculate_movement_metrics(self, current_pos):
        """Calculate speed, heading, and distance from position changes"""
        if not self.last_position:
            self.last_position = current_pos
            current_pos['distance_traveled'] = 0.0
            current_pos['total_distance'] = self.total_distance
            return current_pos
        
        # Calculate distance using Haversine formula
        distance = self.haversine_distance(
            self.last_position['latitude'],
            self.last_position['longitude'],
            current_pos['latitude'],
            current_pos['longitude']
        )
        
        current_pos['distance_traveled'] = distance
        self.total_distance += distance
        current_pos['total_distance'] = self.total_distance
        
        # Calculate time difference
        try:
            last_time = datetime.fromisoformat(self.last_position['timestamp'])
            curr_time = datetime.fromisoformat(current_pos['timestamp'])
            time_diff = (curr_time - last_time).total_seconds()
            
            if time_diff > 0:
                # Calculate speed if not already provided (km/h)
                if 'speed' not in current_pos or current_pos.get('speed') is None:
                    current_pos['speed'] = (distance / time_diff) * 3600
                
                # Calculate heading if not already provided
                if 'heading' not in current_pos or current_pos.get('heading') is None:
                    current_pos['heading'] = self.calculate_bearing(
                        self.last_position['latitude'],
                        self.last_position['longitude'],
                        current_pos['latitude'],
                        current_pos['longitude']
                    )
                
                # Calculate climb rate if altitude is available
                if 'altitude' in current_pos and 'altitude' in self.last_position:
                    if current_pos['altitude'] and self.last_position['altitude']:
                        alt_diff = current_pos['altitude'] - self.last_position['altitude']
                        current_pos['climb_rate'] = alt_diff / time_diff  # m/s
                        
        except Exception as e:
            self.logger.debug(f"Movement calculation error: {e}")
        
        self.last_position = current_pos
        return current_pos
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula (km)"""
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
    
    def check_geofence(self, latitude, longitude, gps_data):
        """Check if position is inside safe zone and alert on boundary violations"""
        if not self.geofence or not GEOFENCE_AVAILABLE:
            return
        
        try:
            point = Point(longitude, latitude)
            
            # Define safe zone counties
            SAFE_ZONE = ['YOUR_CITY', 'Fauquier', 'Prince William', 'YOUR_CITY']
            
            # Check if currently in safe zone
            in_safe_zone = False
            current_county = None
            
            for fence in self.geofence:
                if fence['geometry'].contains(point):
                    current_county = fence['county']
                    if current_county in SAFE_ZONE:
                        in_safe_zone = True
                    break
            
            # Initialize safe zone tracking on first run
            if 'safe_zone_status' not in self.geofence_states:
                self.geofence_states['safe_zone_status'] = in_safe_zone
                if in_safe_zone:
                    self.geofence_states['last_safe_county'] = current_county
                return
            
            # Get previous safe zone status
            previous_safe_status = self.geofence_states.get('safe_zone_status', True)
            
            # Detect boundary violation (exiting safe zone)
            if previous_safe_status and not in_safe_zone:
                # BOUNDARY VIOLATION - LEFT SAFE ZONE
                last_safe_county = self.geofence_states.get('last_safe_county', 'Unknown')
                
                # Send boundary violation alert
                self.send_boundary_violation_alert(
                    gps_data=gps_data,
                    last_safe_county=last_safe_county,
                    current_location=current_county or 'Outside tracked area'
                )
                
                # Log to database
                self.log_geofence_event('BOUNDARY_VIOLATION', gps_data, last_safe_county)
                
                self.logger.warning(f"🚨 BOUNDARY VIOLATION: Exited {last_safe_county} County")
            
            # Detect re-entry to safe zone (optional logging)
            elif not previous_safe_status and in_safe_zone:
                self.logger.info(f"✅ Re-entered safe zone: {current_county} County")
                self.log_geofence_event('SAFE_ZONE_REENTRY', gps_data, current_county)
            
            # Update state
            self.geofence_states['safe_zone_status'] = in_safe_zone
            if in_safe_zone and current_county:
                self.geofence_states['last_safe_county'] = current_county
            
            # Debug logging
            if in_safe_zone:
                self.logger.debug(f"In safe zone: {current_county} County")
            else:
                location = current_county if current_county else "Outside tracked area"
                self.logger.debug(f"Outside safe zone: {location}")
            
        except Exception as e:
            self.logger.error(f"Geofence check error: {e}")
    
    def send_boundary_violation_alert(self, gps_data, last_safe_county, current_location):
        """Send boundary violation notification via ntfy.sh"""
        notification_url = self.config.get('notification_url')
        if not notification_url:
            self.logger.warning("No notification URL configured")
            return
        
        try:
            from datetime import datetime
            
            # Convert speed from knots to mph
            speed_knots = gps_data.get('speed', 0) or 0
            speed_mph = speed_knots * 1.15078
            
            # Format time
            utc_time = gps_data.get('utc_time', 'N/A')
            if utc_time != 'N/A':
                try:
                    time_obj = datetime.strptime(str(utc_time), '%H:%M:%S.%f')
                    time_str = time_obj.strftime('%I:%M %p')
                except:
                    time_str = str(utc_time)
            else:
                time_str = datetime.now().strftime('%I:%M %p')
            
            # Build notification message
            message = (
                f"🚨 BOUNDARY VIOLATION\n"
                f"Exited: {last_safe_county} County\n"
                f"Location: {gps_data['latitude']:.4f}°N, {abs(gps_data['longitude']):.4f}°W\n"
                f"Time: {time_str}\n"
                f"Speed: {speed_mph:.0f} mph"
            )
            
            # Send to ntfy.sh
            response = requests.post(
                notification_url,
                data=message.encode('utf-8'),
                headers={
                    'Title': '🚨 BOUNDARY VIOLATION',
                    'Priority': 'default',
                    'Tags': 'warning,geo'
                }
            )
            
            if response.status_code == 200:
                self.logger.info(f"Boundary violation alert sent successfully")
            else:
                self.logger.error(f"Failed to send alert: HTTP {response.status_code}")
            
        except Exception as e:
            self.logger.error(f"Failed to send boundary violation alert: {e}")
    
    def send_notification(self, event_type, gps_data, region_name=None):
        """Send push notification for geofence event"""
        notification_url = self.config.get('notification_url')
        if not notification_url:
            return
        
        try:
            location_name = f" {region_name}" if region_name else ""
            title = f"GPS Alert - {event_type}{location_name}"
            
            message = (f"Geofence {event_type}\n"
                      f"Region: {region_name or 'Unknown'}\n"
                      f"Location: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}\n"
                      f"Speed: {gps_data.get('speed', 0):.1f} km/h\n"
                      f"Heading: {gps_data.get('heading', 0):.1f}°\n"
                      f"Time: {gps_data.get('utc_time', 'N/A')}")
            
            requests.post(
                notification_url,
                data=message.encode('utf-8'),
                headers={
                    'Title': title,
                    'Priority': '4' if event_type == 'EXIT' else '3',
                    'Tags': 'warning' if event_type == 'EXIT' else 'white_check_mark'
                },
                timeout=5
            )
            
            self.logger.info(f"Notification sent: {event_type}{location_name}")
            
        except Exception as e:
            self.logger.error(f"Notification error: {e}")
    
    def save_gps_data(self, gps_data):
        """Save complete GPS data to database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO gps_data 
                (timestamp, utc_time, latitude, longitude, altitude, speed, heading,
                 climb_rate, satellites_used, satellites_visible, hdop, vdop, pdop,
                 fix_quality, fix_type, mode, distance_traveled, total_distance,
                 magnetic_variation, geoid_height, dgps_age, dgps_station_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                gps_data.get('timestamp'),
                gps_data.get('utc_time'),
                gps_data['latitude'],
                gps_data['longitude'],
                gps_data.get('altitude'),
                gps_data.get('speed'),
                gps_data.get('heading'),
                gps_data.get('climb_rate'),
                gps_data.get('satellites_used'),
                gps_data.get('satellites_visible'),
                gps_data.get('hdop'),
                gps_data.get('vdop'),
                gps_data.get('pdop'),
                gps_data.get('fix_quality', 0),
                gps_data.get('fix_type'),
                gps_data.get('mode'),
                gps_data.get('distance_traveled'),
                gps_data.get('total_distance'),
                gps_data.get('magnetic_variation'),
                gps_data.get('geoid_height'),
                gps_data.get('dgps_age'),
                gps_data.get('dgps_station_id')
            ))
            self.db_conn.commit()
            
        except Exception as e:
            self.logger.error(f"Database save error: {e}")
    
    def run(self):
        """Main GPS logging loop"""
        self.logger.info("Starting GPS Data Logger...")
        self.logger.info(f"GPS Device: {self.gps_device} @ {self.gps_baud} baud")
        self.logger.info(f"Database: {self.db_path}")
        
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
                    
                    # Parse GPS data (accumulates from multiple NMEA sentences)
                    gps_data = self.parse_nmea_sentence(line)
                    
                    if gps_data:
                        # Calculate movement metrics
                        gps_data = self.calculate_movement_metrics(gps_data)
                        
                        # Save to database
                        self.save_gps_data(gps_data)
                        
                        # Check geofence
                        self.check_geofence(gps_data['latitude'], gps_data['longitude'], gps_data)
                        
                        record_count += 1
                        
                        if record_count % 20 == 0:  # Log every 20 records
                            self.logger.info(
                                f"Record #{record_count} | "
                                f"Pos: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f} | "
                                f"Speed: {gps_data.get('speed', 0):.1f} km/h | "
                                f"Heading: {gps_data.get('heading', 0):.1f}° | "
                                f"Sats: {gps_data.get('satellites_used', 0)} | "
                                f"Fix: {gps_data.get('fix_type', 'Unknown')} | "
                                f"HDOP: {gps_data.get('hdop', 0):.1f} | "
                                f"Distance: {gps_data.get('total_distance', 0):.2f} km"
                            )
                
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    self.logger.error(f"Loop error: {e}", exc_info=True)
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