# VoidRemote CLI

The `voidremote` command-line tool is a thin wrapper over the
[VoidRemote SDK](../README.md). Install it with:

```bash
pip install voidremote[cli]
```

## Global options

```
voidremote [--verbose] [--debug] [--json] [--version] <command> [args...]
```

- `--verbose` / `-v` — INFO-level logging to stderr
- `--debug` — DEBUG-level logging, and re-raises internal exceptions with
  a full traceback instead of a clean error message
- `--json` — every command that supports it emits a single JSON document
  on stdout and nothing else, making it safe to pipe into `jq` or similar

## Device discovery

```bash
voidremote devices                  # list connected devices
voidremote info <serial>            # detailed info for one device
voidremote doctor                   # check adb, Python, and dependency versions
```

## Wireless debugging

```bash
voidremote pair                                    # interactive
voidremote pair 192.168.1.42 37831 482913           # scripted
voidremote connect 192.168.1.42                     # connect (already paired)
voidremote disconnect 192.168.1.42:5555             # disconnect one device
voidremote disconnect                               # disconnect all wireless devices
```

## Input

```bash
voidremote tap <serial> <x> <y>
voidremote swipe <serial> <x1> <y1> <x2> <y2> [--duration MS]
voidremote text <serial> "hello world"
voidremote keyevent <serial> <keycode>
voidremote clipboard <serial> "text to paste"
```

## Files

```bash
voidremote push <serial> <local> <remote>
voidremote pull <serial> <remote> [local]
```

## Packages

```bash
voidremote install <serial> app.apk [--no-replace]
voidremote uninstall <serial> com.example.app
```

## Screen

```bash
voidremote screenshot <serial> [output.png]
voidremote screenrecord <serial> [output.mp4] [--time SECONDS] [--bitrate BPS]
voidremote mirror <serial> [--fps N] [--bitrate 8M] [--fullscreen]
```

`mirror` shells out to [scrcpy](https://github.com/Genymobile/scrcpy) if
it's on `PATH`; VoidRemote doesn't implement its own video pipeline for
the CLI. The desktop GUI's Screen Mirror panel is native.

## Device state

```bash
voidremote battery <serial>
voidremote wifi <serial>
voidremote reboot <serial> [--mode bootloader|recovery]
voidremote shell <serial> <command...>
```

## Application

```bash
voidremote logs [-n LINES] [--follow]
voidremote config [--show] [--reset]
voidremote update [--check-only]
voidremote version
```

## Scripting example

```bash
#!/usr/bin/env bash
set -euo pipefail

for serial in $(voidremote --json devices | jq -r '.[].serial'); do
    echo "Installing on $serial"
    voidremote install "$serial" app-release.apk
done
```

## Exit codes

`0` on success, `1` on any handled error (device not found, ADB error,
invalid input). Uncaught exceptions with `--debug` exit non-zero with a
full traceback.
