"""GPIO servo drivers used by the stabilizer."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from .config import ActuatorConfig

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - GPIO unavailable on CI
    GPIO = None  # type: ignore[assignment]


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


class ServoActuator:
    """PWM-based servo driver with optional simulation mode."""

    def __init__(self, name: str, config: ActuatorConfig):
        self.name = name
        self.config = config
        self._simulate = config.simulate or GPIO is None
        if GPIO is None and not config.simulate:
            warnings.warn(
                "RPi.GPIO not available; ServoActuator running in simulation mode.",
                RuntimeWarning,
            )
        self._pwm = None
        self._last_pulse = config.neutral_pulse_us

        if not self._simulate:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(config.pin, config.frequency_hz)
            self._pwm.start(self._pulse_to_duty(config.neutral_pulse_us))

    def _pulse_to_duty(self, pulse_us: float) -> float:
        period_us = 1_000_000 / self.config.frequency_hz
        return 100.0 * pulse_us / period_us

    def close(self) -> None:
        if self._pwm:
            self._pwm.stop()
        if GPIO and not self._simulate:
            GPIO.cleanup(self.config.pin)

    def set_normalized(self, demand: float) -> float:
        demand = _clamp(demand, -1.0, 1.0)
        if demand >= 0:
            span = self.config.max_pulse_us - self.config.neutral_pulse_us
        else:
            span = self.config.neutral_pulse_us - self.config.min_pulse_us
        pulse = self.config.neutral_pulse_us + span * demand

        delta = pulse - self._last_pulse
        max_delta = self.config.rate_limit_us
        if abs(delta) > max_delta:
            pulse = self._last_pulse + max_delta * (1 if delta > 0 else -1)

        self._last_pulse = pulse

        if self._simulate:
            return pulse

        if GPIO is None or self._pwm is None:  # pragma: no cover
            raise RuntimeError("GPIO not initialized")

        self._pwm.ChangeDutyCycle(self._pulse_to_duty(pulse))
        return pulse


@dataclass
class GimbalOutputs:
    pan_pulse: float
    tilt_pulse: float


class GimbalActuator:
    """Aggregates two ServoActuators for pan and tilt axes."""

    def __init__(self, pan: ServoActuator, tilt: ServoActuator):
        self.pan = pan
        self.tilt = tilt

    @classmethod
    def from_configs(cls, pan_cfg: ActuatorConfig, tilt_cfg: ActuatorConfig) -> "GimbalActuator":
        return cls(ServoActuator("pan", pan_cfg), ServoActuator("tilt", tilt_cfg))

    def close(self) -> None:
        self.pan.close()
        self.tilt.close()

    def set_demands(self, pan_demand: float, tilt_demand: float) -> GimbalOutputs:
        pan_pulse = self.pan.set_normalized(pan_demand)
        tilt_pulse = self.tilt.set_normalized(tilt_demand)
        return GimbalOutputs(pan_pulse=pan_pulse, tilt_pulse=tilt_pulse)
