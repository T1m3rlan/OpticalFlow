"""Lightweight PID controller."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIDGains:
    kp: float
    ki: float
    kd: float
    i_clamp: float
    output_limit: float


class PIDController:
    def __init__(self, gains: PIDGains):
        self.gains = gains
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False

    def update(self, error: float, dt: float) -> float:
        if dt <= 0:
            dt = 1e-3
        p_term = self.gains.kp * error
        self._integral += error * dt * self.gains.ki
        self._integral = max(min(self._integral, self.gains.i_clamp), -self.gains.i_clamp)
        i_term = self._integral

        if not self._initialized:
            d_term = 0.0
            self._initialized = True
        else:
            derivative = (error - self._prev_error) / dt
            d_term = self.gains.kd * derivative

        self._prev_error = error
        output = p_term + i_term + d_term
        return max(min(output, self.gains.output_limit), -self.gains.output_limit)


__all__ = ["PIDController", "PIDGains"]
