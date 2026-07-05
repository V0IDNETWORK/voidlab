"""
attacker-box exec server.

A tiny, purpose-built HTTP service that runs a fixed allowlist of read-only
recon/lab tools (curl, nmap, dig, whoami, ...) and returns their output. It
is the *second*, independent enforcement point for the terminal's command
allowlist (the first is in apps/terminal/consumers.py on the Django side) —
a bug in one layer should not become a full bypass on its own.

Deliberate constraints, please keep these when you extend this file:
  * shell=False always — argv is built from shlex.split(), never handed to
    a shell, so shell metacharacters (;, &&, |, $(), backticks) do nothing.
  * Every subprocess call has a hard wall-clock timeout and an output size
    cap, so a runaway or noisy tool can't wedge the container or flood the
    browser.
  * This container runs as a non-root user, holds no secrets, has no route
    to the host or to Django's database, and only needs outbound access to
    the vulnerable-apps network segment plus DNS for the recon tools to be
    useful at all.
"""
import shlex
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "curl", "nmap", "nikto", "sqlmap", "whoami", "ls", "cat", "pwd",
    "echo", "dig", "nslookup", "id",
}

MAX_OUTPUT_CHARS = 8000
TIMEOUT_SECONDS = 20


@app.post("/exec")
def exec_command():
    body = request.get_json(silent=True) or {}
    command_line = (body.get("command") or "").strip()

    if not command_line:
        return jsonify(output=""), 200

    try:
        argv = shlex.split(command_line)
    except ValueError:
        return jsonify(output="voidlab: could not parse command (unbalanced quotes?)."), 200

    if not argv or argv[0] not in ALLOWED_COMMANDS:
        return jsonify(output=f"voidlab: '{argv[0] if argv else ''}' is not allowed here."), 200

    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output[:MAX_OUTPUT_CHARS]
        return jsonify(output=output or "(command produced no output)"), 200
    except subprocess.TimeoutExpired:
        return jsonify(output="voidlab: command timed out."), 200
    except FileNotFoundError:
        return jsonify(output=f"voidlab: '{argv[0]}' is not installed in this sandbox."), 200


@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
