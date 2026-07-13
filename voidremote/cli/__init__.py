"""
VoidRemote command-line interface.

Not imported by the base ``voidremote`` package (which stays
dependency-light for SDK-only users) — import explicitly, or just run
the ``voidremote`` console script installed by ``pip install voidremote[cli]``.
"""

from voidremote.cli.main import cli, main

__all__ = ["cli", "main"]
