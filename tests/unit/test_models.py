"""Unit tests for data models."""

from __future__ import annotations

import pytest

from voidremote.models.device import (
    ConnectionConfig,
    ConnectionType,
    Device,
    DeviceCapability,
    DeviceInfo,
    DeviceState,
    PairingInfo,
    StorageInfo,
)
from voidremote.models.device import BatteryInfo as BI


class TestBatteryInfo:
    def test_temperature_celsius(self) -> None:
        assert BI(temperature=280).temperature_celsius == pytest.approx(28.0)

    def test_voltage_volts(self) -> None:
        assert BI(voltage=4200).voltage_volts == pytest.approx(4.2)

    def test_defaults(self) -> None:
        b = BI()
        assert b.level == 0
        assert not b.is_charging


class TestStorageInfo:
    def test_usage_percent(self) -> None:
        s = StorageInfo(total_bytes=100 * 1024**3, used_bytes=60 * 1024**3, available_bytes=40 * 1024**3)
        assert s.usage_percent == pytest.approx(60.0)

    def test_zero_total(self) -> None:
        assert StorageInfo().usage_percent == 0.0

    def test_gb_properties(self) -> None:
        s = StorageInfo(total_bytes=1024**3, used_bytes=512 * 1024**2, available_bytes=512 * 1024**2)
        assert s.total_gb == pytest.approx(1.0)
        assert s.used_gb == pytest.approx(0.5)


class TestDeviceInfo:
    def test_display_name_with_model(self, sample_device_info: DeviceInfo) -> None:
        assert "Pixel" in sample_device_info.display_name

    def test_display_name_fallback(self) -> None:
        assert DeviceInfo(serial="abc123").display_name == "abc123"

    def test_screen_resolution(self, sample_device_info: DeviceInfo) -> None:
        assert sample_device_info.screen_resolution == "1080x2400"

    def test_screen_resolution_unknown(self) -> None:
        assert DeviceInfo(serial="abc123").screen_resolution == "Unknown"

    def test_serial_validation_empty(self) -> None:
        with pytest.raises(ValueError):
            DeviceInfo(serial="")

    def test_serial_validation_whitespace(self) -> None:
        with pytest.raises(ValueError):
            DeviceInfo(serial="   ")

    def test_serial_stripped(self) -> None:
        assert DeviceInfo(serial="  abc123  ").serial == "abc123"

    def test_ram_properties(self, sample_device_info: DeviceInfo) -> None:
        assert sample_device_info.ram_total_gb == pytest.approx(8.0)
        assert sample_device_info.ram_available_gb == pytest.approx(4.0)


class TestDevice:
    def test_is_connected_online(self, sample_device: Device) -> None:
        assert sample_device.is_connected is True

    def test_is_connected_offline(self, sample_device: Device) -> None:
        sample_device.state = DeviceState.OFFLINE
        assert sample_device.is_connected is False

    def test_serial_property(self, sample_device: Device) -> None:
        assert sample_device.serial == "192.168.1.50:5555"

    def test_adb_address_wireless(self, sample_device: Device) -> None:
        assert sample_device.adb_address == "192.168.1.50:5555"

    def test_adb_address_usb(self) -> None:
        device = Device(info=DeviceInfo(serial="ABC123DEF456"), connection_type=ConnectionType.USB)
        assert device.adb_address == "ABC123DEF456"

    def test_has_capability(self, sample_device: Device) -> None:
        assert sample_device.has_capability(DeviceCapability.SHELL)
        assert sample_device.has_capability(DeviceCapability.SCREEN_MIRROR)

    def test_display_name_alias(self, sample_device: Device) -> None:
        sample_device.alias = "My Phone"
        assert sample_device.display_name == "My Phone"

    def test_display_name_no_alias(self, sample_device: Device) -> None:
        sample_device.alias = None
        assert "Pixel" in sample_device.display_name


class TestPairingInfo:
    def test_valid(self) -> None:
        p = PairingInfo(host="192.168.1.1", port=37001, pairing_code="123456")
        assert p.host == "192.168.1.1"
        assert p.port == 37001

    def test_empty_host(self) -> None:
        with pytest.raises(ValueError):
            PairingInfo(host="", port=37001, pairing_code="123456")

    def test_invalid_port(self) -> None:
        with pytest.raises(ValueError):
            PairingInfo(host="192.168.1.1", port=0, pairing_code="123456")

    def test_empty_code(self) -> None:
        with pytest.raises(ValueError):
            PairingInfo(host="192.168.1.1", port=37001, pairing_code="")


class TestConnectionConfig:
    def test_valid(self) -> None:
        c = ConnectionConfig(host="192.168.1.1", port=5555)
        assert c.host == "192.168.1.1"
        assert c.port == 5555

    def test_empty_host(self) -> None:
        with pytest.raises(ValueError):
            ConnectionConfig(host="")

    def test_invalid_port(self) -> None:
        with pytest.raises(ValueError):
            ConnectionConfig(host="192.168.1.1", port=70000)
