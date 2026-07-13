"""Parses ADB device listing and device property output into typed models."""

from __future__ import annotations

import logging
import re
from typing import Optional

from voidremote.models.device import (
    BatteryInfo,
    ConnectionType,
    CpuInfo,
    Device,
    DeviceCapability,
    DeviceInfo,
    DeviceState,
    NetworkInfo,
    StorageInfo,
)

logger = logging.getLogger(__name__)

_DEVICE_LINE_RE = re.compile(r"^(?P<serial>\S+)\s+(?P<state>\w+)(?:\s+(?P<attrs>.*))?$")
_ATTR_RE = re.compile(r"(\w+):(\S+)")
_RESOLUTION_RE = re.compile(r"Physical size:\s*(\d+)x(\d+)")
_DENSITY_RE = re.compile(r"Physical density:\s*(\d+)")
_IP_RE = re.compile(r"inet\s+([\d.]+)/")
_GETPROP_RE = re.compile(r"\[([^\]]+)\]:\s*\[([^\]]*)\]")
_MEMTOTAL_RE = re.compile(r"MemTotal:\s+(\d+)\s+kB")
_MEMAVAIL_RE = re.compile(r"MemAvailable:\s+(\d+)\s+kB")


def parse_devices_output(raw: str) -> list[dict[str, str]]:
    """Parse the output of ``adb devices -l`` into a list of device dicts."""
    devices: list[dict[str, str]] = []
    lines = raw.strip().splitlines()

    for line in lines[1:]:  # skip "List of devices attached" header
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        m = _DEVICE_LINE_RE.match(line)
        if not m:
            continue
        entry: dict[str, str] = {"serial": m.group("serial"), "state": m.group("state")}
        for km in _ATTR_RE.finditer(m.group("attrs") or ""):
            entry[km.group(1)] = km.group(2)
        devices.append(entry)

    return devices


def state_from_string(state_str: str) -> DeviceState:
    """Map an ADB state string to :class:`DeviceState`."""
    mapping: dict[str, DeviceState] = {
        "device": DeviceState.ONLINE,
        "offline": DeviceState.OFFLINE,
        "unauthorized": DeviceState.UNAUTHORIZED,
        "connecting": DeviceState.CONNECTING,
    }
    return mapping.get(state_str.lower(), DeviceState.UNKNOWN)


def connection_type_from_serial(serial: str) -> ConnectionType:
    """Infer connection type from an ADB serial string."""
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$", serial):
        return ConnectionType.WIRELESS
    if re.match(r"^emulator-\d+$", serial):
        return ConnectionType.EMULATOR
    return ConnectionType.USB


def parse_battery(raw: str) -> BatteryInfo:
    """Parse ``dumpsys battery`` output."""

    def _int(pattern: str) -> int:
        m = re.search(pattern, raw, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    def _bool(pattern: str) -> bool:
        m = re.search(pattern, raw, re.IGNORECASE)
        return bool(m) and m.group(1).strip().lower() == "true"

    level = _int(r"level:\s*(\d+)")
    is_ac = _bool(r"AC powered:\s*(true|false)")
    is_usb = _bool(r"USB powered:\s*(true|false)")
    status_m = re.search(r"status:\s*(\d+)", raw)
    is_charging = bool(status_m) and status_m.group(1) in ("2", "5")  # CHARGING, FULL

    health_codes = {
        1: "unknown", 2: "good", 3: "overheat", 4: "dead",
        5: "over voltage", 6: "unspecified failure", 7: "cold",
    }
    health_m = re.search(r"health:\s*(\d+)", raw)
    health = health_codes.get(int(health_m.group(1)), "unknown") if health_m else "unknown"

    tech_m = re.search(r"technology:\s*(\S+)", raw)
    technology = tech_m.group(1) if tech_m else "unknown"

    return BatteryInfo(
        level=level,
        is_charging=is_charging,
        is_ac_powered=is_ac,
        is_usb_powered=is_usb,
        voltage=float(_int(r"voltage:\s*(\d+)")),
        temperature=float(_int(r"temperature:\s*(\d+)")),
        health=health,
        technology=technology,
    )


def parse_storage(raw_df: str) -> StorageInfo:
    """Parse ``df`` output for a mount point."""
    lines = raw_df.strip().splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 6:
            try:
                total_kb, used_kb, avail_kb = int(parts[1]), int(parts[2]), int(parts[3])
                mount = parts[5]
                return StorageInfo(
                    total_bytes=total_kb * 1024,
                    used_bytes=used_kb * 1024,
                    available_bytes=avail_kb * 1024,
                    mount_point=mount,
                )
            except (ValueError, IndexError):
                continue
    return StorageInfo()


def parse_screen_resolution(wm_size_output: str) -> tuple[int, int]:
    """Parse ``wm size`` output, return (width, height)."""
    m = _RESOLUTION_RE.search(wm_size_output)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def parse_density(wm_density_output: str) -> int:
    """Parse ``wm density`` output, return DPI."""
    m = _DENSITY_RE.search(wm_density_output)
    return int(m.group(1)) if m else 0


def parse_ip_address(ip_addr_output: str) -> str:
    """Parse IP from ``ip addr show wlan0`` output."""
    m = _IP_RE.search(ip_addr_output)
    return m.group(1) if m else ""


def parse_meminfo(meminfo: str) -> tuple[int, int]:
    """Parse ``/proc/meminfo``, return (total_bytes, available_bytes)."""
    tm = _MEMTOTAL_RE.search(meminfo)
    am = _MEMAVAIL_RE.search(meminfo)
    total_kb = int(tm.group(1)) if tm else 0
    avail_kb = int(am.group(1)) if am else 0
    return total_kb * 1024, avail_kb * 1024


def parse_getprop(raw: str) -> dict[str, str]:
    """Parse ``getprop`` output into a property dict."""
    return {m.group(1): m.group(2) for m in _GETPROP_RE.finditer(raw)}


def build_device_from_raw(
    serial: str,
    state_str: str,
    props: dict[str, str],
    extended_info: Optional[dict[str, str]] = None,
) -> Device:
    """Construct a :class:`Device` from parsed ADB data."""
    ext = extended_info or {}
    cpu = CpuInfo(
        abi=props.get("ro.product.cpu.abi", "unknown"),
        abi_list=[a for a in props.get("ro.product.cpu.abilist", "").split(",") if a],
    )
    network = NetworkInfo(ip_address=ext.get("ip_address", ""))
    battery = parse_battery(ext["battery_raw"]) if ext.get("battery_raw") else BatteryInfo()
    storage = parse_storage(ext["storage_raw"]) if ext.get("storage_raw") else StorageInfo()

    width, height = parse_screen_resolution(ext["resolution"]) if "resolution" in ext else (0, 0)
    total_ram, avail_ram = parse_meminfo(ext["meminfo"]) if "meminfo" in ext else (0, 0)

    info = DeviceInfo(
        serial=serial,
        model=props.get("ro.product.model", "Unknown"),
        manufacturer=props.get("ro.product.manufacturer", "Unknown"),
        brand=props.get("ro.product.brand", "Unknown"),
        product=props.get("ro.product.name", "Unknown"),
        device_name=props.get("ro.product.device", "Unknown"),
        android_version=props.get("ro.build.version.release", "Unknown"),
        sdk_version=int(props.get("ro.build.version.sdk", "0") or "0"),
        build_id=props.get("ro.build.id", "Unknown"),
        build_fingerprint=props.get("ro.build.fingerprint", ""),
        screen_width=width,
        screen_height=height,
        screen_density=parse_density(ext.get("density", "")),
        battery=battery,
        storage=storage,
        cpu=cpu,
        network=network,
        ram_total_bytes=total_ram,
        ram_available_bytes=avail_ram,
    )

    conn_type = connection_type_from_serial(serial)
    host, port = "", 5555
    if conn_type == ConnectionType.WIRELESS and ":" in serial:
        host, _, port_str = serial.rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            port = 5555

    capabilities: list[DeviceCapability] = []
    if state_str == "device":
        capabilities = [
            DeviceCapability.SHELL,
            DeviceCapability.FILE_TRANSFER,
            DeviceCapability.INPUT_CONTROL,
            DeviceCapability.PACKAGE_MANAGER,
            DeviceCapability.MONITORING,
        ]
        if info.sdk_version >= 21:
            capabilities.append(DeviceCapability.SCREEN_MIRROR)

    return Device(
        info=info,
        state=state_from_string(state_str),
        connection_type=conn_type,
        host=host,
        port=port,
        capabilities=capabilities,
    )
