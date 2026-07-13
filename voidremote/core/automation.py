"""Automation engine — macro recording and playback."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MacroStep:
    """A single recorded automation step."""

    action: str  # tap | swipe | text | keyevent | sleep
    params: dict
    delay_after: float = 0.0


@dataclass(slots=True)
class Macro:
    """A recorded sequence of automation steps."""

    name: str
    steps: list[MacroStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    repeat: int = 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "repeat": self.repeat,
            "steps": [asdict(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Macro:
        steps = [MacroStep(**s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            repeat=data.get("repeat", 1),
            steps=steps,
        )


class MacroRecorder:
    """Records a sequence of input actions into a :class:`Macro`."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._steps: list[MacroStep] = []
        self._last_time: float = time.monotonic()

    def _delay(self) -> float:
        now = time.monotonic()
        delay = now - self._last_time
        self._last_time = now
        return round(delay, 3)

    def record_tap(self, x: int, y: int) -> None:
        self._steps.append(MacroStep("tap", {"x": x, "y": y}, self._delay()))

    def record_swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        self._steps.append(MacroStep(
            "swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
            self._delay(),
        ))

    def record_text(self, text: str) -> None:
        self._steps.append(MacroStep("text", {"text": text}, self._delay()))

    def record_keyevent(self, keycode: int) -> None:
        self._steps.append(MacroStep("keyevent", {"keycode": keycode}, self._delay()))

    def record_sleep(self, seconds: float) -> None:
        self._steps.append(MacroStep("sleep", {"seconds": seconds}, 0.0))

    def finish(self) -> Macro:
        return Macro(name=self._name, steps=self._steps)


class MacroPlayer:
    """Plays back a :class:`Macro` against a target device via any object
    exposing ``tap``, ``swipe``, ``type_text``, ``key_event`` (e.g. a
    :class:`~voidremote.controllers.app_controller.AppController` or the
    public SDK's :class:`~voidremote.api.Device`).
    """

    def __init__(self, controller: object) -> None:
        self._controller = controller
        self._stop_event = threading.Event()

    def play(self, macro: Macro, serial: str, speed: float = 1.0) -> None:
        """
        Execute a macro on the specified device. Blocks until finished
        or :meth:`stop` is called.

        If :meth:`stop` was called since this player was created (or
        since the last :meth:`reset`), this returns immediately without
        executing anything — "stop" is sticky by design, so a stray
        pre-emptive stop can never be silently overridden. Call
        :meth:`reset` (or construct a new :class:`MacroPlayer`) before
        replaying on the same instance.
        """
        logger.info("Playing macro '%s' on %s (repeat=%d)", macro.name, serial, macro.repeat)

        for iteration in range(macro.repeat):
            if self._stop_event.is_set():
                break
            logger.debug("Macro iteration %d/%d", iteration + 1, macro.repeat)
            for step in macro.steps:
                if self._stop_event.is_set():
                    break
                if step.delay_after > 0:
                    self._stop_event.wait(step.delay_after / speed)
                    if self._stop_event.is_set():
                        break
                self._execute_step(step, serial)

        logger.info("Macro '%s' finished (stopped=%s)", macro.name, self._stop_event.is_set())

    def stop(self) -> None:
        """Request playback to stop as soon as possible. Sticky until :meth:`reset`."""
        self._stop_event.set()

    def reset(self) -> None:
        """Clear a prior stop request so this instance can be reused for a fresh :meth:`play`."""
        self._stop_event.clear()

    def _execute_step(self, step: MacroStep, serial: str) -> None:
        try:
            if step.action == "tap":
                self._controller.tap(serial, step.params["x"], step.params["y"])
            elif step.action == "swipe":
                self._controller.swipe(
                    serial, step.params["x1"], step.params["y1"],
                    step.params["x2"], step.params["y2"], step.params.get("duration_ms", 300),
                )
            elif step.action == "text":
                self._controller.type_text(serial, step.params["text"])
            elif step.action == "keyevent":
                self._controller.key_event(serial, step.params["keycode"])
            elif step.action == "sleep":
                time.sleep(step.params.get("seconds", 0.5))
            else:
                logger.warning("Unknown macro action: %s", step.action)
        except Exception:
            logger.exception("Macro step %r failed", step.action)


class MacroLibrary:
    """Persistent JSON-backed storage for named macros."""

    def __init__(self, storage_dir: Path) -> None:
        self._dir = storage_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(name: str) -> str:
        return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).replace(" ", "_")

    def save(self, macro: Macro) -> Path:
        path = self._dir / f"{self._safe_name(macro.name)}.json"
        path.write_text(json.dumps(macro.to_dict(), indent=2), encoding="utf-8")
        logger.debug("Saved macro: %s", path)
        return path

    def load(self, name: str) -> Macro:
        path = self._dir / f"{self._safe_name(name)}.json"
        if not path.exists():
            raise FileNotFoundError(f"Macro not found: {name!r}")
        return Macro.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_macros(self) -> list[str]:
        return [p.stem.replace("_", " ") for p in sorted(self._dir.glob("*.json"))]

    def delete(self, name: str) -> bool:
        path = self._dir / f"{self._safe_name(name)}.json"
        if path.exists():
            path.unlink()
            return True
        return False
