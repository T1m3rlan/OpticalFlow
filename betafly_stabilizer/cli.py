"""Command-line entrypoint for the Betafly stabilizer."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .stabilizer import OpticalPositionStabilizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Betafly optical position stabilizer")
    parser.add_argument(
        "--config",
        type=str,
        default="config/betafly_default.yaml",
        help="Path to the YAML configuration file",
    )
    parser.add_argument("--duration", type=float, default=None, help="Seconds to run (default infinite)")
    parser.add_argument("--log", type=str, default=None, help="CSV path for telemetry logging")
    parser.add_argument("--camera-index", type=int, default=None, help="Override OpenCV camera index")
    parser.add_argument("--use-picamera", action=argparse.BooleanOptionalAction, default=None, help="Force PiCamera usage")
    parser.add_argument("--preview", action=argparse.BooleanOptionalAction, default=None, help="Enable debug preview window")
    parser.add_argument("--control-rate", type=float, default=None, help="Override control rate in Hz")
    parser.add_argument(
        "--simulate-actuators",
        action="store_true",
        help="Run with virtual actuators (disables GPIO requirement)",
    )
    return parser


def apply_overrides(args, config):
    if args.log:
        config.log_path = args.log
        Path(args.log).expanduser().parent.mkdir(parents=True, exist_ok=True)
    if args.preview is not None:
        config.preview = args.preview
    if args.control_rate:
        config.control_rate_hz = args.control_rate
    if args.camera_index is not None:
        config.camera.device_index = args.camera_index
    if args.use_picamera is not None:
        config.camera.use_picamera = args.use_picamera
    if args.simulate_actuators:
        config.pan_actuator.simulate = True
        config.tilt_actuator.simulate = True
    return config


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    config = apply_overrides(args, config)
    stabilizer = OpticalPositionStabilizer(config)
    stabilizer.run(duration=args.duration)


if __name__ == "__main__":
    main()
