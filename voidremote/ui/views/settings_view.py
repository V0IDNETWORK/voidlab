"""Settings panel view."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from voidremote.config.settings import get_settings
from voidremote.ui.theme import Colors


class SettingsView(QWidget):
    """Full settings panel with save/reset functionality."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = get_settings()
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(24, 16, 24, 12)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        header.addWidget(btn_reset)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("accent")
        btn_save.setFixedWidth(70)
        btn_save.clicked.connect(self._save)
        header.addWidget(btn_save)

        header_w = QWidget()
        header_w.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_w.setLayout(header)
        root.addWidget(header_w)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_BASE};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        content_layout.addWidget(self._build_adb_group())
        content_layout.addWidget(self._build_ui_group())
        content_layout.addWidget(self._build_mirror_group())
        content_layout.addWidget(self._build_logging_group())
        content_layout.addStretch()

        scroll.setWidget(content)  # setWidget() called exactly once here too
        root.addWidget(scroll, stretch=1)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; padding: 6px 24px; "
            f"background: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER};"
        )
        root.addWidget(self._status_label)

    def _build_adb_group(self) -> QGroupBox:
        group = QGroupBox("ADB")
        form = QFormLayout(group)
        form.setSpacing(10)

        self._adb_path = QLineEdit()
        self._adb_path.setPlaceholderText("adb")
        form.addRow("ADB Binary Path:", self._adb_path)

        self._adb_port = QSpinBox()
        self._adb_port.setRange(1, 65535)
        form.addRow("Default Port:", self._adb_port)

        self._adb_timeout = QSpinBox()
        self._adb_timeout.setRange(1, 300)
        self._adb_timeout.setSuffix(" s")
        form.addRow("Command Timeout:", self._adb_timeout)

        self._adb_retry = QSpinBox()
        self._adb_retry.setRange(0, 10)
        form.addRow("Retry Count:", self._adb_retry)

        self._auto_start = QCheckBox("Auto-start ADB server")
        form.addRow("", self._auto_start)

        self._kill_on_exit = QCheckBox("Kill ADB server on exit")
        form.addRow("", self._kill_on_exit)
        return group

    def _build_ui_group(self) -> QGroupBox:
        group = QGroupBox("Interface")
        form = QFormLayout(group)
        form.setSpacing(10)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "auto"])
        form.addRow("Theme:", self._theme_combo)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 24)
        self._font_size.setSuffix(" px")
        form.addRow("Font Size:", self._font_size)

        self._animations = QCheckBox("Enable animations")
        form.addRow("", self._animations)

        self._notifications = QCheckBox("Enable notifications")
        form.addRow("", self._notifications)

        self._tray_icon = QCheckBox("Show system tray icon")
        form.addRow("", self._tray_icon)
        return group

    def _build_mirror_group(self) -> QGroupBox:
        group = QGroupBox("Screen Mirror")
        form = QFormLayout(group)
        form.setSpacing(10)

        self._mirror_fps = QSpinBox()
        self._mirror_fps.setRange(1, 120)
        self._mirror_fps.setSuffix(" FPS")
        form.addRow("Max FPS:", self._mirror_fps)

        self._mirror_bitrate = QSpinBox()
        self._mirror_bitrate.setRange(1, 64)
        self._mirror_bitrate.setSuffix(" Mbps")
        form.addRow("Bitrate:", self._mirror_bitrate)

        self._mirror_width = QSpinBox()
        self._mirror_width.setRange(320, 3840)
        self._mirror_width.setSingleStep(16)
        form.addRow("Max Width:", self._mirror_width)

        self._stay_awake = QCheckBox("Keep device awake while mirroring")
        form.addRow("", self._stay_awake)

        self._show_touches = QCheckBox("Show touch points")
        form.addRow("", self._show_touches)
        return group

    def _build_logging_group(self) -> QGroupBox:
        group = QGroupBox("Logging")
        form = QFormLayout(group)
        form.setSpacing(10)

        self._log_level = QComboBox()
        self._log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow("Log Level:", self._log_level)

        self._log_file_enabled = QCheckBox("Write log file")
        form.addRow("", self._log_file_enabled)

        self._log_max_size = QSpinBox()
        self._log_max_size.setRange(1, 100)
        self._log_max_size.setSuffix(" MB")
        form.addRow("Max File Size:", self._log_max_size)

        self._log_backup = QSpinBox()
        self._log_backup.setRange(0, 20)
        form.addRow("Backup Files:", self._log_backup)
        return group

    def _load_values(self) -> None:
        s = self._settings
        self._adb_path.setText(s.adb.path)
        self._adb_port.setValue(s.adb.default_port)
        self._adb_timeout.setValue(int(s.adb.command_timeout))
        self._adb_retry.setValue(s.adb.retry_count)
        self._auto_start.setChecked(s.adb.auto_start_server)
        self._kill_on_exit.setChecked(s.adb.kill_server_on_exit)

        self._theme_combo.setCurrentText(s.ui.theme)
        self._font_size.setValue(s.ui.font_size)
        self._animations.setChecked(s.ui.animations_enabled)
        self._notifications.setChecked(s.ui.notifications_enabled)
        self._tray_icon.setChecked(s.ui.tray_icon_enabled)

        self._mirror_fps.setValue(s.mirror.max_fps)
        self._mirror_bitrate.setValue(s.mirror.max_bitrate_mbps)
        self._mirror_width.setValue(s.mirror.max_width)
        self._stay_awake.setChecked(s.mirror.stay_awake)
        self._show_touches.setChecked(s.mirror.show_touches)

        self._log_level.setCurrentText(s.logging.level)
        self._log_file_enabled.setChecked(s.logging.file_enabled)
        self._log_max_size.setValue(s.logging.max_file_size_mb)
        self._log_backup.setValue(s.logging.backup_count)

    def _save(self) -> None:
        s = self._settings
        s.adb.path = self._adb_path.text().strip() or "adb"
        s.adb.default_port = self._adb_port.value()
        s.adb.command_timeout = float(self._adb_timeout.value())
        s.adb.retry_count = self._adb_retry.value()
        s.adb.auto_start_server = self._auto_start.isChecked()
        s.adb.kill_server_on_exit = self._kill_on_exit.isChecked()

        s.ui.theme = self._theme_combo.currentText()
        s.ui.font_size = self._font_size.value()
        s.ui.animations_enabled = self._animations.isChecked()
        s.ui.notifications_enabled = self._notifications.isChecked()
        s.ui.tray_icon_enabled = self._tray_icon.isChecked()

        s.mirror.max_fps = self._mirror_fps.value()
        s.mirror.max_bitrate_mbps = self._mirror_bitrate.value()
        s.mirror.max_width = self._mirror_width.value()
        s.mirror.stay_awake = self._stay_awake.isChecked()
        s.mirror.show_touches = self._show_touches.isChecked()

        s.logging.level = self._log_level.currentText()
        s.logging.file_enabled = self._log_file_enabled.isChecked()
        s.logging.max_file_size_mb = self._log_max_size.value()
        s.logging.backup_count = self._log_backup.value()

        s.save()
        self._status_label.setText("✓ Settings saved")

    def _reset_defaults(self) -> None:
        self._settings.reset_to_defaults()
        self._load_values()
        self._status_label.setText("Settings reset to defaults")
