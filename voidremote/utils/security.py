"""Security utilities: input validation and command-injection prevention."""

from __future__ import annotations

import ipaddress
import re
import shlex
from pathlib import Path

_SHELL_INJECTION_PATTERN = re.compile(r"[;&|`$<>\\]")
_SAFE_PACKAGE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9._]{1,255}$")
_SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-. ()]+$")
_HOSTNAME_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)$"
)
_PAIRING_CODE_RE = re.compile(r"^\d{6}$")


def validate_ip_address(address: str) -> str:
    """Validate an IPv4/IPv6 address string. Raises ValueError if invalid."""
    try:
        return str(ipaddress.ip_address(address))
    except ValueError as exc:
        raise ValueError(f"Invalid IP address: {address!r}") from exc


def validate_host(host: str) -> str:
    """Validate a host (IP or hostname) for use in ADB connections."""
    host = host.strip()
    if not host:
        raise ValueError("Host cannot be empty")
    if len(host) > 253:
        raise ValueError("Hostname too long")
    try:
        return validate_ip_address(host)
    except ValueError:
        pass
    if not _HOSTNAME_RE.match(host):
        raise ValueError(f"Invalid hostname: {host!r}")
    return host


def validate_port(port: int | str) -> int:
    """Validate a network port number (1-65535)."""
    try:
        p = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Port must be an integer, got: {port!r}") from exc
    if not (1 <= p <= 65535):
        raise ValueError(f"Port must be 1-65535, got: {p}")
    return p


def validate_pairing_code(code: str) -> str:
    """Validate an ADB wireless pairing code (exactly 6 digits)."""
    code = code.strip()
    if not code:
        raise ValueError("Pairing code cannot be empty")
    if not _PAIRING_CODE_RE.match(code):
        raise ValueError("Pairing code must be exactly 6 digits")
    return code


def sanitize_shell_arg(arg: str) -> str:
    """
    Reject shell metacharacters and quote an argument for ADB shell use.

    Raises ValueError on any of ``; & | ` $ < > \\`` — these have no
    legitimate use in the arguments VoidRemote passes to ``adb shell``
    and are the classic command-injection vector.
    """
    if _SHELL_INJECTION_PATTERN.search(arg):
        raise ValueError(f"Shell argument contains forbidden characters: {arg!r}")
    return shlex.quote(arg)


def sanitize_shell_args(args: list[str]) -> list[str]:
    """Sanitize a list of shell arguments."""
    return [sanitize_shell_arg(a) for a in args]


def validate_package_name(package: str) -> str:
    """Validate an Android package name (e.g. ``com.example.app``)."""
    package = package.strip()
    if not _SAFE_PACKAGE_PATTERN.match(package):
        raise ValueError(f"Invalid Android package name: {package!r}")
    return package


def validate_device_path(path: str) -> str:
    """Validate an absolute path on the Android device."""
    if not path.startswith("/"):
        raise ValueError(f"Device path must be absolute, got: {path!r}")
    if "\x00" in path:
        raise ValueError("Device path contains null byte")
    normalized = str(Path(path))
    if ".." in normalized.split("/"):
        raise ValueError(f"Device path contains parent traversal: {path!r}")
    return normalized


def validate_local_path(path: Path) -> Path:
    """Resolve and validate a local file system path."""
    resolved = path.resolve()
    if "\x00" in str(resolved):
        raise ValueError("Path contains null byte")
    return resolved


def is_safe_filename(name: str) -> bool:
    """Return True if ``name`` is safe for use as a file/directory name."""
    return bool(_SAFE_FILENAME_PATTERN.match(name)) and ".." not in name
