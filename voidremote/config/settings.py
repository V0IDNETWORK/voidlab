"""
Application settings and configuration management.

Uses pydantic-settings for type-safe, validated configuration with
environment variable support and JSON persistence. Uses ``platformdirs``
(the maintained successor to the abandoned ``appdirs``) for cross-platform
config/data/log/cache directory resolution on Windows, Linux, and macOS.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from platformdirs import PlatformDirs
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

APP_NAME = "VoidRemote"
APP_AUTHOR = "V0IDNETWORK"

_dirs = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)

CONFIG_DIR = Path(_dirs.user_config_dir)
DATA_DIR = Path(_dirs.user_data_dir)
LOG_DIR = Path(_dirs.user_log_dir)
CACHE_DIR = Path(_dirs.user_cache_dir)

CONFIG_FILE = CONFIG_DIR / "settings.json"
TRUSTED_DEVICES_FILE = DATA_DIR / "trusted_devices.json"
LOG_FILE = LOG_DIR / "voidremote.log"


class AdbSettings(BaseSettings):
    """ADB-specific configuration."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_ADB_")

    path: str = Field(default="adb", description="Path to the ADB binary")
    default_port: int = Field(default=5555, ge=1, le=65535)
    connection_timeout: float = Field(default=10.0, gt=0)
    command_timeout: float = Field(default=30.0, gt=0)
    retry_count: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    server_port: int = Field(default=5037, ge=1, le=65535)
    auto_start_server: bool = Field(default=True)
    kill_server_on_exit: bool = Field(default=False)

    @field_validator("path")
    @classmethod
    def _validate_adb_path(cls, v: str) -> str:
        return v.strip() or "adb"


class UISettings(BaseSettings):
    """UI / appearance configuration."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_UI_")

    theme: str = Field(default="dark", pattern="^(dark|light|auto)$")
    language: str = Field(default="en")
    font_family: str = Field(default="Inter")
    font_size: int = Field(default=13, ge=8, le=24)
    window_width: int = Field(default=1280, ge=800)
    window_height: int = Field(default=800, ge=600)
    window_maximized: bool = Field(default=False)
    sidebar_width: int = Field(default=220, ge=160, le=400)
    show_statusbar: bool = Field(default=True)
    show_toolbar: bool = Field(default=True)
    animations_enabled: bool = Field(default=True)
    notifications_enabled: bool = Field(default=True)
    tray_icon_enabled: bool = Field(default=True)


class MirrorSettings(BaseSettings):
    """Screen mirroring configuration."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_MIRROR_")

    max_fps: int = Field(default=30, ge=1, le=120)
    max_bitrate_mbps: int = Field(default=8, ge=1, le=64)
    max_width: int = Field(default=1920, ge=320)
    max_height: int = Field(default=1080, ge=240)
    encoder: str = Field(default="h264")
    orientation_lock: bool = Field(default=False)
    show_touches: bool = Field(default=False)
    stay_awake: bool = Field(default=True)
    turn_screen_off: bool = Field(default=False)
    always_on_top: bool = Field(default=False)
    fullscreen: bool = Field(default=False)
    record_path: Optional[str] = Field(default=None)


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_LOG_")

    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_enabled: bool = Field(default=True)
    file_path: Optional[str] = Field(default=None)
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    backup_count: int = Field(default=5, ge=0, le=20)
    format: str = Field(default="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s")
    console_enabled: bool = Field(default=True)
    console_color: bool = Field(default=True)


class KeyboardShortcuts(BaseSettings):
    """Keyboard shortcut bindings."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_KEY_")

    connect_device: str = Field(default="Ctrl+Shift+C")
    disconnect_device: str = Field(default="Ctrl+Shift+D")
    screenshot: str = Field(default="Ctrl+Shift+S")
    start_mirror: str = Field(default="Ctrl+Shift+M")
    open_shell: str = Field(default="Ctrl+Shift+T")
    open_files: str = Field(default="Ctrl+Shift+F")
    refresh_devices: str = Field(default="F5")
    toggle_fullscreen: str = Field(default="F11")
    quit: str = Field(default="Ctrl+Q")


class AppSettings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(env_prefix="VOIDREMOTE_", env_nested_delimiter="__")

    app_name: str = Field(default="VoidRemote")
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    first_run: bool = Field(default=True)
    check_updates: bool = Field(default=True)
    update_channel: str = Field(default="stable", pattern="^(stable|beta|nightly)$")
    telemetry_enabled: bool = Field(default=False)

    adb: AdbSettings = Field(default_factory=AdbSettings)
    ui: UISettings = Field(default_factory=UISettings)
    mirror: MirrorSettings = Field(default_factory=MirrorSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    shortcuts: KeyboardShortcuts = Field(default_factory=KeyboardShortcuts)

    def save(self, path: Optional[Path] = None) -> None:
        """Persist settings to a JSON file."""
        target = path or CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        logger.debug("Settings saved to %s", target)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> AppSettings:
        """Load settings from a JSON file, falling back to defaults on any error."""
        target = path or CONFIG_FILE
        if target.exists():
            try:
                data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
                instance = cls(**data)
                logger.debug("Settings loaded from %s", target)
                return instance
            except Exception as exc:
                logger.warning("Failed to load settings from %s: %s", target, exc)
        return cls()

    def reset_to_defaults(self) -> None:
        """
        Reset all fields to their default values in place.

        Copies field *objects* from a fresh instance rather than going
        through :meth:`model_dump` — dumping recursively flattens nested
        models (``adb``, ``ui``, ...) into plain dicts, and plain
        ``setattr`` doesn't re-validate/re-hydrate them back into
        ``AdbSettings`` etc. without ``validate_assignment=True``, which
        would silently leave e.g. ``self.adb`` as a dict instead of an
        ``AdbSettings`` instance.
        """
        defaults = AppSettings()
        for key in vars(defaults):
            setattr(self, key, getattr(defaults, key))


_settings_instance: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Return the process-wide settings singleton, loading it on first use."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings.load()
    return _settings_instance


def save_settings() -> None:
    """Save the global settings singleton to disk."""
    get_settings().save()


def ensure_dirs() -> None:
    """Ensure all application directories exist."""
    for directory in (CONFIG_DIR, DATA_DIR, LOG_DIR, CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
