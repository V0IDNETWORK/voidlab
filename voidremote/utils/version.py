"""
Robust package version lookup.

Never use ``module.__version__`` to check an installed package's version:
many packages (rich, click 8.2+, and others) don't reliably expose it, or
deprecate it in favor of standard packaging metadata. Use
``importlib.metadata`` instead — it reads the distribution's installed
metadata directly and works for every properly-packaged dependency.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def get_version(distribution_name: str) -> str | None:
    """
    Return the installed version of a distribution, or None if not installed.

    Args:
        distribution_name: PyPI/distribution name (e.g. "rich", "PySide6"),
            NOT the importable module name if they differ.

    Returns:
        Version string, or None if the distribution isn't installed.
    """
    try:
        return version(distribution_name)
    except PackageNotFoundError:
        return None


def require_version(distribution_name: str) -> str:
    """Like get_version, but raises if the distribution is not installed."""
    installed = get_version(distribution_name)
    if installed is None:
        raise PackageNotFoundError(distribution_name)
    return installed
