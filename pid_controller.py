#!/usr/bin/env python3
"""
PID Controller for position stabilization
"""

import time
from typing import Optional


class PIDController:
    """Proportional-Integral-Derivative controller"""
    
    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        setpoint: float = 0.0,
        output_limits: Optional[tuple] = None
    ):
        """
        Initialize PID controller
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            setpoint: Target value
            output_limits: Tuple of (min, max) output limits
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        # Internal state
        self._integral = 0.0
        self._previous_error = 0.0
        self._previous_time = None
        
    def compute(self, process_value: float) -> float:
        """
        Compute PID output
        
        Args:
            process_value: Current process value
            
        Returns:
            Control output
        """
        current_time = time.time()
        
        # Calculate error
        error = self.setpoint - process_value
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        if self._previous_time is not None:
            dt = current_time - self._previous_time
            if dt > 0:
                self._integral += error * dt
                # Anti-windup: limit integral term
                if self.output_limits is not None:
                    max_integral = (self.output_limits[1] - p_term) / (self.ki if self.ki != 0 else 1)
                    min_integral = (self.output_limits[0] - p_term) / (self.ki if self.ki != 0 else 1)
                    self._integral = max(min_integral, min(max_integral, self._integral))
        
        i_term = self.ki * self._integral
        
        # Derivative term
        d_term = 0.0
        if self._previous_time is not None:
            dt = current_time - self._previous_time
            if dt > 0:
                d_term = self.kd * (error - self._previous_error) / dt
        
        # Compute output
        output = p_term + i_term + d_term
        
        # Apply output limits
        if self.output_limits is not None:
            output = max(self.output_limits[0], min(self.output_limits[1], output))
        
        # Update state
        self._previous_error = error
        self._previous_time = current_time
        
        return output
    
    def reset(self) -> None:
        """Reset controller state"""
        self._integral = 0.0
        self._previous_error = 0.0
        self._previous_time = None
    
    def set_setpoint(self, setpoint: float) -> None:
        """Update setpoint"""
        self.setpoint = setpoint
    
    def set_tunings(self, kp: float, ki: float, kd: float) -> None:
        """Update PID tunings"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
