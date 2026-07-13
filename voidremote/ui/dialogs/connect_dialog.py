"""Connect-to-device dialog."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voidremote.ui.theme import Colors
from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin


class ConnectWorker(BaseWorker):
    connect_success = Signal(object)
    connect_failure = Signal(str)

    def __init__(
        self, controller: object, host: str, port: int, remember: bool, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._host = host
        self._port = port
        self._remember = remember

    def do_work(self) -> None:
        try:
            device = self._controller.connect_device(self._host, self._port, self._remember)  # type: ignore[attr-defined]
        except Exception as exc:
            self.connect_failure.emit(str(exc))
            return
        self.connect_success.emit(device)


class ConnectDialog(QDialog, WorkerOwnerMixin):
    connected = Signal(object)

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        QDialog.__init__(self, parent)
        WorkerOwnerMixin.__init__(self)
        self._controller = controller
        self.setWindowTitle("Connect to Device")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 20)

        title = QLabel("Connect via TCP/IP")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        hint = QLabel("Enter the IP address and port of your Android device.\nDefault ADB port is 5555.")
        hint.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; "
            f"background: {Colors.BG_ELEVATED}; border-radius: 6px; padding: 10px;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("192.168.1.x")
        form.addRow("IP Address:", self._host_edit)

        self._port_edit = QLineEdit("5555")
        form.addRow("Port:", self._port_edit)
        layout.addLayout(form)

        self._remember_check = QCheckBox("Remember this device")
        self._remember_check.setChecked(True)
        layout.addWidget(self._remember_check)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.hide()
        layout.addWidget(self._status)

        buttons = QDialogButtonBox()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setObjectName("accent")
        self._connect_btn.clicked.connect(self._start_connect)
        buttons.addButton(self._connect_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _start_connect(self) -> None:
        host = self._host_edit.text().strip()
        port_str = self._port_edit.text().strip()

        if not host:
            self._show_error("Enter an IP address.")
            return
        if not port_str.isdigit():
            self._show_error("Port must be a number.")
            return

        self._connect_btn.setEnabled(False)
        self._progress.show()
        self._status.hide()

        worker = ConnectWorker(self._controller, host, int(port_str), self._remember_check.isChecked(), self)
        worker.connect_success.connect(self._on_success)
        worker.connect_failure.connect(self._on_failure)
        self.track_worker(worker)
        worker.start()

    def _on_success(self, device: object) -> None:
        self._progress.hide()
        self.connected.emit(device)
        self.accept()

    def _on_failure(self, msg: str) -> None:
        self._progress.hide()
        self._connect_btn.setEnabled(True)
        self._show_error(msg)

    def _show_error(self, msg: str) -> None:
        self._status.setText(f"✗ {msg}")
        self._status.setStyleSheet(f"color: {Colors.ERROR};")
        self._status.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown_workers()
        super().closeEvent(event)

    def reject(self) -> None:
        self.shutdown_workers()
        super().reject()
