"""Circular gauge widget for CPU/RAM/Battery monitoring."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from voidremote.ui.theme import Colors


class MetricGauge(QWidget):
    """Circular progress gauge for displaying a percentage-like metric."""

    def __init__(self, label: str = "", color: str = Colors.ACCENT, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._suffix = "%"
        self.setMinimumSize(100, 100)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(100.0, value))
        self.update()

    def set_label(self, label: str) -> None:
        self._label = label
        self.update()

    def set_suffix(self, suffix: str) -> None:
        self._suffix = suffix
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h)
        margin = size * 0.1
        arc_rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        pen = QPen(QColor(Colors.BG_ELEVATED))
        pen.setWidth(int(size * 0.08))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225 * 16, -270 * 16)

        if self._value > 0:
            val_pen = QPen(QColor(self._color))
            val_pen.setWidth(int(size * 0.08))
            val_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(val_pen)
            span = int(-270 * 16 * self._value / 100.0)
            painter.drawArc(arc_rect, 225 * 16, span)

        painter.setPen(QPen(QColor(Colors.TEXT_PRIMARY)))
        painter.setFont(QFont("Inter, Segoe UI", max(int(size * 0.2), 1), QFont.Weight.Bold))
        painter.drawText(
            QRectF(0, h * 0.3, w, h * 0.3), Qt.AlignmentFlag.AlignCenter, f"{self._value:.0f}{self._suffix}"
        )

        painter.setPen(QPen(QColor(Colors.TEXT_MUTED)))
        painter.setFont(QFont("Inter, Segoe UI", max(int(size * 0.1), 1)))
        painter.drawText(QRectF(0, h * 0.58, w, h * 0.2), Qt.AlignmentFlag.AlignCenter, self._label)
