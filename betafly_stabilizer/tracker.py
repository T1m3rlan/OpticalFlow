"""Optical flow-based drift estimator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from .config import TrackerConfig

try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency during lint/tests
    cv2 = None  # type: ignore[assignment]


@dataclass
class TrackingResult:
    dx: float
    dy: float
    quality: float
    feature_count: int


class OpticalFlowTracker:
    """Tracks features frame to frame and reports aggregate translation."""

    def __init__(self, config: TrackerConfig):
        if cv2 is None:
            raise RuntimeError("OpenCV is required for OpticalFlowTracker.")
        self.config = config
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_points: Optional[np.ndarray] = None

    def _roi_mask(self, frame_shape: Tuple[int, int]) -> Optional[np.ndarray]:
        if not self.config.roi:
            return None
        x, y, w, h = self.config.roi
        mask = np.zeros(frame_shape, dtype=np.uint8)
        mask[y : y + h, x : x + w] = 255
        return mask

    def _detect_features(self, frame: np.ndarray) -> Optional[np.ndarray]:
        mask = self._roi_mask(frame.shape)
        points = cv2.goodFeaturesToTrack(
            frame,
            mask=mask,
            maxCorners=self.config.max_corners,
            qualityLevel=self.config.quality_level,
            minDistance=self.config.min_distance,
            blockSize=self.config.block_size,
        )
        return points

    def initialize(self, frame: np.ndarray) -> None:
        self._prev_frame = frame.copy()
        self._prev_points = self._detect_features(self._prev_frame)

    def reset(self) -> None:
        self._prev_frame = None
        self._prev_points = None

    def track(self, frame: np.ndarray) -> TrackingResult:
        if self._prev_frame is None or self._prev_points is None or len(self._prev_points) == 0:
            self.initialize(frame)
            return TrackingResult(0.0, 0.0, 0.0, 0)

        next_points, status, err = cv2.calcOpticalFlowPyrLK(
            self._prev_frame,
            frame,
            self._prev_points,
            None,
            winSize=(self.config.win_size, self.config.win_size),
            maxLevel=self.config.pyramids,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
        )

        if next_points is None or status is None:
            self.reset()
            return TrackingResult(0.0, 0.0, 0.0, 0)

        good_prev = self._prev_points[status.flatten() == 1]
        good_next = next_points[status.flatten() == 1]
        feature_count = len(good_prev)

        if feature_count == 0:
            self.reset()
            return TrackingResult(0.0, 0.0, 0.0, 0)

        deltas = good_next - good_prev
        dx = float(np.median(deltas[:, 0]))
        dy = float(np.median(deltas[:, 1]))

        quality = feature_count / float(len(self._prev_points))
        if quality < self.config.reinit_threshold:
            self.initialize(frame)
        else:
            self._prev_frame = frame.copy()
            self._prev_points = good_next.reshape(-1, 1, 2)

        return TrackingResult(dx=dx, dy=dy, quality=quality, feature_count=feature_count)
