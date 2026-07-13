"""File manager view for browsing and transferring device files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voidremote.ui.theme import Colors
from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin


class ListDirWorker(BaseWorker):
    entries_ready = Signal(list)
    load_error = Signal(str)

    def __init__(self, controller: object, serial: str, path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._serial = serial
        self._path = path

    def do_work(self) -> None:
        try:
            raw = self._controller.shell(self._serial, f"ls -la '{self._path}'")  # type: ignore[attr-defined]
        except Exception as exc:
            self.load_error.emit(str(exc))
            return
        self.entries_ready.emit(self._parse_ls(raw))

    @staticmethod
    def _parse_ls(raw: str) -> list[dict]:
        entries: list[dict] = []
        for line in raw.splitlines():
            parts = line.split(None, 8)
            if len(parts) < 8:
                continue
            perms = parts[0]
            size = parts[4] if len(parts) > 4 else "0"
            name = parts[8] if len(parts) > 8 else parts[-1]
            if name in (".", ".."):
                continue
            entries.append({"name": name, "is_dir": perms.startswith("d"), "size": size, "permissions": perms})
        return entries


class TransferWorker(BaseWorker):
    transfer_done = Signal()
    transfer_error = Signal(str)

    def __init__(
        self, controller: object, serial: str, mode: str, local: str, remote: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._serial = serial
        self._mode = mode
        self._local = local
        self._remote = remote

    def do_work(self) -> None:
        try:
            if self._mode == "push":
                self._controller.push_file(self._serial, Path(self._local), self._remote)  # type: ignore[attr-defined]
            else:
                self._controller.pull_file(self._serial, self._remote, Path(self._local))  # type: ignore[attr-defined]
        except Exception as exc:
            self.transfer_error.emit(str(exc))
            return
        self.transfer_done.emit()


class FilesView(QWidget, WorkerOwnerMixin):
    """ADB file manager with navigation, upload, and download."""

    def __init__(self, controller: object, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        WorkerOwnerMixin.__init__(self)
        self._controller = controller
        self._serial: Optional[str] = None
        self._current_path = "/sdcard"
        self._path_history: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(24, 16, 24, 12)
        header.setSpacing(10)

        title = QLabel("Files")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Device:"))
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(200)
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        header.addWidget(self._device_combo)

        header_w = QWidget()
        header_w.setStyleSheet(f"background: {Colors.BG_SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_w.setLayout(header)
        root.addWidget(header_w)

        path_bar = QHBoxLayout()
        path_bar.setContentsMargins(16, 8, 16, 8)
        path_bar.setSpacing(8)

        self._back_btn = QPushButton("←")
        self._back_btn.setFixedWidth(36)
        self._back_btn.clicked.connect(self._go_back)
        path_bar.addWidget(self._back_btn)

        self._path_edit = QLineEdit(self._current_path)
        self._path_edit.returnPressed.connect(self._navigate_to_path)
        path_bar.addWidget(self._path_edit, stretch=1)

        btn_go = QPushButton("Go")
        btn_go.setFixedWidth(40)
        btn_go.clicked.connect(self._navigate_to_path)
        path_bar.addWidget(btn_go)

        btn_upload = QPushButton("↑ Upload")
        btn_upload.clicked.connect(self._upload_file)
        path_bar.addWidget(btn_upload)

        btn_download = QPushButton("↓ Download")
        btn_download.clicked.connect(self._download_selected)
        path_bar.addWidget(btn_download)

        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(36)
        btn_refresh.clicked.connect(self._load_directory)
        path_bar.addWidget(btn_refresh)

        path_bar_w = QWidget()
        path_bar_w.setStyleSheet(f"background: {Colors.BG_ELEVATED}; border-bottom: 1px solid {Colors.BORDER};")
        path_bar_w.setLayout(path_bar)
        root.addWidget(path_bar_w)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Permissions"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            self._table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_double_click)
        root.addWidget(self._table, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        root.addWidget(self._progress)

        self._status = QLabel("Select a device to browse files")
        self._status.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; padding: 6px 24px; "
            f"background: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER};"
        )
        root.addWidget(self._status)

    def set_devices(self, devices: list) -> None:
        current = self._device_combo.currentData()
        self._device_combo.blockSignals(True)
        self._device_combo.clear()
        for d in devices:
            self._device_combo.addItem(f"{d.info.display_name} ({d.serial})", userData=d.serial)
        idx = self._device_combo.findData(current)
        self._device_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._device_combo.blockSignals(False)
        if self._device_combo.count() > 0 and self._serial != self._device_combo.currentData():
            self._on_device_changed()

    def _on_device_changed(self) -> None:
        self._serial = self._device_combo.currentData()
        if self._serial:
            self._current_path = "/sdcard"
            self._path_history.clear()
            self._path_edit.setText(self._current_path)
            self._load_directory()

    def _navigate_to_path(self) -> None:
        path = self._path_edit.text().strip()
        if path:
            self._path_history.append(self._current_path)
            self._current_path = path
            self._load_directory()

    def _go_back(self) -> None:
        if self._path_history:
            self._current_path = self._path_history.pop()
            self._path_edit.setText(self._current_path)
            self._load_directory()

    def _load_directory(self) -> None:
        if not self._serial:
            return
        self._table.setRowCount(0)
        self._status.setText(f"Loading {self._current_path}…")

        worker = ListDirWorker(self._controller, self._serial, self._current_path, self)
        worker.entries_ready.connect(self._on_entries_loaded)
        worker.load_error.connect(lambda e: self._status.setText(f"Error: {e}"))
        self.track_worker(worker)
        worker.start()

    def _on_entries_loaded(self, entries: list) -> None:
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            icon = "📁" if entry["is_dir"] else "📄"
            name_item = QTableWidgetItem(f"{icon}  {entry['name']}")
            name_item.setData(Qt.ItemDataRole.UserRole, entry)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem("Directory" if entry["is_dir"] else "File"))
            self._table.setItem(row, 2, QTableWidgetItem(entry["size"]))
            self._table.setItem(row, 3, QTableWidgetItem(entry["permissions"]))
        self._status.setText(f"{len(entries)} items in {self._current_path}")

    def _on_double_click(self, index) -> None:  # type: ignore[no-untyped-def]
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry and entry.get("is_dir"):
            self._path_history.append(self._current_path)
            self._current_path = f"{self._current_path.rstrip('/')}/{entry['name']}"
            self._path_edit.setText(self._current_path)
            self._load_directory()

    def _upload_file(self) -> None:
        if not self._serial:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return
        remote = f"{self._current_path.rstrip('/')}/{Path(path).name}"
        self._progress.show()

        worker = TransferWorker(self._controller, self._serial, "push", path, remote, self)
        worker.transfer_done.connect(lambda: (self._progress.hide(), self._load_directory()))
        worker.transfer_error.connect(lambda e: (self._progress.hide(), self._status.setText(f"Upload error: {e}")))
        self.track_worker(worker)
        worker.start()

    def _download_selected(self) -> None:
        if not self._serial:
            return
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry or entry.get("is_dir"):
            self._status.setText("Select a file to download (not a directory)")
            return
        remote = f"{self._current_path.rstrip('/')}/{entry['name']}"
        local_dir = QFileDialog.getExistingDirectory(self, "Save to folder")
        if not local_dir:
            return
        local = str(Path(local_dir) / entry["name"])
        self._progress.show()

        worker = TransferWorker(self._controller, self._serial, "pull", local, remote, self)
        worker.transfer_done.connect(lambda: (self._progress.hide(), self._status.setText(f"Downloaded to {local}")))
        worker.transfer_error.connect(lambda e: (self._progress.hide(), self._status.setText(f"Download error: {e}")))
        self.track_worker(worker)
        worker.start()

    def cleanup(self) -> None:
        self.shutdown_workers()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        super().closeEvent(event)
