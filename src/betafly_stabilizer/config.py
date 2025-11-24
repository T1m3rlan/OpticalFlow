"""Configuration helpers for the stabilizer service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml


@dataclass
class CameraConfig:
    width: int = 160
    height: int = 120
    fps: float = 30.0
    video_source: str = "auto"  # auto|cv|picamera|file:<path>
    analog_gain: Optional[float] = None
    shutter_us: Optional[int] = None
    rotation: int = 0


@dataclass
class FlowConfig:
    max_corners: int = 60
    quality_level: float = 0.2
    min_distance: int = 7
    block_size: int = 7
    win_size: int = 15
    max_level: int = 2
    pixel_to_meter: float = 0.002  # tuned experimentally
    confidence_threshold: float = 0.4
    guard_frames: int = 40


@dataclass
class PidAxisConfig:
    kp: float = 0.6
    ki: float = 0.2
    kd: float = 0.05
    i_clamp: float = 0.3
    output_limit: float = 0.4


@dataclass
class FilterConfig:
    ema_alpha: float = 0.4
    median_window: int = 5
    deadband: float = 0.01


@dataclass
class MspConfig:
    port: str = "/dev/ttyAMA0"
    baudrate: int = 115200
    roll_channel: int = 0
    pitch_channel: int = 1
    command_rate_hz: float = 30.0
    rc_mid: int = 1500
    rc_min: int = 1100
    rc_max: int = 1900
    max_trim: int = 80


@dataclass
class StabilizerConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    flow: FlowConfig = field(default_factory=FlowConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    pid_roll: PidAxisConfig = field(default_factory=PidAxisConfig)
    pid_pitch: PidAxisConfig = field(default_factory=PidAxisConfig)
    msp: MspConfig = field(default_factory=MspConfig)
    telemetry_path: Optional[str] = "telemetry.csv"
    dry_run: bool = False


def _update_dataclass(dc: Any, values: Mapping[str, Any]) -> None:
    for key, value in values.items():
        if hasattr(dc, key):
            setattr(dc, key, value)


def _build_config(data: Mapping[str, Any]) -> StabilizerConfig:
    config = StabilizerConfig()
    if "camera" in data:
        _update_dataclass(config.camera, data["camera"])
    if "flow" in data:
        _update_dataclass(config.flow, data["flow"])
    if "filter" in data:
        _update_dataclass(config.filter, data["filter"])
    if "pid" in data:
        pid = data["pid"]
        if "roll" in pid:
            _update_dataclass(config.pid_roll, pid["roll"])
        if "pitch" in pid:
            _update_dataclass(config.pid_pitch, pid["pitch"])
    if "msp" in data:
        _update_dataclass(config.msp, data["msp"])
    if "telemetry_path" in data:
        config.telemetry_path = data["telemetry_path"]
    if "dry_run" in data:
        config.dry_run = bool(data["dry_run"])
    return config


def load_config(path: Optional[str | Path]) -> StabilizerConfig:
    """Load YAML config; when None return defaults."""
    if path is None:
        return StabilizerConfig()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, Mapping):
        raise ValueError("Config root must be a mapping/object")
    return _build_config(data)


__all__ = [
    "CameraConfig",
    "FlowConfig",
    "PidAxisConfig",
    "FilterConfig",
    "MspConfig",
    "StabilizerConfig",
    "load_config",
]
