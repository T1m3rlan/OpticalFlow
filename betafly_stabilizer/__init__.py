"""Betafly optical position stabilizer package."""

from .config import (
    CameraConfig,
    TrackerConfig,
    PIDConfig,
    ActuatorConfig,
    StabilizerConfig,
    load_config,
)
from .stabilizer import OpticalPositionStabilizer

__all__ = [
    "CameraConfig",
    "TrackerConfig",
    "PIDConfig",
    "ActuatorConfig",
    "StabilizerConfig",
    "load_config",
    "OpticalPositionStabilizer",
]

__version__ = "0.1.0"
