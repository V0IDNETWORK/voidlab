#!/usr/bin/env python3
"""
VoidRemote build script.

Builds a wheel and source distribution using the standard PEP 517
build frontend. Requires the ``build`` package
(``pip install voidremote[dev]`` includes it).

Usage:
    python scripts/build.py             # build wheel + sdist into dist/
    python scripts/build.py --check     # also run twine check on the results
    python scripts/build.py --clean     # remove dist/, build/, *.egg-info first
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"


def clean() -> None:
    print("Cleaning build artifacts...")
    for path in (DIST_DIR, PROJECT_ROOT / "build"):
        if path.exists():
            shutil.rmtree(path)
            print(f"  removed {path}")
    for egg_info in PROJECT_ROOT.glob("*.egg-info"):
        shutil.rmtree(egg_info)
        print(f"  removed {egg_info}")


def build() -> None:
    print("Building wheel and sdist...")
    try:
        import build  # noqa: F401
    except ImportError:
        print("The 'build' package is required: pip install build", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([sys.executable, "-m", "build", str(PROJECT_ROOT)], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("Build failed.", file=sys.stderr)
        sys.exit(result.returncode)

    print("\nBuilt artifacts:")
    for artifact in sorted(DIST_DIR.glob("*")):
        print(f"  {artifact.name}")


def check() -> None:
    print("Checking distribution with twine...")
    result = subprocess.run(
        [sys.executable, "-m", "twine", "check", str(DIST_DIR / "*")], cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        print("twine check failed. Install it with: pip install twine", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build VoidRemote's wheel and sdist.")
    parser.add_argument("--clean", action="store_true", help="Remove build artifacts first.")
    parser.add_argument("--check", action="store_true", help="Run 'twine check' after building.")
    args = parser.parse_args()

    if args.clean:
        clean()

    build()

    if args.check:
        check()

    print("\nDone. Install locally with:")
    print(f"  pip install {DIST_DIR}/voidremote-*.whl")
    print("Publish with:")
    print(f"  python -m twine upload {DIST_DIR}/*")


if __name__ == "__main__":
    main()
