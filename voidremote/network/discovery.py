"""Network device discovery — scans the local subnet for open ADB ports."""

from __future__ import annotations

import ipaddress
import logging
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ADB_PORTS = [5555, 5556, 5557, 5558, 5559]
DEFAULT_TIMEOUT = 0.5


def _check_port(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_host(host: str, ports: Optional[list[int]] = None) -> list[tuple[str, int]]:
    """Scan a single host for open ADB ports. Returns matching (host, port) pairs."""
    ports = ports if ports is not None else ADB_PORTS
    return [(host, p) for p in ports if _check_port(host, p)]


def scan_subnet(
    subnet: str,
    ports: Optional[list[int]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = 64,
    on_found: Optional[Callable[[str, int], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> list[tuple[str, int]]:
    """
    Scan an entire subnet for ADB devices using a bounded thread pool
    (not one thread per host — safe for large /16s or repeated calls).

    Args:
        subnet: CIDR notation, e.g. ``"192.168.1.0/24"``.
        ports: Ports to probe per host (defaults to common ADB ports).
        timeout: Per-connection timeout in seconds.
        max_workers: Maximum concurrent connection attempts.
        on_found: Optional callback invoked as soon as a device is found.
        on_progress: Optional callback(scanned_count, total_hosts).

    Returns:
        List of (host, port) tuples with an open ADB-like port.
    """
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid subnet: {subnet!r}") from exc

    ports = ports if ports is not None else ADB_PORTS
    hosts = [str(h) for h in network.hosts()]
    total = len(hosts)
    results: list[tuple[str, int]] = []
    scanned = 0
    lock = threading.Lock()

    def scan_one(host: str) -> None:
        nonlocal scanned
        found = scan_host(host, ports)
        with lock:
            scanned += 1
            results.extend(found)
            if on_found:
                for h, p in found:
                    on_found(h, p)
            if on_progress:
                on_progress(scanned, total)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(scan_one, hosts))

    logger.info("Subnet scan %s complete: %d hosts scanned, %d found", subnet, total, len(results))
    return results


def get_local_subnet() -> Optional[str]:
    """Best-effort guess of the local /24 subnet in CIDR notation, or None."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        parts = local_ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    except OSError:
        return None
