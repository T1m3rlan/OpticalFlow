"""Optical position stabilization helpers for Betaflight + Raspberry Pi Zero."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return installed package version or '0.0.0' during local dev."""
    try:
        return version("betafly-stabilizer")
    except PackageNotFoundError:
        return "0.0.0"


__all__ = ["get_version"]
