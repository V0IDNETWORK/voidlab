# VoidRemote

A Python interface to Android Debug Bridge (ADB).

VoidRemote wraps `adb` so you write Python instead of shell commands. It
discovers devices, manages wireless pairing and connections, and gives you
a typed `Device` object for input, file transfer, shell access, package
management, screen capture, and monitoring.

```python
from voidremote import VoidRemote

client = VoidRemote()
client.start()

device = client.devices().first()
device.tap(500, 800)
device.text("hello world")
device.screenshot("screen.png")
```

No `adb shell input tap ...` strings. No manually parsing `adb devices -l`
output. No subprocess plumbing in your code.

---

## Who this is for

- Python developers automating Android devices
- Test engineers writing device-driven test suites
- CI/CD pipelines that need to install, launch, and verify apps
- Scripts and tools that need device telemetry (battery, storage, CPU)
- Applications built on top of ADB — VoidRemote's own CLI and desktop
  GUI are themselves built on this SDK (see [Also included](#also-included))

---

## Installation

```bash
pip install voidremote
```

Requires Python 3.12+ and the `adb` binary on your `PATH` (install via
[Android Platform Tools](https://developer.android.com/tools/releases/platform-tools)).
VoidRemote shells out to your existing `adb` — it does not bundle or
replace it.

The base install is SDK-only, with no CLI or GUI dependencies pulled in:

```bash
pip install voidremote          # SDK only
pip install voidremote[cli]     # + command-line tool
pip install voidremote[gui]     # + desktop app
pip install voidremote[full]    # SDK + CLI + GUI
```

---

## Quick start

```python
from voidremote import VoidRemote

client = VoidRemote()
client.start()                       # verify adb, start the adb server

devices = client.devices()           # discover devices already visible to adb
device = devices.first()

device.tap(500, 800)
device.swipe(500, 1600, 500, 400)
device.text("hello world")
device.key_event(4)                  # KEYCODE_BACK

device.push("app-release.apk", "/sdcard/app.apk")
device.install("app-release.apk")

output = device.shell("pm list packages -3")
device.screenshot("screen.png")
```

Connecting a device that isn't already known to `adb`:

```python
from voidremote import VoidRemote

client = VoidRemote()
client.start()

# Wireless debugging, paired by the 6-digit code shown on-device
device = client.pair_and_connect(host="192.168.1.42", port=37831, code="482913")

# Already paired, just needs a TCP connection
device = client.connect("192.168.1.42")
```

Every call above runs one real `adb` command under the hood — VoidRemote
just gives it a name, a type, and a place to raise a real exception.

---

## Philosophy

VoidRemote exists to remove one layer of indirection: the one between what
you mean and the `adb` command line syntax for it.

| Instead of shelling out to...                          | You write            |
|----------------------------------------------------------|-----------------------|
| `adb shell input tap 500 800`                            | `device.tap(500, 800)` |
| `adb shell input text "hello"`                            | `device.text("hello")` |
| `adb push app.apk /sdcard/app.apk`                        | `device.push("app.apk", "/sdcard/app.apk")` |
| `adb install -r app.apk`                                   | `device.install("app.apk")` |
| `adb shell pm list packages -3`                             | `device.list_packages()` |
| `adb pair 192.168.1.42:37831 482913`                        | `client.pair(host, port, code)` |
| parsing `adb devices -l` output by hand                     | `client.devices()` |
| parsing `dumpsys battery` output by hand                     | `device.battery_level` |

Nothing here is magic — every method is a thin, validated wrapper around
one `adb` invocation. VoidRemote doesn't try to be smarter than `adb`; it
tries to be a smaller, typed surface on top of it, with input validated
against command injection before it ever reaches a shell.

---

## Architecture

```
Your application
       │
       ▼
voidremote (SDK)  ──  Device, VoidRemote, PairingSession
       │
       ▼
adb executable    ──  the real Android Debug Bridge binary
       │
       ▼
Android device    ──  over USB or Wireless Debugging
```

Internally, the SDK is layered:

```
voidremote.api            stable public surface (this is what you import)
    │
voidremote.controllers    composition root — wires services together
    │
voidremote.services       device discovery, input, monitoring
    │
voidremote.adb            subprocess execution, output parsing
    │
adb binary
```

Only `voidremote.api` (re-exported at the top level, `from voidremote import
...`) is a stable, versioned surface. Everything below it — `adb`,
`services`, `controllers`, `models` — is an internal implementation detail
that can change between minor versions without notice.

---

## API design

### `VoidRemote` — the client

```python
from voidremote import VoidRemote

client = VoidRemote()
client.start()

client.devices()                          # -> DeviceList
client.device(serial)                     # -> Device
client.connect(host, port=5555)           # -> Device
client.pair(host, port, code)             # -> PairingSession
client.pair_and_connect(host, port, code) # -> Device
client.auto_reconnect()                   # -> DeviceList
```

Also usable as a context manager, which starts on entry and stops
background monitoring on exit:

```python
with VoidRemote() as client:
    for device in client.devices():
        print(device.name, device.battery_level)
```

### `Device` — everything scoped to one device

```python
device.tap(x, y)
device.swipe(x1, y1, x2, y2)
device.text("hello")
device.key_event(keycode)

device.shell("getprop ro.build.version.release")

device.push(local, remote)
device.pull(remote, local)
device.list_dir("/sdcard")

device.install(apk_path)
device.uninstall(package)
device.list_packages()
device.is_installed(package)

device.screenshot(output_path)
device.screenrecord()

device.reboot()
device.monitor(interval=2.0, callback=on_snapshot)
```

Input methods return `self`, so they chain:

```python
device.tap(500, 800).text("hello").key_event(66)  # tap, type, press Enter
```

### `DeviceList` — what `client.devices()` returns

```python
devices = client.devices()
devices.first()          # -> Device, raises NoDevicesError if empty
devices.get(serial)       # -> Device, raises DeviceNotFoundError
devices.online()          # -> DeviceList filtered to online devices
len(devices)
for device in devices: ...
```

### `PairingSession` — wireless debugging setup

```python
session = client.pair(host="192.168.1.42", port=37831, code="482913")
session.pair()             # perform the handshake
device = session.connect() # then connect on the regular ADB port
```

### Exceptions

Everything VoidRemote raises is a `VoidRemoteError`:

```python
from voidremote import VoidRemoteError, DeviceNotFoundError, NoDevicesError, PairingError

try:
    device = client.devices().first()
except NoDevicesError:
    print("No devices connected.")
except VoidRemoteError as exc:
    print(f"Something went wrong: {exc}")
```

`AdbNotAvailableError`, `AdbTimeoutError`, `AdbCommandError`,
`DeviceNotFoundError`, `NoDevicesError`, `PairingError`, `ConnectionError`,
and `InvalidArgumentError` all subclass it.

### Async

`AsyncVoidRemote` mirrors the sync API as coroutines. `adb` is a
subprocess-based CLI, not a socket protocol VoidRemote speaks directly, so
this runs the same synchronous code via `asyncio.to_thread` rather than
native async I/O — which is enough to keep your event loop unblocked, and
enough to run many devices concurrently with `asyncio.gather`:

```python
import asyncio
from voidremote import AsyncVoidRemote

async def main():
    async with AsyncVoidRemote() as client:
        devices = await client.devices()
        await asyncio.gather(*(d.tap(500, 800) for d in devices))

asyncio.run(main())
```

---

## Examples

Discover and print info for every connected device:

```python
from voidremote import VoidRemote

with VoidRemote() as client:
    for device in client.devices():
        print(f"{device.name}  {device.android_version}  {device.battery_level}%")
```

Install an APK on every connected device:

```python
from voidremote import VoidRemote

with VoidRemote() as client:
    for device in client.devices().online():
        device.install("app-release.apk")
```

Take a screenshot from a specific device:

```python
from voidremote import VoidRemote

client = VoidRemote()
client.start()
client.device("192.168.1.42:5555").screenshot("shot.png")
```

Run a shell command and use the output:

```python
device = client.devices().first()
version = device.shell("getprop ro.build.version.release")
print(f"Android {version}")
```

Poll battery and memory in the background:

```python
def on_snapshot(snapshot):
    print(f"CPU {snapshot.cpu_usage:.0f}%  RAM {snapshot.ram_usage_percent:.0f}%  "
          f"Battery {snapshot.battery_level}%")

device = client.devices().first()
device.monitor(interval=2.0, callback=on_snapshot)
```

Handle errors explicitly:

```python
from voidremote import VoidRemote, NoDevicesError, AdbNotAvailableError

try:
    client = VoidRemote()
    client.start()
    device = client.devices().first()
except AdbNotAvailableError:
    print("adb isn't installed or isn't on PATH.")
except NoDevicesError:
    print("adb is running, but no device is connected.")
```

---

## Security

Every device path, package name, host, port, and pairing code is validated
before use, and shell arguments are checked against a small blocklist of
injection characters (`; & | \` $ < > \`) and rejected outright rather than
escaped-and-hoped. See `voidremote.utils.security` — it's a small module,
worth reading if you're deciding whether to trust this with untrusted
input.

---

## Also included

The `voidremote` repository also ships two applications built entirely on
top of this SDK — neither adds anything to the SDK's public API, both are
optional installs.

**CLI** (`pip install voidremote[cli]`) — a `voidremote` command covering
device discovery, pairing, input, file transfer, package management,
shell access, and monitoring, with `--json` output for scripting. See
[docs/CLI.md](docs/CLI.md).

**Desktop GUI** (`pip install voidremote[gui]`) — a PySide6 application
(`voidremote-gui`) with a device dashboard, embedded shell, file manager,
and live monitoring graphs. See [docs/GUI.md](docs/GUI.md).

Further reading: [docs/API.md](docs/API.md) for the full API reference,
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the layers fit
together, [CONTRIBUTING.md](CONTRIBUTING.md) to work on VoidRemote itself.

---

## Requirements

- Python 3.12 or later
- `adb` (Android SDK Platform Tools) on `PATH`
- An Android device with USB debugging or Wireless Debugging enabled

Tested on Linux, macOS, and Windows.

---

## License

MIT — see [LICENSE](LICENSE).

## Author

**V0IDNETWORK** — an ongoing, open research effort to document, rigorously
and accurately, how the modern Internet's circumvention and surveillance
technologies actually work at the protocol level, in support of a more
open and resilient Internet.

[GitHub](https://github.com/V0IDNETWORK) ·
[Website](https://voidnetwork.ir/) ·
[LinkedIn](https://www.linkedin.com/in/ilianothing) ·
[Instagram](https://www.instagram.com/ilianothing) ·
[YouTube](https://youtube.com/@locailife) ·
[TryHackMe](https://tryhackme.com/p/ilianothingg) ·
[Medium](https://medium.com/@ilianothingg) ·
[Telegram](https://t.me/voidxMaster) ·
[ilianothingg@gmail.com](mailto:ilianothingg@gmail.com)
