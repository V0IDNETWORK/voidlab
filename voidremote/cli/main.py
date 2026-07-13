"""
VoidRemote CLI — enterprise-grade command-line interface built on top
of the ``voidremote`` SDK.

Requires the ``cli`` extra: ``pip install voidremote[cli]``.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except ImportError as _exc:  # pragma: no cover - exercised via test_cli_extra_missing
    raise ImportError(
        "The VoidRemote CLI requires the 'cli' extra. Install it with:\n"
        "    pip install voidremote[cli]"
    ) from _exc

from voidremote import __version__
from voidremote.adb.client import AdbError
from voidremote.controllers.app_controller import AppController
from voidremote.utils.security import validate_host, validate_pairing_code, validate_port
from voidremote.utils.version import get_version

console = Console()
err_console = Console(stderr=True, style="bold red")

logger = logging.getLogger(__name__)


class CliContext:
    """Shared CLI context passed to all sub-commands."""

    def __init__(self, verbose: bool, debug: bool, json_output: bool) -> None:
        self.verbose = verbose
        self.debug = debug
        self.json_output = json_output
        self._controller: Optional[AppController] = None

    @property
    def controller(self) -> AppController:
        if self._controller is None:
            from voidremote.config.settings import get_settings
            self._controller = AppController(get_settings())
        return self._controller

    def init_controller(self) -> None:
        """Initialize the controller (verify ADB, start server)."""
        try:
            self.controller.initialize()
        except Exception as exc:
            from voidremote.adb.client import AdbNotFoundError
            if isinstance(exc, AdbNotFoundError):
                err_console.print(f"[red]✗[/red] {exc}")
                err_console.print(
                    "Install ADB: https://developer.android.com/tools/releases/platform-tools"
                )
            else:
                err_console.print(f"[red]✗ Initialization error:[/red] {exc}")
            if self.debug:
                raise
            sys.exit(1)

    def print_json(self, data: object) -> None:
        console.print(json.dumps(data, indent=2, default=str))

    def success(self, msg: str) -> None:
        if not self.json_output:
            console.print(f"[green]✓[/green] {msg}")

    def error(self, msg: str) -> None:
        if not self.json_output:
            err_console.print(f"[red]✗[/red] {msg}")
        else:
            console.print(json.dumps({"error": msg}))

    def info(self, msg: str) -> None:
        if not self.json_output and self.verbose:
            console.print(f"[blue]ℹ[/blue] {msg}")


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.version_option(__version__, "-V", "--version", prog_name="VoidRemote")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, json_output: bool) -> None:
    """
    \b
    ██╗   ██╗ ██████╗ ██╗██████╗
    ██║   ██║██╔═══██╗██║██╔══██╗
    ██║   ██║██║   ██║██║██║  ██║
    ╚██╗ ██╔╝██║   ██║██║██║  ██║
     ╚████╔╝ ╚██████╔╝██║██████╔╝
      ╚═══╝   ╚═════╝ ╚═╝╚═════╝

    VoidRemote — Wireless Android Remote Controller over ADB
    Built on the `voidremote` Python SDK. by V0IDNETWORK
    """
    from voidremote.config.settings import LOG_FILE, get_settings
    from voidremote.utils.logging import setup_logging

    settings = get_settings()
    level = "DEBUG" if debug else ("INFO" if verbose else settings.logging.level)
    setup_logging(
        level=level,
        log_file=LOG_FILE if settings.logging.file_enabled else None,
        console=not json_output,
        console_color=settings.logging.console_color,
    )

    ctx.obj = CliContext(verbose=verbose, debug=debug, json_output=json_output)

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@cli.command("devices")
@click.option("--refresh/--no-refresh", default=True, help="Refresh device list.")
@click.pass_obj
def cmd_devices(obj: CliContext, refresh: bool) -> None:
    """List all connected ADB devices."""
    obj.init_controller()
    devices = obj.controller.list_devices(refresh=refresh)

    if obj.json_output:
        data = [
            {
                "serial": d.serial, "model": d.info.display_name, "state": d.state.value,
                "type": d.connection_type.value, "android": d.info.android_version,
                "battery": d.info.battery.level,
            }
            for d in devices
        ]
        obj.print_json(data)
        return

    if not devices:
        console.print("[yellow]No devices connected.[/yellow]")
        console.print("Tip: Enable Wireless Debugging on your Android device,")
        console.print("     then run: [bold]voidremote pair[/bold]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan",
                  title=f"[bold]Connected Devices ({len(devices)})[/bold]")
    table.add_column("Serial / Address", style="dim", min_width=20)
    table.add_column("Model", min_width=22)
    table.add_column("Android", justify="center")
    table.add_column("Type", justify="center")
    table.add_column("State", justify="center")
    table.add_column("Battery", justify="right")

    for dev in devices:
        state_color = {"online": "green", "offline": "red", "unauthorized": "yellow"}.get(
            dev.state.value, "white"
        )
        batt = dev.info.battery.level
        batt_color = "green" if batt > 50 else ("yellow" if batt > 20 else "red")
        table.add_row(
            dev.serial, dev.info.display_name, dev.info.android_version,
            dev.connection_type.value, f"[{state_color}]{dev.state.value}[/{state_color}]",
            f"[{batt_color}]{batt}%[/{batt_color}]" if batt else "N/A",
        )
    console.print(table)


@cli.command("pair")
@click.argument("host", required=False)
@click.argument("port", type=int, required=False)
@click.argument("code", required=False)
@click.pass_obj
def cmd_pair(obj: CliContext, host: Optional[str], port: Optional[int], code: Optional[str]) -> None:
    """Pair an Android device via Wireless Debugging.

    \b
    Usage:
        voidremote pair                         # interactive mode
        voidremote pair 192.168.1.10 37001 123456
    """
    obj.init_controller()

    if host is None:
        console.print(Panel(
            "[bold cyan]Wireless Debugging Pairing[/bold cyan]\n\n"
            "On your Android device:\n"
            "  Settings → Developer Options → Wireless Debugging → Pair device with code",
            title="Setup Instructions", border_style="cyan",
        ))
        host = click.prompt("  Device IP address")
        port = click.prompt("  Pairing port (shown on screen)", type=int)
        code = click.prompt("  6-digit pairing code")

    try:
        validated_host = validate_host(host)
        validated_port = validate_port(port or 37001)
        validated_code = validate_pairing_code(code or "")
    except ValueError as exc:
        obj.error(str(exc))
        sys.exit(1)

    try:
        success = obj.controller.pair_device(validated_host, validated_port, validated_code)
        if success:
            obj.success(f"Paired with {validated_host}")
            if obj.json_output:
                obj.print_json({"paired": True, "host": validated_host, "port": validated_port})
        else:
            obj.error("Pairing failed — check IP, port, and code")
            sys.exit(1)
    except AdbError as exc:
        obj.error(f"ADB error: {exc}")
        sys.exit(1)


@cli.command("connect")
@click.argument("host")
@click.argument("port", type=int, default=5555)
@click.option("--no-remember", is_flag=True, help="Do not save as trusted device.")
@click.pass_obj
def cmd_connect(obj: CliContext, host: str, port: int, no_remember: bool) -> None:
    """Connect to a device over TCP/IP.

    \b
    Usage:
        voidremote connect 192.168.1.10
        voidremote connect 192.168.1.10 5555
    """
    obj.init_controller()
    try:
        device = obj.controller.connect_device(host, port, remember=not no_remember)
        if obj.json_output:
            obj.print_json({"connected": True, "serial": device.serial, "model": device.info.display_name})
        else:
            obj.success(f"Connected: {device.info.display_name} ({device.serial})")
    except (AdbError, ValueError) as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("disconnect")
@click.argument("serial", required=False)
@click.pass_obj
def cmd_disconnect(obj: CliContext, serial: Optional[str]) -> None:
    """Disconnect a wireless device. Without SERIAL, disconnects all wireless devices."""
    obj.init_controller()
    if serial:
        ok = obj.controller.disconnect_device(serial)
        obj.success(f"Disconnected: {serial}") if ok else obj.error(f"Could not disconnect {serial}")
    else:
        obj.controller.adb.disconnect_all()
        obj.success("Disconnected all wireless devices")


@cli.command("info")
@click.argument("serial")
@click.pass_obj
def cmd_info(obj: CliContext, serial: str) -> None:
    """Show detailed information about a device."""
    obj.init_controller()
    devices = obj.controller.list_devices(refresh=True)
    device = next((d for d in devices if d.serial == serial), None)
    if device is None:
        obj.error(f"Device not found: {serial}")
        sys.exit(1)

    if obj.json_output:
        obj.print_json(device.model_dump(mode="json"))
        return

    info = device.info
    console.print(Panel(
        f"[bold white]{info.display_name}[/bold white]\n"
        f"  Serial:       [cyan]{device.serial}[/cyan]\n"
        f"  Model:        {info.model}\n"
        f"  Manufacturer: {info.manufacturer}\n"
        f"  Android:      {info.android_version} (SDK {info.sdk_version})\n"
        f"  Resolution:   {info.screen_resolution} @ {info.screen_density}dpi\n"
        f"  CPU ABI:      {info.cpu.abi}\n"
        f"  RAM:          {info.ram_total_gb:.1f} GB total\n"
        f"  Battery:      {info.battery.level}% "
        f"({'charging' if info.battery.is_charging else 'discharging'}) "
        f"{info.battery.temperature_celsius:.1f}°C\n"
        f"  IP Address:   {info.network.ip_address or 'N/A'}\n"
        f"  Storage:      {info.storage.used_gb:.1f}/{info.storage.total_gb:.1f} GB",
        title="[bold cyan]Device Info[/bold cyan]", border_style="cyan",
    ))


@cli.command("screenshot")
@click.argument("serial")
@click.argument("output", type=click.Path(), default="screenshot.png")
@click.pass_obj
def cmd_screenshot(obj: CliContext, serial: str, output: str) -> None:
    """Capture a screenshot from the device."""
    obj.init_controller()
    out_path = Path(output)
    try:
        obj.controller.take_screenshot(serial, out_path)
        if obj.json_output:
            obj.print_json({"path": str(out_path.resolve())})
        else:
            obj.success(f"Screenshot saved: {out_path.resolve()}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("screenrecord")
@click.argument("serial")
@click.argument("output", default="screenrecord.mp4")
@click.option("--time", "-t", "time_limit", type=int, default=180, help="Max duration in seconds.")
@click.option("--bitrate", "-b", type=int, default=8_000_000, help="Bitrate in bps.")
@click.pass_obj
def cmd_screenrecord(obj: CliContext, serial: str, output: str, time_limit: int, bitrate: int) -> None:
    """Record the device screen to a local video file."""
    obj.init_controller()
    remote_path = "/sdcard/void_screenrecord.mp4"
    local_path = Path(output)
    proc = None
    try:
        if not obj.json_output:
            console.print("[cyan]Recording…[/cyan] Press [bold]Ctrl+C[/bold] to stop early.")
        proc = obj.controller.start_screen_record(serial, remote_path)
        try:
            proc.wait(timeout=time_limit)
        except Exception:
            proc.terminate()
        obj.controller.pull_file(serial, remote_path, local_path)
        obj.controller.shell(serial, f"rm -f {remote_path}")
        obj.success(f"Saved: {local_path.resolve()}") if not obj.json_output else obj.print_json(
            {"path": str(local_path.resolve())}
        )
    except KeyboardInterrupt:
        if proc is not None:
            proc.terminate()
        obj.controller.pull_file(serial, remote_path, local_path)
        obj.controller.shell(serial, f"rm -f {remote_path}")
        obj.success(f"Recording stopped. Saved: {local_path.resolve()}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("shell")
@click.argument("serial")
@click.argument("command", nargs=-1)
@click.pass_obj
def cmd_shell(obj: CliContext, serial: str, command: tuple[str, ...]) -> None:
    """Execute a shell command on the device."""
    obj.init_controller()
    if not command:
        obj.error("No command specified")
        sys.exit(1)
    try:
        output = obj.controller.shell(serial, " ".join(command))
        obj.print_json({"output": output}) if obj.json_output else console.print(output)
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("install")
@click.argument("serial")
@click.argument("apk", type=click.Path(exists=True))
@click.option("--replace/--no-replace", default=True, help="Replace existing app.")
@click.pass_obj
def cmd_install(obj: CliContext, serial: str, apk: str, replace: bool) -> None:
    """Install an APK on the device."""
    obj.init_controller()
    apk_path = Path(apk)
    try:
        with console.status(f"Installing {apk_path.name}…"):
            obj.controller.install_apk(serial, apk_path, replace=replace)
        obj.success(f"Installed: {apk_path.name}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("uninstall")
@click.argument("serial")
@click.argument("package")
@click.pass_obj
def cmd_uninstall(obj: CliContext, serial: str, package: str) -> None:
    """Uninstall an app package from the device."""
    obj.init_controller()
    try:
        obj.controller.uninstall_app(serial, package)
        obj.success(f"Uninstalled: {package}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("tap")
@click.argument("serial")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.pass_obj
def cmd_tap(obj: CliContext, serial: str, x: int, y: int) -> None:
    """Tap at screen coordinates."""
    obj.init_controller()
    try:
        obj.controller.tap(serial, x, y)
        obj.success(f"Tapped at ({x}, {y})")
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("swipe")
@click.argument("serial")
@click.argument("x1", type=int)
@click.argument("y1", type=int)
@click.argument("x2", type=int)
@click.argument("y2", type=int)
@click.option("--duration", "-d", type=int, default=300, help="Duration in ms.")
@click.pass_obj
def cmd_swipe(obj: CliContext, serial: str, x1: int, y1: int, x2: int, y2: int, duration: int) -> None:
    """Swipe from (x1,y1) to (x2,y2)."""
    obj.init_controller()
    try:
        obj.controller.swipe(serial, x1, y1, x2, y2, duration)
        obj.success(f"Swiped ({x1},{y1}) → ({x2},{y2})")
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("text")
@click.argument("serial")
@click.argument("text")
@click.pass_obj
def cmd_text(obj: CliContext, serial: str, text: str) -> None:
    """Type text on the device."""
    obj.init_controller()
    try:
        obj.controller.type_text(serial, text)
        obj.success(f"Typed: {text!r}")
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("keyevent")
@click.argument("serial")
@click.argument("keycode", type=int)
@click.pass_obj
def cmd_keyevent(obj: CliContext, serial: str, keycode: int) -> None:
    """Send a hardware key event (by keycode number)."""
    obj.init_controller()
    try:
        obj.controller.key_event(serial, keycode)
        obj.success(f"Key event: {keycode}")
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("clipboard")
@click.argument("serial")
@click.argument("text")
@click.pass_obj
def cmd_clipboard(obj: CliContext, serial: str, text: str) -> None:
    """Type text into the device (best-effort clipboard paste)."""
    obj.init_controller()
    try:
        obj.controller.type_text(serial, text)
        obj.success(f"Sent: {text!r}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("mirror")
@click.argument("serial")
@click.option("--fps", type=int, default=30, help="Maximum FPS.")
@click.option("--bitrate", "-b", default="8M", help="Bitrate (e.g. 8M).")
@click.option("--fullscreen", "-f", is_flag=True, help="Launch fullscreen.")
@click.pass_obj
def cmd_mirror(obj: CliContext, serial: str, fps: int, bitrate: str, fullscreen: bool) -> None:
    """Mirror the device screen (requires scrcpy, or use the VoidRemote GUI)."""
    import shutil
    import subprocess

    scrcpy = shutil.which("scrcpy")
    if scrcpy:
        cmd_parts = [scrcpy, "-s", serial, f"--max-fps={fps}", f"--video-bit-rate={bitrate}"]
        if fullscreen:
            cmd_parts.append("--fullscreen")
        if not obj.json_output:
            console.print("[cyan]Launching scrcpy…[/cyan]")
        subprocess.run(cmd_parts, check=False)
    elif obj.json_output:
        obj.print_json({"error": "scrcpy not found", "hint": "Install scrcpy or use voidremote-gui"})
    else:
        console.print(
            "[yellow]scrcpy not found.[/yellow]\n"
            "Install scrcpy for CLI mirroring: https://github.com/Genymobile/scrcpy\n"
            "Or launch the VoidRemote GUI: [bold]voidremote-gui[/bold] (requires the 'gui' extra)"
        )


@cli.command("push")
@click.argument("serial")
@click.argument("local", type=click.Path(exists=True))
@click.argument("remote")
@click.pass_obj
def cmd_push(obj: CliContext, serial: str, local: str, remote: str) -> None:
    """Push a file to the device."""
    obj.init_controller()
    try:
        with console.status("Pushing file…"):
            obj.controller.push_file(serial, Path(local), remote)
        obj.success(f"Pushed: {local} → {remote}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("pull")
@click.argument("serial")
@click.argument("remote")
@click.argument("local", type=click.Path(), default=".")
@click.pass_obj
def cmd_pull(obj: CliContext, serial: str, remote: str, local: str) -> None:
    """Pull a file from the device."""
    obj.init_controller()
    try:
        with console.status("Pulling file…"):
            obj.controller.pull_file(serial, remote, Path(local))
        obj.success(f"Pulled: {remote} → {local}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("reboot")
@click.argument("serial")
@click.option("--mode", type=click.Choice(["", "bootloader", "recovery"]), default="", help="Reboot mode.")
@click.pass_obj
def cmd_reboot(obj: CliContext, serial: str, mode: str) -> None:
    """Reboot the device."""
    obj.init_controller()
    try:
        obj.controller.reboot(serial, mode)
        obj.success(f"Device rebooting{f' into {mode}' if mode else ''}")
    except AdbError as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("battery")
@click.argument("serial")
@click.pass_obj
def cmd_battery(obj: CliContext, serial: str) -> None:
    """Show battery status."""
    obj.init_controller()
    try:
        from voidremote.adb.device_parser import parse_battery
        info = parse_battery(obj.controller.shell(serial, "dumpsys battery"))
        if obj.json_output:
            obj.print_json({
                "level": info.level, "charging": info.is_charging,
                "temperature_c": info.temperature_celsius, "voltage_v": info.voltage_volts,
                "health": info.health, "technology": info.technology,
            })
        else:
            batt_color = "green" if info.level > 50 else ("yellow" if info.level > 20 else "red")
            console.print(Panel(
                f"  Level:       [{batt_color}]{info.level}%[/{batt_color}]\n"
                f"  Charging:    {'[green]Yes[/green]' if info.is_charging else '[red]No[/red]'}\n"
                f"  Temperature: {info.temperature_celsius:.1f}°C\n"
                f"  Voltage:     {info.voltage_volts:.2f}V\n"
                f"  Health:      {info.health}\n"
                f"  Technology:  {info.technology}",
                title="[bold cyan]Battery[/bold cyan]", border_style="cyan",
            ))
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("wifi")
@click.argument("serial")
@click.pass_obj
def cmd_wifi(obj: CliContext, serial: str) -> None:
    """Show WiFi information."""
    obj.init_controller()
    try:
        from voidremote.adb.device_parser import parse_ip_address
        ip_info = obj.controller.shell(serial, "ip addr show wlan0")
        ip = parse_ip_address(ip_info)
        if obj.json_output:
            obj.print_json({"ip": ip})
        else:
            console.print(f"[cyan]IP Address:[/cyan] {ip or 'N/A'}")
    except Exception as exc:
        obj.error(str(exc))
        sys.exit(1)


@cli.command("doctor")
@click.pass_obj
def cmd_doctor(obj: CliContext) -> None:
    """Check system setup and diagnose common issues."""
    import shutil
    import sys as _sys

    if not obj.json_output:
        console.print(Panel("[bold]VoidRemote Doctor[/bold]", border_style="cyan"))

    checks: list[tuple[str, bool, str]] = []

    adb_path = shutil.which("adb")
    checks.append(("ADB binary", adb_path is not None,
                    adb_path or "Not found — install Android Platform Tools"))

    py_ok = _sys.version_info >= (3, 12)
    checks.append(("Python version", py_ok,
                    f"{_sys.version.split()[0]} ({'OK' if py_ok else 'Python 3.12+ required'})"))

    # Use importlib.metadata, never `module.__version__` — not every
    # package defines that attribute (e.g. click 8.2+ deprecates it,
    # rich doesn't define it at all). This is the only reliable way to
    # read an *installed distribution's* version.
    for dist_name, label in (
        ("pydantic", "pydantic (SDK core)"),
        ("click", "click (CLI)"),
        ("rich", "rich (CLI)"),
        ("PySide6", "PySide6 (GUI)"),
    ):
        v = get_version(dist_name)
        checks.append((label, v is not None, v or "Not installed"))

    if adb_path:
        try:
            obj.init_controller()
            version = obj.controller.adb.verify_adb()
            checks.append(("ADB server", True, version))
        except Exception as exc:
            checks.append(("ADB server", False, str(exc)))

    if obj.json_output:
        obj.print_json({name: {"ok": ok, "detail": detail} for name, ok, detail in checks})
        return

    for name, ok, detail in checks:
        icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {icon}  {name:<24} {detail}")

    if all(ok for _, ok, _ in checks):
        console.print("\n[green bold]All checks passed! VoidRemote is ready.[/green bold]")
    else:
        console.print("\n[yellow]Some checks failed. Fix the issues above and re-run.[/yellow]")


@cli.command("update")
@click.option("--check-only", is_flag=True, help="Only check, do not install.")
@click.pass_obj
def cmd_update(obj: CliContext, check_only: bool) -> None:
    """Check for VoidRemote updates on PyPI."""
    try:
        import requests
        resp = requests.get("https://pypi.org/pypi/voidremote/json", timeout=5)
        resp.raise_for_status()
        latest = resp.json().get("info", {}).get("version", "")
        if obj.json_output:
            obj.print_json({"current": __version__, "latest": latest, "update_available": latest != __version__})
        elif latest and latest != __version__:
            console.print(f"[yellow]Update available:[/yellow] v{__version__} → v{latest}")
            console.print("Run: [bold]pip install --upgrade voidremote[/bold]")
        else:
            console.print(f"[green]✓ Up to date:[/green] VoidRemote v{__version__}")
    except Exception as exc:
        if obj.json_output:
            obj.print_json({"current": __version__, "error": str(exc)})
        else:
            console.print(f"[dim]Could not check for updates: {exc}[/dim]")
            console.print(f"Current version: VoidRemote v{__version__}")


@cli.command("version")
@click.pass_obj
def cmd_version(obj: CliContext) -> None:
    """Show version information."""
    if obj.json_output:
        obj.print_json({"version": __version__, "author": "V0IDNETWORK",
                         "url": "https://github.com/V0IDNETWORK/VoidRemote"})
    else:
        console.print(f"[bold cyan]VoidRemote[/bold cyan] v{__version__}\n"
                       f"by V0IDNETWORK | https://github.com/V0IDNETWORK/VoidRemote")


@cli.command("logs")
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show.")
@click.option("--follow", "-f", is_flag=True, help="Follow log output.")
@click.pass_obj
def cmd_logs(obj: CliContext, lines: int, follow: bool) -> None:
    """Show application logs."""
    from voidremote.config.settings import LOG_FILE

    if not LOG_FILE.exists():
        if obj.json_output:
            obj.print_json([])
        else:
            console.print("[yellow]No log file found.[/yellow]")
        return

    log_lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = log_lines[-lines:]

    if obj.json_output:
        # --follow doesn't make sense for a single JSON document; ignored here.
        obj.print_json(tail)
        return

    for line in tail:
        color = "red" if "ERROR" in line else "yellow" if "WARNING" in line else "dim" if "DEBUG" in line else "white"
        console.print(f"[{color}]{line}[/{color}]")

    if follow:
        import time
        try:
            while True:
                new_lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in new_lines[len(log_lines):]:
                    console.print(line)
                log_lines = new_lines
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass


@cli.command("config")
@click.option("--show", is_flag=True, help="Show current configuration.")
@click.option("--reset", is_flag=True, help="Reset to defaults.")
@click.pass_obj
def cmd_config(obj: CliContext, show: bool, reset: bool) -> None:
    """Manage VoidRemote configuration."""
    from voidremote.config.settings import CONFIG_FILE, get_settings

    settings = get_settings()

    if reset:
        settings.reset_to_defaults()
        settings.save()
        obj.success("Configuration reset to defaults")
        return

    if obj.json_output:
        obj.print_json(json.loads(settings.model_dump_json()))
    else:
        console.print(Panel(
            f"  Config file: [cyan]{CONFIG_FILE}[/cyan]\n"
            f"  ADB path:    {settings.adb.path}\n"
            f"  Theme:       {settings.ui.theme}\n"
            f"  Log level:   {settings.logging.level}\n"
            f"  Debug:       {settings.debug}\n"
            f"  Mirror FPS:  {settings.mirror.max_fps}",
            title="[bold cyan]Configuration[/bold cyan]", border_style="cyan",
        ))


def main() -> None:
    """CLI entry point (registered as the ``voidremote`` console script)."""
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
