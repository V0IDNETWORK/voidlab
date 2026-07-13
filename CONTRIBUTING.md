# Contributing to VoidRemote

Thanks for your interest in contributing — bug reports, feature
requests, documentation fixes, and code changes are all welcome.

## Development setup

```bash
git clone https://github.com/V0IDNETWORK/VoidRemote.git
cd VoidRemote
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pre-commit install
```

`pip install -e ".[dev]"` pulls in the SDK, CLI, GUI, and every
development tool (pytest, mypy, ruff, black) in one shot. Run
`python scripts/setup_dev.py` for the same thing plus a couple of
convenience checks.

## Project layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full layer
breakdown. In short:

- `voidremote/api/` — the public SDK surface. Changes here need to
  stay backward-compatible within a major version.
- `voidremote/adb/`, `services/`, `controllers/` — internal
  implementation. Free to refactor as long as `api/` behavior doesn't
  change.
- `voidremote/cli/`, `voidremote/ui/` — the two applications built on
  the SDK. Neither should ever be imported by `voidremote/__init__.py`.
- `tests/unit`, `tests/integration`, `tests/cli`, `tests/packaging`,
  `tests/gui` — see each directory's own scope; put new tests in the
  narrowest one that applies.

## Before opening a PR

```bash
black voidremote tests
ruff check voidremote tests
mypy voidremote
pytest                                        # unit + integration + cli + packaging
QT_QPA_PLATFORM=offscreen pytest -m gui        # if you touched voidremote/ui
```

All four must pass. CI runs the same commands and will reject a PR
that doesn't.

## Testing conventions

- Every test above `voidremote.adb` mocks `AdbClient` — never spawn a
  real `adb` subprocess in `tests/unit` or `tests/integration`.
- If you're injecting state that used to be monkeypatched (a file
  path, a config directory), prefer adding a constructor parameter
  with a sensible default over `unittest.mock.patch`-ing a module
  global — see `DeviceService.__init__`'s `trusted_devices_file`
  parameter for the pattern.
- GUI tests go in `tests/gui`, are marked `@pytest.mark.gui`, and must
  pass with `QT_QPA_PLATFORM=offscreen` (no real display available).
  If you add a `QThread` subclass, add a lifecycle test alongside it
  that asserts the thread has actually stopped, not just that
  `.quit()` was called.
- Packaging changes (`pyproject.toml`) need a test in
  `tests/packaging` that would have failed before your fix — a
  `pyproject.toml` typo that's syntactically valid TOML won't be
  caught by parsing it; it needs an actual build-backend resolution or
  install attempt.

## Code style

- Python 3.12+, full type hints, `from __future__ import annotations`
  at the top of every module.
- `black` (line length 100) and `ruff` are the source of truth for
  formatting/lint — don't hand-format against a different style.
- Docstrings on every public class and method in `voidremote/api/`;
  internal modules should have module- and class-level docstrings at
  minimum.
- No bare `except:` — catch specific exceptions, or `except Exception`
  with a comment explaining why it's a deliberate thread/process
  boundary (see `voidremote/ui/workers.py` for an example).

## Commit messages

Conventional, plain-English commit messages describing what changed
and why. Reference the issue number if there is one.

## Reporting bugs

Open an issue with:
- VoidRemote version (`voidremote version` or `pip show voidremote`)
- Python version and OS
- Minimal reproduction (a script, or exact CLI command)
- Full traceback if there is one

## Security issues

Do not open a public issue — see [SECURITY.md](SECURITY.md).
