# VoidRemote Desktop

A PySide6 desktop application built on the [VoidRemote SDK](../README.md).
Install it with:

```bash
pip install voidremote[gui]
voidremote-gui
```

## Layout

- **Devices** — a card grid of every device visible to `adb`, with
  connect/disconnect, quick info, and a mirror shortcut per card
- **Shell** — an embedded ADB shell terminal with command history
- **Monitor** — live CPU, RAM, battery, and temperature gauges with
  rolling sparkline history, polled on a background thread
- **Files** — browse device storage, upload, and download
- **Settings** — ADB path/timeouts, theme, mirror quality, logging
- **Logs** — a live view of the application's own log output

## Pairing a device

Toolbar → **+ Pair**, or `Ctrl+Shift+P`. Enter the IP, pairing port, and
6-digit code shown under **Settings → Developer Options → Wireless
Debugging → Pair device with pairing code** on the Android device.

## Connecting an already-paired device

Toolbar → **⚡ Connect**, or `Ctrl+Shift+C`. Enter the device's IP (default
port 5555).

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `F5` | Refresh device list |
| `Ctrl+Shift+P` | Pair new device |
| `Ctrl+Shift+C` | Connect by IP |
| `Ctrl+Q` | Quit |

## Threading model

Every network/ADB call that could block runs on a `QThread` subclass
(`voidremote.ui.workers.BaseWorker`), never on the UI thread. Every
widget that starts one tracks it via `WorkerOwnerMixin` and blocks
briefly on close until it has actually exited — this is what's behind
"the app closes without warnings" rather than something you need to
manage yourself if you're extending the GUI.

## Running headless (CI smoke tests)

PySide6 supports an offscreen platform plugin, so the GUI test suite
runs without a real display:

```bash
QT_QPA_PLATFORM=offscreen pytest -m gui
```

## Building a standalone executable

Not bundled by VoidRemote itself, but the usual PyInstaller/Nuitka
approach works against the `voidremote-gui` entry point:

```bash
pip install voidremote[gui] pyinstaller
pyinstaller --onefile --windowed --name VoidRemote \
    --collect-all PySide6 \
    -p . "$(python -c 'import voidremote.ui.app as m; print(m.__file__)')"
```
