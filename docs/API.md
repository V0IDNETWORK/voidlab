# API Reference

Everything documented here lives in `voidremote.api` and is re-exported
at the top level (`from voidremote import ...`). This is VoidRemote's
stable, semantic-versioned surface — nothing else in the package
(`voidremote.adb`, `voidremote.services`, `voidremote.controllers`,
`voidremote.models`) is guaranteed stable between minor versions.

## `VoidRemote`

```python
class VoidRemote:
    def __init__(self, adb_path: str = "adb", settings: AppSettings | None = None, auto_start: bool = False): ...
    def start(self) -> str: ...
    def close(self) -> None: ...
    def devices(self, refresh: bool = True) -> DeviceList: ...
    def device(self, serial: str) -> Device: ...
    def pair(self, host: str, port: int, code: str) -> PairingSession: ...
    def pair_and_connect(self, host: str, port: int, code: str, adb_port: int = 5555) -> Device: ...
    def connect(self, host: str, port: int = 5555, remember: bool = True) -> Device: ...
    def auto_reconnect(self) -> DeviceList: ...
```

`__enter__`/`__exit__` call `start()`/`close()` — prefer the context
manager form unless you need finer control over when `start()` runs.

`start()` raises `AdbNotAvailableError` if the `adb` binary can't be
resolved. Constructing `VoidRemote()` never raises or has side effects.

## `Device`

Properties (read-only, reflect the state at the time the `Device` was
obtained — call `client.device(serial)` again, or `.refresh()`, for
current values):

| Property | Type |
|---|---|
| `serial` | `str` |
| `name` | `str` |
| `model` | `str` |
| `manufacturer` | `str` |
| `android_version` | `str` |
| `sdk_version` | `int` |
| `resolution` | `tuple[int, int]` |
| `ip_address` | `str` |
| `battery_level` | `int` (0-100) |
| `is_charging` | `bool` |
| `is_online` | `bool` |
| `raw` | underlying `voidremote.models.device.Device` (escape hatch) |

Methods:

```python
device.refresh() -> Device                        # re-query, returns a new Device
device.disconnect() -> bool                        # wireless only

device.tap(x, y) -> Device
device.double_tap(x, y) -> Device
device.long_press(x, y, duration_ms=1000) -> Device
device.swipe(x1, y1, x2, y2, duration_ms=300) -> Device
device.scroll_down(x=540, y=1200, amount=500) -> Device
device.scroll_up(x=540, y=800, amount=500) -> Device
device.text(value) -> Device
device.key_event(keycode) -> Device
device.home() -> Device
device.back() -> Device
device.wake() -> Device

device.shell(command) -> str

device.push(local, remote) -> Device
device.pull(remote, local) -> Path
device.list_dir(path="/sdcard") -> list[str]

device.install(apk_path, replace=True) -> Device
device.uninstall(package) -> Device
device.list_packages(user_only=True) -> list[str]
device.is_installed(package) -> bool

device.screenshot(output) -> Path
device.screenrecord() -> subprocess.Popen

device.reboot(mode="") -> None

device.monitor(interval=2.0, callback=None) -> None
device.stop_monitoring() -> None
```

Input methods (`tap`, `swipe`, `text`, `key_event`, and friends) return
`self`, so they chain: `device.tap(x, y).text("hi").key_event(66)`.

## `DeviceList`

Returned by `client.devices()`. Implements `Sequence[Device]`
(`len()`, indexing, slicing, iteration) plus:

```python
devices.first() -> Device        # raises NoDevicesError if empty
devices.get(serial) -> Device    # raises DeviceNotFoundError
devices.online() -> DeviceList   # filtered to is_online devices
```

## `PairingSession`

Returned by `client.pair(host, port, code)`.

```python
session.pair() -> PairingResult
session.connect(adb_port=5555, remember=True) -> Device
session.host -> str
session.port -> int
```

`connect()` calls `pair()` first if it hasn't run yet, so
`client.pair(...).connect()` and `client.pair_and_connect(...)` are
equivalent.

## `AsyncVoidRemote` / `AsyncDevice` / `AsyncDeviceList`

Same shape as the sync API, `async def` throughout, implemented via
`asyncio.to_thread` around the sync implementation (see
[README: Async](../README.md#async) for why). `AsyncDevice.sync` and
`AsyncVoidRemote.sync` expose the underlying sync object if you need
something not yet mirrored on the async side.

## Enums and value objects

```python
from voidremote import DeviceState, DeviceCapability, KeyCode, DeviceSnapshot

DeviceState.ONLINE | OFFLINE | UNAUTHORIZED | CONNECTING | PAIRING | DISCONNECTED | UNKNOWN
DeviceCapability.SCREEN_MIRROR | FILE_TRANSFER | SHELL | INPUT_CONTROL | PACKAGE_MANAGER | MONITORING
KeyCode.KEYCODE_HOME | KEYCODE_BACK | KEYCODE_ENTER | ...  # standard Android keycodes
```

`DeviceSnapshot` (passed to `device.monitor()` callbacks):

```python
snapshot.serial: str
snapshot.timestamp: datetime
snapshot.cpu_usage: float          # percent
snapshot.ram_used_mb: float
snapshot.ram_total_mb: float
snapshot.ram_usage_percent: float  # computed
snapshot.battery_level: int
snapshot.battery_temperature: float  # Celsius
snapshot.battery_is_charging: bool
```

## Exceptions

```
VoidRemoteError                 # base class for everything below
├── AdbNotAvailableError        # adb binary not found
├── AdbTimeoutError             # a command exceeded its timeout
├── AdbCommandError             # adb ran, exited non-zero (.returncode, .stderr)
├── DeviceNotFoundError         # no device matches the given serial
├── NoDevicesError              # DeviceList.first() on an empty list
├── PairingError                # wireless pairing failed
├── ConnectionError             # TCP/IP connection failed
└── InvalidArgumentError        # bad host/port/pairing code/etc.
```

## Error handling patterns

```python
from voidremote import VoidRemote, VoidRemoteError, NoDevicesError, AdbNotAvailableError

try:
    client = VoidRemote()
    client.start()
except AdbNotAvailableError:
    raise SystemExit("Install Android Platform Tools and ensure `adb` is on PATH.")

try:
    device = client.devices().first()
except NoDevicesError:
    raise SystemExit("No device connected. Run `voidremote pair` or enable USB debugging.")

try:
    device.install("app.apk")
except VoidRemoteError as exc:
    print(f"Install failed: {exc}")
```

## Type hints and IDE support

The package ships a `py.typed` marker (PEP 561), so `mypy`, Pyright, and
IDE autocomplete work against the real signatures with no stub packages
needed.
