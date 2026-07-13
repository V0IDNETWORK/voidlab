"""Unit tests for InputService."""

from __future__ import annotations

from unittest.mock import MagicMock, call

from voidremote.services.input_service import InputService, KeyCode


class TestTap:
    def test_tap_calls_shell(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.tap("serial1", 500, 800)
        mock_adb.shell.assert_called_once_with("serial1", "input tap 500 800")

    def test_double_tap_taps_twice(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.double_tap("serial1", 100, 200, delay_ms=0)
        assert mock_adb.shell.call_count == 2


class TestSwipe:
    def test_swipe_basic(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.swipe("serial1", 0, 500, 0, 100, 300)
        mock_adb.shell.assert_called_once_with("serial1", "input swipe 0 500 0 100 300")

    def test_scroll_down_swipes_upward(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.scroll_down("serial1", 540, 1200, amount=500)
        args = mock_adb.shell.call_args[0]
        assert "540 1200 540 700" in args[1]

    def test_scroll_down_never_negative(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.scroll_down("serial1", 540, 100, amount=500)
        args = mock_adb.shell.call_args[0]
        assert "540 100 540 0" in args[1]  # clamped at 0, not negative


class TestTextInput:
    def test_type_text_encodes(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.type_text("serial1", "hello world")
        mock_adb.shell.assert_called_once_with("serial1", "input text hello%20world")

    def test_type_text_special_chars_dont_break_shell(self, input_service: InputService, mock_adb: MagicMock) -> None:
        # Quotes/backticks in user text must never reach the shell unescaped.
        input_service.type_text("serial1", "it's a `test`; rm -rf")
        args = mock_adb.shell.call_args[0]
        assert "`" not in args[1]
        assert ";" not in args[1]
        assert " " not in args[1].removeprefix("input text ")


class TestKeyEvents:
    def test_key_event_int(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.key_event("serial1", 4)
        mock_adb.shell.assert_called_once_with("serial1", "input keyevent 4")

    def test_key_event_enum(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.key_event("serial1", KeyCode.KEYCODE_HOME)
        mock_adb.shell.assert_called_once_with("serial1", "input keyevent 3")

    def test_home(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.home("serial1")
        mock_adb.shell.assert_called_once_with("serial1", "input keyevent 3")

    def test_back(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.back("serial1")
        mock_adb.shell.assert_called_once_with("serial1", "input keyevent 4")

    def test_volume_up(self, input_service: InputService, mock_adb: MagicMock) -> None:
        input_service.volume_up("serial1")
        mock_adb.shell.assert_called_once_with("serial1", "input keyevent 24")


class TestKeyCodeEnum:
    def test_values_match_android(self) -> None:
        assert KeyCode.KEYCODE_HOME == 3
        assert KeyCode.KEYCODE_BACK == 4
        assert KeyCode.KEYCODE_ENTER == 66
        assert KeyCode.KEYCODE_APP_SWITCH == 187
