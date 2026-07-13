#!/usr/bin/env python3
"""
VoidRemote developer setup script.

Run once after cloning to set up a complete development environment:
editable install with every extra, pre-commit hooks, and a sanity
check that the toolchain (adb, Python version) is in place.

Usage:
    python scripts/setup_dev.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], description: str) -> bool:
    print(f"-> {description}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    ok = result.returncode == 0
    print("   OK" if ok else "   FAILED")
    return ok


def check_python_version() -> bool:
    print("-> Checking Python version")
    ok = sys.version_info >= (3, 12)
    print(f"   {sys.version.split()[0]} ({'OK' if ok else 'Python 3.12+ required'})")
    return ok


def check_adb() -> bool:
    print("-> Checking for adb binary")
    path = shutil.which("adb")
    if path:
        print(f"   found at {path}")
        return True
    print("   NOT FOUND — install Android Platform Tools:")
    print("   https://developer.android.com/tools/releases/platform-tools")
    return False


def main() -> None:
    print("VoidRemote developer setup\n" + "=" * 40)

    results = {
        "Python version": check_python_version(),
        "adb binary": check_adb(),
        "Editable install (SDK + CLI + GUI + dev tools)": run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            "Installing package in editable mode with all extras",
        ),
        "pre-commit hooks": run(
            [sys.executable, "-m", "pre_commit", "install"], "Installing pre-commit hooks"
        ),
    }

    print("\n" + "=" * 40)
    print("Summary:")
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {name}")

    if all(results.values()):
        print("\nSetup complete. Try:")
        print("  pytest")
        print("  voidremote doctor")
        print("  voidremote-gui")
    else:
        print("\nSome steps failed — see above. Setup is not complete.")
        sys.exit(1)


if __name__ == "__main__":
    main()
