#!/usr/bin/env python3
"""
Optical Position Stabilization Controller for BetaFly
Raspberry Pi Zero implementation using OpenCV for optical flow detection
"""

import cv2
import numpy as np
import time
import logging
from typing import Tuple, Optional
from pid_controller import PIDController
from hardware_interface import HardwareInterface
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpticalStabilizationController:
    """Main controller for optical position stabilization"""
    
    def __init__(self, config: Config):
        self.config = config
        self.camera = None
        self.previous_frame = None
        self.previous_points = None
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Feature detection parameters
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
        
        # PID controllers for X and Y axes
        self.pid_x = PIDController(
            kp=config.PID_KP_X,
            ki=config.PID_KI_X,
            kd=config.PID_KD_X,
            setpoint=config.CAMERA_CENTER_X
        )
        
        self.pid_y = PIDController(
            kp=config.PID_KP_Y,
            ki=config.PID_KI_Y,
            kd=config.PID_KD_Y,
            setpoint=config.CAMERA_CENTER_Y
        )
        
        # Hardware interface
        self.hardware = HardwareInterface(config)
        
        # Position tracking
        self.current_position = np.array([config.CAMERA_CENTER_X, config.CAMERA_CENTER_Y])
        self.target_position = np.array([config.CAMERA_CENTER_X, config.CAMERA_CENTER_Y])
        self.running = False
        
    def initialize_camera(self) -> bool:
        """Initialize camera capture"""
        try:
            self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX)
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera {self.config.CAMERA_INDEX}")
                return False
            
            # Set camera resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.CAMERA_FPS)
            
            logger.info("Camera initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            return False
    
    def detect_features(self, frame: np.ndarray) -> np.ndarray:
        """Detect good features to track"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        points = cv2.goodFeaturesToTrack(
            gray,
            mask=None,
            **self.feature_params
        )
        return points if points is not None else np.array([])
    
    def calculate_optical_flow(self, current_frame: np.ndarray) -> Optional[Tuple[float, float]]:
        """Calculate optical flow and return average displacement"""
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_frame is None:
            self.previous_frame = gray
            self.previous_points = self.detect_features(current_frame)
            return None
        
        # Calculate optical flow
        if self.previous_points is not None and len(self.previous_points) > 0:
            new_points, status, error = cv2.calcOpticalFlowPyrLK(
                self.previous_frame,
                gray,
                self.previous_points,
                None,
                **self.lk_params
            )
            
            # Select good points
            good_new = new_points[status == 1]
            good_old = self.previous_points[status == 1]
            
            if len(good_new) > 0:
                # Calculate displacement
                displacement = good_new - good_old
                avg_displacement = np.mean(displacement, axis=0)
                
                # Update tracking points periodically
                if len(good_new) < self.config.MIN_TRACKING_POINTS:
                    self.previous_points = self.detect_features(current_frame)
                else:
                    self.previous_points = good_new.reshape(-1, 1, 2)
                
                self.previous_frame = gray
                return (avg_displacement[0], avg_displacement[1])
        
        # Re-detect features if tracking fails
        self.previous_points = self.detect_features(current_frame)
        self.previous_frame = gray
        return None
    
    def update_position(self, displacement: Tuple[float, float]) -> None:
        """Update current position based on displacement"""
        dx, dy = displacement
        
        # Update position (inverse of displacement since we want to stabilize)
        self.current_position[0] -= dx * self.config.DISPLACEMENT_SCALE_X
        self.current_position[1] -= dy * self.config.DISPLACEMENT_SCALE_Y
        
        # Clamp position to reasonable bounds
        self.current_position[0] = np.clip(
            self.current_position[0],
            0,
            self.config.CAMERA_WIDTH
        )
        self.current_position[1] = np.clip(
            self.current_position[1],
            0,
            self.config.CAMERA_HEIGHT
        )
    
    def compute_control_output(self) -> Tuple[float, float]:
        """Compute PID control output for stabilization"""
        error_x = self.target_position[0] - self.current_position[0]
        error_y = self.target_position[1] - self.current_position[1]
        
        # Compute PID outputs
        output_x = self.pid_x.compute(self.current_position[0])
        output_y = self.pid_y.compute(self.current_position[1])
        
        return output_x, output_y
    
    def run(self) -> None:
        """Main control loop"""
        if not self.initialize_camera():
            logger.error("Failed to initialize camera. Exiting.")
            return
        
        if not self.hardware.initialize():
            logger.error("Failed to initialize hardware. Exiting.")
            return
        
        self.running = True
        logger.info("Starting stabilization controller...")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Calculate optical flow
                displacement = self.calculate_optical_flow(frame)
                
                if displacement is not None:
                    # Update position
                    self.update_position(displacement)
                    
                    # Compute control output
                    output_x, output_y = self.compute_control_output()
                    
                    # Apply control to hardware
                    self.hardware.apply_control(output_x, output_y)
                    
                    # Logging
                    if frame_count % self.config.LOG_INTERVAL == 0:
                        logger.info(
                            f"Position: ({self.current_position[0]:.1f}, {self.current_position[1]:.1f}), "
                            f"Output: ({output_x:.2f}, {output_y:.2f})"
                        )
                
                # Performance monitoring
                frame_count += 1
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    logger.info(f"FPS: {fps:.2f}")
                
                # Control loop timing
                time.sleep(1.0 / self.config.CONTROL_FREQUENCY)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in control loop: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up...")
        self.running = False
        
        if self.camera is not None:
            self.camera.release()
        
        self.hardware.cleanup()
        cv2.destroyAllWindows()
        logger.info("Cleanup complete")


def main():
    """Main entry point"""
    config = Config()
    controller = OpticalStabilizationController(config)
    controller.run()


if __name__ == "__main__":
    main()
