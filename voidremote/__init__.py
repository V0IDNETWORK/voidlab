"""
VoidRemote
==========

A Python SDK for controlling Android devices over ADB — wired or
wireless — without shelling out to ``adb`` commands yourself.

    from voidremote import VoidRemote

    client = VoidRemote()
    client.start()

    device = client.devices().first()
    device.tap(500, 800)
    device.text("hello")
    device.screenshot("shot.png")

See ``voidremote.api`` for the full stable surface, or the project
README / docs/API.md for a complete guide. A CLI (``voidremote`` on
your PATH, requires the ``cli`` extra) and a desktop GUI
(``voidremote-gui``, requires the ``gui`` extra) are built on top of
this same SDK — see ``voidremote.cli`` and ``voidremote.ui``.

Author: V0IDNETWORK <ilianothingg@gmail.com>
Homepage: https://github.com/V0IDNETWORK/VoidRemote
License: MIT
"""

from __future__ import annotations

from voidremote.api import (
    AdbCommandError,
    AdbNotAvailableError,
    AdbTimeoutError,
    AsyncDevice,
    AsyncDeviceList,
    AsyncVoidRemote,
    ConnectionError,
    Device,
    DeviceCapability,
    DeviceList,
    DeviceNotFoundError,
    DeviceSnapshot,
    DeviceState,
    InvalidArgumentError,
    KeyCode,
    NoDevicesError,
    PairingError,
    PairingResult,
    PairingSession,
    VoidRemote,
    VoidRemoteError,
)

__version__ = "1.0.0"
__author__ = "V0IDNETWORK"
__email__ = "ilianothingg@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/V0IDNETWORK/VoidRemote"
__description__ = "A Python SDK for controlling Android devices over ADB."

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__url__",
    "__description__",
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
