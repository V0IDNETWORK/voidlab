"""
Public exception hierarchy for the VoidRemote SDK.

Everything the SDK raises is a :class:`VoidRemoteError`, so callers can
write one broad ``except VoidRemoteError`` if they don't care about the
distinction, or catch the specific subclass if they do.
"""

from __future__ import annotations


class VoidRemoteError(Exception):
    """Base class for all errors raised by the VoidRemote SDK."""


class AdbNotAvailableError(VoidRemoteError):
    """The ``adb`` binary could not be found or executed."""


class AdbTimeoutError(VoidRemoteError):
    """An ADB operation did not complete within its timeout."""


class AdbCommandError(VoidRemoteError):
    """An ADB command ran but returned a non-zero exit status."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class DeviceNotFoundError(VoidRemoteError):
    """No device matches the requested serial / selector."""


class NoDevicesError(VoidRemoteError):
    """An operation required at least one connected device and found none."""


class PairingError(VoidRemoteError):
    """Wireless-debugging pairing failed."""


class ConnectionError(VoidRemoteError):  # noqa: A001 - intentional shadow, this is our public API
    """Connecting to a device over TCP/IP failed."""


class InvalidArgumentError(VoidRemoteError):
    """A caller-supplied argument (host, port, package name, path, ...) was invalid."""
