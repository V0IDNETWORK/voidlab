"""
Packaging tests.

These tests use the real, installed ``setuptools``/``pip`` toolchain
to verify the package actually builds — not just that
``pyproject.toml`` is syntactically valid TOML, which would NOT have
caught the reported
``BackendUnavailable: Cannot import setuptools.backends.legacy`` bug
(a bogus-but-syntactically-valid build-backend string).

Slow / networked steps (an actual ``pip install`` that resolves
dependencies from PyPI) are marked ``@pytest.mark.packaging``; the
ones here all run offline via ``--no-deps --no-build-isolation``
against the already-installed toolchain, so they run in CI or locally
without network access.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from importlib.util import find_spec
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pyproject_data() -> dict:
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


class TestPyprojectStructure:
    def test_parses_as_valid_toml(self, pyproject_data: dict) -> None:
        assert pyproject_data  # tomllib.load already raised if invalid

    def test_build_backend_is_a_real_importable_module(self, pyproject_data: dict) -> None:
        """
        The exact regression test for the reported bug: the previous
        pyproject.toml declared
        ``build-backend = "setuptools.backends.legacy:build"`` — a
        module path that does not exist in setuptools. TOML validation
        can never catch this; only actually trying to resolve the
        module does.
        """
        backend = pyproject_data["build-system"]["build-backend"]
        module_path = backend.split(":")[0]
        spec = find_spec(module_path)
        assert spec is not None, (
            f"build-backend {backend!r} points at {module_path!r}, which "
            f"cannot be imported — pip install/build would fail with "
            f"BackendUnavailable."
        )

    def test_build_backend_is_setuptools_build_meta(self, pyproject_data: dict) -> None:
        assert pyproject_data["build-system"]["build-backend"] == "setuptools.build_meta"

    def test_requires_setuptools_new_enough_for_editable_installs(self, pyproject_data: dict) -> None:
        # PEP 660 editable installs need setuptools>=64.
        requires = pyproject_data["build-system"]["requires"]
        setuptools_req = next(r for r in requires if r.startswith("setuptools"))
        assert ">=68" in setuptools_req or ">=64" in setuptools_req

    def test_package_name(self, pyproject_data: dict) -> None:
        assert pyproject_data["project"]["name"] == "voidremote"

    def test_console_script_target_is_importable_path(self, pyproject_data: dict) -> None:
        entry = pyproject_data["project"]["scripts"]["voidremote"]
        module_path, _, func_name = entry.partition(":")
        assert module_path == "voidremote.cli.main"
        assert func_name == "main"

    def test_gui_script_target_is_importable_path(self, pyproject_data: dict) -> None:
        entry = pyproject_data["project"]["gui-scripts"]["voidremote-gui"]
        module_path, _, func_name = entry.partition(":")
        assert module_path == "voidremote.ui.app"
        assert func_name == "main"

    def test_core_dependencies_do_not_include_gui_or_cli_only_packages(self, pyproject_data: dict) -> None:
        """The SDK/extras split means `pip install voidremote` alone stays lightweight."""
        core_deps = " ".join(pyproject_data["project"]["dependencies"]).lower()
        assert "pyside6" not in core_deps
        assert "click" not in core_deps
        assert "rich" not in core_deps

    def test_cli_extra_declares_click_and_rich(self, pyproject_data: dict) -> None:
        cli_extra = " ".join(pyproject_data["project"]["optional-dependencies"]["cli"]).lower()
        assert "click" in cli_extra
        assert "rich" in cli_extra

    def test_gui_extra_declares_pyside6(self, pyproject_data: dict) -> None:
        gui_extra = " ".join(pyproject_data["project"]["optional-dependencies"]["gui"]).lower()
        assert "pyside6" in gui_extra

    def test_license_is_declared(self, pyproject_data: dict) -> None:
        assert pyproject_data["project"]["license"]["file"] == "LICENSE"

    def test_python_requires_312_plus(self, pyproject_data: dict) -> None:
        assert pyproject_data["project"]["requires-python"] == ">=3.12"

    def test_classifiers_include_python_versions(self, pyproject_data: dict) -> None:
        classifiers = pyproject_data["project"]["classifiers"]
        assert any("3.12" in c for c in classifiers)
        assert any("3.13" in c for c in classifiers)


class TestRequiredFilesExist:
    @pytest.mark.parametrize("filename", [
        "LICENSE", "README.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md",
        ".gitignore", "pyproject.toml", "voidremote/py.typed",
    ])
    def test_file_exists(self, filename: str) -> None:
        assert (PROJECT_ROOT / filename).exists(), f"Missing required file: {filename}"


class TestPyTypedMarker:
    def test_py_typed_is_declared_in_package_data(self, pyproject_data: dict) -> None:
        package_data = pyproject_data["tool"]["setuptools"]["package-data"]["voidremote"]
        assert "py.typed" in package_data

    def test_py_typed_file_actually_exists(self) -> None:
        # A declared-but-missing py.typed silently disables type checking
        # for downstream users, with no error at install time.
        assert (PROJECT_ROOT / "voidremote" / "py.typed").exists()


@pytest.mark.packaging
class TestRealBuildToolchain:
    """
    Exercises the real, installed setuptools/pip to actually attempt a
    build/install. ``--no-build-isolation`` deliberately reuses
    whatever setuptools/wheel are already installed instead of
    creating a fresh isolated build environment (which needs network
    access to fetch build requirements) — this is what makes it
    possible to run this offline while still exercising the real
    PEP 517/660 build-backend resolution and metadata generation.
    """

    def test_setuptools_build_meta_resolves_our_metadata(self) -> None:
        """
        Directly exercises the exact code path pip uses: import the
        declared build backend and ask it to prepare metadata. This is
        the precise operation that failed with BackendUnavailable
        before the fix.
        """
        if find_spec("setuptools.build_meta") is None:
            pytest.skip("setuptools.build_meta not available in this environment")

        import os
        import tempfile

        from setuptools import build_meta

        with tempfile.TemporaryDirectory() as td:
            cwd = os.getcwd()
            try:
                os.chdir(PROJECT_ROOT)
                metadata_dir = build_meta.prepare_metadata_for_build_wheel(td)
                dist_info = Path(td) / metadata_dir
                assert dist_info.exists()
                metadata_text = (dist_info / "METADATA").read_text(encoding="utf-8")
                assert "Name: voidremote" in metadata_text
            finally:
                os.chdir(cwd)

    def test_editable_install_no_deps_no_isolation(self) -> None:
        """
        The literal regression test for
        ``pip install -e ".[dev]"`` -> ``BackendUnavailable``. Uses
        ``--no-deps --no-build-isolation`` so it runs fully offline
        against the already-installed setuptools/pip, while still
        exercising real PEP 660 editable-install machinery.

        Skips (does not fail) if the environment is PEP 668
        "externally managed" (e.g. Debian/Ubuntu system Python) and
        refuses ANY pip install without ``--break-system-packages`` —
        that's an OS policy unrelated to whether this package's build
        backend actually works, which is what this test exists to
        check. A venv or a typical CI runner won't hit this.
        """
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_ROOT),
             "--no-deps", "--no-build-isolation", "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0 and "externally-managed-environment" in result.stderr:
            pytest.skip(
                "This Python is PEP 668 externally-managed and refuses any "
                "`pip install` without --break-system-packages; not a "
                "packaging defect in this project. Run in a venv to "
                "exercise this test."
            )
        assert result.returncode == 0, (
            f"Editable install failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_wheel_builds_no_deps_no_isolation(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", str(PROJECT_ROOT),
             "--no-deps", "--no-build-isolation", "--quiet", "-w", str(tmp_path)],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, (
            f"Wheel build failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        wheels = list(tmp_path.glob("voidremote-*.whl"))
        assert len(wheels) == 1, f"Expected exactly one wheel, found: {wheels}"
