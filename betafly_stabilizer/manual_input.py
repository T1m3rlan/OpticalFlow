"""Manual stick input helpers."""

from __future__ import annotations

import threading
import time
import warnings
from typing import Optional, Tuple

from .config import ManualInputConfig

try:
    from inputs import devices, UnpluggedError  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    devices = None  # type: ignore[assignment]


class ManualInputSource:
    """Reads joystick/RC stick input (evdev) and exposes normalized offsets."""

    def __init__(self, config: ManualInputConfig):
        self.config = config
        self._virtual = config.mode == "virtual"
        self._enabled = bool(config.enabled and (devices is not None or self._virtual))
        self._device = None
        self._offset = (0.0, 0.0)
        self._lock = threading.Lock()
        self._last_update = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        if self._enabled and not self._virtual:
            self._select_device()

    def _select_device(self) -> None:
        if devices is None:  # pragma: no cover - handled via _enabled flag
            self._enabled = False
            return
        candidates = devices.gamepads
        if self.config.device:
            candidates = [
                dev
                for dev in devices.gamepads
                if dev.fn == self.config.device or dev.path == self.config.device
            ]
        if not candidates:
            warnings.warn(
                "ManualInputSource enabled but no matching joystick/gamepad found.",
                RuntimeWarning,
            )
            self._enabled = False
            return
        self._device = candidates[0]

    def start(self) -> "ManualInputSource":
        if not self._enabled or self._device is None:
            return self
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:  # pragma: no cover - hard to simulate in tests
        assert self._device is not None
        while not self._stop_event.is_set():
            try:
                events = self._device.read()
            except (OSError, AttributeError):
                time.sleep(0.05)
                continue
            except UnpluggedError:  # type: ignore[name-defined]
                warnings.warn("Manual input device unplugged; zeroing offsets.", RuntimeWarning)
                self._set_offset(0.0, 0.0)
                time.sleep(1.0)
                continue
            for event in events:
                if event.code == self.config.roll_axis:
                    self._handle_axis(event.state, axis="roll")
                elif event.code == self.config.pitch_axis:
                    self._handle_axis(event.state, axis="pitch")

    def _handle_axis(self, raw_value: int, axis: str) -> None:
        normalized = self._normalize(raw_value)
        with self._lock:
            roll, pitch = self._offset
            if axis == "roll":
                roll = normalized
            else:
                pitch = -normalized  # invert pitch so up stick = negative error
            self._offset = (roll, pitch)
            self._last_update = time.monotonic()

    def _normalize(self, raw_value: int) -> float:
        span = max(1, self.config.axis_max - self.config.axis_min)
        centered = (raw_value - self.config.axis_min) / span  # 0..1
        norm = (centered - 0.5) * 2.0  # -1..1
        if abs(norm) < self.config.deadband:
            norm = 0.0
        norm = max(-1.0, min(1.0, norm))
        return norm * self.config.scale

    def _set_offset(self, roll: float, pitch: float) -> None:
        with self._lock:
            self._offset = (roll, pitch)
            self._last_update = time.monotonic()

    def inject_virtual(self, roll: float, pitch: float) -> None:
        """Testing hook to spoof manual inputs without hardware."""
        self._set_offset(
            max(-1.0, min(1.0, roll)),
            max(-1.0, min(1.0, pitch)),
        )

    def get_offsets(self) -> Tuple[float, float]:
        if not self._enabled:
            return 0.0, 0.0
        with self._lock:
            if (time.monotonic() - self._last_update) > self.config.fail_safe_timeout_s:
                return 0.0, 0.0
            return self._offset
