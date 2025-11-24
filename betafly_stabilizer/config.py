"""Configuration utilities for the Betafly stabilizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - optional at import time
    yaml = None  # type: ignore[assignment]


@dataclass
class AnalogProfile:
    device: str = "/dev/video0"
    width: int = 640
    height: int = 480
    framerate: int = 30
    standard: str = "NTSC"
    input_channel: int = 0


@dataclass
class CameraConfig:
    width: int = 640
    height: int = 480
    framerate: int = 30
    device_index: int = 0
    use_picamera: bool = False
    rotation_deg: int = 0
    source: str = "opencv"  # opencv | picamera | analog
    flip_horizontal: bool = False
    flip_vertical: bool = False
    analog_profile: str = "default"
    analog_profiles: Dict[str, AnalogProfile] = field(
        default_factory=lambda: {"default": AnalogProfile()}
    )

    def active_analog_profile(self) -> AnalogProfile:
        if not self.analog_profiles:
            self.analog_profiles = {"default": AnalogProfile()}
        return self.analog_profiles.get(self.analog_profile) or next(
            iter(self.analog_profiles.values())
        )


@dataclass
class TrackerConfig:
    max_corners: int = 200
    quality_level: float = 0.01
    min_distance: int = 7
    block_size: int = 7
    win_size: int = 21
    pyramids: int = 3
    reinit_threshold: float = 0.4
    roi: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h (pixels)


@dataclass
class PIDConfig:
    kp: float = 0.05
    ki: float = 0.0
    kd: float = 0.01
    integrator_limit: float = 0.4
    output_limit: float = 1.0
    deadband: float = 0.0
    derivative_filter_hz: float = 8.0


@dataclass
class ActuatorConfig:
    pin: int = 18
    neutral_pulse_us: int = 1500
    min_pulse_us: int = 1100
    max_pulse_us: int = 1900
    rate_limit_us: int = 200
    simulate: bool = False
    frequency_hz: int = 50


@dataclass
class ManualInputConfig:
    enabled: bool = False
    device: Optional[str] = None
    mode: str = "gamepad"
    roll_axis: str = "ABS_X"
    pitch_axis: str = "ABS_Y"
    axis_min: int = -32768
    axis_max: int = 32767
    deadband: float = 0.05
    scale: float = 0.4
    fail_safe_timeout_s: float = 1.5


@dataclass
class StabilizerConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    pan_pid: PIDConfig = field(default_factory=PIDConfig)
    tilt_pid: PIDConfig = field(default_factory=lambda: PIDConfig(kp=0.06, kd=0.012))
    pan_actuator: ActuatorConfig = field(default_factory=lambda: ActuatorConfig(pin=18))
    tilt_actuator: ActuatorConfig = field(default_factory=lambda: ActuatorConfig(pin=19))
    control_rate_hz: float = 25.0
    preview: bool = False
    log_path: Optional[str] = None
    manual_input: ManualInputConfig = field(default_factory=ManualInputConfig)


def _to_dataclass(data: Dict[str, Any], cls: Any):
    field_names = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def _load_camera_config(data: Dict[str, Any]) -> CameraConfig:
    values = dict(data)
    analog_profiles_raw = values.pop("analog_profiles", None) or {}
    camera = _to_dataclass(values, CameraConfig)
    camera.analog_profiles = {
        name: _to_dataclass(profile, AnalogProfile) for name, profile in analog_profiles_raw.items()
    } or {"default": AnalogProfile()}
    if camera.use_picamera:
        camera.source = "picamera"
    return camera


def _load_manual_input(data: Dict[str, Any]) -> ManualInputConfig:
    if not data:
        return ManualInputConfig()
    return _to_dataclass(data, ManualInputConfig)


def load_config(path: str | Path) -> StabilizerConfig:
    """Load a YAML config file into a StabilizerConfig instance."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to load configuration files. Install PyYAML first.")
    with Path(path).expanduser().open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return StabilizerConfig(
        camera=_load_camera_config(raw.get("camera", {})),
        tracker=_to_dataclass(raw.get("tracker", {}), TrackerConfig),
        pan_pid=_to_dataclass(raw.get("pan_pid", {}), PIDConfig),
        tilt_pid=_to_dataclass(raw.get("tilt_pid", {}), PIDConfig),
        pan_actuator=_to_dataclass(raw.get("pan_actuator", {}), ActuatorConfig),
        tilt_actuator=_to_dataclass(raw.get("tilt_actuator", {}), ActuatorConfig),
        control_rate_hz=raw.get("control_rate_hz", 25.0),
        preview=raw.get("preview", False),
        log_path=raw.get("log_path"),
        manual_input=_load_manual_input(raw.get("manual_input", {})),
    )
