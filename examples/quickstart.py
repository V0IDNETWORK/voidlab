"""
VoidRemote SDK — Quick Start

Minimal example covering discovery, input, files, and shell — the
same code shown in the README. Requires a real device connected via
`adb` (USB debugging enabled, or already paired/connected wirelessly).

Run:
    pip install voidremote
    python examples/quickstart.py
"""

from __future__ import annotations

from voidremote import AdbNotAvailableError, NoDevicesError, VoidRemote, VoidRemoteError


def main() -> None:
    client = VoidRemote()

    try:
        version = client.start()
        print(f"Using {version}")
    except AdbNotAvailableError:
        print("adb isn't installed or isn't on PATH. Install Android Platform Tools:")
        print("  https://developer.android.com/tools/releases/platform-tools")
        return

    try:
        device = client.devices().first()
    except NoDevicesError:
        print("No device connected. Enable USB debugging, or pair one:")
        print("  client.pair_and_connect(host, port, code)")
        return

    print(f"Connected: {device.name} (Android {device.android_version})")
    print(f"Battery: {device.battery_level}% {'(charging)' if device.is_charging else ''}")
    print(f"Resolution: {device.resolution[0]}x{device.resolution[1]}")

    # Input — chainable
    device.tap(500, 800).text("hello from voidremote")

    # Shell
    packages = device.shell("pm list packages -3").splitlines()
    print(f"{len(packages)} user-installed packages")

    # Screen capture
    output = device.screenshot("quickstart_screenshot.png")
    print(f"Saved screenshot: {output}")

    client.close()


if __name__ == "__main__":
    try:
        main()
    except VoidRemoteError as exc:
        print(f"VoidRemote error: {exc}")
