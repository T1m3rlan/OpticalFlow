"""PID controllers for the Betafly stabilizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .config import PIDConfig


@dataclass
class PIDState:
    p: float
    i: float
    d: float
    output: float


class PIDController:
    """Lightweight PID implementation with derivative filtering."""

    def __init__(self, config: PIDConfig):
        self.config = config
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_derivative = 0.0
        self._initialized = False

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_derivative = 0.0
        self._initialized = False

    def update(self, error: float, dt: float) -> PIDState:
        if abs(error) < self.config.deadband:
            error = 0.0

        if dt <= 0:
            dt = 1e-3  # avoid div-by-zero when timestamps jitter

        p_term = self.config.kp * error

        self._integral += error * dt * self.config.ki
        self._integral = max(-self.config.integrator_limit, min(self._integral, self.config.integrator_limit))

        derivative = (error - self._prev_error) / dt if self._initialized else 0.0
        # Single pole IIR filter for noisy derivative terms
        alpha = min(1.0, max(0.0, dt * self.config.derivative_filter_hz))
        self._prev_derivative = (1 - alpha) * self._prev_derivative + alpha * derivative
        d_term = self.config.kd * self._prev_derivative

        output = p_term + self._integral + d_term
        output = max(-self.config.output_limit, min(output, self.config.output_limit))

        self._prev_error = error
        self._initialized = True

        return PIDState(p=p_term, i=self._integral, d=d_term, output=output)


class PositionController:
    """Runs two independent PID loops for pan & tilt axes."""

    def __init__(self, pan_config: PIDConfig, tilt_config: PIDConfig):
        self.pan = PIDController(pan_config)
        self.tilt = PIDController(tilt_config)

    def reset(self) -> None:
        self.pan.reset()
        self.tilt.reset()

    def update(self, error_x: float, error_y: float, dt: float) -> Tuple[float, float, Dict[str, PIDState]]:
        pan_state = self.pan.update(error_x, dt)
        tilt_state = self.tilt.update(error_y, dt)
        return pan_state.output, tilt_state.output, {"pan": pan_state, "tilt": tilt_state}
