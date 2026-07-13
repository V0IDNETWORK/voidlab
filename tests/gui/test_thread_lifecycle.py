"""
GUI tests for background-thread lifecycle.

These are the tests that would have caught
``QThread: Destroyed while thread is still running``: they start real
QThread-based workers against a real (offscreen) QApplication event
loop and assert every thread has actually exited before the test ends
— not just that ``.quit()`` was called.
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.gui


def test_base_worker_finished_signal_fires_on_success(qapp) -> None:  # noqa: ANN001
    from voidremote.ui.workers import BaseWorker

    results = []

    class OkWorker(BaseWorker):
        def do_work(self) -> None:
            time.sleep(0.05)

    worker = OkWorker()
    worker.worker_finished.connect(lambda ok: results.append(ok))
    worker.start()
    assert worker.wait(2000), "worker did not finish in time"
    qapp.processEvents()
    assert results == [True]


def test_base_worker_finished_signal_fires_on_exception(qapp) -> None:  # noqa: ANN001
    from voidremote.ui.workers import BaseWorker

    results = []

    class FailWorker(BaseWorker):
        def do_work(self) -> None:
            raise RuntimeError("boom")

    worker = FailWorker()
    worker.worker_finished.connect(lambda ok: results.append(ok))
    worker.start()
    assert worker.wait(2000)
    qapp.processEvents()
    assert results == [False]
    assert isinstance(worker.error, RuntimeError)


def test_stop_and_wait_actually_stops_a_running_worker(qapp) -> None:  # noqa: ANN001
    from voidremote.ui.workers import BaseWorker

    class LoopingWorker(BaseWorker):
        def do_work(self) -> None:
            for _ in range(200):  # ~2s if not interrupted
                if self.stopping:
                    return
                time.sleep(0.01)

    worker = LoopingWorker()
    worker.start()
    time.sleep(0.05)  # let it actually start looping
    stopped = worker.stop_and_wait(timeout_ms=3000)
    assert stopped is True
    assert not worker.isRunning()


def test_worker_owner_mixin_shutdown_blocks_until_workers_exit(qapp) -> None:  # noqa: ANN001
    """
    The literal regression scenario: a widget that started a worker
    gets closed/destroyed. shutdown_workers() must not return until
    every tracked worker has actually stopped, so the widget (and its
    QThread children) can be safely garbage-collected without Qt
    printing "Destroyed while thread is still running".
    """
    from PySide6.QtWidgets import QWidget
    from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin

    class DummyView(QWidget, WorkerOwnerMixin):
        def __init__(self) -> None:
            QWidget.__init__(self)
            WorkerOwnerMixin.__init__(self)

    class SlowWorker(BaseWorker):
        def do_work(self) -> None:
            for _ in range(300):
                if self.stopping:
                    return
                time.sleep(0.01)

    view = DummyView()
    worker = SlowWorker(view)
    view.track_worker(worker)
    worker.start()
    time.sleep(0.05)

    assert view.active_worker_count == 1
    view.shutdown_workers(timeout_ms=3000)
    assert view.active_worker_count == 0
    assert not worker.isRunning()

    view.deleteLater()
    qapp.processEvents()


def test_untracked_after_normal_finish(qapp) -> None:  # noqa: ANN001
    from PySide6.QtWidgets import QWidget
    from voidremote.ui.workers import BaseWorker, WorkerOwnerMixin

    class DummyView(QWidget, WorkerOwnerMixin):
        def __init__(self) -> None:
            QWidget.__init__(self)
            WorkerOwnerMixin.__init__(self)

    class QuickWorker(BaseWorker):
        def do_work(self) -> None:
            time.sleep(0.02)

    view = DummyView()
    worker = QuickWorker(view)
    view.track_worker(worker)
    worker.start()
    worker.wait(2000)
    qapp.processEvents()
    # finished-normally workers should self-remove from tracking
    assert view.active_worker_count == 0
