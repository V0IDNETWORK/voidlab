"""
VoidRemote main application window.

Provides the shell: sidebar navigation, stacked views, toolbar, status
bar, and device-aware state management. ``closeEvent`` cascades
cleanup to every child view/dialog that owns background threads before
the window (and process) actually goes away — see ``ui.workers`` for
why this matters.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from voidremote.ui.dialogs.connect_dialog import ConnectDialog
from voidremote.ui.dialogs.pair_dialog import PairDialog
from voidremote.ui.theme import Colors
from voidremote.ui.views.dashboard_view import DashboardView
from voidremote.ui.views.files_view import FilesView
from voidremote.ui.views.monitor_view import MonitorView
from voidremote.ui.views.settings_view import SettingsView
from voidremote.ui.views.shell_view import ShellView
from voidremote.ui.widgets.log_view import LogView

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("📱", "Devices", "Dashboard — view and manage connected devices"),
    ("🖥️", "Mirror", "Screen mirroring (launch from a device card)"),
    ("🖥", "Shell", "ADB shell terminal"),
    ("📊", "Monitor", "Real-time device performance monitoring"),
    ("📁", "Files", "File manager — browse, upload, download"),
    ("⚙️", "Settings", "Application settings"),
    ("📋", "Logs", "Live application logs"),
]


class SidebarItem(QListWidgetItem):
    def __init__(self, icon: str, label: str, tooltip: str) -> None:
        super().__init__(f"  {icon}  {label}")
        self.setToolTip(tooltip)
        self.setSizeHint(QSize(200, 46))


class MainWindow(QMainWindow):
    """Primary application window: sidebar + stacked content + status bar."""

    def __init__(self, controller: object) -> None:
        super().__init__()
        self._controller = controller
        self._devices: list = []
        self._closing = False

        self._build_window()
        self._build_toolbar()
        self._build_sidebar()
        self._build_views()
        self._build_statusbar()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_geometry()

        QTimer.singleShot(500, self._initial_refresh)

    def _build_window(self) -> None:
        self.setWindowTitle("VoidRemote — Wireless Android Controller")
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)

        central = QWidget()
        central.setObjectName("MainWidget")
        self.setCentralWidget(central)

        self._root_layout = QHBoxLayout(central)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

    def _build_toolbar(self) -> None:
        from PySide6.QtGui import QAction

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setFloatable(False)

        self._toolbar_title = QLabel("  VoidRemote")
        self._toolbar_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.ACCENT};")
        toolbar.addWidget(self._toolbar_title)
        toolbar.addSeparator()

        act_pair = QAction("+ Pair", self)
        act_pair.setToolTip("Pair new device via Wireless Debugging")
        act_pair.triggered.connect(self._open_pair_dialog)
        toolbar.addAction(act_pair)

        act_connect = QAction("⚡ Connect", self)
        act_connect.setToolTip("Connect to device by IP")
        act_connect.triggered.connect(self._open_connect_dialog)
        toolbar.addAction(act_connect)

        act_refresh = QAction("↻ Refresh", self)
        act_refresh.setToolTip("Refresh device list (F5)")
        act_refresh.triggered.connect(self._refresh_devices)
        toolbar.addAction(act_refresh)

        spacer = QWidget()
        spacer.setStyleSheet("background: transparent;")
        toolbar.addWidget(spacer)

        self._device_count_label = QLabel("No devices")
        self._device_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; padding: 0 12px;")
        toolbar.addWidget(self._device_count_label)

        self.addToolBar(toolbar)

    def _build_sidebar(self) -> None:
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("Sidebar")
        self._sidebar.setFixedWidth(200)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for icon, label, tooltip in NAV_ITEMS:
            self._sidebar.addItem(SidebarItem(icon, label, tooltip))

        self._sidebar.setCurrentRow(0)
        self._sidebar.currentRowChanged.connect(self._on_nav_changed)
        self._root_layout.addWidget(self._sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        self._root_layout.addWidget(sep)

    def _build_views(self) -> None:
        self._stack = QStackedWidget()
        self._root_layout.addWidget(self._stack, stretch=1)

        self._dashboard = DashboardView(self._controller)
        self._mirror_placeholder = self._make_placeholder(
            "🖥️", "Screen Mirror", "Click 'Mirror' on a device card to launch screen mirroring."
        )
        self._shell = ShellView(self._controller)
        self._monitor = MonitorView(self._controller)
        self._files = FilesView(self._controller)
        self._settings = SettingsView()
        self._log_view = LogView()

        for view in (
            self._dashboard, self._mirror_placeholder, self._shell,
            self._monitor, self._files, self._settings, self._log_view,
        ):
            self._stack.addWidget(view)

    def _make_placeholder(self, icon: str, title: str, desc: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {Colors.BG_BASE};")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 52px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_SECONDARY};")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        return w

    def _build_statusbar(self) -> None:
        bar = QStatusBar()
        bar.setStyleSheet(f"QStatusBar {{ background: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER}; }}")

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        bar.addWidget(self._status_label)

        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        bar.addPermanentWidget(self._conn_dot)

        self._adb_status = QLabel("ADB: initializing…")
        self._adb_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; padding-right: 8px;")
        bar.addPermanentWidget(self._adb_status)

        self.setStatusBar(bar)

    def _connect_signals(self) -> None:
        self._dashboard.pair_device.connect(self._open_pair_dialog)
        self._dashboard.connect_device.connect(self._connect_device)
        self._dashboard.disconnect_device.connect(self._disconnect_device)
        self._dashboard.mirror_device.connect(self._mirror_device)
        self._dashboard.show_device_info.connect(self._show_device_info)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("F5"), self, self._refresh_devices)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._open_connect_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self._open_pair_dialog)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    @Slot(int)
    def _on_nav_changed(self, row: int) -> None:
        self._stack.setCurrentIndex(row)
        if row == 0:
            self._dashboard.refresh()

    def _initial_refresh(self) -> None:
        try:
            self._controller.initialize()
            self._adb_status.setText("ADB: connected")
            self._adb_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px; padding-right: 8px;")
        except Exception as exc:
            self._adb_status.setText(f"ADB: {exc}")
            self._adb_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px; padding-right: 8px;")
            logger.warning("ADB initialization failed: %s", exc)
        self._refresh_devices()
        self._dashboard.start_auto_refresh()

    def _refresh_devices(self) -> None:
        self._dashboard.refresh()
        try:
            self._devices = self._controller.list_devices(refresh=False)
            count = len(self._devices)
            self._device_count_label.setText(f"{count} device{'s' if count != 1 else ''} connected")
            self._conn_dot.setStyleSheet(f"color: {Colors.SUCCESS if count else Colors.TEXT_MUTED}; font-size: 10px;")
            self._shell.set_devices(self._devices)
            self._monitor.set_devices(self._devices)
            self._files.set_devices(self._devices)
        except Exception as exc:
            logger.warning("Refresh error: %s", exc)

    def _open_pair_dialog(self) -> None:
        dlg = PairDialog(self._controller, self)
        dlg.paired.connect(self._on_paired)
        dlg.exec()

    def _open_connect_dialog(self) -> None:
        dlg = ConnectDialog(self._controller, self)
        dlg.connected.connect(self._on_connected)
        dlg.exec()

    @Slot(str, int)
    def _on_paired(self, host: str, port: int) -> None:
        self._set_status(f"Paired with {host}:{port} — connecting…")
        QTimer.singleShot(1000, lambda: self._connect_device(host, 5555))

    @Slot(object)
    def _on_connected(self, device: object) -> None:
        self._set_status(f"Connected: {device.info.display_name}")  # type: ignore[attr-defined]
        self._refresh_devices()

    @Slot(str, int)
    def _connect_device(self, host: str, port: int) -> None:
        try:
            device = self._controller.connect_device(host, port)
            self._set_status(f"Connected: {device.info.display_name}")
            self._refresh_devices()
        except Exception as exc:
            self._set_status(f"Connection failed: {exc}", error=True)

    @Slot(str)
    def _disconnect_device(self, serial: str) -> None:
        self._controller.disconnect_device(serial)
        self._set_status(f"Disconnected: {serial}")
        self._refresh_devices()

    @Slot(str)
    def _mirror_device(self, serial: str) -> None:
        self._set_status(f"Screen mirror for {serial} — use 'voidremote mirror {serial}' in the CLI")

    @Slot(str)
    def _show_device_info(self, serial: str) -> None:
        device = self._controller.get_device(serial)
        if device:
            self._set_status(
                f"{device.info.display_name} | Android {device.info.android_version} | {device.info.screen_resolution}"
            )

    def _set_status(self, msg: str, error: bool = False) -> None:
        color = Colors.ERROR if error else Colors.TEXT_SECONDARY
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        logger.info("Status: %s", msg)

    def _restore_geometry(self) -> None:
        from voidremote.config.settings import get_settings
        s = get_settings().ui
        self.resize(s.window_width, s.window_height)
        if s.window_maximized:
            self.showMaximized()

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Cascade shutdown to every child view/dialog that owns background
        threads, in a fixed order, before letting Qt actually tear the
        window down. Idempotent — Qt can call this more than once in
        some shutdown paths, so a re-entrancy guard prevents double
        cleanup (and the confusing warnings that would cause).
        """
        if self._closing:
            event.accept()
            return
        self._closing = True

        from voidremote.config.settings import get_settings, save_settings

        s = get_settings()
        s.ui.window_width = self.width()
        s.ui.window_height = self.height()
        s.ui.window_maximized = self.isMaximized()
        save_settings()

        self._dashboard.cleanup()
        self._shell.cleanup()
        self._monitor.cleanup()
        self._files.cleanup()
        self._log_view.remove_handler()

        try:
            self._controller.shutdown()
        except Exception:
            logger.exception("Error during controller shutdown")

        super().closeEvent(event)
