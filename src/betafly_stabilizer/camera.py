"""Camera capture utilities optimized for Raspberry Pi Zero."""

from __future__ import annotations

import logging
import time
from typing import Generator, Optional, Tuple

import cv2
import numpy as np

from .config import CameraConfig

LOGGER = logging.getLogger(__name__)


def _rotate_frame(frame: np.ndarray, rotation: int) -> np.ndarray:
    if rotation == 0:
        return frame
    rotation = rotation % 360
    if rotation == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rotation == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


class CameraStream:
    """Thin wrapper around cv2 capture that yields grayscale frames."""

    def __init__(self, config: CameraConfig):
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None

    def start(self) -> None:
        if self._cap is not None:
            return
        source = self.config.video_source
        if source.startswith("file:"):
            path = source.split(":", 1)[1]
            LOGGER.info("Opening video file: %s", path)
            self._cap = cv2.VideoCapture(path)
        else:
            index = 0
            if source.startswith("cv:"):
                index = int(source.split(":", 1)[1])
            LOGGER.info("Opening camera index %s", index)
            self._cap = cv2.VideoCapture(index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.config.fps)

        if not self._cap or not self._cap.isOpened():
            raise RuntimeError("Unable to open camera source")

    def stop(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None

    def read(self) -> Tuple[float, np.ndarray]:
        if not self._cap:
            raise RuntimeError("Camera not started")
        ok, frame = self._cap.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to read frame from camera")
        frame = cv2.resize(frame, (self.config.width, self.config.height))
        frame = _rotate_frame(frame, self.config.rotation)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        timestamp = time.monotonic()
        return timestamp, gray

    def frames(self) -> Generator[Tuple[float, np.ndarray], None, None]:
        target_period = 1.0 / max(self.config.fps, 1.0)
        while True:
            start = time.monotonic()
            yield self.read()
            elapsed = time.monotonic() - start
            to_sleep = target_period - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    def __enter__(self) -> "CameraStream":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


__all__ = ["CameraStream"]
