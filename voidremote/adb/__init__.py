"""Internal ADB communication layer. Not part of the public API — use ``voidremote.api``."""

from voidremote.adb.client import (
    AdbClient,
    AdbCommandResult,
    AdbError,
    AdbNotFoundError,
    AdbTimeoutError,
)
from voidremote.adb.device_parser import (
    build_device_from_raw,
    parse_battery,
    parse_devices_output,
    parse_getprop,
    parse_ip_address,
    parse_meminfo,
    parse_screen_resolution,
    parse_storage,
    state_from_string,
)

__all__ = [
    "AdbClient",
    "AdbCommandResult",
    "AdbError",
    "AdbNotFoundError",
    "AdbTimeoutError",
    "build_device_from_raw",
    "parse_battery",
    "parse_devices_output",
    "parse_getprop",
    "parse_ip_address",
    "parse_meminfo",
    "parse_screen_resolution",
    "parse_storage",
    "state_from_string",
]
