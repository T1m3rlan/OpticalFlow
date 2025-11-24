"""Simple filtering utilities to stabilize flow measurements."""

from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

from .config import FilterConfig


def apply_deadband(value: float, threshold: float) -> float:
    if abs(value) < threshold:
        return 0.0
    return value


class FlowFilter:
    """Median + EMA cascade for (vx, vy)."""

    def __init__(self, config: FilterConfig):
        self.config = config
        self._median_window: Deque[Tuple[float, float]] = deque(maxlen=config.median_window)
        self._ema_vx = 0.0
        self._ema_vy = 0.0
        self._initialized = False

    def push(self, vx: float, vy: float) -> Tuple[float, float]:
        self._median_window.append((vx, vy))
        if len(self._median_window) == 0:
            return 0.0, 0.0

        median_vx, median_vy = self._median()

        if not self._initialized:
            self._ema_vx, self._ema_vy = median_vx, median_vy
            self._initialized = True
        else:
            alpha = self.config.ema_alpha
            self._ema_vx = alpha * median_vx + (1 - alpha) * self._ema_vx
            self._ema_vy = alpha * median_vy + (1 - alpha) * self._ema_vy

        filtered_vx = apply_deadband(self._ema_vx, self.config.deadband)
        filtered_vy = apply_deadband(self._ema_vy, self.config.deadband)
        return filtered_vx, filtered_vy

    def _median(self) -> Tuple[float, float]:
        vx_vals = sorted(val[0] for val in self._median_window)
        vy_vals = sorted(val[1] for val in self._median_window)
        idx = len(vx_vals) // 2
        return vx_vals[idx], vy_vals[idx]


__all__ = ["FlowFilter", "apply_deadband"]
