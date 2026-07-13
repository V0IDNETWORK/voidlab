"""
ADB client — subprocess-based ADB communication layer.

Wraps the system ``adb`` binary. This is the only module that actually
shells out to a subprocess; every other layer (services, controllers,
the public SDK) is built on top of this and is fully mockable in tests.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from voidremote.models.device import ConnectionConfig, PairingInfo
from voidremote.utils.security import (
    sanitize_shell_arg,
    validate_device_path,
    validate_local_path,
    validate_package_name,
)

logger = logging.getLogger(__name__)


class AdbError(Exception):
    """Raised when an ADB operation fails."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class AdbNotFoundError(AdbError):
    """Raised when the ADB binary cannot be found on PATH or the configured path."""


class AdbTimeoutError(AdbError):
    """Raised when an ADB command exceeds its timeout."""


class AdbCommandResult:
    """Result of a completed ADB command."""

    __slots__ = ("stdout", "stderr", "returncode")

    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        self.returncode = returncode

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def __repr__(self) -> str:
        return f"AdbCommandResult(returncode={self.returncode}, stdout={self.stdout[:60]!r})"


class AdbClient:
    """
    Low-level ADB client wrapping the system ``adb`` binary.

    All command execution funnels through :meth:`_run_sync` /
    :meth:`_run_async`, which normalize timeouts, error handling, and
    output decoding in one place.
    """

    def __init__(
        self,
        adb_path: str = "adb",
        default_timeout: float = 30.0,
        server_port: int = 5037,
    ) -> None:
        self._adb_path = adb_path
        self._default_timeout = default_timeout
        self._server_port = server_port
        self._verified = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def verify_adb(self) -> str:
        """
        Verify the ADB binary is available and return its version string.

        Raises:
            AdbNotFoundError: If the binary cannot be resolved on PATH.
        """
        resolved = shutil.which(self._adb_path)
        if resolved is None:
            raise AdbNotFoundError(
                f"ADB binary not found: {self._adb_path!r}. Install Android SDK "
                "Platform Tools (https://developer.android.com/tools/releases/platform-tools) "
                "or set the correct path via `voidremote config` / VOIDREMOTE_ADB_PATH."
            )
        result = self._run_sync(["version"])
        self._verified = True
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown version"
        logger.info("ADB available: %s (%s)", version_line, resolved)
        return version_line

    def start_server(self) -> None:
        self._run_sync(["start-server"])
        logger.debug("ADB server started")

    def kill_server(self) -> None:
        self._run_sync(["kill-server"])
        logger.debug("ADB server killed")

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------

    def list_devices_raw(self) -> str:
        return self._run_sync(["devices", "-l"]).stdout

    def get_state(self, serial: str) -> str:
        return self._run_sync(["-s", serial, "get-state"], timeout=5.0).stdout.lower()

    def wait_for_device(self, serial: str, timeout: float = 30.0) -> None:
        self._run_sync(["-s", serial, "wait-for-device"], timeout=timeout)

    # ------------------------------------------------------------------
    # Wireless pairing / connection
    # ------------------------------------------------------------------

    def pair(self, pairing: PairingInfo) -> AdbCommandResult:
        address = f"{pairing.host}:{pairing.port}"
        logger.info("Pairing with %s", address)
        result = self._run_sync(["pair", address, pairing.pairing_code], timeout=pairing.timeout)
        if "successfully paired" not in result.stdout.lower() and result.returncode != 0:
            raise AdbError(f"Pairing failed: {result.stderr or result.stdout}", result.returncode)
        return result

    def connect(self, config: ConnectionConfig) -> AdbCommandResult:
        address = f"{config.host}:{config.port}"
        logger.info("Connecting to %s", address)
        result: Optional[AdbCommandResult] = None
        for attempt in range(1, config.retry_count + 1):
            result = self._run_sync(["connect", address], timeout=config.timeout)
            if "connected" in result.stdout.lower() and "unable" not in result.stdout.lower():
                logger.info("Connected to %s", address)
                return result
            if attempt < config.retry_count:
                logger.warning(
                    "Connect attempt %d/%d failed, retrying in %.1fs",
                    attempt, config.retry_count, config.retry_delay,
                )
                time.sleep(config.retry_delay)
        assert result is not None
        raise AdbError(
            f"Could not connect to {address}: {result.stderr or result.stdout}", result.returncode
        )

    def disconnect(self, host: str, port: int = 5555) -> AdbCommandResult:
        address = f"{host}:{port}"
        logger.info("Disconnecting from %s", address)
        return self._run_sync(["disconnect", address])

    def disconnect_all(self) -> AdbCommandResult:
        return self._run_sync(["disconnect"])

    def tcpip(self, serial: str, port: int = 5555) -> AdbCommandResult:
        return self._run_sync(["-s", serial, "tcpip", str(port)])

    # ------------------------------------------------------------------
    # Shell execution
    # ------------------------------------------------------------------

    def shell(self, serial: str, command: str, timeout: Optional[float] = None) -> AdbCommandResult:
        return self._run_sync(["-s", serial, "shell", command], timeout=timeout or self._default_timeout)

    def shell_raw(
        self, serial: str, args: list[str], timeout: Optional[float] = None
    ) -> AdbCommandResult:
        """Execute shell with individually-validated, injection-safe args."""
        safe_args = [sanitize_shell_arg(a) for a in args]
        return self._run_sync(["-s", serial, "shell"] + safe_args, timeout=timeout or self._default_timeout)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def push(self, serial: str, local: Path, remote: str) -> AdbCommandResult:
        validated_local = validate_local_path(local)
        validated_remote = validate_device_path(remote)
        if not validated_local.exists():
            raise FileNotFoundError(f"Local file not found: {validated_local}")
        return self._run_sync(["-s", serial, "push", str(validated_local), validated_remote], timeout=120.0)

    def pull(self, serial: str, remote: str, local: Path) -> AdbCommandResult:
        validated_remote = validate_device_path(remote)
        local.parent.mkdir(parents=True, exist_ok=True)
        return self._run_sync(["-s", serial, "pull", validated_remote, str(local)], timeout=120.0)

    # ------------------------------------------------------------------
    # APK management
    # ------------------------------------------------------------------

    def install(
        self, serial: str, apk_path: Path, replace: bool = True, allow_downgrade: bool = False
    ) -> AdbCommandResult:
        validated = validate_local_path(apk_path)
        if not validated.exists():
            raise FileNotFoundError(f"APK not found: {validated}")
        args = ["-s", serial, "install"]
        if replace:
            args.append("-r")
        if allow_downgrade:
            args.append("-d")
        args.append(str(validated))
        return self._run_sync(args, timeout=180.0)

    def uninstall(self, serial: str, package: str, keep_data: bool = False) -> AdbCommandResult:
        validated_pkg = validate_package_name(package)
        args = ["-s", serial, "uninstall"]
        if keep_data:
            args.append("-k")
        args.append(validated_pkg)
        return self._run_sync(args, timeout=60.0)

    # ------------------------------------------------------------------
    # Reboot
    # ------------------------------------------------------------------

    def reboot(self, serial: str, mode: str = "") -> AdbCommandResult:
        args = ["-s", serial, "reboot"]
        if mode in ("bootloader", "recovery", "sideload", "sideload-auto-reboot"):
            args.append(mode)
        return self._run_sync(args)

    # ------------------------------------------------------------------
    # Screenshots & recording
    # ------------------------------------------------------------------

    def screenshot(self, serial: str, local_path: Path) -> AdbCommandResult:
        remote_tmp = "/sdcard/void_screenshot.png"
        self.shell(serial, f"screencap -p {remote_tmp}")
        result = self.pull(serial, remote_tmp, local_path)
        self.shell(serial, f"rm -f {remote_tmp}")
        return result

    def screenrecord(
        self,
        serial: str,
        remote_path: str = "/sdcard/void_screenrecord.mp4",
        time_limit: int = 180,
        bit_rate: int = 8_000_000,
        size: Optional[str] = None,
    ) -> subprocess.Popen[bytes]:
        """
        Start screen recording as a background subprocess and return the
        :class:`subprocess.Popen` handle. Caller is responsible for
        eventually calling ``.wait()``/``.terminate()`` and pulling the
        recorded file with :meth:`pull`.
        """
        cmd = [
            self._adb_path, "-s", serial, "shell", "screenrecord",
            f"--time-limit={time_limit}", f"--bit-rate={bit_rate}",
        ]
        if size:
            cmd += ["--size", size]
        cmd.append(remote_path)
        logger.info("Starting screen record: %s", " ".join(cmd))
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, args: list[str]) -> list[str]:
        return [self._adb_path, "-P", str(self._server_port), *args]

    def _run_sync(
        self, args: list[str], timeout: Optional[float] = None, input_data: Optional[bytes] = None
    ) -> AdbCommandResult:
        """Execute an ADB command synchronously. This is the single subprocess chokepoint."""
        cmd = self._build_cmd(args)
        effective_timeout = timeout or self._default_timeout
        logger.debug("ADB command: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=effective_timeout, input=input_data
            )
        except subprocess.TimeoutExpired as exc:
            raise AdbTimeoutError(
                f"ADB command timed out after {effective_timeout}s: {' '.join(cmd)}"
            ) from exc
        except FileNotFoundError as exc:
            raise AdbNotFoundError(f"ADB binary not found: {self._adb_path!r}") from exc

        result = AdbCommandResult(
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
            proc.returncode,
        )
        if result.stderr and result.returncode != 0:
            logger.debug("ADB stderr: %s", result.stderr)
        return result

    async def _run_async(self, args: list[str], timeout: Optional[float] = None) -> AdbCommandResult:
        """Execute an ADB command using a genuinely non-blocking asyncio subprocess."""
        cmd = self._build_cmd(args)
        effective_timeout = timeout or self._default_timeout
        logger.debug("ADB async command: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=effective_timeout
            )
        except asyncio.TimeoutError as exc:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
            raise AdbTimeoutError(f"ADB async command timed out after {effective_timeout}s") from exc
        return AdbCommandResult(
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
            proc.returncode or 0,
        )
