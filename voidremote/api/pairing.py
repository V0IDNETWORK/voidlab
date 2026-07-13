"""Wireless-debugging pairing session."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from voidremote.api.exceptions import InvalidArgumentError, PairingError
from voidremote.utils.security import validate_host, validate_pairing_code, validate_port

if TYPE_CHECKING:
    from voidremote.controllers.app_controller import AppController
    from voidremote.api.device import Device

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PairingResult:
    """Outcome of a completed pairing attempt."""

    host: str
    port: int
    paired: bool


class PairingSession:
    """
    Guides a wireless-debugging pairing flow end-to-end: pair by code,
    then connect on the device's regular ADB port.

    Example:
        >>> from voidremote import VoidRemote
        >>> client = VoidRemote()
        >>> session = client.pair(host="192.168.1.50", port=37001, code="123456")  # doctest: +SKIP
        >>> device = session.connect()  # doctest: +SKIP
    """

    def __init__(self, controller: "AppController", host: str, port: int, code: str) -> None:
        try:
            self._host = validate_host(host)
            self._port = validate_port(port)
            self._code = validate_pairing_code(code)
        except ValueError as exc:
            raise InvalidArgumentError(str(exc)) from exc
        self._controller = controller
        self._result: Optional[PairingResult] = None

    def pair(self) -> PairingResult:
        """Perform the pairing handshake. Idempotent — safe to call more than once."""
        from voidremote.adb.client import AdbError

        try:
            success = self._controller.pair_device(self._host, self._port, self._code)
        except AdbError as exc:
            raise PairingError(f"Pairing with {self._host}:{self._port} failed: {exc}") from exc

        if not success:
            raise PairingError(
                f"Pairing with {self._host}:{self._port} failed — check the IP, "
                "port, and 6-digit code shown on the device."
            )
        self._result = PairingResult(host=self._host, port=self._port, paired=True)
        logger.info("Paired with %s:%s", self._host, self._port)
        return self._result

    def connect(self, adb_port: int = 5555, remember: bool = True) -> "Device":
        """
        Pair (if not already paired) and connect on the device's regular
        ADB port, returning a ready-to-use :class:`~voidremote.api.device.Device`.

        Args:
            adb_port: The device's regular ADB TCP port (usually 5555,
                distinct from the pairing port).
            remember: Persist this device so it auto-reconnects later.
        """
        from voidremote.adb.client import AdbError
        from voidremote.api.device import Device

        if self._result is None:
            self.pair()

        try:
            raw_device = self._controller.connect_device(self._host, adb_port, remember=remember)
        except AdbError as exc:
            raise PairingError(
                f"Paired with {self._host}, but connecting on port {adb_port} failed: {exc}"
            ) from exc
        return Device(raw_device, self._controller)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def __repr__(self) -> str:
        return f"PairingSession(host={self._host!r}, port={self._port})"
