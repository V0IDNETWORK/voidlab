"""
Application controller — dependency-injection root.

Owns every service instance and exposes one facade consumed by the CLI,
the GUI, and (indirectly, via composition) the public SDK in
``voidremote.api``. Constructing an :class:`AppController` never talks to
ADB; call :meth:`initialize` explicitly once you're ready to.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from voidremote.adb.client import AdbClient
from voidremote.config.settings import AppSettings, get_settings
from voidremote.models.device import Device
from voidremote.services.device_service import DeviceService
from voidremote.services.input_service import InputService
from voidremote.services.monitor_service import MonitorService, SnapshotCallback

logger = logging.getLogger(__name__)


class AppController:
    """
    Central application controller composing the ADB client and services.

    Example:
        >>> ctrl = AppController()
        >>> ctrl.initialize()          # doctest: +SKIP
        >>> devices = ctrl.list_devices()   # doctest: +SKIP
    """

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        adb_client: Optional[AdbClient] = None,
        device_service: Optional[DeviceService] = None,
        input_service: Optional[InputService] = None,
        monitor_service: Optional[MonitorService] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._adb = adb_client or AdbClient(
            adb_path=self._settings.adb.path,
            default_timeout=self._settings.adb.command_timeout,
            server_port=self._settings.adb.server_port,
        )
        self._device_service = device_service or DeviceService(self._adb)
        self._input_service = input_service or InputService(self._adb)
        self._monitor_service = monitor_service or MonitorService(self._adb)
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> str:
        """
        Verify ADB is available and optionally start the ADB server.

        Returns:
            The ADB version string.

        Raises:
            AdbNotFoundError: If the ADB binary can't be resolved.
        """
        version = self._adb.verify_adb()
        if self._settings.adb.auto_start_server:
            try:
                self._adb.start_server()
            except Exception:
                logger.warning("Failed to start ADB server", exc_info=True)
        self._initialized = True
        logger.info("AppController initialized, ADB: %s", version)
        return version

    def shutdown(self) -> None:
        """Stop all monitoring threads and optionally kill the ADB server. Idempotent."""
        self._monitor_service.stop_all()
        if self._settings.adb.kill_server_on_exit:
            try:
                self._adb.kill_server()
            except Exception:
                logger.warning("Failed to kill ADB server on exit", exc_info=True)
        logger.info("AppController shut down")

    def __enter__(self) -> "AppController":
        self.initialize()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------

    def list_devices(self, refresh: bool = True) -> list[Device]:
        if refresh:
            return self._device_service.refresh_devices()
        return self._device_service.list_devices()

    def get_device(self, serial: str) -> Optional[Device]:
        return self._device_service.get_device(serial)

    def pair_device(self, host: str, port: int, code: str) -> bool:
        return self._device_service.pair_device(host, port, code)

    def connect_device(self, host: str, port: int = 5555, remember: bool = True) -> Device:
        return self._device_service.connect_device(host, port, remember)

    def disconnect_device(self, serial: str) -> bool:
        return self._device_service.disconnect_device(serial)

    def auto_reconnect(self) -> list[Device]:
        return self._device_service.auto_reconnect_trusted()

    def list_trusted_devices(self) -> list:
        return self._device_service.list_trusted_devices()

    def forget_device(self, serial: str) -> bool:
        return self._device_service.forget_device(serial)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def tap(self, serial: str, x: int, y: int) -> None:
        self._input_service.tap(serial, x, y)

    def double_tap(self, serial: str, x: int, y: int) -> None:
        self._input_service.double_tap(serial, x, y)

    def long_press(self, serial: str, x: int, y: int, duration_ms: int = 1000) -> None:
        self._input_service.long_press(serial, x, y, duration_ms)

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        self._input_service.swipe(serial, x1, y1, x2, y2, duration_ms)

    def type_text(self, serial: str, text: str) -> None:
        self._input_service.type_text(serial, text)

    def key_event(self, serial: str, keycode: int) -> None:
        self._input_service.key_event(serial, keycode)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def push_file(self, serial: str, local: Path, remote: str) -> None:
        self._adb.push(serial, local, remote)

    def pull_file(self, serial: str, remote: str, local: Path) -> None:
        self._adb.pull(serial, remote, local)

    # ------------------------------------------------------------------
    # APK management
    # ------------------------------------------------------------------

    def install_apk(self, serial: str, apk_path: Path, replace: bool = True) -> None:
        self._adb.install(serial, apk_path, replace=replace)

    def uninstall_app(self, serial: str, package: str) -> None:
        self._adb.uninstall(serial, package)

    # ------------------------------------------------------------------
    # Screenshot & recording
    # ------------------------------------------------------------------

    def take_screenshot(self, serial: str, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        self._adb.screenshot(serial, output)
        return output

    def start_screen_record(
        self, serial: str, remote_path: str = "/sdcard/void_rec.mp4"
    ) -> subprocess.Popen:
        return self._adb.screenrecord(serial, remote_path)

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def shell(self, serial: str, command: str) -> str:
        return self._adb.shell(serial, command).stdout

    # ------------------------------------------------------------------
    # Reboot
    # ------------------------------------------------------------------

    def reboot(self, serial: str, mode: str = "") -> None:
        self._adb.reboot(serial, mode)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def start_monitoring(
        self, serial: str, interval: float = 2.0, callback: Optional[SnapshotCallback] = None
    ) -> None:
        self._monitor_service.start(serial, interval, callback)

    def stop_monitoring(self, serial: str) -> None:
        self._monitor_service.stop(serial)

    def is_monitoring(self, serial: str) -> bool:
        return self._monitor_service.is_monitoring(serial)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def settings(self) -> AppSettings:
        return self._settings

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def adb(self) -> AdbClient:
        """Escape hatch to the underlying :class:`AdbClient` for advanced use."""
        return self._adb
