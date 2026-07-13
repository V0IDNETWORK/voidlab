"""Unit tests for the automation/macro engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from voidremote.core.automation import Macro, MacroLibrary, MacroPlayer, MacroRecorder, MacroStep


class TestMacroRecorder:
    def test_record_tap(self) -> None:
        rec = MacroRecorder("test")
        rec.record_tap(100, 200)
        macro = rec.finish()
        assert len(macro.steps) == 1
        assert macro.steps[0].action == "tap"
        assert macro.steps[0].params == {"x": 100, "y": 200}

    def test_record_swipe(self) -> None:
        rec = MacroRecorder("test")
        rec.record_swipe(0, 500, 0, 100, 300)
        macro = rec.finish()
        assert macro.steps[0].action == "swipe"
        assert macro.steps[0].params["x1"] == 0

    def test_record_text(self) -> None:
        rec = MacroRecorder("test")
        rec.record_text("hello world")
        macro = rec.finish()
        assert macro.steps[0].action == "text"
        assert macro.steps[0].params["text"] == "hello world"

    def test_record_keyevent(self) -> None:
        rec = MacroRecorder("test")
        rec.record_keyevent(4)
        macro = rec.finish()
        assert macro.steps[0].action == "keyevent"
        assert macro.steps[0].params["keycode"] == 4

    def test_record_multiple_steps(self) -> None:
        rec = MacroRecorder("multi")
        rec.record_tap(100, 100)
        rec.record_text("hello")
        rec.record_keyevent(66)
        macro = rec.finish()
        assert len(macro.steps) == 3
        assert macro.name == "multi"

    def test_finish_returns_macro(self) -> None:
        rec = MacroRecorder("my_macro")
        macro = rec.finish()
        assert isinstance(macro, Macro)
        assert macro.name == "my_macro"


class TestMacroSerialization:
    def test_to_dict(self) -> None:
        macro = Macro(name="test", steps=[MacroStep("tap", {"x": 1, "y": 2}, 0.1)], description="desc", repeat=2)
        d = macro.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert d["repeat"] == 2
        assert len(d["steps"]) == 1
        assert d["steps"][0]["action"] == "tap"

    def test_from_dict_roundtrip(self) -> None:
        macro = Macro(
            name="roundtrip",
            steps=[MacroStep("tap", {"x": 10, "y": 20}, 0.5), MacroStep("text", {"text": "hi"}, 0.3)],
            repeat=3,
        )
        restored = Macro.from_dict(macro.to_dict())
        assert restored.name == macro.name
        assert restored.repeat == macro.repeat
        assert len(restored.steps) == 2
        assert restored.steps[0].action == "tap"
        assert restored.steps[1].params["text"] == "hi"


class TestMacroPlayer:
    def test_play_tap(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("tap", {"x": 100, "y": 200}, 0.0)])
        player.play(macro, "serial123")
        ctrl.tap.assert_called_once_with("serial123", 100, 200)

    def test_play_swipe(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="s", steps=[MacroStep("swipe", {"x1": 0, "y1": 500, "x2": 0, "y2": 100, "duration_ms": 300}, 0.0)])
        player.play(macro, "s1")
        ctrl.swipe.assert_called_once()

    def test_play_text(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("text", {"text": "hello"}, 0.0)])
        player.play(macro, "s1")
        ctrl.type_text.assert_called_once_with("s1", "hello")

    def test_play_keyevent(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="k", steps=[MacroStep("keyevent", {"keycode": 4}, 0.0)])
        player.play(macro, "s1")
        ctrl.key_event.assert_called_once_with("s1", 4)

    def test_stop_before_play_skips_everything(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("tap", {"x": 0, "y": 0}, 0.0)] * 5)
        player.stop()
        player.play(macro, "s1")
        assert ctrl.tap.call_count == 0

    def test_repeat(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("tap", {"x": 1, "y": 1}, 0.0)], repeat=3)
        player.play(macro, "s1")
        assert ctrl.tap.call_count == 3

    def test_step_error_continues_to_next_step(self) -> None:
        ctrl = MagicMock()
        ctrl.tap.side_effect = Exception("ADB error")
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("tap", {"x": 0, "y": 0}, 0.0), MacroStep("text", {"text": "ok"}, 0.0)])
        player.play(macro, "s1")  # should not raise
        ctrl.type_text.assert_called_once()

    def test_stop_is_interruptible_mid_delay(self) -> None:
        # Real correctness fix under test: stop() must wake an in-progress
        # delay via threading.Event rather than waiting out a blocking
        # time.sleep(). We can't easily assert timing here without
        # flakiness, but we can assert the Event-based API exists and
        # stopping before any delay elapses still halts iteration.
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(
            name="t",
            steps=[MacroStep("tap", {"x": 1, "y": 1}, 10.0)] * 3,  # 10s delay each — must never fully elapse
            repeat=1,
        )
        import threading
        t = threading.Thread(target=player.play, args=(macro, "s1"))
        t.start()
        player.stop()
        t.join(timeout=2.0)
        assert not t.is_alive(), "MacroPlayer.play() did not stop promptly when stop() was called"

    def test_reset_allows_replay_after_stop(self) -> None:
        ctrl = MagicMock()
        player = MacroPlayer(ctrl)
        macro = Macro(name="t", steps=[MacroStep("tap", {"x": 1, "y": 1}, 0.0)])

        player.stop()
        player.play(macro, "s1")
        assert ctrl.tap.call_count == 0, "stop() before play() must be honored (sticky)"

        player.reset()
        player.play(macro, "s1")
        assert ctrl.tap.call_count == 1, "reset() must allow the player to be reused"


class TestMacroLibrary:
    def test_save_and_load(self, tmp_path: Path) -> None:
        lib = MacroLibrary(tmp_path)
        macro = Macro(name="my test macro", steps=[MacroStep("tap", {"x": 1, "y": 1}, 0.0)])
        lib.save(macro)
        loaded = lib.load("my test macro")
        assert loaded.name == "my test macro"
        assert len(loaded.steps) == 1

    def test_list_macros(self, tmp_path: Path) -> None:
        lib = MacroLibrary(tmp_path)
        lib.save(Macro(name="macro one"))
        lib.save(Macro(name="macro two"))
        assert len(lib.list_macros()) == 2

    def test_delete(self, tmp_path: Path) -> None:
        lib = MacroLibrary(tmp_path)
        lib.save(Macro(name="delete me"))
        assert lib.delete("delete me") is True
        assert "delete me" not in lib.list_macros()

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        assert MacroLibrary(tmp_path).delete("ghost") is False

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            MacroLibrary(tmp_path).load("ghost macro")
