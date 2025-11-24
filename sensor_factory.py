"""
Sensor Factory for Betafly Stabilization System
Handles creation of various optical flow sensors (PMW3901, Caddx, Camera-based)
"""

import logging
from typing import Optional

from optical_flow_sensor import PMW3901
from camera_optical_flow import CameraOpticalFlow, AnalogCameraFlow, auto_detect_camera

# Try to import Caddx Infra 256
try:
    from caddx_infra256 import CaddxInfra256
    CADDX_AVAILABLE = True
except ImportError:
    CADDX_AVAILABLE = False

logger = logging.getLogger(__name__)

def create_sensor(config: dict):
    """
    Factory function to create the appropriate sensor based on configuration
    
    Args:
        config: Complete configuration dictionary containing 'sensor' and 'camera' keys
        
    Returns:
        Sensor instance (PMW3901, CaddxInfra256, CameraOpticalFlow, or AnalogCameraFlow)
    """
    sensor_config = config.get('sensor', {})
    camera_type = sensor_config.get('type', 'pmw3901')
    logger.info(f"Initializing sensor: {camera_type}")

    if camera_type == 'pmw3901':
        return PMW3901(
            spi_bus=sensor_config.get('spi_bus', 0),
            spi_device=sensor_config.get('spi_device', 0),
            rotation=sensor_config.get('rotation', 0)
        )
    elif camera_type == 'caddx_infra256':
        if not CADDX_AVAILABLE:
            raise RuntimeError("Caddx Infra 256 support not available. Install smbus2: pip install smbus2")
        
        return CaddxInfra256(
            bus_number=sensor_config.get('i2c_bus', 1),
            address=sensor_config.get('i2c_address', 0x29),
            rotation=sensor_config.get('rotation', 0)
        )
    elif camera_type in ['usb_camera', 'csi_camera', 'opencv_any']:
        camera_config = config.get('camera', {})
        camera_id = camera_config.get('device', 0)
        if camera_id == 'auto':
            camera_id = auto_detect_camera()
            if camera_id is None:
                raise RuntimeError("No camera detected")
        
        sensor = CameraOpticalFlow(
            camera_id=camera_id,
            width=camera_config.get('width', 640),
            height=camera_config.get('height', 480),
            fps=camera_config.get('fps', 30),
            method=camera_config.get('method', 'farneback')
        )
        sensor.start()
        return sensor
    elif camera_type == 'analog_usb':
        camera_config = config.get('camera', {})
        sensor = AnalogCameraFlow(
            device_path=camera_config.get('device', '/dev/video0'),
            width=camera_config.get('width', 720),
            height=camera_config.get('height', 480),
            deinterlace=camera_config.get('deinterlace', True)
        )
        sensor.start()
        return sensor
    else:
        raise ValueError(f"Unknown camera type: {camera_type}")
