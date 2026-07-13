"""CLI command tests using Click's test runner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from voidremote.cli.main import cli
from voidremote.models.device import BatteryInfo, ConnectionType, Device, DeviceInfo, DeviceState


def _make_device(serial: str = "192.168.1.50:5555") -> Device:
    info = DeviceInfo(
        serial=serial, model="Pixel 6", manufacturer="Google", android_version="13",
        sdk_version=33, battery=BatteryInfo(level=80, is_charging=False),
    )
    return Device(info=info, state=DeviceState.ONLINE, connection_type=ConnectionType.WIRELESS, host="192.168.1.50", port=5555)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_controller() -> MagicMock:
    ctrl = MagicMock()
    ctrl.initialize.return_value = "Android Debug Bridge version 1.0.41"
    ctrl.list_devices.return_value = [_make_device()]
    ctrl.get_device.return_value = _make_device()
    ctrl.pair_device.return_value = True
    ctrl.connect_device.return_value = _make_device()
    ctrl.shell.return_value = "output text"
    return ctrl


class TestVersionCommand:
    def test_version_output(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "VoidRemote" in result.output

    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output


class TestDevicesCommand:
    def test_no_devices(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        mock_controller.list_devices.return_value = []
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["devices"])
            assert result.exit_code == 0

    def test_json_output(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["--json", "devices"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert data[0]["serial"] == "192.168.1.50:5555"


class TestDoctorCommand:
    def test_doctor_runs_without_crashing(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Python" in result.output

    def test_doctor_uses_importlib_metadata_not_dunder_version(self, runner: CliRunner) -> None:
        # Regression test for the exact reported bug: `rich.__version__`
        # is unreliable / doesn't exist on every version. Doctor must
        # use importlib.metadata instead, which correctly reports a
        # real installed version string for click in this environment.
        result = runner.invoke(cli, ["--json", "doctor"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "click (CLI)" in data
        assert data["click (CLI)"]["ok"] is True
        assert data["click (CLI)"]["detail"] not in ("", None)


class TestConfigCommand:
    def test_show_config(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "--show"])
        assert result.exit_code == 0

    def test_config_json(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--json", "config", "--show"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "adb" in data


class TestLogsCommand:
    def test_logs_no_file(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("voidremote.config.settings.LOG_FILE", tmp_path / "nonexistent.log"):
            result = runner.invoke(cli, ["logs"])
            assert result.exit_code == 0

    def test_logs_json_no_file_returns_empty_array(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("voidremote.config.settings.LOG_FILE", tmp_path / "nonexistent.log"):
            result = runner.invoke(cli, ["--json", "logs"])
            assert result.exit_code == 0
            assert json.loads(result.output) == []

    def test_logs_json_returns_array_of_lines(self, runner: CliRunner, tmp_path: Path) -> None:
        log_file = tmp_path / "voidremote.log"
        log_file.write_text("line one\nline two\nline three\n", encoding="utf-8")
        with patch("voidremote.config.settings.LOG_FILE", log_file):
            result = runner.invoke(cli, ["--json", "logs", "-n", "2"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data == ["line two", "line three"]


class TestConnectCommand:
    def test_connect_success(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["connect", "192.168.1.50"])
            assert result.exit_code == 0


class TestShellCommand:
    def test_shell_output(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["shell", "192.168.1.50:5555", "ls"])
            assert result.exit_code == 0
            assert "output text" in result.output

    def test_shell_no_command(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["shell", "192.168.1.50:5555"])
            assert result.exit_code != 0


class TestTapCommand:
    def test_tap_success(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["tap", "192.168.1.50:5555", "540", "960"])
            assert result.exit_code == 0
            mock_controller.tap.assert_called_once_with("192.168.1.50:5555", 540, 960)


class TestSwipeCommand:
    def test_swipe_success(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["swipe", "192.168.1.50:5555", "100", "500", "100", "200"])
            assert result.exit_code == 0


class TestRebootCommand:
    def test_reboot_default(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["reboot", "192.168.1.50:5555"])
            assert result.exit_code == 0
            mock_controller.reboot.assert_called_once()


class TestPairCommand:
    def test_pair_with_args(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["pair", "192.168.1.50", "37001", "123456"])
            assert result.exit_code == 0
            mock_controller.pair_device.assert_called_once_with("192.168.1.50", 37001, "123456")

    def test_pair_rejects_bad_code(self, runner: CliRunner, mock_controller: MagicMock) -> None:
        with patch("voidremote.cli.main.AppController", return_value=mock_controller):
            result = runner.invoke(cli, ["pair", "192.168.1.50", "37001", "12"])
            assert result.exit_code != 0
            mock_controller.pair_device.assert_not_called()
