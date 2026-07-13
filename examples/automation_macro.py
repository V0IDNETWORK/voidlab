"""
VoidRemote — Macro Recording and Playback

The macro engine (voidremote.core.automation) isn't part of the
stable public API yet. MacroPlayer drives any object exposing
``tap(serial, x, y)`` / ``swipe(serial, ...)`` / ``type_text(serial, ...)``
/ ``key_event(serial, ...)`` — that's AppController's signature (the
same object the CLI and GUI are built on), not VoidRemote's or
Device's, so this example talks to AppController directly rather than
through the top-level SDK client.

Run:
    python examples/automation_macro.py
"""

from __future__ import annotations

from pathlib import Path

from voidremote.adb.client import AdbError
from voidremote.controllers.app_controller import AppController
from voidremote.core.automation import MacroLibrary, MacroPlayer, MacroRecorder


def record_a_macro() -> None:
    """Record steps programmatically (a GUI would record real taps live)."""
    recorder = MacroRecorder("open settings and search")
    recorder.record_tap(540, 1200)       # open app drawer
    recorder.record_sleep(0.5)
    recorder.record_text("settings")
    recorder.record_sleep(0.3)
    recorder.record_tap(540, 300)        # tap first result
    macro = recorder.finish()

    library = MacroLibrary(Path.home() / ".voidremote" / "macros")
    library.save(macro)
    print(f"Saved macro: {macro.name} ({len(macro.steps)} steps)")


def play_it_back() -> None:
    library = MacroLibrary(Path.home() / ".voidremote" / "macros")
    macro = library.load("open settings and search")

    controller = AppController()
    controller.initialize()

    devices = controller.list_devices()
    if not devices:
        print("No device connected.")
        return
    serial = devices[0].serial

    player = MacroPlayer(controller)
    try:
        player.play(macro, serial=serial)
    except AdbError as exc:
        print(f"Playback failed: {exc}")

    controller.shutdown()


if __name__ == "__main__":
    record_a_macro()
    play_it_back()
