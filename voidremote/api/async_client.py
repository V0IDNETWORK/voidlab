"""
Async wrapper around :class:`~voidremote.api.client.VoidRemote`.

Honest implementation note: ``adb`` is a subprocess-based CLI tool, not
a socket protocol VoidRemote speaks directly, so there's no native
async I/O to hook into here. :class:`AsyncVoidRemote` runs the same
synchronous, well-tested code as :class:`VoidRemote` inside
``asyncio.to_thread``, which keeps your event loop unblocked while a
command is in flight — the standard, correct way to make blocking I/O
"async" in Python. If you need true concurrency across many devices,
prefer :meth:`AsyncVoidRemote.devices` plus ``asyncio.gather`` over
several :class:`AsyncDevice` calls, which *will* run those ADB
subprocesses in parallel.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Iterator, Optional, Sequence

from voidremote.api.client import Device, DeviceList, VoidRemote
from voidremote.api.pairing import PairingSession
from voidremote.config.settings import AppSettings

logger = logging.getLogger(__name__)


class AsyncDevice:
    """
    Async counterpart of :class:`~voidremote.api.device.Device`.

    Every method mirrors the sync :class:`Device` API 1:1 but is a
    coroutine, executing the underlying call via ``asyncio.to_thread``.
    """

    def __init__(self, device: Device) -> None:
        self._device = device

    @property
    def serial(self) -> str:
        return self._device.serial

    @property
    def name(self) -> str:
        return self._device.name

    @property
    def android_version(self) -> str:
        return self._device.android_version

    @property
    def battery_level(self) -> int:
        return self._device.battery_level

    @property
    def is_online(self) -> bool:
        return self._device.is_online

    @property
    def sync(self) -> Device:
        """Escape hatch to the underlying sync :class:`Device`."""
        return self._device

    async def tap(self, x: int, y: int) -> "AsyncDevice":
        await asyncio.to_thread(self._device.tap, x, y)
        return self

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> "AsyncDevice":
        await asyncio.to_thread(self._device.swipe, x1, y1, x2, y2, duration_ms)
        return self

    async def text(self, value: str) -> "AsyncDevice":
        await asyncio.to_thread(self._device.text, value)
        return self

    async def key_event(self, keycode: int) -> "AsyncDevice":
        await asyncio.to_thread(self._device.key_event, keycode)
        return self

    async def shell(self, command: str) -> str:
        return await asyncio.to_thread(self._device.shell, command)

    async def push(self, local: str, remote: str) -> "AsyncDevice":
        await asyncio.to_thread(self._device.push, local, remote)
        return self

    async def pull(self, remote: str, local: str) -> str:
        result = await asyncio.to_thread(self._device.pull, remote, local)
        return str(result)

    async def install(self, apk_path: str, replace: bool = True) -> "AsyncDevice":
        await asyncio.to_thread(self._device.install, apk_path, replace)
        return self

    async def uninstall(self, package: str) -> "AsyncDevice":
        await asyncio.to_thread(self._device.uninstall, package)
        return self

    async def screenshot(self, output: str) -> str:
        result = await asyncio.to_thread(self._device.screenshot, output)
        return str(result)

    async def reboot(self, mode: str = "") -> None:
        await asyncio.to_thread(self._device.reboot, mode)

    def __repr__(self) -> str:
        return f"AsyncDevice(serial={self.serial!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AsyncDevice) and other.serial == self.serial

    def __hash__(self) -> int:
        return hash(self.serial)


class AsyncDeviceList(Sequence[AsyncDevice]):
    """Async counterpart of :class:`~voidremote.api.client.DeviceList`."""

    def __init__(self, devices: list[AsyncDevice]) -> None:
        self._devices = devices

    def first(self) -> AsyncDevice:
        from voidremote.api.exceptions import NoDevicesError
        if not self._devices:
            raise NoDevicesError("No devices available.")
        return self._devices[0]

    def __getitem__(self, index):  # type: ignore[no-untyped-def]
        if isinstance(index, slice):
            return AsyncDeviceList(self._devices[index])
        return self._devices[index]

    def __len__(self) -> int:
        return len(self._devices)

    def __iter__(self) -> Iterator[AsyncDevice]:
        return iter(self._devices)

    def __repr__(self) -> str:
        return f"AsyncDeviceList({self._devices!r})"


class AsyncVoidRemote:
    """
    Async entry point for the VoidRemote SDK.

    Example:
        >>> import asyncio
        >>> from voidremote import AsyncVoidRemote
        >>>
        >>> async def main():
        ...     async with AsyncVoidRemote() as client:
        ...         devices = await client.devices()
        ...         await asyncio.gather(*(d.tap(500, 800) for d in devices))
        >>>
        >>> asyncio.run(main())  # doctest: +SKIP
    """

    def __init__(self, adb_path: str = "adb", settings: Optional[AppSettings] = None) -> None:
        self._sync = VoidRemote(adb_path=adb_path, settings=settings, auto_start=False)

    async def start(self) -> str:
        return await asyncio.to_thread(self._sync.start)

    async def close(self) -> None:
        await asyncio.to_thread(self._sync.close)

    async def __aenter__(self) -> "AsyncVoidRemote":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def devices(self, refresh: bool = True) -> AsyncDeviceList:
        device_list = await asyncio.to_thread(self._sync.devices, refresh)
        return AsyncDeviceList([AsyncDevice(d) for d in device_list])

    async def device(self, serial: str) -> AsyncDevice:
        d = await asyncio.to_thread(self._sync.device, serial)
        return AsyncDevice(d)

    async def connect(self, host: str, port: int = 5555, remember: bool = True) -> AsyncDevice:
        d = await asyncio.to_thread(self._sync.connect, host, port, remember)
        return AsyncDevice(d)

    def pair(self, host: str, port: int, code: str) -> PairingSession:
        """Synchronous — pairing just validates arguments and returns a session object."""
        return self._sync.pair(host, port, code)

    async def pair_and_connect(self, host: str, port: int, code: str, adb_port: int = 5555) -> AsyncDevice:
        d = await asyncio.to_thread(self._sync.pair_and_connect, host, port, code, adb_port)
        return AsyncDevice(d)

    async def auto_reconnect(self) -> AsyncDeviceList:
        device_list = await asyncio.to_thread(self._sync.auto_reconnect)
        return AsyncDeviceList([AsyncDevice(d) for d in device_list])

    @property
    def sync(self) -> VoidRemote:
        """Escape hatch to the underlying sync :class:`VoidRemote`."""
        return self._sync

    def __repr__(self) -> str:
        return f"AsyncVoidRemote({self._sync!r})"
