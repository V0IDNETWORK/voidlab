"""Device card widget for the dashboard."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from voidremote.models.device import Device, DeviceState
from voidremote.ui.theme import Colors


class BatteryBar(QWidget):
    """Compact battery level indicator, drawn with QPainter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._level = 0
        self.setFixedSize(28, 14)

    def set_level(self, level: int) -> None:
        self._level = max(0, min(100, level))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(Colors.BORDER))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(Colors.BG_ELEVATED)))
        painter.drawRoundedRect(0, 0, 24, 14, 3, 3)

        painter.setBrush(QBrush(QColor(Colors.BORDER)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(24, 4, 3, 6, 1, 1)

        color = (
            QColor(Colors.BATTERY_FULL) if self._level > 50
            else QColor(Colors.BATTERY_MID) if self._level > 20
            else QColor(Colors.BATTERY_LOW)
        )
        fill_width = int((22 * self._level) / 100)
        if fill_width > 0:
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(1, 1, fill_width, 12, 2, 2)


class StatusDot(QWidget):
    """Small colored dot reflecting device connection state."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = QColor(Colors.TEXT_MUTED)
        self.setFixedSize(10, 10)

    def set_state(self, state: DeviceState) -> None:
        color_map = {
            DeviceState.ONLINE: Colors.SUCCESS,
            DeviceState.OFFLINE: Colors.ERROR,
            DeviceState.UNAUTHORIZED: Colors.WARNING,
            DeviceState.CONNECTING: Colors.INFO,
        }
        self._color = QColor(color_map.get(state, Colors.TEXT_MUTED))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(1, 1, 8, 8)


class DeviceCard(QFrame):
    """
    Device card shown in the dashboard grid.

    Signals:
        connect_requested(serial): Connect button clicked while offline.
        disconnect_requested(serial): Disconnect button clicked while online.
        mirror_requested(serial): Mirror button clicked.
        info_requested(serial): Info button clicked.
    """

    connect_requested = Signal(str)
    disconnect_requested = Signal(str)
    mirror_requested = Signal(str)
    info_requested = Signal(str)

    def __init__(self, device: Device, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._device = device
        self.setObjectName("DeviceCard")
        self._build_ui()
        self.refresh(device)

    def _build_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(140)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._status_dot = StatusDot()
        header.addWidget(self._status_dot)

        self._name_label = QLabel()
        self._name_label.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(self._name_label, stretch=1)

        self._battery_bar = BatteryBar()
        header.addWidget(self._battery_bar)

        self._battery_label = QLabel()
        self._battery_label.setTextFormat(Qt.TextFormat.RichText)
        self._battery_label.setStyleSheet("font-size: 11px; min-width: 32px;")
        header.addWidget(self._battery_label)
        root.addLayout(header)

        meta = QHBoxLayout()
        meta.setSpacing(16)
        self._serial_label = QLabel()
        self._serial_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-family: monospace;")
        meta.addWidget(self._serial_label, stretch=1)

        self._android_label = QLabel()
        self._android_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        meta.addWidget(self._android_label)
        root.addLayout(meta)

        info = QHBoxLayout()
        info.setSpacing(20)
        self._res_label = QLabel()
        self._res_label.setTextFormat(Qt.TextFormat.RichText)
        self._ip_label = QLabel()
        self._ip_label.setTextFormat(Qt.TextFormat.RichText)
        self._type_label = QLabel()
        self._type_label.setTextFormat(Qt.TextFormat.RichText)
        for lbl in (self._res_label, self._ip_label, self._type_label):
            info.addWidget(lbl)
        info.addStretch()
        root.addLayout(info)
        root.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch()

        self._btn_info = QPushButton("Info")
        self._btn_info.setFixedWidth(60)
        self._btn_info.clicked.connect(lambda: self.info_requested.emit(self._device.serial))
        actions.addWidget(self._btn_info)

        self._btn_mirror = QPushButton("Mirror")
        self._btn_mirror.setFixedWidth(66)
        self._btn_mirror.clicked.connect(lambda: self.mirror_requested.emit(self._device.serial))
        actions.addWidget(self._btn_mirror)

        self._btn_connect = QPushButton("Connect")
        self._btn_connect.setObjectName("accent")
        self._btn_connect.setFixedWidth(80)
        self._btn_connect.clicked.connect(self._on_connect_toggle)
        actions.addWidget(self._btn_connect)
        root.addLayout(actions)

    def _on_connect_toggle(self) -> None:
        if self._device.is_connected:
            self.disconnect_requested.emit(self._device.serial)
        else:
            self.connect_requested.emit(self._device.serial)

    def refresh(self, device: Device) -> None:
        """Update card contents in place from a new Device snapshot."""
        self._device = device
        info = device.info

        self._status_dot.set_state(device.state)
        self._name_label.setText(device.display_name)
        self._serial_label.setText(device.serial)
        self._android_label.setText(f"Android {info.android_version}")

        batt = info.battery.level
        self._battery_bar.set_level(batt)
        batt_color = Colors.BATTERY_FULL if batt > 50 else Colors.BATTERY_MID if batt > 20 else Colors.BATTERY_LOW
        self._battery_label.setText(f"<span style='color:{batt_color}'>{batt}%</span>")

        def _kv(title: str, value: str) -> str:
            return (
                f"<span style='color:{Colors.TEXT_MUTED};font-size:10px'>{title}</span>"
                f"<br><span style='color:{Colors.TEXT_PRIMARY};font-size:12px'>{value}</span>"
            )

        self._res_label.setText(_kv("Resolution", info.screen_resolution))
        self._ip_label.setText(_kv("IP", info.network.ip_address or "N/A"))
        self._type_label.setText(_kv("Type", device.connection_type.value))

        if device.is_connected:
            self._btn_connect.setText("Disconnect")
            self._btn_connect.setObjectName("danger")
        else:
            self._btn_connect.setText("Connect")
            self._btn_connect.setObjectName("accent")
        self._btn_connect.style().unpolish(self._btn_connect)
        self._btn_connect.style().polish(self._btn_connect)

    @property
    def serial(self) -> str:
        return self._device.serial
