"""Command-line entrypoint for the Betafly stabilizer."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .stabilizer import OpticalPositionStabilizer
from .webui import run_webui


DEFAULT_CONFIG = "config/betafly_default.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Betafly optical position stabilizer")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Start the stabilizer loop (default)")
    add_run_arguments(run_parser)

    web_parser = subparsers.add_parser("webui", help="Launch the local configuration server")
    add_web_arguments(web_parser)

    parser.set_defaults(command="run")
    return parser


def add_run_arguments(run_parser: argparse.ArgumentParser) -> None:
    run_parser.add_argument("--config", type=str, default=DEFAULT_CONFIG, help="Path to the YAML configuration file")
    run_parser.add_argument("--duration", type=float, default=None, help="Seconds to run (default: infinite)")
    run_parser.add_argument("--log", type=str, default=None, help="CSV path for telemetry logging")
    run_parser.add_argument("--camera-index", type=int, default=None, help="Override OpenCV camera index")
    run_parser.add_argument("--camera-source", type=str, choices=["opencv", "picamera", "analog"], default=None, help="Force a specific camera backend")
    run_parser.add_argument("--analog-profile", type=str, default=None, help="Select a named analog profile from the config")
    run_parser.add_argument("--use-picamera", action=argparse.BooleanOptionalAction, default=None, help="Force PiCamera usage")
    run_parser.add_argument("--preview", action=argparse.BooleanOptionalAction, default=None, help="Enable debug preview window")
    run_parser.add_argument("--control-rate", type=float, default=None, help="Override control rate in Hz")
    run_parser.add_argument("--manual-input", action=argparse.BooleanOptionalAction, default=None, help="Toggle manual stick input fusion")
    run_parser.add_argument("--manual-device", type=str, default=None, help="Manual input device path (e.g. /dev/input/js0)")
    run_parser.add_argument("--manual-scale", type=float, default=None, help="Manual input scaling factor (0-1)")
    run_parser.add_argument(
        "--simulate-actuators",
        action="store_true",
        help="Run with virtual actuators (disables GPIO requirement)",
    )


def add_web_arguments(web_parser: argparse.ArgumentParser) -> None:
    web_parser.add_argument("--config", type=str, default=DEFAULT_CONFIG, help="Path to the YAML configuration file")
    web_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host/IP for the web UI")
    web_parser.add_argument("--port", type=int, default=8080, help="Port for the web UI")
    web_parser.add_argument("--open-browser", action="store_true", help="Open the default browser automatically")


def apply_run_overrides(args, config):
    if args.log:
        config.log_path = args.log
        Path(args.log).expanduser().parent.mkdir(parents=True, exist_ok=True)
    if args.preview is not None:
        config.preview = args.preview
    if args.control_rate:
        config.control_rate_hz = args.control_rate
    if args.camera_index is not None:
        config.camera.device_index = args.camera_index
    if args.camera_source:
        config.camera.source = args.camera_source
    if args.analog_profile:
        config.camera.analog_profile = args.analog_profile
    if args.use_picamera is not None:
        config.camera.use_picamera = args.use_picamera
    if args.simulate_actuators:
        config.pan_actuator.simulate = True
        config.tilt_actuator.simulate = True
    if args.manual_input is not None:
        config.manual_input.enabled = args.manual_input
    if args.manual_device:
        config.manual_input.device = args.manual_device
    if args.manual_scale is not None:
        config.manual_input.scale = args.manual_scale
    return config


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    command = getattr(args, "command", "run")

    if command == "webui":
        run_webui(args.config, host=args.host, port=args.port, open_browser=args.open_browser)
        return

    config = load_config(args.config)
    config = apply_run_overrides(args, config)
    stabilizer = OpticalPositionStabilizer(config)
    stabilizer.run(duration=args.duration)


if __name__ == "__main__":
    main()
