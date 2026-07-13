"""
Lifecycle-safe QThread infrastructure.

The bug this module exists to prevent: a ``QThread`` subclass gets
constructed, started, and assigned to ``self._worker`` on some widget —
but nothing ever guarantees ``quit()``/``wait()`` runs before that
widget (or the whole application) is destroyed. Qt then prints
``QThread: Destroyed while thread is still running`` and, in the worst
case, the interpreter can crash on exit.

Two things fix this:

1. Every worker is a :class:`BaseWorker`, which standardizes how a
   worker is asked to stop (:meth:`request_stop`) and guarantees its
   ``finished`` signal always fires exactly once, even on error.
2. Every widget that starts workers uses a :class:`WorkerOwnerMixin`,
   which tracks every worker it has started and provides
   :meth:`shutdown_workers` — a single call that requests-stop and
   *blocks* (with a timeout) until every tracked worker has actually
   exited. Call this from ``closeEvent``/``reject``/before dropping a
   view, and the "destroyed while running" warning cannot happen for
   workers started through it.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

#: Default time to wait for a worker to notice a stop request and exit
#: cleanly before giving up. Workers wrapping a single blocking ADB
#: subprocess call can't be interrupted mid-call, so this mostly bounds
#: how long shutdown takes rather than guaranteeing instant exit.
DEFAULT_STOP_TIMEOUT_MS = 5000


class BaseWorker(QThread):
    """
    Base class for all VoidRemote background workers.

    Subclasses implement :meth:`do_work` instead of ``run()`` directly.
    ``run()`` wraps it so ``finished`` always fires (success or error)
    and any raised exception is captured on :attr:`error` rather than
    propagating into the Qt event loop (where it would be silently
    swallowed anyway).
    """

    #: Emitted exactly once when the worker finishes, whether it
    #: succeeded, failed, or was stopped early. ``bool`` is True on
    #: normal completion, False if :meth:`request_stop` was called.
    worker_finished = Signal(bool)

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self._stop_requested = False
        self.error: Optional[Exception] = None

    def request_stop(self) -> None:
        """Ask the worker to stop. Cooperative — subclasses should poll :attr:`stopping`."""
        self._stop_requested = True

    @property
    def stopping(self) -> bool:
        return self._stop_requested

    def do_work(self) -> None:  # pragma: no cover - overridden by subclasses
        raise NotImplementedError

    def run(self) -> None:
        completed_normally = False
        try:
            self.do_work()
            completed_normally = not self._stop_requested
        except Exception as exc:  # noqa: BLE001 - deliberately broad: this is a thread boundary
            self.error = exc
            logger.exception("Worker %s raised an exception", type(self).__name__)
        finally:
            self.worker_finished.emit(completed_normally)

    def stop_and_wait(self, timeout_ms: int = DEFAULT_STOP_TIMEOUT_MS) -> bool:
        """
        Request stop and block until the thread exits or ``timeout_ms``
        elapses. Returns True if the thread actually stopped.
        """
        if not self.isRunning():
            return True
        self.request_stop()
        self.quit()
        stopped = self.wait(timeout_ms)
        if not stopped:
            logger.warning(
                "%s did not stop within %dms; it will keep running detached "
                "(likely blocked on a subprocess call)",
                type(self).__name__, timeout_ms,
            )
        return stopped


class WorkerOwnerMixin:
    """
    Mixin for any QWidget/QDialog that starts :class:`BaseWorker` threads.

    Usage:
        class MyView(QWidget, WorkerOwnerMixin):
            def __init__(self):
                QWidget.__init__(self)
                WorkerOwnerMixin.__init__(self)

            def do_thing(self):
                worker = SomeWorker(...)
                self.track_worker(worker)   # instead of self._worker = worker
                worker.start()

            def closeEvent(self, event):
                self.shutdown_workers()
                super().closeEvent(event)

    Tracked workers are automatically untracked when they finish
    normally, so :meth:`shutdown_workers` only ever has to deal with
    what's genuinely still in flight.
    """

    def __init__(self) -> None:
        self._tracked_workers: list[BaseWorker] = []

    def track_worker(self, worker: BaseWorker) -> None:
        self._tracked_workers.append(worker)
        worker.worker_finished.connect(lambda _ok, w=worker: self._untrack_worker(w))

    def _untrack_worker(self, worker: BaseWorker) -> None:
        try:
            self._tracked_workers.remove(worker)
        except ValueError:
            pass

    def shutdown_workers(self, timeout_ms: int = DEFAULT_STOP_TIMEOUT_MS) -> None:
        """Stop and wait for every tracked worker. Call from closeEvent/reject/__del__."""
        for worker in list(self._tracked_workers):
            worker.stop_and_wait(timeout_ms)
        self._tracked_workers.clear()

    @property
    def active_worker_count(self) -> int:
        return sum(1 for w in self._tracked_workers if w.isRunning())
