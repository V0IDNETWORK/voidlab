"""
GUI test for the DashboardView widget-lifecycle bug.

This is the test that would have caught
``RuntimeError: Internal C++ object already deleted`` in
``DashboardView::_update_grid()``: it constructs a real DashboardView,
feeds it several rounds of device lists (added, changed, removed —
the exact operations ``_update_grid`` performs), and drives multiple
refresh cycles, asserting no exception is raised and the widget tree
stays consistent throughout.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.gui


def _fake_device(serial: str, model: str = "Pixel 6"):
    from voidremote.models.device import BatteryInfo, ConnectionType, Device, DeviceInfo, DeviceState
    info = DeviceInfo(serial=serial, model=model, manufacturer="Google", android_version="13", sdk_version=33,
                       battery=BatteryInfo(level=80))
    return Device(info=info, state=DeviceState.ONLINE, connection_type=ConnectionType.WIRELESS,
                  host=serial.split(":")[0], port=5555)


def test_dashboard_view_constructs_without_error(qapp) -> None:  # noqa: ANN001
    from voidremote.ui.views.dashboard_view import DashboardView
    ctrl = MagicMock()
    view = DashboardView(ctrl)
    assert view is not None
    view.cleanup()


def test_scroll_area_setwidget_called_exactly_once(qapp) -> None:  # noqa: ANN001
    """
    Direct regression test for the root cause: patch QScrollArea.setWidget
    and assert it is invoked exactly once during DashboardView construction.
    """
    from PySide6.QtWidgets import QScrollArea
    from voidremote.ui.views.dashboard_view import DashboardView

    call_count = 0
    original = QScrollArea.setWidget

    def counting_setwidget(self, widget):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        return original(self, widget)

    QScrollArea.setWidget = counting_setwidget
    try:
        ctrl = MagicMock()
        view = DashboardView(ctrl)
        assert call_count == 1, f"QScrollArea.setWidget() called {call_count} times, expected exactly 1"
        view.cleanup()
    finally:
        QScrollArea.setWidget = original


def test_update_grid_survives_add_change_remove_cycles(qapp) -> None:  # noqa: ANN001
    """
    Drives _update_grid through the exact sequence that crashed before:
    devices appearing, refreshing in place, and disappearing across
    multiple refresh cycles, on the same DashboardView instance.
    """
    from voidremote.ui.views.dashboard_view import DashboardView

    ctrl = MagicMock()
    view = DashboardView(ctrl)

    # Round 1: two devices appear
    view._update_grid([_fake_device("192.168.1.10:5555"), _fake_device("192.168.1.11:5555")])
    qapp.processEvents()
    assert len(view._cards) == 2

    # Round 2: one device drops, one stays, one new one appears
    view._update_grid([_fake_device("192.168.1.11:5555"), _fake_device("192.168.1.12:5555")])
    qapp.processEvents()
    assert len(view._cards) == 2
    assert "192.168.1.10:5555" not in view._cards

    # Round 3: all devices drop — empty state must show, no crash
    view._update_grid([])
    qapp.processEvents()
    assert len(view._cards) == 0

    # Round 4: devices come back after being empty
    view._update_grid([_fake_device("192.168.1.20:5555")])
    qapp.processEvents()
    assert len(view._cards) == 1

    view.cleanup()


def test_refresh_worker_lifecycle_is_clean(qapp) -> None:  # noqa: ANN001
    """Runs a real refresh() through RefreshWorker (a real QThread) end to end."""
    from voidremote.ui.views.dashboard_view import DashboardView

    ctrl = MagicMock()
    ctrl.list_devices.return_value = [_fake_device("192.168.1.10:5555")]

    view = DashboardView(ctrl)
    view.refresh()

    deadline = time.monotonic() + 3.0
    while view.active_worker_count > 0 and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert view.active_worker_count == 0
    assert len(view._cards) == 1
    view.cleanup()


def test_cleanup_is_idempotent(qapp) -> None:  # noqa: ANN001
    from voidremote.ui.views.dashboard_view import DashboardView
    ctrl = MagicMock()
    view = DashboardView(ctrl)
    view.cleanup()
    view.cleanup()  # must not raise second time
