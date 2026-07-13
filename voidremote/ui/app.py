"""
VoidRemote GUI application entry point.

Requires the ``gui`` extra: ``pip install voidremote[gui]``.
Bootstraps QApplication, applies the theme, and launches the main window.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the VoidRemote GUI application (registered as ``voidremote-gui``)."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(
            "The VoidRemote GUI requires the 'gui' extra. Install it with:\n"
            "    pip install voidremote[gui]",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from voidremote.config.settings import LOG_FILE, ensure_dirs, get_settings
    from voidremote.controllers.app_controller import AppController
    from voidremote.ui.main_window import MainWindow
    from voidremote.ui.theme import apply_dark_theme
    from voidremote.utils.logging import setup_logging

    ensure_dirs()
    settings = get_settings()

    setup_logging(
        level=settings.logging.level,
        log_file=LOG_FILE if settings.logging.file_enabled else None,
        console=settings.logging.console_enabled,
        console_color=settings.logging.console_color,
    )

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("VoidRemote")
    app.setApplicationDisplayName("VoidRemote")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("V0IDNETWORK")
    app.setOrganizationDomain("voidnetwork.ir")

    apply_dark_theme(app)
    app.setFont(QFont(settings.ui.font_family, settings.ui.font_size))

    controller = AppController(settings)
    window = MainWindow(controller)
    window.show()

    logger.info("VoidRemote GUI started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
