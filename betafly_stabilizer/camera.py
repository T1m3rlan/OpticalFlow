"""Camera capture helpers."""

from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np

from .config import CameraConfig

try:
    import cv2
except ImportError:  # pragma: no cover - OpenCV might not be installed on CI
    cv2 = None  # type: ignore[assignment]

try:
    from picamera import PiCamera
    from picamera.array import PiRGBArray
except ImportError:  # pragma: no cover - Pi hardware not available in tests
    PiCamera = None  # type: ignore[assignment]
    PiRGBArray = None  # type: ignore[assignment]


class CameraError(RuntimeError):
    """Raised when a camera operation fails."""


class CameraStream:
    """Thin wrapper around OpenCV / PiCamera that yields grayscale frames."""

    def __init__(self, config: CameraConfig):
        self.config = config
        self._capture = None
        self._picamera = None
        self._stream = None
        self._last_timestamp: Optional[float] = None
        self._mode: Optional[str] = None

    def _resolve_source(self) -> str:
        if self.config.use_picamera or self.config.source.lower() == "picamera":
            return "picamera"
        if self.config.source.lower() == "analog":
            return "analog"
        return "opencv"

    def _open_opencv_capture(self, source, backend=None):
        if cv2 is None:
            raise CameraError("OpenCV is not available. Install opencv-python or enable PiCamera.")
        if backend is None:
            capture = cv2.VideoCapture(source)
        else:
            capture = cv2.VideoCapture(source, backend)
        if not capture or not capture.isOpened():
            raise CameraError(f"Unable to open video source '{source}'")
        return capture

    def _configure_capture(self, width: int, height: int, fps: int, analog: bool = False) -> None:
        if not self._capture:
            return
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._capture.set(cv2.CAP_PROP_FPS, fps)
        if analog:
            cap_standard = getattr(cv2, "CAP_PROP_STANDARD", None)
            cap_channel = getattr(cv2, "CAP_PROP_CHANNEL", None)
            profile = self.config.active_analog_profile()
            if cap_standard is not None:
                standard = profile.standard.upper()
                standard_map = {"NTSC": 0, "PAL": 1, "SECAM": 2}
                if standard in standard_map:
                    self._capture.set(cap_standard, standard_map[standard])
            if cap_channel is not None:
                self._capture.set(cap_channel, profile.input_channel)

    def start(self) -> "CameraStream":
        mode = self._resolve_source()
        self._mode = mode
        if mode == "picamera":
            if PiCamera is None or PiRGBArray is None:
                raise CameraError(
                    "PiCamera support is not available. Install 'picamera' or disable use_picamera."
                )
            self._picamera = PiCamera()
            self._picamera.resolution = (self.config.width, self.config.height)
            self._picamera.framerate = self.config.framerate
            self._stream = PiRGBArray(self._picamera, size=self._picamera.resolution)
            time.sleep(2)  # Allow sensor to warm up
        else:
            if mode == "analog":
                profile = self.config.active_analog_profile()
                self._capture = self._open_opencv_capture(profile.device, getattr(cv2, "CAP_V4L2", 0))
                self._configure_capture(profile.width, profile.height, profile.framerate, analog=True)
                self.config.width = profile.width
                self.config.height = profile.height
                self.config.framerate = profile.framerate
            else:
                self._capture = self._open_opencv_capture(self.config.device_index)
                self._configure_capture(self.config.width, self.config.height, self.config.framerate)
        return self

    def stop(self) -> None:
        if self._capture:
            self._capture.release()
            self._capture = None
        if self._picamera:
            self._picamera.close()
            self._picamera = None
        if self._stream:
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "CameraStream":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def read(self) -> Tuple[np.ndarray, float]:
        """Grab a frame as a 8-bit grayscale numpy array."""
        frame: Optional[np.ndarray] = None
        if self._mode == "picamera" and self._picamera and self._stream:
            self._stream.truncate(0)
            self._picamera.capture(self._stream, format="bgr", use_video_port=True)
            frame = self._stream.array
        elif self._capture:
            ret, frame = self._capture.read()
            if not ret:
                raise CameraError("Failed to read frame from OpenCV capture")
        else:
            raise CameraError("CameraStream is not started")

        if frame is None:
            raise CameraError("Camera returned an empty frame")

        if cv2:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:  # pragma: no cover - fallback path without cv2 should rarely be used
            gray = frame.mean(axis=2).astype(np.uint8)

        if self.config.rotation_deg:
            if cv2 is None:
                raise CameraError("Rotation requires OpenCV to be installed")
            rot_code = {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE,
            }.get(self.config.rotation_deg % 360)
            if rot_code is not None:
                gray = cv2.rotate(gray, rot_code)

        if self.config.flip_horizontal:
            if cv2:
                gray = cv2.flip(gray, 1)
            else:
                gray = np.fliplr(gray)
        if self.config.flip_vertical:
            if cv2:
                gray = cv2.flip(gray, 0)
            else:
                gray = np.flipud(gray)

        timestamp = time.monotonic()
        self._last_timestamp = timestamp
        return gray, timestamp

    @property
    def resolution(self) -> Tuple[int, int]:
        return self.config.width, self.config.height

    @property
    def last_timestamp(self) -> Optional[float]:
        return self._last_timestamp
