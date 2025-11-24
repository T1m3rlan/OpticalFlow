"""
Caddx Infra 256 Optical Flow Sensor Driver
I2C-based infrared optical flow sensor for drone position tracking
"""

import time
import logging
from typing import Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import I2C library
try:
    import smbus2 as smbus
    I2C_AVAILABLE = True
except ImportError:
    try:
        import smbus
        I2C_AVAILABLE = True
    except ImportError:
        I2C_AVAILABLE = False
        logger.warning("smbus/smbus2 not available - Caddx Infra 256 disabled")


class CaddxInfra256:
    """
    Driver for Caddx Infra 256 infrared optical flow sensor
    Uses I2C communication protocol
    """
    
    # I2C address
    DEFAULT_ADDRESS = 0x29
    
    # Register addresses (based on similar sensors)
    REG_PRODUCT_ID = 0x00
    REG_REVISION_ID = 0x01
    REG_MOTION = 0x02
    REG_DELTA_X_L = 0x03
    REG_DELTA_X_H = 0x04
    REG_DELTA_Y_L = 0x05
    REG_DELTA_Y_H = 0x06
    REG_SQUAL = 0x07
    REG_SHUTTER_UPPER = 0x08
    REG_SHUTTER_LOWER = 0x09
    REG_PIX_MAX = 0x0A
    REG_PIX_AVG = 0x0B
    REG_PIX_MIN = 0x0C
    REG_CONFIG = 0x10
    REG_RESOLUTION = 0x11
    REG_POWER_MODE = 0x12
    
    # Expected product ID
    PRODUCT_ID = 0x49  # May vary - to be confirmed
    
    def __init__(self, 
                 bus_number: int = 1,
                 address: int = DEFAULT_ADDRESS,
                 rotation: int = 0):
        """
        Initialize Caddx Infra 256 sensor
        
        Args:
            bus_number: I2C bus number (1 for Raspberry Pi)
            address: I2C address (default 0x29)
            rotation: Sensor rotation in degrees (0, 90, 180, 270)
        """
        if not I2C_AVAILABLE:
            raise RuntimeError("smbus or smbus2 library required for Caddx Infra 256")
        
        self.bus_number = bus_number
        self.address = address
        self.rotation = rotation
        
        # Initialize I2C bus
        self.bus = smbus.SMBus(bus_number)
        
        # Initialize sensor
        self._reset()
        self._init_sensor()
        
        # Verify communication
        try:
            product_id = self._read_register(self.REG_PRODUCT_ID)
            logger.info(f"Caddx Infra 256 detected, Product ID: 0x{product_id:02X}")
        except Exception as e:
            logger.warning(f"Could not verify product ID: {e}")
        
        logger.info("Caddx Infra 256 initialized successfully")
    
    def _read_register(self, register: int) -> int:
        """Read a single byte from register"""
        try:
            value = self.bus.read_byte_data(self.address, register)
            return value
        except Exception as e:
            logger.error(f"Failed to read register 0x{register:02X}: {e}")
            return 0
    
    def _write_register(self, register: int, value: int):
        """Write a single byte to register"""
        try:
            self.bus.write_byte_data(self.address, register, value)
            time.sleep(0.001)  # Small delay after write
        except Exception as e:
            logger.error(f"Failed to write register 0x{register:02X}: {e}")
    
    def _read_word(self, register_low: int) -> int:
        """Read 16-bit word (low byte, then high byte)"""
        try:
            low = self._read_register(register_low)
            high = self._read_register(register_low + 1)
            return (high << 8) | low
        except Exception as e:
            logger.error(f"Failed to read word at 0x{register_low:02X}: {e}")
            return 0
    
    def _reset(self):
        """Perform soft reset of sensor"""
        try:
            # Write reset command (if available)
            self._write_register(self.REG_POWER_MODE, 0x5A)
            time.sleep(0.05)  # Wait for reset
            logger.info("Sensor reset complete")
        except Exception as e:
            logger.warning(f"Reset failed: {e}")
    
    def _init_sensor(self):
        """Initialize sensor with optimal settings"""
        try:
            # Set configuration
            # High resolution mode
            self._write_register(self.REG_RESOLUTION, 0x00)
            
            # Normal power mode
            self._write_register(self.REG_POWER_MODE, 0x00)
            
            # Configuration register (enable motion detection)
            self._write_register(self.REG_CONFIG, 0x01)
            
            time.sleep(0.02)  # Wait for settings to apply
            logger.info("Sensor configuration complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
    
    def get_motion(self) -> Tuple[int, int]:
        """
        Read motion data (delta X and Y) from sensor
        
        Returns:
            Tuple of (delta_x, delta_y) in sensor units
        """
        try:
            # Check if motion data is available
            motion = self._read_register(self.REG_MOTION)
            
            if not (motion & 0x80):
                # No motion detected
                return (0, 0)
            
            # Read delta values (16-bit signed integers)
            delta_x = self._read_word(self.REG_DELTA_X_L)
            delta_y = self._read_word(self.REG_DELTA_Y_L)
            
            # Convert to signed 16-bit
            delta_x = self._to_signed_16bit(delta_x)
            delta_y = self._to_signed_16bit(delta_y)
            
            # Apply rotation correction
            delta_x, delta_y = self._apply_rotation(delta_x, delta_y)
            
            return (delta_x, delta_y)
            
        except Exception as e:
            logger.error(f"Failed to read motion: {e}")
            return (0, 0)
    
    def _to_signed_16bit(self, value: int) -> int:
        """Convert unsigned 16-bit to signed"""
        if value > 32767:
            return value - 65536
        return value
    
    def _apply_rotation(self, x: int, y: int) -> Tuple[int, int]:
        """Apply rotation correction based on sensor orientation"""
        if self.rotation == 0:
            return (x, y)
        elif self.rotation == 90:
            return (y, -x)
        elif self.rotation == 180:
            return (-x, -y)
        elif self.rotation == 270:
            return (-y, x)
        return (x, y)
    
    def get_surface_quality(self) -> int:
        """
        Get surface quality measure (0-255)
        Higher values indicate better surface tracking
        """
        try:
            squal = self._read_register(self.REG_SQUAL)
            return squal
        except Exception as e:
            logger.error(f"Failed to read surface quality: {e}")
            return 0
    
    def get_shutter_value(self) -> int:
        """Get current shutter value (exposure time indicator)"""
        try:
            upper = self._read_register(self.REG_SHUTTER_UPPER)
            lower = self._read_register(self.REG_SHUTTER_LOWER)
            return (upper << 8) | lower
        except Exception as e:
            logger.error(f"Failed to read shutter: {e}")
            return 0
    
    def get_pixel_stats(self) -> Tuple[int, int, int]:
        """
        Get pixel statistics
        
        Returns:
            Tuple of (max, avg, min) pixel values
        """
        try:
            pix_max = self._read_register(self.REG_PIX_MAX)
            pix_avg = self._read_register(self.REG_PIX_AVG)
            pix_min = self._read_register(self.REG_PIX_MIN)
            return (pix_max, pix_avg, pix_min)
        except Exception as e:
            logger.error(f"Failed to read pixel stats: {e}")
            return (0, 0, 0)
    
    def set_resolution(self, high_res: bool = True):
        """
        Set sensor resolution mode
        
        Args:
            high_res: True for high resolution, False for low resolution
        """
        try:
            value = 0x00 if high_res else 0x01
            self._write_register(self.REG_RESOLUTION, value)
            logger.info(f"Resolution set to {'high' if high_res else 'low'}")
        except Exception as e:
            logger.error(f"Failed to set resolution: {e}")
    
    def set_power_mode(self, low_power: bool = False):
        """
        Set power mode
        
        Args:
            low_power: True for low power mode, False for normal
        """
        try:
            value = 0x01 if low_power else 0x00
            self._write_register(self.REG_POWER_MODE, value)
            logger.info(f"Power mode set to {'low' if low_power else 'normal'}")
        except Exception as e:
            logger.error(f"Failed to set power mode: {e}")
    
    def shutdown(self):
        """Put sensor into low power mode and close I2C bus"""
        try:
            self.set_power_mode(low_power=True)
            self.bus.close()
            logger.info("Caddx Infra 256 shutdown")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
    
    def get_diagnostics(self) -> dict:
        """
        Get comprehensive diagnostic information
        
        Returns:
            Dictionary with sensor status
        """
        try:
            product_id = self._read_register(self.REG_PRODUCT_ID)
            revision = self._read_register(self.REG_REVISION_ID)
            squal = self.get_surface_quality()
            shutter = self.get_shutter_value()
            pix_max, pix_avg, pix_min = self.get_pixel_stats()
            
            return {
                'product_id': f"0x{product_id:02X}",
                'revision': f"0x{revision:02X}",
                'surface_quality': squal,
                'shutter': shutter,
                'pixel_max': pix_max,
                'pixel_avg': pix_avg,
                'pixel_min': pix_min
            }
        except Exception as e:
            logger.error(f"Failed to get diagnostics: {e}")
            return {}


def detect_caddx_infra256(bus_number: int = 1) -> Optional[int]:
    """
    Auto-detect Caddx Infra 256 on I2C bus
    
    Args:
        bus_number: I2C bus to scan
    
    Returns:
        I2C address if found, None otherwise
    """
    if not I2C_AVAILABLE:
        return None
    
    # Common I2C addresses to try
    addresses = [0x29, 0x28, 0x2A, 0x30]
    
    try:
        bus = smbus.SMBus(bus_number)
        
        for addr in addresses:
            try:
                # Try to read product ID
                bus.write_byte(addr, 0x00)
                time.sleep(0.01)
                product_id = bus.read_byte(addr)
                
                # If we get a valid response, sensor might be present
                if product_id != 0xFF and product_id != 0x00:
                    logger.info(f"Possible Caddx Infra 256 found at address 0x{addr:02X}")
                    bus.close()
                    return addr
                    
            except:
                continue
        
        bus.close()
        
    except Exception as e:
        logger.error(f"I2C scan failed: {e}")
    
    return None


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    print("Caddx Infra 256 Test")
    print("=" * 50)
    
    # Try to detect sensor
    print("\nScanning for sensor...")
    addr = detect_caddx_infra256()
    
    if addr:
        print(f"Sensor detected at address 0x{addr:02X}")
        
        # Initialize sensor
        sensor = CaddxInfra256(address=addr)
        
        # Get diagnostics
        print("\nDiagnostics:")
        diag = sensor.get_diagnostics()
        for key, value in diag.items():
            print(f"  {key}: {value}")
        
        # Read motion for 5 seconds
        print("\nReading motion (5 seconds):")
        print("Time  | Delta X | Delta Y | Quality")
        print("-" * 45)
        
        start_time = time.time()
        while time.time() - start_time < 5.0:
            dx, dy = sensor.get_motion()
            squal = sensor.get_surface_quality()
            elapsed = time.time() - start_time
            print(f"{elapsed:5.2f} | {dx:7d} | {dy:7d} | {squal:3d}", end='\r')
            time.sleep(0.1)
        
        print("\n\nTest complete!")
        sensor.shutdown()
        
    else:
        print("No sensor detected. Check connections:")
        print("  - I2C enabled (sudo raspi-config)")
        print("  - Sensor connected to I2C pins (SDA/SCL)")
        print("  - Sensor powered (3.3V)")
