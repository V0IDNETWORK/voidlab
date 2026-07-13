"""
VoidRemote SDK — Wireless Debugging Pairing

Shows both the step-by-step PairingSession flow and the one-call
shortcut. Requires a device with Wireless Debugging's pairing screen
open (Settings -> Developer Options -> Wireless Debugging -> Pair
device with pairing code), which shows an IP, a pairing port, and a
6-digit code.

Run:
    python examples/pairing.py
"""

from __future__ import annotations

from voidremote import PairingError, VoidRemote


def pair_step_by_step(client: VoidRemote) -> None:
    host = input("Device IP: ").strip()
    port = int(input("Pairing port: ").strip())
    code = input("6-digit code: ").strip()

    session = client.pair(host=host, port=port, code=code)
    print(f"Pairing with {session.host}:{session.port}...")

    try:
        result = session.pair()
    except PairingError as exc:
        print(f"Pairing failed: {exc}")
        return

    print(f"Paired: {result.paired}")

    device = session.connect()  # connects on the regular ADB port (5555)
    print(f"Connected: {device.name}")


def pair_one_call(client: VoidRemote, host: str, port: int, code: str) -> None:
    try:
        device = client.pair_and_connect(host=host, port=port, code=code)
        print(f"Connected: {device.name}")
    except PairingError as exc:
        print(f"Pairing failed: {exc}")


if __name__ == "__main__":
    client = VoidRemote()
    client.start()
    pair_step_by_step(client)
    client.close()
