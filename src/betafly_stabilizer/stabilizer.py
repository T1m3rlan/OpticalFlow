"""High-level orchestration for the optical stabilizer."""

from __future__ import annotations

import csv
import logging
import signal
import time
from pathlib import Path
from typing import Optional, Tuple

from .camera import CameraStream
from .config import StabilizerConfig
from .filters import FlowFilter
from .msp import MSPClient
from .optical_flow import FlowEstimate, OpticalFlowTracker
from .pid import PIDController, PIDGains

LOGGER = logging.getLogger(__name__)


class OpticalStabilizer:
    def __init__(self, config: StabilizerConfig):
        self.config = config
        self.camera = CameraStream(config.camera)
        self.flow = OpticalFlowTracker(config.flow)
        self.filter = FlowFilter(config.filter)
        self.pid_roll = PIDController(PIDGains(**config.pid_roll.__dict__))
        self.pid_pitch = PIDController(PIDGains(**config.pid_pitch.__dict__))
        self.msp = MSPClient(config.msp)
        self._telemetry_writer: Optional[csv.writer] = None
        self._telemetry_file = None
        self._running = False
        self._guard_frames = config.flow.guard_frames

    def _open_telemetry(self) -> None:
        if not self.config.telemetry_path:
            return
        path = Path(self.config.telemetry_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._telemetry_file = path.open("w", encoding="utf-8", newline="")
        self._telemetry_writer = csv.writer(self._telemetry_file)
        self._telemetry_writer.writerow(
            ["timestamp", "vx", "vy", "filtered_vx", "filtered_vy", "roll_cmd", "pitch_cmd", "confidence"]
        )

    def _close_telemetry(self) -> None:
        if self._telemetry_file:
            self._telemetry_file.close()
            self._telemetry_file = None
            self._telemetry_writer = None

    def _write_telemetry(
        self, estimate: FlowEstimate, filtered: Tuple[float, float], roll_cmd: float, pitch_cmd: float
    ) -> None:
        if not self._telemetry_writer:
            return
        self._telemetry_writer.writerow(
            [time.time(), estimate.vx, estimate.vy, filtered[0], filtered[1], roll_cmd, pitch_cmd, estimate.confidence]
        )
        self._telemetry_file.flush()

    def _handle_estimate(self, estimate: FlowEstimate) -> None:
        filtered_vx, filtered_vy = self.filter.push(estimate.vx, estimate.vy)
        pitch_error = -filtered_vx
        roll_error = filtered_vy

        roll_cmd = self.pid_roll.update(roll_error, estimate.dt)
        pitch_cmd = self.pid_pitch.update(pitch_error, estimate.dt)

        if not self.config.dry_run:
            self.msp.send_trim(roll_cmd, pitch_cmd)

        self._write_telemetry(estimate, (filtered_vx, filtered_vy), roll_cmd, pitch_cmd)

    def run(self) -> None:
        LOGGER.info("Starting optical stabilizer (dry_run=%s)", self.config.dry_run)
        self._running = True
        self._open_telemetry()
        signal.signal(signal.SIGINT, self._stop_signal)
        signal.signal(signal.SIGTERM, self._stop_signal)
        try:
            with self.camera:
                if not self.config.dry_run:
                    self.msp.connect()
                for timestamp, frame in self.camera.frames():
                    if not self._running:
                        break
                    estimate = self.flow.process(timestamp, frame)
                    if estimate is None:
                        continue
                    if self._guard_frames > 0:
                        self._guard_frames -= 1
                        continue
                    if estimate.confidence <= 0.0:
                        continue
                    self._handle_estimate(estimate)
        finally:
            LOGGER.info("Shutting down stabilizer")
            self._close_telemetry()
            self.msp.close()

    def _stop_signal(self, signum, frame) -> None:  # pragma: no cover
        LOGGER.info("Received signal %s, stopping...", signum)
        self._running = False


__all__ = ["OpticalStabilizer"]
