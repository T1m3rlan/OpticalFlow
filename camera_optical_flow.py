"""
Camera-based Optical Flow for Analog and Digital Cameras
Supports USB cameras, CSI cameras, and analog cameras via capture cards
"""

import cv2
import numpy as np
import time
import logging
from typing import Tuple, Optional
from threading import Thread, Lock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraOpticalFlow:
    """
    Optical flow calculation using camera input
    Supports various camera types including analog cameras
    """
    
    def __init__(self, 
                 camera_id: int = 0,
                 width: int = 640,
                 height: int = 480,
                 fps: int = 30,
                 method: str = 'farneback'):
        """
        Initialize camera-based optical flow
        
        Args:
            camera_id: Camera device ID or path (0 for /dev/video0)
            width: Frame width
            height: Frame height
            fps: Target frame rate
            method: Optical flow method ('farneback' or 'lucas_kanade')
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.method = method
        
        # Camera capture
        self.cap = None
        self.frame_lock = Lock()
        self.current_frame = None
        self.prev_gray = None
        
        # Optical flow parameters
        self.flow_x = 0.0
        self.flow_y = 0.0
        
        # Feature tracking for Lucas-Kanade
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
        
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        self.prev_points = None
        
        # Running flag
        self.running = False
        self.capture_thread = None
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open camera {self.camera_id}")
            
            # Set camera parameters
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Read actual values
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Capture first frame
            ret, frame = self.cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                with self.frame_lock:
                    self.prev_gray = gray
                    self.current_frame = frame
            
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            raise
    
    def start(self):
        """Start capture thread"""
        if not self.running:
            self.running = True
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info("Camera capture started")
    
    def stop(self):
        """Stop capture thread"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info("Camera capture stopped")
    
    def _capture_loop(self):
        """Continuous capture loop"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.current_frame = frame
            else:
                logger.warning("Failed to capture frame")
                time.sleep(0.1)
    
    def get_motion(self) -> Tuple[float, float]:
        """
        Calculate optical flow and return motion
        
        Returns:
            Tuple of (delta_x, delta_y) motion values
        """
        with self.frame_lock:
            if self.current_frame is None or self.prev_gray is None:
                return (0.0, 0.0)
            
            frame = self.current_frame.copy()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.method == 'farneback':
            flow_x, flow_y = self._calculate_farneback_flow(gray)
        else:
            flow_x, flow_y = self._calculate_lucas_kanade_flow(gray)
        
        with self.frame_lock:
            self.prev_gray = gray
        
        self.flow_x = flow_x
        self.flow_y = flow_y
        
        return (flow_x, flow_y)
    
    def _calculate_farneback_flow(self, gray: np.ndarray) -> Tuple[float, float]:
        """
        Calculate optical flow using Farneback method (dense flow)
        """
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        # Calculate average flow in center region (ignore edges)
        h, w = gray.shape
        center_h = slice(h//4, 3*h//4)
        center_w = slice(w//4, 3*w//4)
        
        flow_center = flow[center_h, center_w]
        
        # Average flow
        flow_x = np.mean(flow_center[:, :, 0])
        flow_y = np.mean(flow_center[:, :, 1])
        
        # Scale to match PMW3901 output range
        scale = 50.0
        flow_x *= scale
        flow_y *= scale
        
        return (flow_x, flow_y)
    
    def _calculate_lucas_kanade_flow(self, gray: np.ndarray) -> Tuple[float, float]:
        """
        Calculate optical flow using Lucas-Kanade method (sparse flow)
        """
        # Find features to track if needed
        if self.prev_points is None or len(self.prev_points) < 10:
            self.prev_points = cv2.goodFeaturesToTrack(
                self.prev_gray,
                mask=None,
                **self.feature_params
            )
        
        if self.prev_points is None:
            return (0.0, 0.0)
        
        # Calculate optical flow
        next_points, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray,
            gray,
            self.prev_points,
            None,
            **self.lk_params
        )
        
        if next_points is None:
            self.prev_points = None
            return (0.0, 0.0)
        
        # Select good points
        good_new = next_points[status == 1]
        good_old = self.prev_points[status == 1]
        
        if len(good_new) < 5:
            self.prev_points = None
            return (0.0, 0.0)
        
        # Calculate average motion
        motion = good_new - good_old
        flow_x = np.mean(motion[:, 0])
        flow_y = np.mean(motion[:, 1])
        
        # Update points for next iteration
        self.prev_points = good_new.reshape(-1, 1, 2)
        
        # Scale to match PMW3901 output range
        scale = 10.0
        flow_x *= scale
        flow_y *= scale
        
        return (flow_x, flow_y)
    
    def get_surface_quality(self) -> int:
        """
        Estimate surface quality based on feature detectability
        Returns value 0-255 (similar to PMW3901)
        """
        with self.frame_lock:
            if self.current_frame is None:
                return 0
            frame = self.current_frame.copy()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate image sharpness using Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # Calculate number of features
        corners = cv2.goodFeaturesToTrack(
            gray,
            mask=None,
            **self.feature_params
        )
        
        num_features = len(corners) if corners is not None else 0
        
        # Combine metrics to get quality (0-255)
        quality = min(255, int(variance * 2 + num_features * 2))
        
        return quality
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current camera frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None


class AnalogCameraFlow:
    """
    Wrapper specifically for analog cameras via USB capture cards
    Includes additional processing for analog video artifacts
    """
    
    def __init__(self,
                 device_path: str = '/dev/video0',
                 width: int = 720,
                 height: int = 480,
                 deinterlace: bool = True):
        """
        Initialize analog camera optical flow
        
        Args:
            device_path: Path to video device
            width: Frame width (720 for standard analog)
            height: Frame height (480 for NTSC, 576 for PAL)
            deinterlace: Apply deinterlacing filter
        """
        self.device_path = device_path
        self.deinterlace = deinterlace
        
        # Convert device path to camera ID if needed
        camera_id = device_path if device_path.startswith('/dev/') else int(device_path)
        
        # Initialize base optical flow
        self.optical_flow = CameraOpticalFlow(
            camera_id=camera_id,
            width=width,
            height=height,
            fps=30,
            method='farneback'  # Farneback works better for analog video
        )
        
        logger.info(f"Analog camera initialized: {device_path}")
    
    def start(self):
        """Start capture"""
        self.optical_flow.start()
    
    def stop(self):
        """Stop capture"""
        self.optical_flow.stop()
    
    def get_motion(self) -> Tuple[float, float]:
        """Get motion with analog video preprocessing"""
        # Get frame
        frame = self.optical_flow.get_current_frame()
        if frame is None:
            return (0.0, 0.0)
        
        # Apply deinterlacing if needed
        if self.deinterlace:
            frame = self._deinterlace(frame)
            
            # Update frame in optical flow processor
            with self.optical_flow.frame_lock:
                self.optical_flow.current_frame = frame
        
        # Calculate motion
        return self.optical_flow.get_motion()
    
    def _deinterlace(self, frame: np.ndarray) -> np.ndarray:
        """
        Simple deinterlacing filter
        Blends adjacent lines to reduce interlacing artifacts
        """
        # Simple line averaging deinterlace
        deinterlaced = frame.copy()
        deinterlaced[1::2] = (frame[0:-1:2].astype(np.float32) + 
                              frame[2::2].astype(np.float32)) / 2
        return deinterlaced.astype(np.uint8)
    
    def get_surface_quality(self) -> int:
        """Get surface quality"""
        return self.optical_flow.get_surface_quality()


def auto_detect_camera() -> Optional[int]:
    """
    Auto-detect available camera
    Returns camera ID or None
    """
    for camera_id in range(5):
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    logger.info(f"Camera detected at ID {camera_id}")
                    return camera_id
        except:
            pass
    
    return None
