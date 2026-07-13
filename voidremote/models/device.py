"""
Device data models.

These are internal representations. Stable public re-exports live in
``voidremote.api``; import from there unless you are working on
VoidRemote itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceState(str, Enum):
    """Connection state of an ADB device."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    CONNECTING = "connecting"
    PAIRING = "pairing"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


class ConnectionType(str, Enum):
    """How the device is connected."""

    USB = "usb"
    WIRELESS = "wireless"
    EMULATOR = "emulator"


class DeviceCapability(str, Enum):
    """Optional capabilities a device may support."""

    SCREEN_MIRROR = "screen_mirror"
    FILE_TRANSFER = "file_transfer"
    SHELL = "shell"
    INPUT_CONTROL = "input_control"
    PACKAGE_MANAGER = "package_manager"
    MONITORING = "monitoring"


class BatteryInfo(BaseModel):
    """Battery status information."""

    model_config = ConfigDict(frozen=True)

    level: int = Field(default=0, ge=0, le=100, description="Battery percentage 0-100")
    is_charging: bool = Field(default=False)
    is_ac_powered: bool = Field(default=False)
    is_usb_powered: bool = Field(default=False)
    voltage: float = Field(default=0.0, description="Voltage in mV")
    temperature: float = Field(default=0.0, description="Temperature in tenths of degree Celsius")
    health: str = Field(default="unknown")
    technology: str = Field(default="unknown")

    @property
    def temperature_celsius(self) -> float:
        """Temperature in Celsius."""
        return self.temperature / 10.0

    @property
    def voltage_volts(self) -> float:
        """Voltage in Volts."""
        return self.voltage / 1000.0


class StorageInfo(BaseModel):
    """Storage usage information."""

    model_config = ConfigDict(frozen=True)

    total_bytes: int = Field(default=0, ge=0)
    available_bytes: int = Field(default=0, ge=0)
    used_bytes: int = Field(default=0, ge=0)
    mount_point: str = Field(default="/data")

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3)

    @property
    def available_gb(self) -> float:
        return self.available_bytes / (1024**3)

    @property
    def used_gb(self) -> float:
        return self.used_bytes / (1024**3)

    @property
    def usage_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0


class CpuInfo(BaseModel):
    """CPU information."""

    model_config = ConfigDict(frozen=True)

    abi: str = Field(default="unknown", description="Primary CPU ABI (e.g. arm64-v8a)")
    abi_list: list[str] = Field(default_factory=list)
    cores: int = Field(default=0, ge=0)
    governor: str = Field(default="unknown")
    usage_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    frequency_mhz: float = Field(default=0.0, ge=0.0)


class NetworkInfo(BaseModel):
    """Network connection information."""

    model_config = ConfigDict(frozen=True)

    ip_address: str = Field(default="")
    wifi_ssid: str = Field(default="")
    wifi_signal: int = Field(default=0, description="WiFi signal strength in dBm")
    mac_address: str = Field(default="")
    interface: str = Field(default="wlan0")


class DeviceInfo(BaseModel):
    """Complete static + dynamic device information."""

    model_config = ConfigDict(frozen=True)

    serial: str = Field(description="ADB serial identifier")
    model: str = Field(default="Unknown")
    manufacturer: str = Field(default="Unknown")
    brand: str = Field(default="Unknown")
    product: str = Field(default="Unknown")
    device_name: str = Field(default="Unknown")
    android_version: str = Field(default="Unknown")
    sdk_version: int = Field(default=0)
    build_id: str = Field(default="Unknown")
    build_fingerprint: str = Field(default="")
    screen_width: int = Field(default=0, ge=0)
    screen_height: int = Field(default=0, ge=0)
    screen_density: int = Field(default=0, ge=0, description="DPI")
    battery: BatteryInfo = Field(default_factory=BatteryInfo)
    storage: StorageInfo = Field(default_factory=StorageInfo)
    cpu: CpuInfo = Field(default_factory=CpuInfo)
    network: NetworkInfo = Field(default_factory=NetworkInfo)
    ram_total_bytes: int = Field(default=0, ge=0)
    ram_available_bytes: int = Field(default=0, ge=0)
    features: list[str] = Field(default_factory=list)

    @field_validator("serial")
    @classmethod
    def _validate_serial(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Device serial cannot be empty")
        return v.strip()

    @property
    def display_name(self) -> str:
        if self.model and self.model != "Unknown":
            return f"{self.manufacturer} {self.model}".strip()
        return self.serial

    @property
    def screen_resolution(self) -> str:
        if self.screen_width and self.screen_height:
            return f"{self.screen_width}x{self.screen_height}"
        return "Unknown"

    @property
    def ram_total_gb(self) -> float:
        return self.ram_total_bytes / (1024**3)

    @property
    def ram_available_gb(self) -> float:
        return self.ram_available_bytes / (1024**3)


class Device(BaseModel):
    """A connected ADB device with full state."""

    model_config = ConfigDict(use_enum_values=False)

    info: DeviceInfo
    state: DeviceState = Field(default=DeviceState.UNKNOWN)
    connection_type: ConnectionType = Field(default=ConnectionType.USB)
    host: str = Field(default="")
    port: int = Field(default=5555, ge=1, le=65535)
    is_trusted: bool = Field(default=False)
    connected_at: Optional[datetime] = Field(default=None)
    last_seen: Optional[datetime] = Field(default=None)
    capabilities: list[DeviceCapability] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    alias: Optional[str] = Field(default=None)

    @property
    def serial(self) -> str:
        return self.info.serial

    @property
    def display_name(self) -> str:
        return self.alias or self.info.display_name

    @property
    def is_connected(self) -> bool:
        return self.state == DeviceState.ONLINE

    @property
    def adb_address(self) -> str:
        """Network address for wireless devices, else the raw serial."""
        if self.connection_type == ConnectionType.WIRELESS and self.host:
            return f"{self.host}:{self.port}"
        return self.serial

    def has_capability(self, cap: DeviceCapability) -> bool:
        return cap in self.capabilities


@dataclass(frozen=True, slots=True)
class PairingInfo:
    """Parameters needed to pair a device over wireless debugging."""

    host: str
    port: int
    pairing_code: str
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("Host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")
        if not self.pairing_code:
            raise ValueError("Pairing code cannot be empty")


@dataclass(frozen=True, slots=True)
class ConnectionConfig:
    """Configuration for an ADB TCP/IP connection."""

    host: str
    port: int = 5555
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    keep_alive: bool = True

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("Host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")


@dataclass(slots=True)
class TrustedDevice:
    """A remembered device for auto-reconnect."""

    serial: str
    host: str
    port: int
    alias: Optional[str] = None
    last_connected: Optional[datetime] = None
    auto_connect: bool = True
    tags: list[str] = field(default_factory=list)
