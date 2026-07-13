"""
The public :class:`Device` — an object-oriented handle to a single
Android device, wrapping :class:`~voidremote.controllers.app_controller.AppController`
so callers never touch ``adb`` subprocess plumbing directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from voidremote.api.exceptions import AdbCommandError, ConnectionError, InvalidArgumentError
from voidremote.models.device import Device as _DeviceModel

if TYPE_CHECKING:
    import subprocess

    from voidremote.controllers.app_controller import AppController

logger = logging.getLogger(__name__)


class Device:
    """
    A single Android device.

    Every method is a thin, validated wrapper over one ADB operation —
    there is no hidden batching or magic. Instances are normally obtained
    from :class:`~voidremote.api.client.VoidRemote`, not constructed directly.

    Example:
        >>> from voidremote import VoidRemote
        >>> client = VoidRemote()
        >>> device = client.devices().first()   # doctest: +SKIP
        >>> device.tap(500, 800)                # doctest: +SKIP
        >>> device.text("hello world")          # doctest: +SKIP
        >>> device.screenshot("shot.png")        # doctest: +SKIP
    """

    def __init__(self, model: _DeviceModel, controller: "AppController") -> None:
        self._model = model
        self._controller = controller

    # ------------------------------------------------------------------
    # Identity & info
    # ------------------------------------------------------------------

    @property
    def serial(self) -> str:
        """The ADB serial (``host:port`` for wireless devices)."""
        return self._model.serial

    @property
    def name(self) -> str:
        """Human-readable name, e.g. ``"Google Pixel 6"``."""
        return self._model.display_name

    @property
    def android_version(self) -> str:
        return self._model.info.android_version

    @property
    def sdk_version(self) -> int:
        return self._model.info.sdk_version

    @property
    def model(self) -> str:
        return self._model.info.model

    @property
    def manufacturer(self) -> str:
        return self._model.info.manufacturer

    @property
    def resolution(self) -> tuple[int, int]:
        """``(width, height)`` in pixels."""
        return (self._model.info.screen_width, self._model.info.screen_height)

    @property
    def ip_address(self) -> str:
        return self._model.info.network.ip_address

    @property
    def battery_level(self) -> int:
        """Battery percentage, 0-100."""
        return self._model.info.battery.level

    @property
    def is_charging(self) -> bool:
        return self._model.info.battery.is_charging

    @property
    def is_online(self) -> bool:
        return self._model.is_connected

    @property
    def raw(self) -> _DeviceModel:
        """The underlying data model, for anything not exposed on :class:`Device` yet."""
        return self._model

    def refresh(self) -> "Device":
        """Re-query the device and return an updated :class:`Device` (does not mutate self)."""
        updated = self._controller.get_device(self.serial)
        if updated is None:
            self._controller.list_devices(refresh=True)
            updated = self._controller.get_device(self.serial)
        if updated is None:
            raise ConnectionError(f"Device {self.serial} is no longer reachable")
        return Device(updated, self._controller)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def disconnect(self) -> bool:
        """Disconnect this device (wireless only; no-op for USB, returns False)."""
        return self._controller.disconnect_device(self.serial)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def tap(self, x: int, y: int) -> "Device":
        """Tap at screen coordinates. Returns ``self`` for chaining."""
        self._controller.tap(self.serial, x, y)
        return self

    def double_tap(self, x: int, y: int) -> "Device":
        self._controller.double_tap(self.serial, x, y)
        return self

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> "Device":
        self._controller.long_press(self.serial, x, y, duration_ms)
        return self

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> "Device":
        self._controller.swipe(self.serial, x1, y1, x2, y2, duration_ms)
        return self

    def scroll_down(self, x: int = 540, y: int = 1200, amount: int = 500) -> "Device":
        self.swipe(x, y, x, max(0, y - amount))
        return self

    def scroll_up(self, x: int = 540, y: int = 800, amount: int = 500) -> "Device":
        self.swipe(x, y, x, y + amount)
        return self

    def text(self, value: str) -> "Device":
        """Type text into the currently focused field."""
        self._controller.type_text(self.serial, value)
        return self

    def key_event(self, keycode: int) -> "Device":
        """Send a raw Android keycode. See :class:`voidremote.api.KeyCode` for common ones."""
        self._controller.key_event(self.serial, keycode)
        return self

    def home(self) -> "Device":
        from voidremote.services.input_service import KeyCode
        return self.key_event(KeyCode.KEYCODE_HOME)

    def back(self) -> "Device":
        from voidremote.services.input_service import KeyCode
        return self.key_event(KeyCode.KEYCODE_BACK)

    def wake(self) -> "Device":
        from voidremote.services.input_service import KeyCode
        return self.key_event(KeyCode.KEYCODE_WAKEUP)

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def shell(self, command: str) -> str:
        """Run a raw shell command and return stdout."""
        try:
            return self._controller.shell(self.serial, command)
        except Exception as exc:
            raise AdbCommandError(f"shell command failed: {command!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def push(self, local: str | Path, remote: str) -> "Device":
        """Copy a local file onto the device."""
        self._controller.push_file(self.serial, Path(local), remote)
        return self

    def pull(self, remote: str, local: str | Path) -> Path:
        """Copy a file from the device to a local path. Returns the local path."""
        local_path = Path(local)
        self._controller.pull_file(self.serial, remote, local_path)
        return local_path

    def list_dir(self, path: str = "/sdcard") -> list[str]:
        """List entries in a device directory (raw ``ls -la`` names)."""
        output = self.shell(f"ls -la '{path}'")
        entries = []
        for line in output.splitlines()[1:]:
            parts = line.split(None, 8)
            if len(parts) >= 9 and parts[-1] not in (".", ".."):
                entries.append(parts[-1])
        return entries

    # ------------------------------------------------------------------
    # Packages
    # ------------------------------------------------------------------

    def install(self, apk_path: str | Path, replace: bool = True) -> "Device":
        """Install an APK."""
        self._controller.install_apk(self.serial, Path(apk_path), replace=replace)
        return self

    def uninstall(self, package: str) -> "Device":
        """Uninstall an app by package name."""
        self._controller.uninstall_app(self.serial, package)
        return self

    def list_packages(self, user_only: bool = True) -> list[str]:
        """List installed package names."""
        flag = "-3" if user_only else ""
        output = self.shell(f"pm list packages {flag}".strip())
        return [line.removeprefix("package:").strip() for line in output.splitlines() if line]

    def is_installed(self, package: str) -> bool:
        return package in self.list_packages(user_only=False)

    # ------------------------------------------------------------------
    # Screen
    # ------------------------------------------------------------------

    def screenshot(self, output: str | Path) -> Path:
        """Capture a screenshot to a local PNG file. Returns the output path."""
        output_path = Path(output)
        self._controller.take_screenshot(self.serial, output_path)
        return output_path

    def screenrecord(self) -> "subprocess.Popen":
        """
        Start recording the screen on-device. Returns the underlying
        :class:`subprocess.Popen`; call ``.wait()`` or ``.terminate()``,
        then :meth:`pull` the resulting ``/sdcard/void_rec.mp4``.
        """
        return self._controller.start_screen_record(self.serial)

    # ------------------------------------------------------------------
    # Power
    # ------------------------------------------------------------------

    def reboot(self, mode: str = "") -> None:
        """Reboot the device. ``mode`` may be ``""``, ``"bootloader"``, or ``"recovery"``."""
        self._controller.reboot(self.serial, mode)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def monitor(self, interval: float = 2.0, callback: Optional[object] = None) -> None:
        """
        Start background CPU/RAM/battery polling for this device.

        Args:
            interval: Seconds between samples.
            callback: ``Callable[[DeviceSnapshot], None]`` invoked on the
                polling thread for each sample.
        """
        self._controller.start_monitoring(self.serial, interval, callback)  # type: ignore[arg-type]

    def stop_monitoring(self) -> None:
        self._controller.stop_monitoring(self.serial)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Device(serial={self.serial!r}, name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Device) and other.serial == self.serial

    def __hash__(self) -> int:
        return hash(self.serial)
