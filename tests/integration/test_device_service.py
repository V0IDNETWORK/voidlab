"""Integration tests for DeviceService — mocked ADB subprocess layer, real parsing/persistence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from voidremote.adb.client import AdbClient, AdbCommandResult, AdbError
from voidremote.models.device import DeviceState
from voidremote.services.device_service import DeviceService

DEVICES_OUTPUT = (
    "List of devices attached\n"
    "192.168.1.50:5555\tdevice product:pixel6 model:Pixel_6 device:pixel6\n"
)


@pytest.fixture
def mock_adb_with_devices() -> MagicMock:
    adb = MagicMock(spec=AdbClient)
    adb.list_devices_raw.return_value = DEVICES_OUTPUT
    adb.shell.return_value = AdbCommandResult("", "", 0)
    return adb


@pytest.fixture
def svc(mock_adb_with_devices: MagicMock, tmp_path: Path) -> DeviceService:
    return DeviceService(mock_adb_with_devices, trusted_devices_file=tmp_path / "trusted.json")


class TestDeviceServiceRefresh:
    def test_refresh_returns_devices(self, svc: DeviceService) -> None:
        assert len(svc.refresh_devices()) == 1

    def test_device_serial(self, svc: DeviceService) -> None:
        assert svc.refresh_devices()[0].serial == "192.168.1.50:5555"

    def test_device_state_online(self, svc: DeviceService) -> None:
        assert svc.refresh_devices()[0].state == DeviceState.ONLINE

    def test_empty_output(self, tmp_path: Path) -> None:
        adb = MagicMock(spec=AdbClient)
        adb.list_devices_raw.return_value = "List of devices attached\n"
        adb.shell.return_value = AdbCommandResult("", "", 0)
        svc = DeviceService(adb, trusted_devices_file=tmp_path / "t.json")
        assert svc.refresh_devices() == []

    def test_get_device_after_refresh(self, svc: DeviceService) -> None:
        svc.refresh_devices()
        assert svc.get_device("192.168.1.50:5555") is not None

    def test_get_device_before_refresh_returns_none(self, svc: DeviceService) -> None:
        assert svc.get_device("192.168.1.50:5555") is None


class TestDeviceServicePairing:
    def test_pair_success(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        mock_adb_with_devices.pair.return_value = AdbCommandResult("Successfully paired", "", 0)
        assert svc.pair_device("192.168.1.50", 37001, "123456") is True
        mock_adb_with_devices.pair.assert_called_once()

    def test_pair_failure(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        mock_adb_with_devices.pair.side_effect = AdbError("Failed to pair", 1)
        with pytest.raises(AdbError):
            svc.pair_device("192.168.1.50", 37001, "999999")

    def test_pair_invalid_host(self, svc: DeviceService) -> None:
        with pytest.raises(ValueError):
            svc.pair_device("", 37001, "123456")

    def test_pair_invalid_port(self, svc: DeviceService) -> None:
        with pytest.raises(ValueError):
            svc.pair_device("192.168.1.50", 0, "123456")


class TestDeviceServiceConnection:
    def test_connect_success(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected to 192.168.1.50:5555", "", 0)
        device = svc.connect_device("192.168.1.50", 5555, remember=False)
        assert device.serial == "192.168.1.50:5555"

    def test_connect_saves_trusted(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected", "", 0)
        svc.connect_device("192.168.1.50", 5555, remember=True)
        assert "192.168.1.50:5555" in {t.serial for t in svc.list_trusted_devices()}

    def test_disconnect_wireless(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        svc.refresh_devices()
        assert svc.disconnect_device("192.168.1.50:5555") is True
        mock_adb_with_devices.disconnect.assert_called_once_with("192.168.1.50", 5555)

    def test_disconnect_usb_skipped(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        assert svc.disconnect_device("ABC123XYZ") is False
        mock_adb_with_devices.disconnect.assert_not_called()


class TestTrustedDevicePersistenceAcrossInstances:
    """The whole point of injecting trusted_devices_file: verify persistence
    survives a fresh DeviceService instance (i.e. an app restart), without
    monkeypatching module-level globals."""

    def test_save_and_reload_in_new_instance(
        self, svc: DeviceService, mock_adb_with_devices: MagicMock, tmp_path: Path
    ) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected", "", 0)
        svc.connect_device("192.168.1.50", 5555, remember=True)

        fresh_svc = DeviceService(mock_adb_with_devices, trusted_devices_file=tmp_path / "trusted.json")
        trusted = fresh_svc.list_trusted_devices()
        assert len(trusted) == 1
        assert trusted[0].serial == "192.168.1.50:5555"

    def test_forget_device(self, svc: DeviceService, mock_adb_with_devices: MagicMock) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected", "", 0)
        svc.connect_device("192.168.1.50", 5555, remember=True)
        assert svc.forget_device("192.168.1.50:5555") is True
        assert svc.list_trusted_devices() == []

    def test_forget_nonexistent(self, svc: DeviceService) -> None:
        assert svc.forget_device("nonexistent:5555") is False


class TestAutoReconnect:
    def test_auto_reconnect_uses_trusted_devices(
        self, svc: DeviceService, mock_adb_with_devices: MagicMock
    ) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected", "", 0)
        svc.connect_device("192.168.1.50", 5555, remember=True)

        mock_adb_with_devices.connect.reset_mock()
        reconnected = svc.auto_reconnect_trusted()
        assert len(reconnected) == 1
        mock_adb_with_devices.connect.assert_called_once()

    def test_auto_reconnect_skips_devices_with_auto_connect_disabled(
        self, svc: DeviceService, mock_adb_with_devices: MagicMock
    ) -> None:
        mock_adb_with_devices.connect.return_value = AdbCommandResult("connected", "", 0)
        svc.connect_device("192.168.1.50", 5555, remember=True)
        list(svc._trusted.values())[0].auto_connect = False

        mock_adb_with_devices.connect.reset_mock()
        reconnected = svc.auto_reconnect_trusted()
        assert reconnected == []
        mock_adb_with_devices.connect.assert_not_called()
