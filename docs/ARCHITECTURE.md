# Architecture

VoidRemote is a layered SDK with two optional applications (CLI, GUI)
built on top. This document describes how the layers fit together and
why they're separated the way they are.

## Layers

```
┌─────────────────────────────────────────────────────────┐
│  voidremote.cli / voidremote.ui        (optional apps)   │
│      Click commands, PySide6 widgets                     │
│      Depend on: the layer below, plus click/rich/PySide6 │
├─────────────────────────────────────────────────────────┤
│  voidremote.api                        (PUBLIC, STABLE)  │
│      VoidRemote, Device, DeviceList, PairingSession,      │
│      AsyncVoidRemote, exceptions                          │
│      Depends on: controllers                               │
├─────────────────────────────────────────────────────────┤
│  voidremote.controllers                (internal)         │
│      AppController — the one dependency-injection root    │
│      Depends on: services, adb, config                    │
├─────────────────────────────────────────────────────────┤
│  voidremote.services                   (internal)         │
│      DeviceService, InputService, MonitorService           │
│      Depends on: adb, models                               │
├─────────────────────────────────────────────────────────┤
│  voidremote.adb                        (internal)         │
│      AdbClient — the only module that runs subprocess      │
│      Depends on: models, utils                             │
├─────────────────────────────────────────────────────────┤
│  voidremote.models / config / utils / core / network      │
│      Pydantic models, settings, validation, macros          │
└─────────────────────────────────────────────────────────┘
```

Only `voidremote.api` (re-exported at the package top level) is a
stable, semantically-versioned surface. Everything below it can change
between minor versions without notice — if you're building on
VoidRemote, import from `voidremote` or `voidremote.api`, not from
`voidremote.adb`, `.services`, or `.controllers` directly.

## Why this separation

**`voidremote.adb`** is the only place a subprocess ever gets spawned.
Every ADB command — `devices`, `connect`, `shell`, `push`, `install`,
`screenrecord` — funnels through `AdbClient._run_sync` /
`_run_async`. This means: one place to get timeout handling right, one
place to get error normalization right, and one seam to mock in every
test above this layer (every test in `tests/unit` and
`tests/integration` mocks `AdbClient`, never touches a real device).

**`voidremote.services`** turns raw ADB output into typed objects and
owns state that outlives a single command: `DeviceService` parses
`adb devices -l` into `Device` models and persists trusted devices to
disk; `MonitorService` owns the background polling thread per device;
`InputService` is stateless, just a typed wrapper over `input`
commands.

**`voidremote.controllers.AppController`** is the single composition
root. It's constructed with every service injectable via the
constructor (not hardcoded), so tests can swap in mocks without
monkeypatching module globals — see `tests/conftest.py`. Both the CLI
and the public SDK sit on top of the same `AppController`; there is
exactly one implementation of "what does `tap(serial, x, y)` do",
not one per consumer.

**`voidremote.api`** wraps `AppController` in an object-oriented,
per-device interface (`Device.tap()` instead of
`controller.tap(serial, x, y)`), translates internal exceptions into
the public `VoidRemoteError` hierarchy, and is the only layer this
project promises not to break within a major version.

**`voidremote.cli`** and **`voidremote.ui`** are consumers, not
special. They're built entirely on `AppController` — either is
optional at install time via extras, and neither is imported by
`voidremote/__init__.py`, so `pip install voidremote` alone never
pulls in `click`, `rich`, or `PySide6`.

## Threading

- `voidremote.adb.AdbClient._run_sync` is a blocking `subprocess.run`
  call. `_run_async` is a genuine `asyncio.create_subprocess_exec`
  call for the async path.
- `voidremote.services.monitor_service.MonitorService` runs one
  `threading.Thread` per monitored device, using
  `threading.Event.wait()` for its poll interval (interruptible, not a
  blocking `time.sleep`), so `stop()` returns promptly instead of
  waiting out a full poll cycle.
- `voidremote.api.async_client.AsyncVoidRemote` wraps the sync API in
  `asyncio.to_thread` rather than reimplementing the ADB wire protocol
  — see the README's Async section for why that's the honest tradeoff.
- `voidremote.ui.workers.BaseWorker` (GUI only) standardizes QThread
  lifecycle: every worker's `finished` signal fires exactly once, and
  every widget that starts one tracks it via `WorkerOwnerMixin`, whose
  `shutdown_workers()` blocks until every tracked worker has actually
  exited. This exists specifically to prevent
  `QThread: Destroyed while thread is still running`.

## Configuration

`voidremote.config.settings.AppSettings` is a `pydantic-settings`
tree (`AdbSettings`, `UISettings`, `MirrorSettings`, `LoggingSettings`,
`KeyboardShortcuts`), loadable from environment variables
(`VOIDREMOTE_ADB_PATH`, etc.) or a JSON file at a platform-appropriate
config directory (via `platformdirs`, not the unmaintained `appdirs`).
`AppController` takes an `AppSettings` instance through its
constructor rather than reading the global singleton itself, so tests
inject their own settings instead of mutating global state.

## Testing strategy

- **`tests/unit`** — pure logic: parsers, validators, models, the
  macro engine. No subprocess, no network, no Qt.
- **`tests/integration`** — service-level behavior against a mocked
  `AdbClient`, including real file I/O for trusted-device persistence.
- **`tests/cli`** — Click's `CliRunner` against a mocked
  `AppController`.
- **`tests/packaging`** — the build backend and metadata actually
  resolve, an editable install and a wheel actually build, using the
  real installed `setuptools`/`pip` (`--no-build-isolation` so this
  runs offline).
- **`tests/gui`** — real `QThread` workers and real widgets against a
  real (offscreen) `QApplication`, gated on the `gui` extra being
  installed via `pytest.importorskip`.
