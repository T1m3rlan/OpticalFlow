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
from camera_interface import CameraInterface
from joystick_input import JoystickInput
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
        self.camera_interface = CameraInterface(config)
        self.previous_frame = None
        self.previous_points = None
        self.control_mode = config.CONTROL_MODE  # 'auto', 'manual', 'poshold'
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
        
        # Joystick input
        self.joystick = JoystickInput(config)
        
        # Position tracking
        self.current_position = np.array([config.CAMERA_CENTER_X, config.CAMERA_CENTER_Y])
        self.target_position = np.array([config.CAMERA_CENTER_X, config.CAMERA_CENTER_Y])
        self.running = False
        
        # Manual input tracking
        self.manual_input_x = 0.0
        self.manual_input_y = 0.0
        
        # Position hold state
        self.poshold_target = None
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = None
        self.fps = 0.0
        
    def initialize_camera(self) -> bool:
        """Initialize camera capture"""
        return self.camera_interface.initialize()
    
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
        if self.control_mode == 'manual':
            # Manual mode: direct stick input
            stick_x, stick_y = self.joystick.read_stick_values()
            output_x = stick_x * self.config.MAX_CONTROL_OUTPUT
            output_y = stick_y * self.config.MAX_CONTROL_OUTPUT
            return output_x, output_y
        
        elif self.control_mode == 'poshold':
            # Position hold: use stick input to set target, then PID to maintain
            stick_x, stick_y = self.joystick.read_stick_values()
            
            # Update target position based on stick input
            if self.poshold_target is None:
                self.poshold_target = self.current_position.copy()
            
            # Scale stick input to position offset
            max_offset = 50.0  # Maximum offset from center
            self.poshold_target[0] += stick_x * max_offset * 0.1
            self.poshold_target[1] += stick_y * max_offset * 0.1
            
            # Clamp target position
            self.poshold_target[0] = np.clip(
                self.poshold_target[0],
                0,
                self.config.CAMERA_WIDTH
            )
            self.poshold_target[1] = np.clip(
                self.poshold_target[1],
                0,
                self.config.CAMERA_HEIGHT
            )
            
            # Update PID setpoints
            self.pid_x.set_setpoint(self.poshold_target[0])
            self.pid_y.set_setpoint(self.poshold_target[1])
            
            # Compute PID outputs
            output_x = self.pid_x.compute(self.current_position[0])
            output_y = self.pid_y.compute(self.current_position[1])
            
            return output_x, output_y
        
        else:  # auto mode
            # Auto mode: optical flow stabilization
            error_x = self.target_position[0] - self.current_position[0]
            error_y = self.target_position[1] - self.current_position[1]
            
            # Compute PID outputs
            output_x = self.pid_x.compute(self.current_position[0])
            output_y = self.pid_y.compute(self.current_position[1])
            
            return output_x, output_y
    
    def set_control_mode(self, mode: str) -> None:
        """Set control mode"""
        if mode in ['auto', 'manual', 'poshold']:
            self.control_mode = mode
            logger.info(f"Control mode set to: {mode}")
            
            # Reset position hold target when switching modes
            if mode == 'poshold':
                self.poshold_target = None
            elif mode == 'auto':
                self.target_position = np.array([
                    self.config.CAMERA_CENTER_X,
                    self.config.CAMERA_CENTER_Y
                ])
        else:
            logger.warning(f"Invalid control mode: {mode}")
    
    def set_manual_input(self, x: float, y: float) -> None:
        """Set manual input from web interface"""
        self.joystick.set_manual_input(x, y)
        self.manual_input_x = x
        self.manual_input_y = y
    
    def update_config(self, new_config: Config) -> None:
        """Update configuration dynamically"""
        self.config = new_config
        
        # Update PID controllers
        self.pid_x.set_tunings(
            new_config.PID_KP_X,
            new_config.PID_KI_X,
            new_config.PID_KD_X
        )
        self.pid_y.set_tunings(
            new_config.PID_KP_Y,
            new_config.PID_KI_Y,
            new_config.PID_KD_Y
        )
        
        # Update camera if needed
        if self.camera_interface.camera_type != new_config.CAMERA_TYPE:
            self.camera_interface.release()
            self.camera_interface = CameraInterface(new_config)
            if self.running:
                self.camera_interface.initialize()
        
        logger.info("Configuration updated")
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps
    
    def run(self) -> None:
        """Main control loop"""
        if not self.initialize_camera():
            logger.error("Failed to initialize camera. Exiting.")
            return
        
        if not self.hardware.initialize():
            logger.error("Failed to initialize hardware. Exiting.")
            return
        
        # Initialize joystick if in manual or poshold mode
        if self.control_mode in ['manual', 'poshold']:
            if not self.joystick.initialize():
                logger.warning("Joystick initialization failed. Manual control may not work.")
        
        self.running = True
        self.start_time = time.time()
        self.frame_count = 0
        logger.info(f"Starting stabilization controller in {self.control_mode} mode...")
        
        try:
            while self.running:
                # Read frame (only needed for auto mode)
                if self.control_mode == 'auto':
                    ret, frame = self.camera_interface.read()
                    if not ret:
                        logger.warning("Failed to read frame from camera")
                        time.sleep(0.1)
                        continue
                    
                    # Calculate optical flow
                    displacement = self.calculate_optical_flow(frame)
                    
                    if displacement is not None:
                        # Update position
                        self.update_position(displacement)
                else:
                    # In manual/poshold mode, still update position if camera available
                    # but don't require it
                    ret, frame = self.camera_interface.read()
                    if ret:
                        displacement = self.calculate_optical_flow(frame)
                        if displacement is not None:
                            self.update_position(displacement)
                
                # Compute control output based on mode
                output_x, output_y = self.compute_control_output()
                
                # Apply control to hardware
                self.hardware.apply_control(output_x, output_y)
                
                # Update manual input tracking
                if self.control_mode in ['manual', 'poshold']:
                    stick_x, stick_y = self.joystick.read_stick_values()
                    self.manual_input_x = stick_x
                    self.manual_input_y = stick_y
                
                # Logging
                self.frame_count += 1
                if self.frame_count % self.config.LOG_INTERVAL == 0:
                    logger.info(
                        f"Mode: {self.control_mode}, "
                        f"Position: ({self.current_position[0]:.1f}, {self.current_position[1]:.1f}), "
                        f"Output: ({output_x:.2f}, {output_y:.2f})"
                    )
                
                # Performance monitoring
                if self.frame_count % 100 == 0:
                    elapsed = time.time() - self.start_time
                    self.fps = self.frame_count / elapsed if elapsed > 0 else 0.0
                    logger.info(f"FPS: {self.fps:.2f}")
                
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
        
        self.camera_interface.release()
        self.hardware.cleanup()
        self.joystick.cleanup()
        cv2.destroyAllWindows()
        logger.info("Cleanup complete")


def main():
    """Main entry point"""
    config = Config()
    controller = OpticalStabilizationController(config)
    controller.run()


if __name__ == "__main__":
    main()
