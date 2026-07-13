"""
The main synchronous SDK entry point: :class:`VoidRemote`.

    from voidremote import VoidRemote

    client = VoidRemote()
    devices = client.devices()
    device = devices.first()
    device.tap(500, 800)
"""

from __future__ import annotations

import logging
from typing import Iterator, Optional, Sequence, overload

from voidremote.adb.client import AdbError, AdbNotFoundError
from voidremote.adb.client import AdbTimeoutError as _AdbTimeoutError
from voidremote.api.device import Device
from voidremote.api.exceptions import (
    AdbCommandError,
    AdbNotAvailableError,
    AdbTimeoutError,
    ConnectionError,
    DeviceNotFoundError,
    NoDevicesError,
)
from voidremote.api.pairing import PairingSession
from voidremote.config.settings import AppSettings
from voidremote.controllers.app_controller import AppController

logger = logging.getLogger(__name__)


class DeviceList(Sequence[Device]):
    """
    An immutable, list-like collection of :class:`Device`.

    Supports indexing, iteration, ``len()``, and a couple of convenience
    accessors (:meth:`first`, :meth:`get`) on top of plain ``Sequence``
    behavior.
    """

    def __init__(self, devices: list[Device]) -> None:
        self._devices = devices

    def first(self) -> Device:
        """
        Return the first device.

        Raises:
            NoDevicesError: If the list is empty.
        """
        if not self._devices:
            raise NoDevicesError(
                "No devices available. Connect a device with `client.connect(host)` "
                "or pair one with `client.pair(host, port, code)` first."
            )
        return self._devices[0]

    def get(self, serial: str) -> Device:
        """
        Return the device with the given serial.

        Raises:
            DeviceNotFoundError: If no device matches.
        """
        for d in self._devices:
            if d.serial == serial:
                return d
        raise DeviceNotFoundError(f"No device with serial {serial!r}")

    def online(self) -> "DeviceList":
        """Return only devices currently online."""
        return DeviceList([d for d in self._devices if d.is_online])

    @overload
    def __getitem__(self, index: int) -> Device: ...
    @overload
    def __getitem__(self, index: slice) -> "DeviceList": ...

    def __getitem__(self, index: int | slice) -> "Device | DeviceList":
        if isinstance(index, slice):
            return DeviceList(self._devices[index])
        return self._devices[index]

    def __len__(self) -> int:
        return len(self._devices)

    def __iter__(self) -> Iterator[Device]:
        return iter(self._devices)

    def __repr__(self) -> str:
        return f"DeviceList({self._devices!r})"

    def __bool__(self) -> bool:
        return bool(self._devices)


class VoidRemote:
    """
    The main entry point for the VoidRemote SDK.

    Wraps ADB device discovery, wireless pairing, and per-device control
    behind a small, typed, Pythonic API. Talks to the ``adb`` binary on
    your PATH (or wherever ``adb_path`` points) — no root or special
    permissions are required beyond what ADB itself needs.

    Example:
        >>> from voidremote import VoidRemote
        >>> client = VoidRemote()
        >>> client.start()                       # doctest: +SKIP
        >>> device = client.devices().first()     # doctest: +SKIP
        >>> device.tap(500, 800).text("hello")    # doctest: +SKIP

    Also usable as a context manager, which calls :meth:`start` on
    entry and :meth:`close` on exit:

        >>> with VoidRemote() as client:          # doctest: +SKIP
        ...     for device in client.devices():
        ...         print(device.name, device.battery_level)
    """

    def __init__(
        self,
        adb_path: str = "adb",
        settings: Optional[AppSettings] = None,
        auto_start: bool = False,
    ) -> None:
        """
        Args:
            adb_path: Path to the ``adb`` binary. Defaults to ``"adb"``,
                resolved via PATH.
            settings: Advanced: inject a pre-built
                :class:`~voidremote.config.settings.AppSettings`. Most
                users don't need this.
            auto_start: If True, call :meth:`start` immediately (verifies
                ADB and starts the server). Off by default so
                constructing a client never has side effects or can
                raise — call :meth:`start` explicitly, or use the
                ``with VoidRemote() as client:`` form.
        """
        effective_settings = settings or AppSettings()
        if adb_path != "adb":
            effective_settings.adb.path = adb_path
        self._controller = AppController(effective_settings)
        if auto_start:
            self.start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> str:
        """
        Verify ADB is installed and reachable, and start the ADB server
        if it isn't running.

        Returns:
            The ``adb version`` output.

        Raises:
            AdbNotAvailableError: If the ``adb`` binary can't be found.
        """
        try:
            return self._controller.initialize()
        except AdbNotFoundError as exc:
            raise AdbNotAvailableError(str(exc)) from exc

    def close(self) -> None:
        """Stop all background monitoring threads. Safe to call multiple times."""
        self._controller.shutdown()

    def __enter__(self) -> "VoidRemote":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def devices(self, refresh: bool = True) -> DeviceList:
        """
        List devices currently visible to ADB (USB and wireless).

        Args:
            refresh: Re-query ADB before returning. Set False to reuse
                the last known list without a round-trip.
        """
        try:
            raw_devices = self._controller.list_devices(refresh=refresh)
        except AdbError as exc:
            raise self._translate_error(exc) from exc
        return DeviceList([Device(d, self._controller) for d in raw_devices])

    def device(self, serial: str) -> Device:
        """
        Get a single device by serial.

        Raises:
            DeviceNotFoundError: If no such device is currently visible.
        """
        raw = self._controller.get_device(serial)
        if raw is None:
            for d in self.devices():
                if d.serial == serial:
                    return d
            raise DeviceNotFoundError(f"No device with serial {serial!r}")
        return Device(raw, self._controller)

    # ------------------------------------------------------------------
    # Pairing & connection
    # ------------------------------------------------------------------

    def pair(self, host: str, port: int, code: str) -> PairingSession:
        """
        Start a wireless-debugging pairing session.

        Returns a :class:`PairingSession`; call ``.connect()`` on it to
        finish pairing and get a ready-to-use :class:`Device`, or use
        :meth:`pair_and_connect` to do both in one call.
        """
        return PairingSession(self._controller, host, port, code)

    def pair_and_connect(self, host: str, port: int, code: str, adb_port: int = 5555) -> Device:
        """Pair and connect in a single call. See :meth:`pair` for details."""
        return self.pair(host, port, code).connect(adb_port=adb_port)

    def connect(self, host: str, port: int = 5555, remember: bool = True) -> Device:
        """
        Connect to a device already reachable over TCP/IP (already
        paired, or with ``adb tcpip`` already enabled).

        Raises:
            ConnectionError: If the device doesn't respond.
        """
        try:
            raw = self._controller.connect_device(host, port, remember=remember)
        except AdbError as exc:
            raise ConnectionError(f"Could not connect to {host}:{port}: {exc}") from exc
        return Device(raw, self._controller)

    def auto_reconnect(self) -> DeviceList:
        """Reconnect every previously-remembered ("trusted") device that allows it."""
        raw_devices = self._controller.auto_reconnect()
        return DeviceList([Device(d, self._controller) for d in raw_devices])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_error(exc: AdbError) -> Exception:
        if isinstance(exc, AdbNotFoundError):
            return AdbNotAvailableError(str(exc))
        if isinstance(exc, _AdbTimeoutError):
            return AdbTimeoutError(str(exc))
        return AdbCommandError(str(exc), returncode=exc.returncode, stderr=exc.stderr)

    def __repr__(self) -> str:
        return f"VoidRemote(adb_path={self._controller.settings.adb.path!r})"
