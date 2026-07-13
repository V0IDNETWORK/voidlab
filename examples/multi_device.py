"""
VoidRemote SDK — Multiple Devices

Installing an APK across every connected device, and printing a status
table. This is the kind of thing you'd wire into a CI job.

Run:
    python examples/multi_device.py app-release.apk
"""

from __future__ import annotations

import sys

from voidremote import NoDevicesError, VoidRemote, VoidRemoteError


def main(apk_path: str) -> int:
    with VoidRemote() as client:
        try:
            devices = client.devices().online()
        except NoDevicesError:
            print("No devices connected.")
            return 1

        if not devices:
            print("No online devices.")
            return 1

        print(f"{len(devices)} device(s) found\n")

        failures = 0
        for device in devices:
            print(f"{device.name:<24} {device.serial:<24} ", end="", flush=True)
            try:
                device.install(apk_path)
                print("OK")
            except VoidRemoteError as exc:
                print(f"FAILED: {exc}")
                failures += 1

        return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python multi_device.py <path-to-apk>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
