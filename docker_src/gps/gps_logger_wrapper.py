#!/usr/bin/env python3
import os, sys, time, logging, signal, glob, subprocess

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'),
                   format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class GPSLoggerWrapper:
    def __init__(self):
        self.auto_detect = os.getenv('GPS_AUTO_DETECT', 'false').lower() == 'true'
        self.vendor_id = os.getenv('GPS_VENDOR_ID', '067b')
        self.product_id = os.getenv('GPS_PRODUCT_ID', '23a3')
        self.gps_device = None
        self.running = True
        self.gps_process = None
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        signal.signal(signal.SIGINT, self.shutdown_handler)
    
    def shutdown_handler(self, signum, frame):
        logger.info(f"Shutting down gracefully...")
        self.running = False
        if self.gps_process:
            self.gps_process.terminate()
            try:
                self.gps_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.gps_process.kill()
        sys.exit(0)
    
    def find_gps_device(self):
        """Auto-detect GPS device by vendor/product ID"""
        if not self.auto_detect:
            device = os.getenv('GPS_DEVICE', '/dev/ttyUSB0')
            if os.path.exists(device):
                return device
            return None
        
        logger.info(f"🔍 Auto-detecting GPS device (Vendor: {self.vendor_id}, Product: {self.product_id})")
        
        # Method 1: Check by-id symlinks
        by_id_path = f"/dev/serial/by-id/*{self.vendor_id}*"
        matches = glob.glob(by_id_path)
        if matches:
            device = matches[0]
            logger.info(f"✅ Found GPS via by-id: {device}")
            return device
        
        # Method 2: Scan all ttyUSB devices
        for port in glob.glob('/dev/ttyUSB*'):
            try:
                result = subprocess.run(
                    ['udevadm', 'info', port],
                    capture_output=True, text=True, timeout=2
                )
                if self.vendor_id.lower() in result.stdout.lower():
                    logger.info(f"✅ Found GPS via udevadm scan: {port}")
                    return port
            except Exception:
                continue
        
        # Method 3: Fallback to /dev/ttyUSB0
        if os.path.exists('/dev/ttyUSB0'):
            logger.info(f"⚠️  Using fallback GPS device: /dev/ttyUSB0")
            return '/dev/ttyUSB0'
        
        return None
    
    def device_exists(self):
        if not self.gps_device:
            return False
        return os.path.exists(self.gps_device) and os.access(self.gps_device, os.R_OK | os.W_OK)
    
    def wait_for_device(self, timeout=30):
        logger.info("=" * 60)
        logger.info("GPS Logger Wrapper Starting (Resilient Mode)")
        logger.info("=" * 60)
        
        for attempt in range(timeout):
            if not self.running:
                return False
            
            self.gps_device = self.find_gps_device()
            
            if self.gps_device and self.device_exists():
                time.sleep(1)
                logger.info(f"✅ GPS device ready: {self.gps_device} (after {attempt+1}s)")
                os.environ['GPS_DEVICE'] = self.gps_device
                return True
            
            time.sleep(1)
        
        return False
    
    def idle_mode(self):
        logger.warning("⚠️  GPS device not available - entering idle mode")
        logger.info("Will check every 60 seconds for device...")
        check_interval = 60
        
        while self.running:
            time.sleep(check_interval)
            self.gps_device = self.find_gps_device()
            if self.gps_device and self.device_exists():
                logger.info("🎉 GPS device detected! Starting logger...")
                os.environ['GPS_DEVICE'] = self.gps_device
                return True
        return False
    
    def run_gps_logger(self):
        try:
            logger.info(f"🚀 Starting GPS data collection on {self.gps_device}...")
            
            # Set environment for subprocess
            env = os.environ.copy()
            env['GPS_DEVICE'] = self.gps_device
            
            # Run gps_logger.py as subprocess
            self.gps_process = subprocess.Popen(
                [sys.executable, '-u', '/app/gps_logger.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )
            
            # Forward output from gps_logger
            for line in self.gps_process.stdout:
                print(line, end='', flush=True)
            
            self.gps_process.wait()
            return_code = self.gps_process.returncode
            
            if return_code != 0:
                logger.error(f"❌ GPS logger exited with code {return_code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ GPS logger crashed: {e}")
            return False
    
    def run(self):
        while self.running:
            if not self.wait_for_device(timeout=600):
                if not self.idle_mode():
                    break
            else:
                if not self.run_gps_logger():
                    logger.warning("GPS logger stopped, will retry in 10s...")
                    time.sleep(10)

if __name__ == "__main__":
    wrapper = GPSLoggerWrapper()
    wrapper.run()
