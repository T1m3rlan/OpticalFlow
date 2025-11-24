"""Main orchestration loop for the Betafly stabilizer."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .actuators import GimbalActuator
from .camera import CameraStream
from .config import StabilizerConfig
from .controller import PositionController
from .tracker import OpticalFlowTracker, TrackingResult

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


class TelemetryLogger:
    def __init__(self, path: Optional[str]):
        self.path = Path(path).expanduser() if path else None
        self._file = None
        self._writer = None

    def __enter__(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(
                self._file,
                fieldnames=[
                    "timestamp",
                    "dx",
                    "dy",
                    "quality",
                    "feature_count",
                    "pan_output",
                    "tilt_output",
                    "pan_pulse",
                    "tilt_pulse",
                ],
            )
            self._writer.writeheader()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None

    def log(self, **row):
        if self._writer:
            self._writer.writerow(row)


class OpticalPositionStabilizer:
    """High-level runner that glues capture, tracking, control, and actuation."""

    def __init__(self, config: StabilizerConfig):
        self.config = config
        self.camera = CameraStream(config.camera)
        self.tracker = OpticalFlowTracker(config.tracker)
        self.controller = PositionController(config.pan_pid, config.tilt_pid)
        self.gimbal = GimbalActuator.from_configs(config.pan_actuator, config.tilt_actuator)
        self.preview = config.preview
        self._last_overlay = time.monotonic()

    def _normalize_error(self, result: TrackingResult) -> tuple[float, float]:
        width, height = self.camera.resolution
        norm_x = result.dx / max(1.0, width / 2.0)
        norm_y = result.dy / max(1.0, height / 2.0)
        return norm_x, norm_y

    def _draw_overlay(self, frame: np.ndarray, result: TrackingResult) -> None:
        if cv2 is None or not self.preview:
            return
        display = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        h, w = frame.shape
        center = (w // 2, h // 2)
        cv2.circle(display, center, 4, (0, 255, 0), 1)
        cv2.circle(
            display,
            (int(center[0] + result.dx), int(center[1] + result.dy)),
            4,
            (0, 0, 255),
            2,
        )
        cv2.putText(
            display,
            f"dx={result.dx:.2f} dy={result.dy:.2f} q={result.quality:.2f}",
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )
        cv2.imshow("Betafly Stabilizer", display)
        cv2.waitKey(1)

    def run(self, duration: Optional[float] = None) -> None:
        start_time = time.monotonic()
        last_ts: Optional[float] = None
        target_period = 1.0 / max(1e-3, self.config.control_rate_hz)

        with self.camera, TelemetryLogger(self.config.log_path) as logger:
            try:
                while True:
                    frame, timestamp = self.camera.read()
                    dt = target_period if last_ts is None else max(1e-3, timestamp - last_ts)
                    last_ts = timestamp

                    tracking = self.tracker.track(frame)
                    err_x, err_y = self._normalize_error(tracking)
                    pan_out, tilt_out, _ = self.controller.update(err_x, err_y, dt)
                    outputs = self.gimbal.set_demands(-pan_out, -tilt_out)

                    logger.log(
                        timestamp=timestamp,
                        dx=tracking.dx,
                        dy=tracking.dy,
                        quality=tracking.quality,
                        feature_count=tracking.feature_count,
                        pan_output=pan_out,
                        tilt_output=tilt_out,
                        pan_pulse=outputs.pan_pulse,
                        tilt_pulse=outputs.tilt_pulse,
                    )

                    if self.preview and (time.monotonic() - self._last_overlay) >= (1 / self.config.control_rate_hz):
                        self._draw_overlay(frame, tracking)
                        self._last_overlay = time.monotonic()

                    if duration and (time.monotonic() - start_time) >= duration:
                        break

                    loop_elapsed = time.monotonic() - timestamp
                    sleep_time = target_period - loop_elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            except KeyboardInterrupt:
                pass
            finally:
                self.gimbal.close()
                if cv2 is not None:
                    cv2.destroyAllWindows()
