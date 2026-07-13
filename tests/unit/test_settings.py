"""Unit tests for application settings."""

from __future__ import annotations

from pathlib import Path

from voidremote.config.settings import AppSettings


class TestAppSettingsDefaults:
    def test_default_adb_path(self) -> None:
        assert AppSettings().adb.path == "adb"

    def test_default_theme(self) -> None:
        assert AppSettings().ui.theme == "dark"

    def test_default_log_level(self) -> None:
        assert AppSettings().logging.level == "INFO"

    def test_default_mirror_fps(self) -> None:
        assert AppSettings().mirror.max_fps == 30


class TestAppSettingsPersistence:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        settings = AppSettings()
        target = tmp_path / "settings.json"
        settings.save(target)
        assert target.exists()

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        settings = AppSettings()
        settings.debug = True
        settings.adb.path = "/custom/path/to/adb"
        settings.ui.theme = "light"
        target = tmp_path / "settings.json"
        settings.save(target)

        loaded = AppSettings.load(target)
        assert loaded.debug is True
        assert loaded.adb.path == "/custom/path/to/adb"
        assert loaded.ui.theme == "light"

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        loaded = AppSettings.load(tmp_path / "does_not_exist.json")
        assert loaded.adb.path == "adb"

    def test_load_corrupt_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        target = tmp_path / "corrupt.json"
        target.write_text("{ not valid json !!!", encoding="utf-8")
        loaded = AppSettings.load(target)
        assert loaded.adb.path == "adb"  # falls back cleanly, does not raise


class TestAppSettingsReset:
    def test_reset_to_defaults(self) -> None:
        settings = AppSettings()
        settings.debug = True
        settings.adb.path = "/weird/path"
        settings.reset_to_defaults()
        assert settings.debug is False
        assert settings.adb.path == "adb"
