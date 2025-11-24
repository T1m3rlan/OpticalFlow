#!/usr/bin/env python3
"""
PID Calibration Tool
Interactive tool to tune PID parameters
"""

import cv2
import numpy as np
import time
import logging
from pid_controller import PIDController
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PIDCalibrator:
    """Interactive PID calibration tool"""
    
    def __init__(self):
        self.config = Config()
        self.pid_x = PIDController(
            kp=self.config.PID_KP_X,
            ki=self.config.PID_KI_X,
            kd=self.config.PID_KD_X,
            setpoint=self.config.CAMERA_CENTER_X
        )
        self.pid_y = PIDController(
            kp=self.config.PID_KP_Y,
            ki=self.config.PID_KI_Y,
            kd=self.config.PID_KD_Y,
            setpoint=self.config.CAMERA_CENTER_Y
        )
        
        self.current_kp_x = self.config.PID_KP_X
        self.current_ki_x = self.config.PID_KI_X
        self.current_kd_x = self.config.PID_KD_X
        self.current_kp_y = self.config.PID_KP_Y
        self.current_ki_y = self.config.PID_KI_Y
        self.current_kd_y = self.config.PID_KD_Y
        
        self.camera = None
        self.previous_frame = None
        self.previous_points = None
        
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
        
        self.current_position = np.array([self.config.CAMERA_CENTER_X, self.config.CAMERA_CENTER_Y])
        self.target_position = np.array([self.config.CAMERA_CENTER_X, self.config.CAMERA_CENTER_Y])
        
    def initialize_camera(self):
        """Initialize camera"""
        self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX)
        if not self.camera.isOpened():
            logger.error("Failed to open camera")
            return False
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
        return True
    
    def calculate_optical_flow(self, current_frame):
        """Calculate optical flow"""
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_frame is None:
            self.previous_frame = gray
            self.previous_points = cv2.goodFeaturesToTrack(
                gray, mask=None, **self.feature_params
            )
            return None
        
        if self.previous_points is not None and len(self.previous_points) > 0:
            new_points, status, error = cv2.calcOpticalFlowPyrLK(
                self.previous_frame, gray, self.previous_points, None, **self.lk_params
            )
            
            good_new = new_points[status == 1]
            good_old = self.previous_points[status == 1]
            
            if len(good_new) > 0:
                displacement = good_new - good_old
                avg_displacement = np.mean(displacement, axis=0)
                
                if len(good_new) < self.config.MIN_TRACKING_POINTS:
                    self.previous_points = cv2.goodFeaturesToTrack(
                        gray, mask=None, **self.feature_params
                    )
                else:
                    self.previous_points = good_new.reshape(-1, 1, 2)
                
                self.previous_frame = gray
                return (avg_displacement[0], avg_displacement[1])
        
        self.previous_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
        self.previous_frame = gray
        return None
    
    def update_position(self, displacement):
        """Update position"""
        dx, dy = displacement
        self.current_position[0] -= dx * self.config.DISPLACEMENT_SCALE_X
        self.current_position[1] -= dy * self.config.DISPLACEMENT_SCALE_Y
        
        self.current_position[0] = np.clip(self.current_position[0], 0, self.config.CAMERA_WIDTH)
        self.current_position[1] = np.clip(self.current_position[1], 0, self.config.CAMERA_HEIGHT)
    
    def print_controls(self):
        """Print control instructions"""
        print("\n" + "=" * 60)
        print("PID Calibration Controls")
        print("=" * 60)
        print("X-axis controls:")
        print("  Q/A: Increase/Decrease KP_X")
        print("  W/S: Increase/Decrease KI_X")
        print("  E/D: Increase/Decrease KD_X")
        print("\nY-axis controls:")
        print("  R/F: Increase/Decrease KP_Y")
        print("  T/G: Increase/Decrease KI_Y")
        print("  Y/H: Increase/Decrease KD_Y")
        print("\nOther:")
        print("  Space: Reset PID values")
        print("  P: Print current values")
        print("  Esc/Q: Exit")
        print("=" * 60 + "\n")
    
    def run(self):
        """Run calibration tool"""
        if not self.initialize_camera():
            return
        
        self.print_controls()
        
        step_size = 0.1
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    continue
                
                # Calculate optical flow
                displacement = self.calculate_optical_flow(frame)
                
                if displacement is not None:
                    self.update_position(displacement)
                    
                    # Compute PID outputs
                    output_x = self.pid_x.compute(self.current_position[0])
                    output_y = self.pid_y.compute(self.current_position[1])
                    
                    # Draw visualization
                    cv2.circle(frame, 
                             (int(self.current_position[0]), int(self.current_position[1])),
                             10, (0, 255, 0), -1)
                    cv2.circle(frame,
                             (int(self.target_position[0]), int(self.target_position[1])),
                             10, (0, 0, 255), 2)
                    
                    # Display info
                    info_text = [
                        f"Position: ({self.current_position[0]:.1f}, {self.current_position[1]:.1f})",
                        f"Output: ({output_x:.2f}, {output_y:.2f})",
                        f"KP_X: {self.current_kp_x:.3f}  KI_X: {self.current_ki_x:.3f}  KD_X: {self.current_kd_x:.3f}",
                        f"KP_Y: {self.current_kp_y:.3f}  KI_Y: {self.current_ki_y:.3f}  KD_Y: {self.current_kd_y:.3f}"
                    ]
                    
                    y_offset = 30
                    for text in info_text:
                        cv2.putText(frame, text, (10, y_offset),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        y_offset += 25
                
                cv2.imshow('PID Calibration', frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    self.current_kp_x += step_size
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('a'):
                    self.current_kp_x = max(0, self.current_kp_x - step_size)
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('w'):
                    self.current_ki_x += step_size
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('s'):
                    self.current_ki_x = max(0, self.current_ki_x - step_size)
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('e'):
                    self.current_kd_x += step_size
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('d'):
                    self.current_kd_x = max(0, self.current_kd_x - step_size)
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                elif key == ord('r'):
                    self.current_kp_y += step_size
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord('f'):
                    self.current_kp_y = max(0, self.current_kp_y - step_size)
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord('t'):
                    self.current_ki_y += step_size
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord('g'):
                    self.current_ki_y = max(0, self.current_ki_y - step_size)
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord('y'):
                    self.current_kd_y += step_size
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord('h'):
                    self.current_kd_y = max(0, self.current_kd_y - step_size)
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                elif key == ord(' '):
                    # Reset
                    self.current_kp_x = self.config.PID_KP_X
                    self.current_ki_x = self.config.PID_KI_X
                    self.current_kd_x = self.config.PID_KD_X
                    self.current_kp_y = self.config.PID_KP_Y
                    self.current_ki_y = self.config.PID_KI_Y
                    self.current_kd_y = self.config.PID_KD_Y
                    self.pid_x.set_tunings(self.current_kp_x, self.current_ki_x, self.current_kd_x)
                    self.pid_y.set_tunings(self.current_kp_y, self.current_ki_y, self.current_kd_y)
                    self.pid_x.reset()
                    self.pid_y.reset()
                    print("PID values reset")
                elif key == ord('p'):
                    print("\nCurrent PID values:")
                    print(f"  KP_X: {self.current_kp_x:.3f}, KI_X: {self.current_ki_x:.3f}, KD_X: {self.current_kd_x:.3f}")
                    print(f"  KP_Y: {self.current_kp_y:.3f}, KI_Y: {self.current_ki_y:.3f}, KD_Y: {self.current_kd_y:.3f}")
                elif key == 27:  # ESC
                    break
                
                time.sleep(1.0 / self.config.CONTROL_FREQUENCY)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.camera.release()
            cv2.destroyAllWindows()
            
            print("\nFinal PID values:")
            print(f"PID_KP_X = {self.current_kp_x:.3f}")
            print(f"PID_KI_X = {self.current_ki_x:.3f}")
            print(f"PID_KD_X = {self.current_kd_x:.3f}")
            print(f"PID_KP_Y = {self.current_kp_y:.3f}")
            print(f"PID_KI_Y = {self.current_ki_y:.3f}")
            print(f"PID_KD_Y = {self.current_kd_y:.3f}")


if __name__ == "__main__":
    calibrator = PIDCalibrator()
    calibrator.run()
