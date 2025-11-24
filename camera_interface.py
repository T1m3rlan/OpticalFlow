#!/usr/bin/env python3
"""
Camera Interface for different camera types
Supports USB, Analog (v4l2), and Raspberry Pi cameras
"""

import cv2
import logging
import subprocess
import os
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

try:
    import picamera
    import picamera.array
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logger.warning("picamera not available. Raspberry Pi camera support disabled.")


class CameraInterface:
    """Unified camera interface supporting multiple camera types"""
    
    def __init__(self, config: Config):
        self.config = config
        self.camera = None
        self.camera_type = config.CAMERA_TYPE.lower()
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize camera based on type"""
        try:
            if self.camera_type == 'raspberry':
                return self._init_raspberry_camera()
            elif self.camera_type == 'analog':
                return self._init_analog_camera()
            else:  # USB or default
                return self._init_usb_camera()
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            return False
    
    def _init_usb_camera(self) -> bool:
        """Initialize USB camera"""
        try:
            self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX)
            if not self.camera.isOpened():
                logger.error(f"Failed to open USB camera {self.config.CAMERA_INDEX}")
                return False
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.CAMERA_FPS)
            
            logger.info(f"USB camera {self.config.CAMERA_INDEX} initialized")
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing USB camera: {e}")
            return False
    
    def _init_analog_camera(self) -> bool:
        """Initialize analog camera using v4l2"""
        try:
            # Check if v4l2-ctl is available
            try:
                subprocess.run(['v4l2-ctl', '--version'], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("v4l2-ctl not found. Trying standard OpenCV capture.")
            
            # Try to set v4l2 device properties
            device_path = f'/dev/video{self.config.CAMERA_INDEX}'
            if os.path.exists(device_path):
                try:
                    # Set v4l2 format and resolution
                    subprocess.run([
                        'v4l2-ctl',
                        f'--device={device_path}',
                        '--set-fmt-video=width={},height={},pixelformat=YUYV'.format(
                            self.config.CAMERA_WIDTH,
                            self.config.CAMERA_HEIGHT
                        )
                    ], capture_output=True, check=False)
                except Exception as e:
                    logger.debug(f"Could not set v4l2 properties: {e}")
            
            # Open camera with v4l2 backend
            self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX, cv2.CAP_V4L2)
            
            if not self.camera.isOpened():
                logger.warning("v4l2 backend failed, trying default backend")
                self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX)
            
            if not self.camera.isOpened():
                logger.error(f"Failed to open analog camera {self.config.CAMERA_INDEX}")
                return False
            
            # Set properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.CAMERA_FPS)
            
            # For analog cameras, try to set additional properties
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
            
            logger.info(f"Analog camera {self.config.CAMERA_INDEX} initialized")
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing analog camera: {e}")
            return False
    
    def _init_raspberry_camera(self) -> bool:
        """Initialize Raspberry Pi camera"""
        if not PICAMERA_AVAILABLE:
            logger.error("picamera library not available")
            return False
        
        try:
            # Note: picamera2 is the newer library, but picamera still works
            # For now, we'll use OpenCV which can work with raspicam
            # For full picamera support, would need picamera2
            self.camera = cv2.VideoCapture(0)
            
            # Try to use gstreamer backend for Raspberry Pi camera
            gstreamer_pipeline = (
                f"libcamerasrc ! "
                f"video/x-raw,width={self.config.CAMERA_WIDTH},height={self.config.CAMERA_HEIGHT},framerate={self.config.CAMERA_FPS}/1 ! "
                f"videoconvert ! "
                f"appsink"
            )
            
            try:
                self.camera = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
                if not self.camera.isOpened():
                    # Fallback to standard capture
                    self.camera = cv2.VideoCapture(0)
            except Exception:
                self.camera = cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                logger.error("Failed to open Raspberry Pi camera")
                return False
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.CAMERA_FPS)
            
            logger.info("Raspberry Pi camera initialized")
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing Raspberry Pi camera: {e}")
            return False
    
    def read(self) -> tuple[bool, Optional]:
        """Read frame from camera"""
        if not self.initialized or self.camera is None:
            return False, None
        
        ret, frame = self.camera.read()
        return ret, frame
    
    def release(self) -> None:
        """Release camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        self.initialized = False
    
    def is_opened(self) -> bool:
        """Check if camera is opened"""
        return self.initialized and self.camera is not None and self.camera.isOpened()
