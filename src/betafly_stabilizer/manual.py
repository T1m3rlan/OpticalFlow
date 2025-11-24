"""Shared state for manual stick overrides delivered via the web UI."""

from __future__ import annotations

import threading
from typing import Tuple


class ManualOverrideState:
    """Thread-safe holder for desired planar velocity overrides."""

    def __init__(self) -> None:
        self._vx = 0.0
        self._vy = 0.0
        self._enabled = False
        self._lock = threading.Lock()

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._vx = 0.0
                self._vy = 0.0

    def update(self, vx: float, vy: float) -> None:
        with self._lock:
            self._vx = float(vx)
            self._vy = float(vy)

    def get_target(self) -> Tuple[float, float]:
        with self._lock:
            if not self._enabled:
                return 0.0, 0.0
            return self._vx, self._vy

    def reset(self) -> None:
        self.update(0.0, 0.0)


__all__ = ["ManualOverrideState"]
