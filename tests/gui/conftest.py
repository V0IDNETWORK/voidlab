"""
Fixtures for GUI tests. Every test in this package is marked ``gui``
and is skipped automatically if PySide6 isn't installed, so the rest
of the test suite (unit/integration/cli/packaging) never depends on
the ``gui`` extra being present.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

pyside6 = pytest.importorskip("PySide6", reason="GUI tests require the 'gui' extra: pip install voidremote[gui]")

# Force the offscreen platform plugin unless the caller already picked
# one — lets these run in headless CI without a real X server/display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    """
    A single QApplication for the whole test session — Qt does not
    support multiple QApplication instances in one process, so this is
    intentionally session-scoped rather than per-test.
    """
    app = QApplication.instance() or QApplication([])
    yield app
    # Do not call app.quit()/sys.exit() here — pytest owns the process.


@pytest.fixture
def mock_controller():
    from unittest.mock import MagicMock
    ctrl = MagicMock()
    ctrl.list_devices.return_value = []
    ctrl.initialize.return_value = "Android Debug Bridge version 1.0.41"
    return ctrl
