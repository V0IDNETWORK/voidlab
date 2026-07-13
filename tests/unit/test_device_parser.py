"""Unit tests for ADB device output parsing."""

from __future__ import annotations

import pytest

from voidremote.adb.device_parser import (
    connection_type_from_serial,
    parse_battery,
    parse_devices_output,
    parse_getprop,
    parse_ip_address,
    parse_meminfo,
    parse_screen_resolution,
    parse_storage,
    state_from_string,
)
from voidremote.models.device import ConnectionType, DeviceState


class TestParseDevicesOutput:
    SAMPLE_OUTPUT = (
        "List of devices attached\n"
        "192.168.1.50:5555\tdevice product:pixel6 model:Pixel_6 device:pixel6\n"
        "emulator-5554\toffline\n"
        "ABC123XYZ\tunauthorized\n"
    )

    def test_parses_three_devices(self) -> None:
        assert len(parse_devices_output(self.SAMPLE_OUTPUT)) == 3

    def test_wireless_device(self) -> None:
        d = parse_devices_output(self.SAMPLE_OUTPUT)[0]
        assert d["serial"] == "192.168.1.50:5555"
        assert d["state"] == "device"
        assert d["model"] == "Pixel_6"

    def test_offline_device(self) -> None:
        assert parse_devices_output(self.SAMPLE_OUTPUT)[1]["state"] == "offline"

    def test_unauthorized_device(self) -> None:
        assert parse_devices_output(self.SAMPLE_OUTPUT)[2]["state"] == "unauthorized"

    def test_empty_output(self) -> None:
        assert parse_devices_output("List of devices attached\n") == []

    def test_skips_daemon_messages(self) -> None:
        output = "List of devices attached\n* daemon not running; starting now at tcp:5037\n192.168.1.1:5555\tdevice\n"
        assert len(parse_devices_output(output)) == 1


class TestStateFromString:
    def test_device(self) -> None:
        assert state_from_string("device") == DeviceState.ONLINE

    def test_offline(self) -> None:
        assert state_from_string("offline") == DeviceState.OFFLINE

    def test_unauthorized(self) -> None:
        assert state_from_string("unauthorized") == DeviceState.UNAUTHORIZED

    def test_unknown(self) -> None:
        assert state_from_string("something_else") == DeviceState.UNKNOWN

    def test_case_insensitive(self) -> None:
        assert state_from_string("DEVICE") == DeviceState.ONLINE


class TestConnectionTypeFromSerial:
    def test_wireless_ip_port(self) -> None:
        assert connection_type_from_serial("192.168.1.1:5555") == ConnectionType.WIRELESS

    def test_emulator(self) -> None:
        assert connection_type_from_serial("emulator-5554") == ConnectionType.EMULATOR

    def test_usb(self) -> None:
        assert connection_type_from_serial("ABC123DEF456") == ConnectionType.USB


class TestParseBattery:
    # status=2 is BatteryManager.BATTERY_STATUS_CHARGING — this is the
    # real Android status code, not the string "true"/"false" the old
    # buggy implementation incorrectly searched for.
    SAMPLE = """
Current Battery Service state:
  AC powered: false
  USB powered: true
  status: 2
  health: 2
  present: true
  level: 85
  scale: 100
  voltage: 4250
  temperature: 310
  technology: Li-ion
"""

    def test_level(self) -> None:
        assert parse_battery(self.SAMPLE).level == 85

    def test_charging_from_status_code(self) -> None:
        assert parse_battery(self.SAMPLE).is_charging is True

    def test_not_charging_status_code(self) -> None:
        not_charging = self.SAMPLE.replace("status: 2", "status: 3")  # DISCHARGING
        assert parse_battery(not_charging).is_charging is False

    def test_full_status_code_counts_as_charging(self) -> None:
        full = self.SAMPLE.replace("status: 2", "status: 5")  # FULL
        assert parse_battery(full).is_charging is True

    def test_usb_powered(self) -> None:
        assert parse_battery(self.SAMPLE).is_usb_powered is True

    def test_ac_not_powered(self) -> None:
        assert parse_battery(self.SAMPLE).is_ac_powered is False

    def test_voltage(self) -> None:
        assert parse_battery(self.SAMPLE).voltage == 4250

    def test_temperature(self) -> None:
        b = parse_battery(self.SAMPLE)
        assert b.temperature == 310
        assert b.temperature_celsius == pytest.approx(31.0)

    def test_technology(self) -> None:
        assert parse_battery(self.SAMPLE).technology == "Li-ion"

    def test_empty_string(self) -> None:
        assert parse_battery("").level == 0


class TestParseScreenResolution:
    def test_standard(self) -> None:
        assert parse_screen_resolution("Physical size: 1080x2400") == (1080, 2400)

    def test_no_match(self) -> None:
        assert parse_screen_resolution("no size here") == (0, 0)


class TestParseIpAddress:
    SAMPLE = (
        "3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
        "    link/ether aa:bb:cc:dd:ee:ff brd ff:ff:ff:ff:ff:ff\n"
        "    inet 192.168.1.50/24 brd 192.168.1.255 scope global dynamic wlan0\n"
    )

    def test_extracts_ip(self) -> None:
        assert parse_ip_address(self.SAMPLE) == "192.168.1.50"

    def test_no_ip(self) -> None:
        assert parse_ip_address("no inet here") == ""


class TestParseMeminfo:
    SAMPLE = "MemTotal:        7959680 kB\nMemFree:          890880 kB\nMemAvailable:    3981312 kB\n"

    def test_total(self) -> None:
        total, _ = parse_meminfo(self.SAMPLE)
        assert total == 7959680 * 1024

    def test_available(self) -> None:
        _, avail = parse_meminfo(self.SAMPLE)
        assert avail == 3981312 * 1024

    def test_empty(self) -> None:
        assert parse_meminfo("") == (0, 0)


class TestParseStorage:
    SAMPLE = "Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/root       52403200 20000000  30000000  40% /data\n"

    def test_parses_all_fields(self) -> None:
        s = parse_storage(self.SAMPLE)
        assert s.total_bytes == 52403200 * 1024
        assert s.used_bytes == 20000000 * 1024
        assert s.available_bytes == 30000000 * 1024
        assert s.mount_point == "/data"

    def test_malformed_returns_empty(self) -> None:
        s = parse_storage("garbage")
        assert s.total_bytes == 0


class TestParseGetprop:
    SAMPLE = "[ro.product.model]: [Pixel 6]\n[ro.build.version.sdk]: [33]\n"

    def test_parses_pairs(self) -> None:
        props = parse_getprop(self.SAMPLE)
        assert props["ro.product.model"] == "Pixel 6"
        assert props["ro.build.version.sdk"] == "33"

    def test_empty(self) -> None:
        assert parse_getprop("") == {}
