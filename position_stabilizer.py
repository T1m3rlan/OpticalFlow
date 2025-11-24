"""
Position Stabilization Controller for Betafly
Uses PID control to maintain position using optical flow feedback
"""

import time
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PIDGains:
    """PID controller gains"""
    kp: float  # Proportional gain
    ki: float  # Integral gain
    kd: float  # Derivative gain


class PIDController:
    """
    PID controller for single axis control
    """
    
    def __init__(self, gains: PIDGains, output_limits: Tuple[float, float] = (-1.0, 1.0)):
        """
        Initialize PID controller
        
        Args:
            gains: PID gains (kp, ki, kd)
            output_limits: Min and max output values
        """
        self.kp = gains.kp
        self.ki = gains.ki
        self.kd = gains.kd
        
        self.output_min, self.output_max = output_limits
        
        # State variables
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None
        
        # Anti-windup limits
        self.integral_limit = 1.0
    
    def update(self, setpoint: float, measured: float, current_time: Optional[float] = None) -> float:
        """
        Update PID controller and compute output
        
        Args:
            setpoint: Desired value
            measured: Current measured value
            current_time: Current time (if None, uses time.time())
        
        Returns:
            Control output
        """
        if current_time is None:
            current_time = time.time()
        
        # Calculate error
        error = setpoint - measured
        
        # Initialize on first call
        if self.prev_time is None:
            self.prev_time = current_time
            self.prev_error = error
            return 0.0
        
        # Calculate time delta
        dt = current_time - self.prev_time
        if dt <= 0:
            return 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term with anti-windup
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        
        # Compute output
        output = p_term + i_term + d_term
        
        # Apply output limits
        output = max(self.output_min, min(self.output_max, output))
        
        # Update state
        self.prev_error = error
        self.prev_time = current_time
        
        return output
    
    def reset(self):
        """Reset controller state"""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None


class PositionStabilizer:
    """
    Position stabilization controller using optical flow
    Controls X and Y position independently using PID controllers
    """
    
    def __init__(self, 
                 x_gains: PIDGains = PIDGains(kp=0.5, ki=0.1, kd=0.2),
                 y_gains: PIDGains = PIDGains(kp=0.5, ki=0.1, kd=0.2),
                 max_tilt_angle: float = 15.0):
        """
        Initialize position stabilizer
        
        Args:
            x_gains: PID gains for X axis
            y_gains: PID gains for Y axis
            max_tilt_angle: Maximum tilt angle in degrees
        """
        self.pid_x = PIDController(x_gains, output_limits=(-max_tilt_angle, max_tilt_angle))
        self.pid_y = PIDController(y_gains, output_limits=(-max_tilt_angle, max_tilt_angle))
        
        # Target position
        self.target_x = 0.0
        self.target_y = 0.0
        
        # Enable/disable flags
        self.enabled = False
        
        # Position tolerance (meters)
        self.position_tolerance = 0.05  # 5cm
        
        logger.info("Position stabilizer initialized")
    
    def set_target_position(self, x: float, y: float):
        """
        Set target position to maintain
        
        Args:
            x: Target X position in meters
            y: Target Y position in meters
        """
        self.target_x = x
        self.target_y = y
        logger.info(f"Target position set to: ({x:.3f}, {y:.3f})")
    
    def enable(self):
        """Enable position stabilization"""
        self.enabled = True
        self.pid_x.reset()
        self.pid_y.reset()
        logger.info("Position stabilization enabled")
    
    def disable(self):
        """Disable position stabilization"""
        self.enabled = False
        logger.info("Position stabilization disabled")
    
    def update(self, current_x: float, current_y: float) -> Tuple[float, float]:
        """
        Update stabilization controller
        
        Args:
            current_x: Current X position in meters
            current_y: Current Y position in meters
        
        Returns:
            Tuple of (pitch_correction, roll_correction) in degrees
            Pitch controls Y movement, Roll controls X movement
        """
        if not self.enabled:
            return (0.0, 0.0)
        
        current_time = time.time()
        
        # Calculate control outputs
        # Roll correction for X position (positive roll moves right)
        roll_correction = self.pid_x.update(self.target_x, current_x, current_time)
        
        # Pitch correction for Y position (positive pitch moves forward)
        pitch_correction = self.pid_y.update(self.target_y, current_y, current_time)
        
        return (pitch_correction, roll_correction)
    
    def is_position_locked(self, current_x: float, current_y: float) -> bool:
        """
        Check if current position is within tolerance of target
        
        Args:
            current_x: Current X position in meters
            current_y: Current Y position in meters
        
        Returns:
            True if position is locked within tolerance
        """
        dx = abs(self.target_x - current_x)
        dy = abs(self.target_y - current_y)
        
        return dx < self.position_tolerance and dy < self.position_tolerance
    
    def get_position_error(self, current_x: float, current_y: float) -> Tuple[float, float]:
        """
        Get position error from target
        
        Returns:
            Tuple of (error_x, error_y) in meters
        """
        return (self.target_x - current_x, self.target_y - current_y)
    
    def reset(self):
        """Reset stabilizer to initial state"""
        self.pid_x.reset()
        self.pid_y.reset()
        self.target_x = 0.0
        self.target_y = 0.0
        logger.info("Position stabilizer reset")


class VelocityDamper:
    """
    Velocity damping controller to reduce drift and oscillations
    """
    
    def __init__(self, damping_factor: float = 0.3, max_correction: float = 10.0):
        """
        Initialize velocity damper
        
        Args:
            damping_factor: How aggressively to damp velocity (0-1)
            max_correction: Maximum correction angle in degrees
        """
        self.damping_factor = damping_factor
        self.max_correction = max_correction
    
    def compute_damping(self, vel_x: float, vel_y: float) -> Tuple[float, float]:
        """
        Compute damping corrections based on current velocity
        
        Args:
            vel_x: Current X velocity in m/s
            vel_y: Current Y velocity in m/s
        
        Returns:
            Tuple of (pitch_damping, roll_damping) in degrees
        """
        # Damping opposes velocity
        roll_damping = -vel_x * self.damping_factor
        pitch_damping = -vel_y * self.damping_factor
        
        # Limit corrections
        roll_damping = max(-self.max_correction, min(self.max_correction, roll_damping))
        pitch_damping = max(-self.max_correction, min(self.max_correction, pitch_damping))
        
        return (pitch_damping, roll_damping)


class StabilizationController:
    """
    Combined stabilization controller with position hold and velocity damping
    """
    
    def __init__(self,
                 position_gains_x: PIDGains = PIDGains(kp=0.5, ki=0.1, kd=0.2),
                 position_gains_y: PIDGains = PIDGains(kp=0.5, ki=0.1, kd=0.2),
                 velocity_damping: float = 0.3,
                 max_tilt: float = 15.0):
        """
        Initialize combined stabilization controller
        
        Args:
            position_gains_x: PID gains for X position control
            position_gains_y: PID gains for Y position control
            velocity_damping: Velocity damping factor
            max_tilt: Maximum tilt angle in degrees
        """
        self.position_stabilizer = PositionStabilizer(
            position_gains_x, position_gains_y, max_tilt
        )
        self.velocity_damper = VelocityDamper(velocity_damping, max_tilt)
        
        # Mode selection
        self.mode = "off"  # "off", "velocity_damping", "position_hold"
        
        logger.info("Stabilization controller initialized")
    
    def set_mode(self, mode: str):
        """
        Set stabilization mode
        
        Args:
            mode: "off", "velocity_damping", or "position_hold"
        """
        if mode not in ["off", "velocity_damping", "position_hold"]:
            logger.error(f"Invalid mode: {mode}")
            return
        
        self.mode = mode
        
        if mode == "position_hold":
            self.position_stabilizer.enable()
        else:
            self.position_stabilizer.disable()
        
        logger.info(f"Stabilization mode set to: {mode}")
    
    def update(self, 
               current_x: float, current_y: float,
               vel_x: float, vel_y: float) -> Tuple[float, float]:
        """
        Update stabilization controller
        
        Args:
            current_x: Current X position in meters
            current_y: Current Y position in meters
            vel_x: Current X velocity in m/s
            vel_y: Current Y velocity in m/s
        
        Returns:
            Tuple of (pitch_correction, roll_correction) in degrees
        """
        if self.mode == "off":
            return (0.0, 0.0)
        
        pitch_correction = 0.0
        roll_correction = 0.0
        
        # Apply velocity damping
        if self.mode in ["velocity_damping", "position_hold"]:
            pitch_damp, roll_damp = self.velocity_damper.compute_damping(vel_x, vel_y)
            pitch_correction += pitch_damp
            roll_correction += roll_damp
        
        # Apply position hold
        if self.mode == "position_hold":
            pitch_pos, roll_pos = self.position_stabilizer.update(current_x, current_y)
            pitch_correction += pitch_pos
            roll_correction += roll_pos
        
        return (pitch_correction, roll_correction)
    
    def hold_current_position(self, current_x: float, current_y: float):
        """
        Set target to current position and enable position hold
        
        Args:
            current_x: Current X position
            current_y: Current Y position
        """
        self.position_stabilizer.set_target_position(current_x, current_y)
        self.set_mode("position_hold")
        logger.info(f"Holding position at ({current_x:.3f}, {current_y:.3f})")
