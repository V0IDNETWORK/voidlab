"""
Dashboard view — device grid with refresh and quick actions.

Bug-fix note (RuntimeError: Internal C++ object already deleted): the
previous implementation called ``QScrollArea.setWidget()`` three times
during construction. Qt's ``QScrollArea.setWidget()`` **deletes** its
previous contained widget when you assign a different one — so the
second/third calls destroyed a widget (and its child layout) that
Python still held a live reference to, which then blew up the next
time anything touched it (e.g. ``_update_grid``). The fix: build the
complete widget tree first, then call ``setWidget()`` exactly once at
the end with the final container.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from voidremote.ui.theme import Colors
from voidremote.ui.widgets.device_card import DeviceCard
from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin


class RefreshWorker(BaseWorker):
    """Fetches the device list off the UI thread."""

    devices_ready = Signal(list)
    load_error = Signal(str)

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller

    def do_work(self) -> None:
        try:
            result = self._controller.list_devices(refresh=True)  # type: ignore[attr-defined]
        except Exception as exc:
            self.load_error.emit(str(exc))
            raise
        else:
            self.devices_ready.emit(result)


class DashboardView(QWidget, WorkerOwnerMixin):
    """
    Main dashboard: a responsive grid of :class:`DeviceCard` widgets.

    Signals:
        connect_device(host, port)
        disconnect_device(serial)
        mirror_device(serial)
        show_device_info(serial)
        pair_device()
    """

    connect_device = Signal(str, int)
    disconnect_device = Signal(str)
    mirror_device = Signal(str)
    show_device_info = Signal(str)
    pair_device = Signal()

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        WorkerOwnerMixin.__init__(self)
        self._controller = controller
        self._cards: dict[str, DeviceCard] = {}
        self._build_ui()

        self._auto_refresh = QTimer(self)
        self._auto_refresh.setInterval(5000)
        self._auto_refresh.timeout.connect(self.refresh)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(24, 20, 24, 16)
        header.setSpacing(12)

        title = QLabel("Devices")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("0 devices")
        self._count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px;")
        header.addWidget(self._count_label)

        btn_pair = QPushButton("+ Pair")
        btn_pair.setObjectName("accent")
        btn_pair.setFixedWidth(80)
        btn_pair.clicked.connect(self.pair_device)
        header.addWidget(btn_pair)

        self._btn_refresh = QPushButton("↻ Refresh")
        self._btn_refresh.setFixedWidth(90)
        self._btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self._btn_refresh)

        header_widget = QWidget()
        header_widget.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_widget.setLayout(header)
        root.addWidget(header_widget)

        # ── Build the FULL content tree before it ever touches the
        #    scroll area. grid_container (device cards) and
        #    empty_state live side by side inside one stack_widget;
        #    only stack_widget is ever handed to the QScrollArea. ──
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet(f"background: {Colors.BG_BASE};")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(24, 20, 24, 20)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._empty_state = self._build_empty_state()

        stack_widget = QWidget()
        stack_widget.setStyleSheet(f"background: {Colors.BG_BASE};")
        stack_layout = QVBoxLayout(stack_widget)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.addWidget(self._grid_container)
        stack_layout.addWidget(self._empty_state)
        self._empty_state.hide()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(stack_widget)  # <-- called exactly ONCE, ever
        root.addWidget(scroll, stretch=1)

    def _build_empty_state(self) -> QWidget:
        empty_state = QWidget()
        empty_layout = QVBoxLayout(empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel("📱")
        empty_icon.setStyleSheet("font-size: 56px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("No devices connected")
        empty_title.setStyleSheet(
            f"font-size: 18px; font-weight: 600; color: {Colors.TEXT_SECONDARY}; margin-top: 12px;"
        )
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_hint = QLabel("Enable Wireless Debugging on your Android device,\nthen click '+ Pair' to get started.")
        empty_hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px; margin-top: 6px;")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_hint)

        btn_pair2 = QPushButton("Pair New Device")
        btn_pair2.setObjectName("accent")
        btn_pair2.setFixedWidth(160)
        btn_pair2.clicked.connect(self.pair_device)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_pair2)
        btn_row.addStretch()
        empty_layout.addLayout(btn_row)

        return empty_state

    def start_auto_refresh(self) -> None:
        self._auto_refresh.start()

    def stop_auto_refresh(self) -> None:
        self._auto_refresh.stop()

    def refresh(self) -> None:
        if self.active_worker_count > 0:
            return
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.setText("Refreshing…")

        worker = RefreshWorker(self._controller, self)
        worker.devices_ready.connect(self._on_devices_loaded)
        worker.load_error.connect(self._on_refresh_error)
        self.track_worker(worker)
        worker.start()

    def _on_devices_loaded(self, devices: list) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("↻ Refresh")
        self._update_grid(devices)
        count = len(devices)
        self._count_label.setText(f"{count} device{'s' if count != 1 else ''}")

    def _on_refresh_error(self, error: str) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("↻ Refresh")
        self._count_label.setText(f"Error: {error[:40]}")

    def _update_grid(self, devices: list) -> None:
        existing_serials = set(self._cards.keys())
        new_serials = {d.serial for d in devices}

        for serial in existing_serials - new_serials:
            card = self._cards.pop(serial)
            self._grid.removeWidget(card)
            card.setParent(None)
            card.deleteLater()

        for device in devices:
            if device.serial in self._cards:
                self._cards[device.serial].refresh(device)
            else:
                card = DeviceCard(device)
                card.connect_requested.connect(self._emit_connect)
                card.disconnect_requested.connect(self.disconnect_device)
                card.mirror_requested.connect(self.mirror_device)
                card.info_requested.connect(self.show_device_info)
                self._cards[device.serial] = card

        for i, card in enumerate(self._cards.values()):
            self._grid.addWidget(card, i // 2, i % 2)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        has_devices = bool(self._cards)
        self._grid_container.setVisible(has_devices)
        self._empty_state.setVisible(not has_devices)

    def _emit_connect(self, serial: str) -> None:
        if ":" in serial:
            host, _, port_str = serial.rpartition(":")
            try:
                port = int(port_str)
            except ValueError:
                port = 5555
        else:
            host, port = serial, 5555
        self.connect_device.emit(host, port)

    def cleanup(self) -> None:
        """Stop auto-refresh and block until any in-flight worker exits. Call before close."""
        self.stop_auto_refresh()
        self.shutdown_workers()
