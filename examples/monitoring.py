"""
VoidRemote SDK — Background Monitoring

Polls CPU, RAM, and battery for a device on a background thread and
prints a live line per sample. Ctrl+C to stop.

Run:
    python examples/monitoring.py
"""

from __future__ import annotations

import time

from voidremote import DeviceSnapshot, NoDevicesError, VoidRemote


def on_snapshot(snapshot: DeviceSnapshot) -> None:
    charging = " ⚡" if snapshot.battery_is_charging else ""
    print(
        f"\r{snapshot.timestamp:%H:%M:%S}  "
        f"CPU {snapshot.cpu_usage:5.1f}%  "
        f"RAM {snapshot.ram_usage_percent:5.1f}%  "
        f"Battery {snapshot.battery_level:3d}%{charging}   ",
        end="",
        flush=True,
    )


def main() -> None:
    client = VoidRemote()
    client.start()

    try:
        device = client.devices().first()
    except NoDevicesError:
        print("No device connected.")
        return

    print(f"Monitoring {device.name} — Ctrl+C to stop\n")
    device.monitor(interval=2.0, callback=on_snapshot)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        device.stop_monitoring()
        client.close()


if __name__ == "__main__":
    main()
