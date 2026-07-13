"""
Real-time device monitoring service.

Polls CPU, RAM, and battery stats on a background thread and emits
:class:`DeviceSnapshot` objects to registered callbacks.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from voidremote.adb.client import AdbClient
from voidremote.adb.device_parser import parse_battery, parse_meminfo

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DeviceSnapshot:
    """Point-in-time device performance metrics."""

    serial: str
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    battery_level: int = 0
    battery_temperature: float = 0.0
    battery_is_charging: bool = False
    storage_used_gb: float = 0.0
    storage_total_gb: float = 0.0

    @property
    def ram_usage_percent(self) -> float:
        return (self.ram_used_mb / self.ram_total_mb * 100.0) if self.ram_total_mb else 0.0

    @property
    def storage_usage_percent(self) -> float:
        return (self.storage_used_gb / self.storage_total_gb * 100.0) if self.storage_total_gb else 0.0


SnapshotCallback = Callable[[DeviceSnapshot], None]


class MonitorService:
    """
    Polls device metrics at a configurable interval on a daemon thread
    per monitored device.

    Thread safety: :meth:`start` / :meth:`stop` / :meth:`stop_all` may be
    called from any thread. Callbacks are invoked on the polling thread,
    not the caller's thread — GUI consumers must marshal back to the
    UI thread themselves (see ``voidremote.ui`` for the Qt-safe pattern).
    """

    def __init__(self, adb: AdbClient) -> None:
        self._adb = adb
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._callbacks: dict[str, list[SnapshotCallback]] = {}
        self._lock = threading.Lock()

    def start(
        self, serial: str, interval: float = 2.0, callback: Optional[SnapshotCallback] = None
    ) -> None:
        """Start monitoring a device. Safe to call again after :meth:`stop`."""
        with self._lock:
            existing = self._threads.get(serial)
            if existing is not None and existing.is_alive():
                logger.warning("Already monitoring %s", serial)
                if callback:
                    self._callbacks.setdefault(serial, []).append(callback)
                return

            stop_event = threading.Event()
            self._stop_events[serial] = stop_event
            self._callbacks[serial] = [callback] if callback else []

            thread = threading.Thread(
                target=self._poll_loop, args=(serial, interval, stop_event),
                name=f"voidremote-monitor-{serial}", daemon=True,
            )
            self._threads[serial] = thread
            thread.start()
            logger.info("Started monitoring %s (interval=%.1fs)", serial, interval)

    def stop(self, serial: str, timeout: float = 5.0) -> None:
        """
        Signal the monitoring thread for ``serial`` to stop and block until
        it actually exits (bounded by ``timeout``). Always call this before
        dropping the last reference to a :class:`MonitorService`, or the
        daemon thread will keep running detached until process exit.
        """
        with self._lock:
            event = self._stop_events.pop(serial, None)
            thread = self._threads.pop(serial, None)
            self._callbacks.pop(serial, None)
        if event:
            event.set()
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.warning("Monitor thread for %s did not stop within %.1fs", serial, timeout)
        logger.info("Stopped monitoring %s", serial)

    def stop_all(self, timeout: float = 5.0) -> None:
        """Stop every active monitor. Call this on application shutdown."""
        for serial in list(self._threads.keys()):
            self.stop(serial, timeout=timeout)

    def is_monitoring(self, serial: str) -> bool:
        thread = self._threads.get(serial)
        return thread is not None and thread.is_alive()

    def add_callback(self, serial: str, callback: SnapshotCallback) -> None:
        with self._lock:
            self._callbacks.setdefault(serial, []).append(callback)

    def _poll_loop(self, serial: str, interval: float, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                snapshot = self._collect_snapshot(serial, stop_event)
                if snapshot is not None:
                    for cb in list(self._callbacks.get(serial, [])):
                        try:
                            cb(snapshot)
                        except Exception:
                            logger.exception("Monitor callback raised for %s", serial)
            except Exception:
                logger.debug("Snapshot collection failed for %s", serial, exc_info=True)
            stop_event.wait(interval)

    def _collect_snapshot(
        self, serial: str, stop_event: threading.Event
    ) -> Optional[DeviceSnapshot]:
        snapshot = DeviceSnapshot(serial=serial)

        try:
            snapshot.cpu_usage = self._get_cpu_usage(serial, stop_event)
        except Exception:
            pass
        if stop_event.is_set():
            return None

        try:
            total, avail = self._get_ram(serial)
            snapshot.ram_total_mb = total / (1024 * 1024)
            snapshot.ram_used_mb = (total - avail) / (1024 * 1024)
        except Exception:
            pass

        try:
            out = self._adb.shell(serial, "dumpsys battery").stdout
            info = parse_battery(out)
            snapshot.battery_level = info.level
            snapshot.battery_temperature = info.temperature_celsius
            snapshot.battery_is_charging = info.is_charging
        except Exception:
            pass

        return snapshot

    def _get_cpu_usage(self, serial: str, stop_event: threading.Event) -> float:
        """Sample /proc/stat twice with a short delay to compute utilization %."""

        def read_stat() -> tuple[int, int]:
            out = self._adb.shell(serial, "cat /proc/stat").stdout
            for line in out.splitlines():
                if line.startswith("cpu "):
                    nums = [int(x) for x in line.split()[1:]]
                    return sum(nums), (nums[3] if len(nums) > 3 else 0)
            return 0, 0

        t1, i1 = read_stat()
        # Bounded, interruptible sleep so stop() isn't blocked for a full poll cycle.
        stop_event.wait(0.2)
        if stop_event.is_set():
            return 0.0
        t2, i2 = read_stat()
        dt = t2 - t1
        di = i2 - i1
        return max(0.0, min(100.0, (1.0 - di / dt) * 100.0)) if dt else 0.0

    def _get_ram(self, serial: str) -> tuple[int, int]:
        return parse_meminfo(self._adb.shell(serial, "cat /proc/meminfo").stdout)
