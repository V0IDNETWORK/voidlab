"""
VoidRemote dark theme and style definitions.

Bug-fix note: the QSS below contains hundreds of literal ``{`` / ``}``
pairs (every CSS rule block). The previous implementation ran the whole
stylesheet through ``str.format()``, which parses ANY ``{...}`` as a
substitution field — this raised ``KeyError`` or
``ValueError: Single '}' encountered`` the moment a selector block
didn't happen to look like a valid format field. ``string.Template``
uses ``$IDENTIFIER`` / ``${IDENTIFIER}`` instead and does not touch
``{`` or ``}`` at all, so CSS braces are structurally safe regardless
of how the stylesheet is written.
"""

from __future__ import annotations

from string import Template

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class Colors:
    """VoidRemote design system colors."""

    BG_BASE = "#0d1117"
    BG_SURFACE = "#161b22"
    BG_ELEVATED = "#1c2128"
    BG_OVERLAY = "#22272e"

    SIDEBAR_BG = "#0d1117"
    SIDEBAR_ACTIVE = "#1c2128"
    SIDEBAR_HOVER = "#161b22"

    ACCENT = "#4f8ef7"
    ACCENT_HOVER = "#6ba3f8"
    ACCENT_PRESSED = "#3a7af5"
    ACCENT_DIM = "rgba(79, 142, 247, 0.15)"

    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    ERROR = "#f85149"
    INFO = "#58a6ff"

    TEXT_PRIMARY = "#e6edf3"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#484f58"
    TEXT_ON_ACCENT = "#ffffff"

    BORDER = "#30363d"
    BORDER_FOCUS = "#4f8ef7"
    BORDER_SUBTLE = "#21262d"

    BTN_BG = "#21262d"
    BTN_HOVER = "#30363d"
    BTN_PRESSED = "#1c2128"

    CARD_BG = "#161b22"
    CARD_BORDER = "#30363d"

    BATTERY_FULL = "#3fb950"
    BATTERY_MID = "#d29922"
    BATTERY_LOW = "#f85149"

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return {k: v for k, v in vars(cls).items() if k.isupper()}


_STYLESHEET_TEMPLATE = Template("""
/* ============================================================
   VoidRemote Dark Theme — Qt Style Sheet
   ============================================================ */

* {
    font-family: "Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: $TEXT_PRIMARY;
    outline: none;
}

QMainWindow, QDialog, QWidget#MainWidget {
    background-color: $BG_BASE;
    border: none;
}

QScrollBar:vertical {
    background: $BG_SURFACE;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: $BORDER;
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover {
    background: $TEXT_MUTED;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: $BG_SURFACE;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: $BORDER;
    border-radius: 4px;
    min-width: 32px;
}

QToolBar {
    background-color: $BG_SURFACE;
    border-bottom: 1px solid $BORDER;
    spacing: 4px;
    padding: 4px 8px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    color: $TEXT_SECONDARY;
}
QToolButton:hover {
    background: $BTN_HOVER;
    color: $TEXT_PRIMARY;
    border-color: $BORDER;
}
QToolButton:pressed {
    background: $BTN_PRESSED;
}

QStatusBar {
    background-color: $BG_SURFACE;
    border-top: 1px solid $BORDER;
    color: $TEXT_SECONDARY;
    font-size: 12px;
    padding: 2px 8px;
}

QTabWidget::pane {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 8px;
}
QTabBar::tab {
    background: transparent;
    color: $TEXT_SECONDARY;
    padding: 8px 18px;
    margin-right: 2px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: $ACCENT;
    border-bottom: 2px solid $ACCENT;
}
QTabBar::tab:hover:!selected {
    color: $TEXT_PRIMARY;
}

QPushButton {
    background: $BTN_BG;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 7px 16px;
    color: $TEXT_PRIMARY;
    font-weight: 500;
}
QPushButton:hover {
    background: $BTN_HOVER;
    border-color: $TEXT_MUTED;
}
QPushButton:pressed {
    background: $BTN_PRESSED;
}
QPushButton:disabled {
    color: $TEXT_MUTED;
    background: $BG_ELEVATED;
    border-color: $BORDER_SUBTLE;
}
QPushButton#accent {
    background: $ACCENT;
    border-color: $ACCENT;
    color: $TEXT_ON_ACCENT;
}
QPushButton#accent:hover {
    background: $ACCENT_HOVER;
    border-color: $ACCENT_HOVER;
}
QPushButton#accent:pressed {
    background: $ACCENT_PRESSED;
}
QPushButton#danger {
    background: transparent;
    border-color: $ERROR;
    color: $ERROR;
}
QPushButton#danger:hover {
    background: rgba(248, 81, 73, 0.15);
}

QLineEdit {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 8px 12px;
    color: $TEXT_PRIMARY;
    selection-background-color: $ACCENT_DIM;
}
QLineEdit:focus {
    border-color: $BORDER_FOCUS;
    background: $BG_OVERLAY;
}
QLineEdit:disabled {
    color: $TEXT_MUTED;
    background: $BG_SURFACE;
}

QComboBox {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 7px 12px;
    color: $TEXT_PRIMARY;
}
QComboBox:hover {
    border-color: $TEXT_MUTED;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: $BG_OVERLAY;
    border: 1px solid $BORDER;
    selection-background-color: $ACCENT_DIM;
    outline: none;
}

QSpinBox, QDoubleSpinBox {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 7px 12px;
    color: $TEXT_PRIMARY;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: $BORDER_FOCUS;
}

QCheckBox {
    spacing: 8px;
    color: $TEXT_PRIMARY;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $BORDER;
    border-radius: 4px;
    background: $BG_ELEVATED;
}
QCheckBox::indicator:checked {
    background: $ACCENT;
    border-color: $ACCENT;
}

QRadioButton {
    spacing: 8px;
    color: $TEXT_PRIMARY;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $BORDER;
    border-radius: 8px;
    background: $BG_ELEVATED;
}
QRadioButton::indicator:checked {
    background: $ACCENT;
    border-color: $ACCENT;
}

QProgressBar {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 4px;
    text-align: center;
    color: $TEXT_PRIMARY;
    font-size: 11px;
    height: 8px;
}
QProgressBar::chunk {
    background: $ACCENT;
    border-radius: 3px;
}

QSlider::groove:horizontal {
    background: $BG_ELEVATED;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: $ACCENT;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: $ACCENT;
    border-radius: 2px;
}

QListWidget, QTreeWidget, QTableWidget {
    background: $BG_SURFACE;
    border: 1px solid $BORDER;
    border-radius: 8px;
    alternate-background-color: $BG_ELEVATED;
    gridline-color: $BORDER_SUBTLE;
    outline: none;
}
QListWidget::item, QTreeWidget::item, QTableWidget::item {
    padding: 6px 8px;
    border: none;
}
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
    background: $ACCENT_DIM;
    color: $TEXT_PRIMARY;
    border-radius: 4px;
}
QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
    background: $BG_ELEVATED;
}
QHeaderView::section {
    background: $BG_OVERLAY;
    border: none;
    border-right: 1px solid $BORDER;
    border-bottom: 1px solid $BORDER;
    padding: 6px 12px;
    color: $TEXT_SECONDARY;
    font-weight: 600;
    font-size: 11px;
}

QGroupBox {
    border: 1px solid $BORDER;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    font-weight: 600;
    color: $TEXT_SECONDARY;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: $TEXT_SECONDARY;
}

QSplitter::handle {
    background: $BORDER;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

QMenuBar {
    background: $BG_SURFACE;
    border-bottom: 1px solid $BORDER;
    color: $TEXT_SECONDARY;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: $BTN_HOVER;
    color: $TEXT_PRIMARY;
}
QMenu {
    background: $BG_OVERLAY;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 7px 18px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: $ACCENT_DIM;
    color: $TEXT_PRIMARY;
}
QMenu::separator {
    background: $BORDER;
    height: 1px;
    margin: 4px 8px;
}

QToolTip {
    background: $BG_OVERLAY;
    border: 1px solid $BORDER;
    border-radius: 6px;
    color: $TEXT_PRIMARY;
    padding: 6px 10px;
    font-size: 12px;
}

QTextEdit, QPlainTextEdit {
    background: $BG_ELEVATED;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 10px;
    color: $TEXT_PRIMARY;
    selection-background-color: $ACCENT_DIM;
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 13px;
}
QTextEdit:focus, QPlainTextEdit:focus {
    border-color: $BORDER_FOCUS;
}

QListWidget#Sidebar {
    background: $SIDEBAR_BG;
    border: none;
    border-right: 1px solid $BORDER;
    padding: 8px 0;
}
QListWidget#Sidebar::item {
    padding: 10px 16px;
    margin: 1px 8px;
    border-radius: 6px;
    color: $TEXT_SECONDARY;
}
QListWidget#Sidebar::item:selected {
    background: $SIDEBAR_ACTIVE;
    color: $TEXT_PRIMARY;
}
QListWidget#Sidebar::item:hover:!selected {
    background: $SIDEBAR_HOVER;
    color: $TEXT_PRIMARY;
}

QFrame#DeviceCard {
    background: $CARD_BG;
    border: 1px solid $CARD_BORDER;
    border-radius: 10px;
    padding: 16px;
}
QFrame#DeviceCard:hover {
    border-color: $ACCENT;
}

QTextEdit#LogView, QPlainTextEdit#LogView {
    background: $BG_BASE;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
    color: $TEXT_SECONDARY;
    border: none;
    padding: 12px;
}
""")


def build_stylesheet() -> str:
    """
    Render the QSS stylesheet with the current color palette substituted in.

    Uses ``string.Template.substitute`` (strict — raises ``KeyError`` if
    the stylesheet references a color name that doesn't exist in
    :class:`Colors`, which is exactly the fail-fast behavior we want at
    development time). CSS braces are never touched.
    """
    return _STYLESHEET_TEMPLATE.substitute(Colors.as_dict())


def apply_dark_theme(app: QApplication) -> None:
    """Apply the VoidRemote dark theme to a QApplication."""
    app.setStyleSheet(build_stylesheet())

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_BASE))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.BTN_BG))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.TEXT_ON_ACCENT))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.BG_OVERLAY))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(Colors.TEXT_SECONDARY))
    palette.setColor(QPalette.ColorRole.Link, QColor(Colors.ACCENT))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(Colors.ACCENT_PRESSED))

    app.setPalette(palette)
