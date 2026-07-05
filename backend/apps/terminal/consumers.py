"""
Interactive in-browser terminal, backed by Django Channels.

SECURITY MODEL (read this before changing anything here):

This is intentionally *not* a general-purpose shell. It never runs
subprocess/os.system inside the Django backend container, and it never
touches the Docker socket (mounting /var/run/docker.sock into a
web-facing container would be equivalent to handing out root on the
host — VOIDLAB does not do that anywhere).

Instead, every command the user types is forwarded over the internal
Docker network to a small, purpose-built, non-root, non-privileged
"attacker-box" service (see /attacker-box in the repo root), which
enforces its own allowlist of read-only recon/lab tools (curl, nmap,
dig, whois, etc. — see TERMINAL_ALLOWED_COMMANDS) independently of this
consumer, applies a hard timeout and output-size cap per command, and
has no route to the host, to Django's database, or to any secret. The
allowlist is enforced in *two* independent places (here, and again in
attacker-box) so a bug in one layer doesn't become a full bypass.

This is appropriate for a self-hosted training lab you run yourself.
It is explicitly NOT hardened for exposing to the public internet as a
multi-tenant SaaS without additional isolation (a fresh, ephemeral
per-session container/sandbox — e.g. gVisor or Firecracker — instead
of one shared attacker-box). That upgrade is called out in the README.
"""
import json

import httpx
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

ATTACKER_BOX_URL = "http://attacker-box:7000/exec"
COMMAND_TIMEOUT_SECONDS = 20


class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.lab_slug = self.scope["url_route"]["kwargs"]["lab_slug"]
        await self.accept()
        await self.send_line(f"VOIDLAB terminal — connected to lab '{self.lab_slug}'.")
        await self.send_line(
            f"Allowed tools: {', '.join(settings.TERMINAL_ALLOWED_COMMANDS)}. Type 'help' for details."
        )

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        command_line = (text_data or "").strip()
        if not command_line:
            return

        if command_line == "clear":
            await self.send(text_data=json.dumps({"type": "clear"}))
            return

        if command_line == "help":
            await self.send_line(
                "This sandboxed terminal only runs a fixed allowlist of read-only "
                "recon tools against the lab's isolated container network — it is "
                "not a general shell. Try: curl, nmap, dig, whoami, id, ls, cat, pwd."
            )
            return

        base_command = command_line.split()[0]
        if base_command not in settings.TERMINAL_ALLOWED_COMMANDS:
            await self.send_line(f"voidlab: '{base_command}' is not an allowed command. Type 'help'.")
            return

        await self.run_remote_command(command_line)

    async def run_remote_command(self, command_line: str):
        try:
            async with httpx.AsyncClient(timeout=COMMAND_TIMEOUT_SECONDS + 5) as client:
                resp = await client.post(
                    ATTACKER_BOX_URL,
                    json={"command": command_line, "lab_slug": self.lab_slug},
                )
            if resp.status_code != 200:
                await self.send_line(f"voidlab: attacker-box error ({resp.status_code}).")
                return
            payload = resp.json()
            output = payload.get("output", "")
            await self.send_line(output if output else "(no output)")
        except httpx.TimeoutException:
            await self.send_line("voidlab: command timed out.")
        except httpx.HTTPError:
            await self.send_line("voidlab: could not reach the attacker-box sandbox.")

    async def send_line(self, text: str):
        await self.send(text_data=json.dumps({"type": "output", "text": text}))
