"""Shared pytest fixtures for VoidRemote tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from voidremote.adb.client import AdbClient, AdbCommandResult
from voidremote.config.settings import AppSettings
from voidremote.controllers.app_controller import AppController
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
from voidremote.services.device_service import DeviceService
from voidremote.services.input_service import InputService
from voidremote.services.monitor_service import MonitorService


@pytest.fixture
def mock_adb() -> MagicMock:
    """A MagicMock standing in for AdbClient, pre-wired with sane defaults."""
    adb = MagicMock(spec=AdbClient)
    adb.verify_adb.return_value = "Android Debug Bridge version 1.0.41"
    adb.list_devices_raw.return_value = (
        "List of devices attached\n"
        "192.168.1.50:5555\tdevice product:pixel6 model:Pixel_6 device:pixel6 transport_id:1\n"
    )
    adb.shell.return_value = AdbCommandResult("", "", 0)
    return adb


@pytest.fixture
def adb_result_ok() -> AdbCommandResult:
    return AdbCommandResult("success", "", 0)


@pytest.fixture
def adb_result_fail() -> AdbCommandResult:
    return AdbCommandResult("", "error: device not found", 1)


@pytest.fixture
def sample_battery() -> BatteryInfo:
    return BatteryInfo(
        level=75, is_charging=True, is_ac_powered=False, is_usb_powered=True,
        voltage=4200, temperature=280, health="good", technology="Li-ion",
    )


@pytest.fixture
def sample_device_info(sample_battery: BatteryInfo) -> DeviceInfo:
    return DeviceInfo(
        serial="192.168.1.50:5555", model="Pixel 6", manufacturer="Google", brand="google",
        product="pixel6", device_name="pixel6", android_version="13", sdk_version=33,
        build_id="TP1A.220905.004", screen_width=1080, screen_height=2400, screen_density=411,
        battery=sample_battery,
        storage=StorageInfo(total_bytes=128 * 1024**3, used_bytes=64 * 1024**3, available_bytes=64 * 1024**3),
        cpu=CpuInfo(abi="arm64-v8a", cores=8),
        network=NetworkInfo(ip_address="192.168.1.50"),
        ram_total_bytes=8 * 1024**3, ram_available_bytes=4 * 1024**3,
    )


@pytest.fixture
def sample_device(sample_device_info: DeviceInfo) -> Device:
    return Device(
        info=sample_device_info, state=DeviceState.ONLINE, connection_type=ConnectionType.WIRELESS,
        host="192.168.1.50", port=5555, is_trusted=True, connected_at=datetime.now(),
        capabilities=[
            DeviceCapability.SHELL, DeviceCapability.SCREEN_MIRROR, DeviceCapability.FILE_TRANSFER,
            DeviceCapability.INPUT_CONTROL, DeviceCapability.PACKAGE_MANAGER, DeviceCapability.MONITORING,
        ],
    )


@pytest.fixture
def test_settings() -> AppSettings:
    settings = AppSettings()
    settings.adb.path = "adb"
    settings.debug = True
    return settings


@pytest.fixture
def device_service(mock_adb: MagicMock, tmp_path: Path) -> DeviceService:
    """DeviceService with trusted-device storage redirected to a temp file via DI (no monkeypatching)."""
    return DeviceService(mock_adb, trusted_devices_file=tmp_path / "trusted.json")


@pytest.fixture
def input_service(mock_adb: MagicMock) -> InputService:
    return InputService(mock_adb)


@pytest.fixture
def monitor_service(mock_adb: MagicMock) -> MonitorService:
    return MonitorService(mock_adb)


@pytest.fixture
def app_controller(mock_adb: MagicMock, test_settings: AppSettings, tmp_path: Path) -> AppController:
    """AppController fully wired via constructor DI — no attribute-poking after construction."""
    return AppController(
        settings=test_settings,
        adb_client=mock_adb,
        device_service=DeviceService(mock_adb, trusted_devices_file=tmp_path / "trusted.json"),
        input_service=InputService(mock_adb),
        monitor_service=MonitorService(mock_adb),
    )
