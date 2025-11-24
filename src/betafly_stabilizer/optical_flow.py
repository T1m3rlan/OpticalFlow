"""Optical flow estimation helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from .config import FlowConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class FlowEstimate:
    vx: float
    vy: float
    confidence: float
    dt: float


class OpticalFlowTracker:
    """Tracks sparse features and emits planar velocity estimates."""

    def __init__(self, config: FlowConfig):
        self.config = config
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_pts: Optional[np.ndarray] = None
        self._prev_ts: Optional[float] = None

    def reset(self) -> None:
        self._prev_frame = None
        self._prev_pts = None
        self._prev_ts = None

    def _detect_features(self, frame: np.ndarray) -> Optional[np.ndarray]:
        pts = cv2.goodFeaturesToTrack(
            frame,
            maxCorners=self.config.max_corners,
            qualityLevel=self.config.quality_level,
            minDistance=self.config.min_distance,
            blockSize=self.config.block_size,
        )
        if pts is None:
            return None
        return pts.reshape(-1, 1, 2)

    def _flow(self, prev: np.ndarray, curr: np.ndarray, pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        next_pts, status, err = cv2.calcOpticalFlowPyrLK(
            prev, curr, pts, None, winSize=(self.config.win_size, self.config.win_size), maxLevel=self.config.max_level
        )
        if next_pts is None or status is None:
            raise RuntimeError("Failed to compute optical flow")
        good_new = next_pts[status[:, 0] == 1]
        good_old = pts[status[:, 0] == 1]
        if err is not None:
            err = err[status[:, 0] == 1]
            mask = err[:, 0] < np.percentile(err[:, 0], 75)
            good_new = good_new[mask]
            good_old = good_old[mask]
        return good_old, good_new

    def process(self, timestamp: float, frame: np.ndarray) -> Optional[FlowEstimate]:
        if self._prev_frame is None:
            self._prev_frame = frame
            self._prev_pts = self._detect_features(frame)
            self._prev_ts = timestamp
            return None

        if self._prev_pts is None or len(self._prev_pts) < 4:
            self._prev_pts = self._detect_features(frame)
            self._prev_frame = frame
            self._prev_ts = timestamp
            return None

        dt = timestamp - (self._prev_ts or timestamp)
        if dt <= 0:
            dt = 1e-3

        try:
            old_pts, new_pts = self._flow(self._prev_frame, frame, self._prev_pts)
        except RuntimeError as exc:
            LOGGER.warning("Optical flow failed: %s", exc)
            self.reset()
            return None

        if old_pts.size == 0 or new_pts.size == 0:
            self.reset()
            return None

        displacement = new_pts - old_pts
        median_disp = np.median(displacement, axis=0)
        vx = (median_disp[0] / dt) * self.config.pixel_to_meter
        vy = (median_disp[1] / dt) * self.config.pixel_to_meter
        confidence = min(1.0, len(old_pts) / self.config.max_corners)

        self._prev_frame = frame
        self._prev_pts = new_pts.reshape(-1, 1, 2)
        self._prev_ts = timestamp

        if confidence < self.config.confidence_threshold:
            return FlowEstimate(0.0, 0.0, 0.0, dt)

        return FlowEstimate(float(vx), float(vy), float(confidence), float(dt))


__all__ = ["OpticalFlowTracker", "FlowEstimate"]
