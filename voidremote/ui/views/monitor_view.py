"""
Real-time device monitoring view with live gauges and sparklines.

Threading note: :class:`~voidremote.services.monitor_service.MonitorService`
polls on a plain ``threading.Thread`` (not a ``QThread``) and calls
callbacks directly on that thread. The previous implementation bridged
this into the Qt GUI thread with
``QMetaObject.invokeMethod(self, "_apply_snapshot", ..., Q_ARG(object, snapshot))``
— a string-based slot lookup that's fragile (renaming the method or
its signature silently breaks the connection with no error at
call-time) and easy to get wrong on non-registered argument types.

The fix: a tiny ``QObject`` bridge with a real typed ``Signal(object)``.
Qt automatically delivers a signal as a queued (thread-safe) call when
the emitting thread differs from the receiving object's thread — which
is exactly what's needed here, using ordinary, type-checked
signal/slot connections instead of string dispatch.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QCloseEvent, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from voidremote.services.monitor_service import DeviceSnapshot
from voidremote.ui.theme import Colors
from voidremote.ui.widgets.metric_gauge import MetricGauge


class _SnapshotBridge(QObject):
    """Lives on the GUI thread; relays snapshots emitted from the polling thread."""

    snapshot_ready = Signal(object)


class SparklineWidget(QWidget):
    """Minimal sparkline chart for a time-series metric."""

    def __init__(self, color: str = Colors.ACCENT, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = color
        self._data: deque[float] = deque(maxlen=60)
        self.setMinimumHeight(60)

    def push(self, value: float) -> None:
        self._data.append(value)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if len(self._data) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        data = list(self._data)
        max_v = max(data) or 1.0
        step = w / max(len(data) - 1, 1)

        path = QPainterPath()
        for i, v in enumerate(data):
            x = i * step
            y = h - (v / max_v) * (h - 4) - 2
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)

        pen = QPen(QColor(self._color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)


class MetricCard(QFrame):
    """Card showing a gauge + sparkline + current value label."""

    def __init__(self, title: str, color: str = Colors.ACCENT, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("DeviceCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(title_label)

        self._gauge = MetricGauge(label="", color=color)
        self._gauge.setFixedHeight(110)
        layout.addWidget(self._gauge, alignment=Qt.AlignmentFlag.AlignCenter)

        self._spark = SparklineWidget(color=color)
        layout.addWidget(self._spark)

        self._value_label = QLabel("–")
        self._value_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

    def update_value(self, value: float, suffix: str = "%", detail: str = "") -> None:
        self._gauge.set_value(value)
        self._gauge.set_suffix(suffix)
        self._spark.push(value)
        self._value_label.setText(detail or f"{value:.1f}{suffix}")


class MonitorView(QWidget):
    """Live device monitoring dashboard: CPU, RAM, battery, temperature."""

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._serial: Optional[str] = None
        self._bridge = _SnapshotBridge(self)
        self._bridge.snapshot_ready.connect(self._apply_snapshot, Qt.ConnectionType.QueuedConnection)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(24, 16, 24, 12)
        header.setSpacing(12)

        title = QLabel("Monitor")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Device:"))
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(220)
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        header.addWidget(self._device_combo)

        header_w = QWidget()
        header_w.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_w.setLayout(header)
        root.addWidget(header_w)

        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_BASE};")
        grid = QGridLayout(content)
        grid.setContentsMargins(24, 20, 24, 20)
        grid.setSpacing(16)

        self._cpu_card = MetricCard("CPU Usage", Colors.ACCENT)
        self._ram_card = MetricCard("RAM Usage", Colors.INFO)
        self._batt_card = MetricCard("Battery", Colors.SUCCESS)
        self._temp_card = MetricCard("Temperature", Colors.WARNING)
        grid.addWidget(self._cpu_card, 0, 0)
        grid.addWidget(self._ram_card, 0, 1)
        grid.addWidget(self._batt_card, 1, 0)
        grid.addWidget(self._temp_card, 1, 1)
        root.addWidget(content, stretch=1)

        self._status_bar = QLabel("Select a device to begin monitoring")
        self._status_bar.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; padding: 8px 24px; "
            f"background: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER};"
        )
        root.addWidget(self._status_bar)

    def set_devices(self, devices: list) -> None:
        current = self._device_combo.currentData()
        self._device_combo.blockSignals(True)
        self._device_combo.clear()
        for d in devices:
            self._device_combo.addItem(f"{d.info.display_name} ({d.serial})", userData=d.serial)
        idx = self._device_combo.findData(current)
        if idx >= 0:
            self._device_combo.setCurrentIndex(idx)
        self._device_combo.blockSignals(False)

    def _on_device_changed(self) -> None:
        serial = self._device_combo.currentData()
        if serial == self._serial:
            return
        if self._serial:
            self._controller.stop_monitoring(self._serial)
        self._serial = serial
        if serial:
            try:
                # emit() is thread-safe to call from the polling thread;
                # the bridge's queued connection marshals it back here.
                self._controller.start_monitoring(serial, interval=2.0, callback=self._bridge.snapshot_ready.emit)
                self._status_bar.setText(f"Monitoring {serial}")
            except Exception as exc:
                self._status_bar.setText(f"Error: {exc}")

    def _apply_snapshot(self, snapshot: DeviceSnapshot) -> None:
        self._cpu_card.update_value(snapshot.cpu_usage, "%", f"CPU: {snapshot.cpu_usage:.1f}%")
        self._ram_card.update_value(
            snapshot.ram_usage_percent, "%", f"{snapshot.ram_used_mb:.0f} / {snapshot.ram_total_mb:.0f} MB"
        )
        self._batt_card.update_value(
            float(snapshot.battery_level), "%",
            f"{snapshot.battery_level}%{' ⚡' if snapshot.battery_is_charging else ''}",
        )
        self._temp_card.update_value(snapshot.battery_temperature, "°C", f"{snapshot.battery_temperature:.1f}°C")

    def cleanup(self) -> None:
        """Stop monitoring the current device. Call before this view is destroyed."""
        if self._serial:
            self._controller.stop_monitoring(self._serial)
            self._serial = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)
