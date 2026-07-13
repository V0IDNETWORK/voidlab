"""
``voidremote.api`` — the stable public surface of the VoidRemote SDK.

Everything exported here follows semantic versioning: within a major
version, signatures won't change incompatibly. Everything *not*
exported here (``voidremote.adb``, ``voidremote.services``,
``voidremote.controllers``, ...) is an internal implementation detail
and may change without notice between minor versions.

Most users should simply do::

    from voidremote import VoidRemote

which re-exports the same names as this module.
"""

from __future__ import annotations

from voidremote.api.async_client import AsyncDevice, AsyncDeviceList, AsyncVoidRemote
from voidremote.api.client import Device, DeviceList, VoidRemote
from voidremote.api.exceptions import (
    AdbCommandError,
    AdbNotAvailableError,
    AdbTimeoutError,
    ConnectionError,
    DeviceNotFoundError,
    InvalidArgumentError,
    NoDevicesError,
    PairingError,
    VoidRemoteError,
)
from voidremote.api.pairing import PairingResult, PairingSession
from voidremote.models.device import DeviceCapability, DeviceState
from voidremote.services.input_service import KeyCode
from voidremote.services.monitor_service import DeviceSnapshot

__all__ = [
    # Core
    "VoidRemote",
    "AsyncVoidRemote",
    "Device",
    "AsyncDevice",
    "DeviceList",
    "AsyncDeviceList",
    # Pairing
    "PairingSession",
    "PairingResult",
    # Enums / value objects
    "DeviceState",
    "DeviceCapability",
    "KeyCode",
    "DeviceSnapshot",
    # Exceptions
    "VoidRemoteError",
    "AdbNotAvailableError",
    "AdbTimeoutError",
    "AdbCommandError",
    "DeviceNotFoundError",
    "NoDevicesError",
    "PairingError",
    "ConnectionError",
    "InvalidArgumentError",
]
