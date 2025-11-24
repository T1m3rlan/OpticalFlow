"""
General optical-flow-based motion tracking utilities.

This module provides the `OpticalFlowTracker` that integrates motion
measurements from any sensor or camera object exposing `get_motion()` and
`get_surface_quality()` methods. It no longer depends on dedicated SPI/I2C
optical flow sensors so it can work with camera-based optical flow sources.
"""

import time
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class OpticalFlowTracker:
    """
    Higher-level optical flow tracking with position estimation.
    Works with any sensor object that implements `get_motion()` and
    `get_surface_quality()`.
    """

    def __init__(self, sensor, scale_factor: float = 0.001, height_m: float = 0.5):
        """
        Initialize optical flow tracker.

        Args:
            sensor: Optical flow source with `get_motion()` method
            scale_factor: Conversion factor from sensor units to meters
            height_m: Height above ground in meters (affects scale)
        """
        self.sensor = sensor
        self.scale_factor = scale_factor
        self.height_m = height_m

        # Position tracking
        self.pos_x = 0.0
        self.pos_y = 0.0

        # Velocity tracking
        self.vel_x = 0.0
        self.vel_y = 0.0

        self.last_update_time = time.time()

        # Moving average filter for noise reduction
        self.velocity_history_x = []
        self.velocity_history_y = []
        self.filter_window = 5

    def update(self) -> Tuple[float, float]:
        """
        Update position estimate based on optical flow.

        Returns:
            Current estimated position (x, y) in meters
        """
        current_time = time.time()
        dt = current_time - self.last_update_time

        if dt < 0.001:  # Avoid division by zero
            return (self.pos_x, self.pos_y)

        # Get raw motion from sensor
        delta_x, delta_y = self.sensor.get_motion()

        # Convert to velocity (m/s) accounting for height
        # Optical flow scales with height above ground
        scale = self.scale_factor * max(self.height_m, 0.01)
        self.vel_x = (delta_x * scale) / dt
        self.vel_y = (delta_y * scale) / dt

        # Apply moving average filter
        self.velocity_history_x.append(self.vel_x)
        self.velocity_history_y.append(self.vel_y)

        if len(self.velocity_history_x) > self.filter_window:
            self.velocity_history_x.pop(0)
            self.velocity_history_y.pop(0)

        filtered_vel_x = sum(self.velocity_history_x) / len(self.velocity_history_x)
        filtered_vel_y = sum(self.velocity_history_y) / len(self.velocity_history_y)

        # Integrate velocity to get position
        self.pos_x += filtered_vel_x * dt
        self.pos_y += filtered_vel_y * dt

        self.last_update_time = current_time

        return (self.pos_x, self.pos_y)

    def get_velocity(self) -> Tuple[float, float]:
        """Get current velocity estimate in m/s"""
        if not self.velocity_history_x:
            return (0.0, 0.0)

        filtered_vel_x = sum(self.velocity_history_x) / len(self.velocity_history_x)
        filtered_vel_y = sum(self.velocity_history_y) / len(self.velocity_history_y)
        return (filtered_vel_x, filtered_vel_y)

    def reset_position(self):
        """Reset position to origin"""
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.velocity_history_x.clear()
        self.velocity_history_y.clear()
        logger.info("Position reset to origin")

    def set_height(self, height_m: float):
        """Update height above ground for accurate scaling"""
        self.height_m = height_m

    def get_surface_quality(self) -> int:
        """Get surface quality from sensor"""
        if hasattr(self.sensor, "get_surface_quality"):
            return self.sensor.get_surface_quality()
        return 0
