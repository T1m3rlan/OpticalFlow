"""Command-line entry point for the stabilizer."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from .config import StabilizerConfig, load_config
from .stabilizer import OpticalStabilizer


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optical stabilizer for Betaflight hover hold")
    parser.add_argument("-c", "--config", type=str, help="Path to YAML config", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Disable MSP output")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, ...)")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config(args.config)
    if args.dry_run:
        config.dry_run = True
    stabilizer = OpticalStabilizer(config)
    stabilizer.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
