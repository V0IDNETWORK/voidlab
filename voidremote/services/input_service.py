"""Input control service — taps, swipes, text entry, and hardware key events."""

from __future__ import annotations

import logging
import time
import urllib.parse
from enum import IntEnum

from voidremote.adb.client import AdbClient

logger = logging.getLogger(__name__)


class KeyCode(IntEnum):
    """Android key event codes (subset covering common hardware/media keys)."""

    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_CALL = 5
    KEYCODE_ENDCALL = 6
    KEYCODE_DPAD_UP = 19
    KEYCODE_DPAD_DOWN = 20
    KEYCODE_DPAD_LEFT = 21
    KEYCODE_DPAD_RIGHT = 22
    KEYCODE_DPAD_CENTER = 23
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_POWER = 26
    KEYCODE_CAMERA = 27
    KEYCODE_MENU = 82
    KEYCODE_SEARCH = 84
    KEYCODE_ENTER = 66
    KEYCODE_DEL = 67
    KEYCODE_ESCAPE = 111
    KEYCODE_APP_SWITCH = 187
    KEYCODE_SLEEP = 223
    KEYCODE_WAKEUP = 224
    KEYCODE_BRIGHTNESS_DOWN = 220
    KEYCODE_BRIGHTNESS_UP = 221
    KEYCODE_MEDIA_PLAY_PAUSE = 85
    KEYCODE_MEDIA_NEXT = 87
    KEYCODE_MEDIA_PREVIOUS = 88
    KEYCODE_PASTE = 279


class InputService:
    """Sends touch/keyboard events to a device via ``adb shell input``."""

    def __init__(self, adb: AdbClient) -> None:
        self._adb = adb

    def tap(self, serial: str, x: int, y: int) -> None:
        logger.debug("tap(%s) -> %d,%d", serial, x, y)
        self._adb.shell(serial, f"input tap {x} {y}")

    def double_tap(self, serial: str, x: int, y: int, delay_ms: int = 100) -> None:
        self.tap(serial, x, y)
        time.sleep(delay_ms / 1000.0)
        self.tap(serial, x, y)

    def long_press(self, serial: str, x: int, y: int, duration_ms: int = 1000) -> None:
        logger.debug("long_press(%s) -> %d,%d (%dms)", serial, x, y, duration_ms)
        self._adb.shell(serial, f"input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(
        self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        logger.debug("swipe(%s) -> %d,%d to %d,%d (%dms)", serial, x1, y1, x2, y2, duration_ms)
        self._adb.shell(serial, f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def drag(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 1000) -> None:
        self.swipe(serial, x1, y1, x2, y2, duration_ms)

    def scroll_down(self, serial: str, x: int, y: int, amount: int = 500) -> None:
        self.swipe(serial, x, y, x, max(0, y - amount))

    def scroll_up(self, serial: str, x: int, y: int, amount: int = 500) -> None:
        self.swipe(serial, x, y, x, y + amount)

    def type_text(self, serial: str, text: str) -> None:
        """Type text on the device. Special characters are shell-escaped."""
        logger.debug("type_text(%s) -> %d chars", serial, len(text))
        # `input text` treats %s as a literal space; encode everything else
        # so quotes/backslashes/unicode can't break out of the shell arg.
        encoded = urllib.parse.quote(text, safe="")
        self._adb.shell(serial, f"input text {encoded}")

    def paste_clipboard(self, serial: str, text: str) -> None:
        """Best-effort: type the text directly (device clipboard APIs vary by OEM/root)."""
        self.type_text(serial, text)

    def key_event(self, serial: str, keycode: int | KeyCode) -> None:
        code = int(keycode)
        logger.debug("key_event(%s) -> %d", serial, code)
        self._adb.shell(serial, f"input keyevent {code}")

    def home(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_HOME)

    def back(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_BACK)

    def app_switch(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_APP_SWITCH)

    def power(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_POWER)

    def volume_up(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_VOLUME_UP)

    def volume_down(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_VOLUME_DOWN)

    def wake_device(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_WAKEUP)

    def sleep_device(self, serial: str) -> None:
        self.key_event(serial, KeyCode.KEYCODE_SLEEP)
