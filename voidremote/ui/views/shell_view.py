"""Embedded ADB shell terminal view."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QKeyEvent, QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voidremote.ui.theme import Colors
from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin


class ShellWorker(BaseWorker):
    output_ready = Signal(str, bool)  # text, is_error

    def __init__(self, controller: object, serial: str, command: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._serial = serial
        self._command = command

    def do_work(self) -> None:
        try:
            result = self._controller.shell(self._serial, self._command)  # type: ignore[attr-defined]
            self.output_ready.emit(result, False)
        except Exception as exc:
            self.output_ready.emit(str(exc), True)


class HistoryLineEdit(QLineEdit):
    """Line edit with Up/Down command history navigation."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._history: list[str] = []
        self._history_idx = -1

    def add_to_history(self, cmd: str) -> None:
        if cmd and (not self._history or self._history[-1] != cmd):
            self._history.append(cmd)
        self._history_idx = -1

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            if self._history:
                self._history_idx = min(self._history_idx + 1, len(self._history) - 1)
                self.setText(self._history[-(self._history_idx + 1)])
            return
        if event.key() == Qt.Key.Key_Down:
            if self._history_idx > 0:
                self._history_idx -= 1
                self.setText(self._history[-(self._history_idx + 1)])
            elif self._history_idx == 0:
                self._history_idx = -1
                self.clear()
            return
        super().keyPressEvent(event)


class ShellView(QWidget, WorkerOwnerMixin):
    """ADB shell terminal emulator embedded in the GUI."""

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        WorkerOwnerMixin.__init__(self)
        self._controller = controller
        self._serial: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(24, 16, 24, 12)
        header.setSpacing(12)

        title = QLabel("Shell")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Device:"))
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(200)
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        header.addWidget(self._device_combo)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(60)
        header.addWidget(btn_clear)

        header_w = QWidget()
        header_w.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_w.setLayout(header)
        root.addWidget(header_w)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setObjectName("LogView")
        mono = QFont("JetBrains Mono, Cascadia Code, Consolas, monospace", 13)
        self._output.setFont(mono)
        self._output.setStyleSheet(f"background: {Colors.BG_BASE}; border: none; padding: 16px;")
        root.addWidget(self._output, stretch=1)

        btn_clear.clicked.connect(self._output.clear)

        input_bar = QHBoxLayout()
        input_bar.setContentsMargins(16, 10, 16, 12)
        input_bar.setSpacing(8)

        prompt = QLabel("$")
        prompt.setStyleSheet(f"color: {Colors.ACCENT}; font-family: monospace; font-size: 15px; font-weight: 700;")
        input_bar.addWidget(prompt)

        self._cmd_edit = HistoryLineEdit()
        self._cmd_edit.setPlaceholderText("Enter shell command…")
        self._cmd_edit.setFont(mono)
        self._cmd_edit.returnPressed.connect(self._run_command)
        input_bar.addWidget(self._cmd_edit, stretch=1)

        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("accent")
        self._run_btn.setFixedWidth(60)
        self._run_btn.clicked.connect(self._run_command)
        input_bar.addWidget(self._run_btn)

        input_bar_w = QWidget()
        input_bar_w.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER};")
        input_bar_w.setLayout(input_bar)
        root.addWidget(input_bar_w)

        self._append(
            "VoidRemote Shell — ADB shell emulator\n"
            "Select a device above, then type a command and press Enter.\n"
            "Use ↑ / ↓ to navigate command history.\n"
        )

    def set_devices(self, devices: list) -> None:
        current = self._device_combo.currentData()
        self._device_combo.blockSignals(True)
        self._device_combo.clear()
        for d in devices:
            self._device_combo.addItem(f"{d.info.display_name} ({d.serial})", userData=d.serial)
        idx = self._device_combo.findData(current)
        self._device_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._device_combo.blockSignals(False)
        self._serial = self._device_combo.currentData()

    def _on_device_changed(self) -> None:
        self._serial = self._device_combo.currentData()

    def _run_command(self) -> None:
        cmd = self._cmd_edit.text().strip()
        if not cmd:
            return
        if not self._serial:
            self._append("No device selected.\n", error=True)
            return
        if self.active_worker_count > 0:
            self._append("Previous command still running…\n", error=True)
            return

        self._cmd_edit.add_to_history(cmd)
        self._cmd_edit.clear()
        self._run_btn.setEnabled(False)
        self._append(f"$ {cmd}\n", dim=True)

        worker = ShellWorker(self._controller, self._serial, cmd, self)
        worker.output_ready.connect(self._on_output)
        worker.worker_finished.connect(lambda _ok: self._run_btn.setEnabled(True))
        self.track_worker(worker)
        worker.start()

    def _on_output(self, text: str, is_error: bool) -> None:
        self._append(text + "\n", error=is_error)

    def _append(self, text: str, error: bool = False, dim: bool = False) -> None:
        fmt = QTextCharFormat()
        if error:
            fmt.setForeground(QColor(Colors.ERROR))
        elif dim:
            fmt.setForeground(QColor(Colors.TEXT_MUTED))
        else:
            fmt.setForeground(QColor(Colors.TEXT_PRIMARY))

        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text, fmt)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def cleanup(self) -> None:
        self.shutdown_workers()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)
