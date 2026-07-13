"""Live scrolling log viewer widget."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from voidremote.ui.theme import Colors


class QtLogHandler(logging.Handler, QObject):
    """
    Logging handler that emits a Qt signal per record instead of touching
    widgets directly — ``logging`` calls can happen on any thread, and
    only the GUI thread may touch Qt widgets. The signal's queued
    cross-thread delivery is what makes this safe.
    """

    log_record = Signal(int, str)

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_record.emit(record.levelno, self.format(record))
        except Exception:
            self.handleError(record)


class LogView(QWidget):
    """Embeddable log viewer with level filtering and auto-scroll."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._handler: Optional[QtLogHandler] = None
        self._level_filter = logging.INFO
        self._auto_scroll = True
        self._build_ui()
        self._install_handler()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)
        toolbar.addWidget(QLabel("Level:"))

        self._level_combo = QComboBox()
        self._level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_combo.setCurrentText("INFO")
        self._level_combo.setFixedWidth(100)
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        toolbar.addWidget(self._level_combo)
        toolbar.addStretch()

        self._auto_scroll_btn = QPushButton("Auto-scroll: ON")
        self._auto_scroll_btn.setCheckable(True)
        self._auto_scroll_btn.setChecked(True)
        self._auto_scroll_btn.setFixedWidth(120)
        self._auto_scroll_btn.clicked.connect(self._toggle_autoscroll)
        toolbar.addWidget(self._auto_scroll_btn)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(60)
        toolbar.addWidget(btn_clear)

        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        toolbar_widget.setLayout(toolbar)
        layout.addWidget(toolbar_widget)

        self._text = QPlainTextEdit()
        self._text.setObjectName("LogView")
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(2000)
        self._text.setFont(QFont("JetBrains Mono, Cascadia Code, Fira Code, Consolas, monospace", 12))
        layout.addWidget(self._text, stretch=1)

        btn_clear.clicked.connect(self._text.clear)

    def _install_handler(self) -> None:
        handler = QtLogHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s", datefmt="%H:%M:%S"))
        handler.log_record.connect(self._append_record)
        self._handler = handler
        logging.getLogger().addHandler(handler)

    def remove_handler(self) -> None:
        """Detach this view's handler from the root logger. Call before destroying the view."""
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None

    @Slot(int, str)
    def _append_record(self, level: int, message: str) -> None:
        if level < self._level_filter:
            return

        fmt = QTextCharFormat()
        if level >= logging.CRITICAL:
            fmt.setForeground(QColor(Colors.ERROR))
            fmt.setFontWeight(QFont.Weight.Bold)
        elif level >= logging.ERROR:
            fmt.setForeground(QColor(Colors.ERROR))
        elif level >= logging.WARNING:
            fmt.setForeground(QColor(Colors.WARNING))
        elif level >= logging.INFO:
            fmt.setForeground(QColor(Colors.TEXT_PRIMARY))
        else:
            fmt.setForeground(QColor(Colors.TEXT_MUTED))

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        if self._auto_scroll:
            self._text.setTextCursor(cursor)
            self._text.ensureCursorVisible()

    def _on_level_changed(self, text: str) -> None:
        self._level_filter = getattr(logging, text, logging.DEBUG)

    def _toggle_autoscroll(self, checked: bool) -> None:
        self._auto_scroll = checked
        self._auto_scroll_btn.setText(f"Auto-scroll: {'ON' if checked else 'OFF'}")

    def clear(self) -> None:
        self._text.clear()

    def append(self, message: str, level: int = logging.INFO) -> None:
        """Manually append a message (also respects the level filter)."""
        self._append_record(level, message)
