# Changelog

All notable changes to VoidRemote are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] — 2025

### Added
- Public Python SDK (`voidremote.api`): `VoidRemote`, `Device`,
  `DeviceList`, `PairingSession`, `AsyncVoidRemote`, `AsyncDevice`,
  a `VoidRemoteError` exception hierarchy, and `py.typed` for full
  type-checker/IDE support.
- CLI (`voidremote`, `pip install voidremote[cli]`) covering device
  discovery, wireless pairing, input, file transfer, package
  management, shell access, screen capture, and monitoring, with
  `--json` output on every command.
- Desktop GUI (`voidremote-gui`, `pip install voidremote[gui]`):
  device dashboard, embedded shell, file manager, live monitoring
  graphs, settings panel.
- Macro recording/playback engine (`voidremote.core.automation`).
- Local subnet scanning for wireless ADB discovery
  (`voidremote.network.discovery`).

### Fixed
- **Packaging**: `build-backend` in `pyproject.toml` pointed at a
  nonexistent module (`setuptools.backends.legacy:build`), breaking
  `pip install -e .` and wheel builds with
  `BackendUnavailable: Cannot import setuptools.backends.legacy`.
  Corrected to `setuptools.build_meta`.
- **GUI**: the dark theme's QSS stylesheet was rendered with
  `str.format()`, which parses every literal `{...}` CSS rule block as
  a substitution field, raising `KeyError` or
  `ValueError: Single '}' encountered in format string` depending on
  content. Rewritten with `string.Template` (`$VAR` syntax), which
  never touches `{`/`}`.
- **GUI**: `DashboardView` called `QScrollArea.setWidget()` three times
  during construction; Qt deletes a scroll area's previous widget when
  a new one is assigned, so the second/third calls destroyed a widget
  (and its layout) Python still held a live reference to, surfacing
  later as `RuntimeError: Internal C++ object already deleted` in
  `_update_grid()`. Fixed to call `setWidget()` exactly once, after
  the full widget tree is built.
- **GUI**: background `QThread` workers had no guaranteed shutdown
  path, producing `QThread: Destroyed while thread is still running`
  on close. Added `voidremote.ui.workers.BaseWorker` +
  `WorkerOwnerMixin`, adopted by every dialog/view that starts a
  worker; `closeEvent` now blocks briefly until all tracked workers
  have actually exited.
- **CLI**: `voidremote doctor` read `module.__version__` to report
  dependency versions — not every package defines that attribute
  (`rich` doesn't; `click` 8.2+ deprecates it). Switched to
  `importlib.metadata.version()`.
- **CLI**: `voidremote --json doctor` and `voidremote --json logs`
  emitted a Rich-rendered banner/colored lines before or instead of
  JSON, corrupting output for anything piping into `jq`. Both now
  honor `--json` like every other command.
- **Core**: `MacroPlayer.play()` unconditionally cleared any prior
  `stop()` request at the start of playback, so calling `stop()`
  before `play()` silently had no effect. `stop()` is now sticky; a
  new `reset()` method allows intentional reuse of a stopped player.
- **Core**: battery charging state was inferred by searching for the
  literal string `"charging"` in `dumpsys battery` output rather than
  decoding the real Android `BatteryManager` status code, an
  incorrect heuristic that happened to often work by coincidence. Now
  decodes status codes 2 (`CHARGING`) and 5 (`FULL`) correctly.
- **Core**: subnet scanning spawned one OS thread per host
  unconditionally (up to 254 for a /24) gated only by a semaphore
  inside each thread body; replaced with a bounded
  `ThreadPoolExecutor`.

### Changed
- `DeviceService` and `AppController` now take every collaborator
  (`AdbClient`, individual services, `AppSettings`) through their
  constructors rather than instantiating them internally, enabling
  tests to inject mocks without monkeypatching module-level globals.
- Replaced the unmaintained `appdirs` dependency with `platformdirs`.
- `pyproject.toml` restructured around optional-dependency extras
  (`cli`, `gui`, `full`, `dev`, `docs`) so `pip install voidremote`
  alone stays SDK-only with no `click`/`rich`/`PySide6` pulled in.

## [0.1.0] — Initial development

Initial internal scaffolding; not released.
