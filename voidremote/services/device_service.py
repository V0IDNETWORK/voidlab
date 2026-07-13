"""
Device management service.

High-level operations over :class:`~voidremote.adb.client.AdbClient`:
discovery, pairing, connection, info retrieval, and trusted-device
persistence. This is what the controller layer and the public SDK
delegate to.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from voidremote.adb.client import AdbClient, AdbError
from voidremote.adb.device_parser import build_device_from_raw, parse_devices_output, parse_getprop
from voidremote.config.settings import TRUSTED_DEVICES_FILE
from voidremote.models.device import ConnectionConfig, Device, DeviceState, PairingInfo, TrustedDevice
from voidremote.utils.security import validate_host, validate_port

logger = logging.getLogger(__name__)


class DeviceService:
    """Orchestrates device discovery, connection, and persistent trusted-device state."""

    def __init__(self, adb: AdbClient, trusted_devices_file: Optional[Path] = None) -> None:
        self._adb = adb
        self._devices: dict[str, Device] = {}
        self._trusted: dict[str, TrustedDevice] = {}
        self._trusted_file = trusted_devices_file or TRUSTED_DEVICES_FILE
        self._load_trusted_devices()

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def refresh_devices(self) -> list[Device]:
        """Refresh and return the list of currently connected ADB devices."""
        raw = self._adb.list_devices_raw()
        entries = parse_devices_output(raw)
        discovered: dict[str, Device] = {}

        for entry in entries:
            serial, state = entry["serial"], entry["state"]
            try:
                discovered[serial] = self._get_device_with_info(serial, state)
            except Exception as exc:
                logger.warning("Failed to get info for %s: %s", serial, exc)
                existing = self._devices.get(serial)
                if existing:
                    discovered[serial] = existing

        self._devices = discovered
        logger.debug("Refreshed devices: %d found", len(self._devices))
        return list(self._devices.values())

    def get_device(self, serial: str) -> Optional[Device]:
        return self._devices.get(serial)

    def list_devices(self) -> list[Device]:
        return list(self._devices.values())

    # ------------------------------------------------------------------
    # Pairing & connection
    # ------------------------------------------------------------------

    def pair_device(self, host: str, port: int, code: str) -> bool:
        """
        Pair a device over wireless debugging.

        Raises:
            AdbError: If pairing fails.
            ValueError: If host/port/code are invalid.
        """
        validated_host = validate_host(host)
        validated_port = validate_port(port)
        pairing = PairingInfo(host=validated_host, port=validated_port, pairing_code=code)
        result = self._adb.pair(pairing)
        success = "successfully paired" in result.stdout.lower()
        if success:
            logger.info("Paired successfully with %s:%d", validated_host, validated_port)
        return success

    def connect_device(self, host: str, port: int = 5555, remember: bool = True) -> Device:
        """
        Connect to an Android device over TCP/IP.

        Raises:
            AdbError: If connection fails or the device doesn't appear
                in `adb devices` afterward.
        """
        validated_host = validate_host(host)
        validated_port = validate_port(port)
        config = ConnectionConfig(host=validated_host, port=validated_port)
        self._adb.connect(config)

        self.refresh_devices()
        serial = f"{validated_host}:{validated_port}"
        device = self._devices.get(serial)
        if device is None:
            raise AdbError(f"Device {serial} not found after connect")

        if remember:
            self._save_trusted(device)
        return device

    def disconnect_device(self, serial: str) -> bool:
        """Disconnect a wireless device. No-op (returns False) for USB serials."""
        if ":" not in serial:
            logger.warning("disconnect_device called on non-wireless serial %s — skipping", serial)
            return False
        host, _, port_str = serial.rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            port = 5555
        self._adb.disconnect(host, port)
        if serial in self._devices:
            self._devices[serial].state = DeviceState.DISCONNECTED
        return True

    # ------------------------------------------------------------------
    # Device info
    # ------------------------------------------------------------------

    def _get_device_with_info(self, serial: str, state: str) -> Device:
        props: dict[str, str] = {}
        extended: dict[str, str] = {}

        if state == "device":
            probes: dict[str, str] = {
                "battery_raw": "dumpsys battery",
                "resolution": "wm size",
                "density": "wm density",
                "meminfo": "cat /proc/meminfo",
                "storage_raw": "df /data",
            }
            try:
                props = parse_getprop(self._adb.shell(serial, "getprop").stdout)
            except Exception as exc:
                logger.debug("getprop failed for %s: %s", serial, exc)

            for key, cmd in probes.items():
                try:
                    extended[key] = self._adb.shell(serial, cmd).stdout
                except Exception as exc:
                    logger.debug("%s failed for %s: %s", cmd, serial, exc)

            try:
                extended["ip_address"] = self._parse_ip(serial)
            except Exception as exc:
                logger.debug("IP lookup failed for %s: %s", serial, exc)

        return build_device_from_raw(serial, state, props, extended)

    def _parse_ip(self, serial: str) -> str:
        from voidremote.adb.device_parser import parse_ip_address
        return parse_ip_address(self._adb.shell(serial, "ip addr show wlan0").stdout)

    # ------------------------------------------------------------------
    # Trusted devices
    # ------------------------------------------------------------------

    def _save_trusted(self, device: Device) -> None:
        serial = device.serial
        self._trusted[serial] = TrustedDevice(
            serial=serial, host=device.host, port=device.port,
            alias=device.alias, last_connected=datetime.now(),
        )
        self._persist_trusted()
        logger.debug("Saved trusted device: %s", serial)

    def _load_trusted_devices(self) -> None:
        if not self._trusted_file.exists():
            return
        try:
            data: list[dict] = json.loads(self._trusted_file.read_text(encoding="utf-8"))
            for entry in data:
                td = TrustedDevice(
                    serial=entry["serial"],
                    host=entry["host"],
                    port=entry["port"],
                    alias=entry.get("alias"),
                    last_connected=(
                        datetime.fromisoformat(entry["last_connected"])
                        if entry.get("last_connected") else None
                    ),
                    auto_connect=entry.get("auto_connect", True),
                    tags=entry.get("tags", []),
                )
                self._trusted[td.serial] = td
            logger.debug("Loaded %d trusted devices", len(self._trusted))
        except Exception as exc:
            logger.warning("Failed to load trusted devices: %s", exc)

    def _persist_trusted(self) -> None:
        self._trusted_file.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            {
                "serial": td.serial,
                "host": td.host,
                "port": td.port,
                "alias": td.alias,
                "last_connected": td.last_connected.isoformat() if td.last_connected else None,
                "auto_connect": td.auto_connect,
                "tags": td.tags,
            }
            for td in self._trusted.values()
        ]
        self._trusted_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def list_trusted_devices(self) -> list[TrustedDevice]:
        return list(self._trusted.values())

    def forget_device(self, serial: str) -> bool:
        if serial in self._trusted:
            del self._trusted[serial]
            self._persist_trusted()
            return True
        return False

    def auto_reconnect_trusted(self) -> list[Device]:
        """Attempt to reconnect all ``auto_connect`` trusted devices; return the successes."""
        reconnected: list[Device] = []
        for td in self._trusted.values():
            if not td.auto_connect or not td.host:
                continue
            try:
                reconnected.append(self.connect_device(td.host, td.port, remember=False))
                logger.info("Auto-reconnected: %s", td.serial)
            except Exception as exc:
                logger.debug("Auto-reconnect failed for %s: %s", td.serial, exc)
        return reconnected
