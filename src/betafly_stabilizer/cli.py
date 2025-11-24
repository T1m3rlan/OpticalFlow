"""Command-line entry point for the stabilizer."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import StabilizerConfig, load_config
from .manual import ManualOverrideState
from .stabilizer import OpticalStabilizer
from .web import WebConfigServer


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optical stabilizer for Betaflight hover hold")
    parser.add_argument("-c", "--config", type=str, help="Path to YAML config", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Disable MSP output")
    parser.add_argument("--web-ui", action="store_true", help="Start local config/manual web UI")
    parser.add_argument("--web-host", type=str, help="Web UI host override")
    parser.add_argument("--web-port", type=int, help="Web UI port override")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, ...)")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    if args.dry_run:
        config.dry_run = True
    manual_state = ManualOverrideState()
    manual_state.set_enabled(config.manual_input.enabled)

    web_server = None
    should_start_web = args.web_ui or config.web.enabled
    if should_start_web:
        host = args.web_host or config.web.host
        port = args.web_port or config.web.port
        try:
            web_server = WebConfigServer(config, manual_state, config_path)
            web_server.start(host, port)
            logging.info("Web UI listening on http://%s:%s", host, port)
        except Exception as exc:  # pragma: no cover - best effort logging
            logging.error("Failed to start web UI: %s", exc)

    stabilizer = OpticalStabilizer(config, manual_state=manual_state)
    stabilizer.run()

    if web_server:
        web_server.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
