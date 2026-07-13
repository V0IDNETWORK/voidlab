"""
Unit tests for voidremote.utils.version — the module that replaced the
buggy ``module.__version__`` pattern (not every package defines that
attribute; e.g. ``rich`` doesn't, and ``click`` 8.2+ deprecates it) with
``importlib.metadata``, the correct way to read an installed
distribution's version.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest

from voidremote.utils.version import get_version, require_version


class TestGetVersion:
    def test_installed_package_returns_version_string(self) -> None:
        # click is a real dependency of this test environment (the `cli`
        # extra); this exercises the real importlib.metadata code path.
        version = get_version("click")
        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0

    def test_nonexistent_package_returns_none(self) -> None:
        assert get_version("this-package-definitely-does-not-exist-xyz-123") is None

    def test_does_not_raise_for_missing_package(self) -> None:
        # The whole point of this helper: never let a missing optional
        # dependency (e.g. PySide6 when only the SDK is installed) crash
        # a version-check call site like `voidremote doctor`.
        try:
            get_version("PySide6")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"get_version() must never raise, got: {exc!r}")


class TestRequireVersion:
    def test_installed_package(self) -> None:
        assert require_version("click") is not None

    def test_missing_package_raises(self) -> None:
        with pytest.raises(PackageNotFoundError):
            require_version("this-package-definitely-does-not-exist-xyz-123")
