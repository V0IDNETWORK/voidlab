"""
VoidRemote SDK — Async Usage

Taps every connected device concurrently using AsyncVoidRemote. See
the README's "Async" section for why this runs the sync
implementation via asyncio.to_thread rather than native async I/O —
it's still enough to get real concurrency across multiple devices'
subprocess calls.

Run:
    python examples/async_example.py
"""

from __future__ import annotations

import asyncio

from voidremote import AsyncVoidRemote, NoDevicesError


async def main() -> None:
    async with AsyncVoidRemote() as client:
        try:
            devices = await client.devices()
        except NoDevicesError:
            print("No devices connected.")
            return

        print(f"{len(devices)} device(s) — tapping all concurrently")

        # Runs each device's tap() in its own thread, concurrently.
        await asyncio.gather(*(device.tap(500, 800) for device in devices))

        # Same pattern for reading data back.
        versions = await asyncio.gather(*(device.shell("getprop ro.build.version.release") for device in devices))
        for device, version in zip(devices, versions):
            print(f"{device.name}: Android {version.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
