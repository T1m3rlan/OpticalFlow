"""Minimal MSP client for Betaflight RC overrides."""

from __future__ import annotations

import logging
import struct
import time
from typing import Sequence

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - serial not available in CI
    serial = None  # type: ignore

from .config import MspConfig

LOGGER = logging.getLogger(__name__)

MSP_SET_RAW_RC = 200
CHANNEL_COUNT = 8


class MSPClient:
    def __init__(self, config: MspConfig):
        self.config = config
        self._serial = None
        self._last_send = 0.0

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial not available on this system")
        if self._serial and self._serial.is_open:
            return
        LOGGER.info("Connecting to Betaflight over %s @ %s", self.config.port, self.config.baudrate)
        self._serial = serial.Serial(self.config.port, self.config.baudrate, timeout=0.05)

    def close(self) -> None:
        if self._serial:
            self._serial.close()
            self._serial = None

    def _clamp_rc(self, value: int) -> int:
        return int(max(min(value, self.config.rc_max), self.config.rc_min))

    def send_trim(self, roll_offset: float, pitch_offset: float) -> None:
        if not self._serial:
            raise RuntimeError("MSP client not connected")
        now = time.monotonic()
        min_period = 1.0 / max(self.config.command_rate_hz, 1.0)
        if now - self._last_send < min_period:
            return
        self._last_send = now
        channels = [self.config.rc_mid] * CHANNEL_COUNT
        channels[self.config.roll_channel] = self._clamp_rc(
            self.config.rc_mid + int(roll_offset * self.config.max_trim)
        )
        channels[self.config.pitch_channel] = self._clamp_rc(
            self.config.rc_mid + int(pitch_offset * self.config.max_trim)
        )
        self._send_channels(channels)

    def _send_channels(self, channels: Sequence[int]) -> None:
        payload = b"".join(struct.pack("<H", val) for val in channels)
        self._send_msp(MSP_SET_RAW_RC, payload)

    def _send_msp(self, command: int, payload: bytes) -> None:
        if not self._serial:
            return
        length = len(payload)
        header = bytearray(b"$M<")
        header.append(length)
        header.append(command)
        packet = header + payload
        checksum = 0
        for byte in packet[3:]:
            checksum ^= byte
        packet.append(checksum)
        self._serial.write(packet)


__all__ = ["MSPClient"]
