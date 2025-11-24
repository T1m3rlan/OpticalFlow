"""Betafly optical position stabilizer package."""

from .config import (
    AnalogProfile,
    CameraConfig,
    TrackerConfig,
    PIDConfig,
    ActuatorConfig,
    ManualInputConfig,
    StabilizerConfig,
    load_config,
)
from .stabilizer import OpticalPositionStabilizer

__all__ = [
    "AnalogProfile",
    "CameraConfig",
    "TrackerConfig",
    "PIDConfig",
    "ActuatorConfig",
    "ManualInputConfig",
    "StabilizerConfig",
    "load_config",
    "OpticalPositionStabilizer",
]

__version__ = "0.1.0"
