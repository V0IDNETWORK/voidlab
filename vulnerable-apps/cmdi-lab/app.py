"""
VOIDLAB · cmdi-lab

Deliberately vulnerable Flask app for the "OS Command Injection: Ping Sweep
Gone Wrong" lab (OWASP A05:2025 - Injection). Runs as a non-root user in its
own isolated, non-privileged container with no capabilities added — a shell
inside this box has nothing to escalate to.

THE VULNERABILITY IS INTENTIONAL: /ping passes the user-supplied host
straight into a shell command via os.system(), so shell metacharacters
(;, &&, |) let an attacker chain arbitrary commands. This exact pattern
(shell=True / os.system with untrusted input) is the textbook root cause
of OS command injection — never do this in real code.
"""
import os

from flask import Flask, render_template_string, request

app = Flask(__name__)
FLAG = os.environ.get("LAB_FLAG", "VOIDLAB{c0mm4nd_1nj3ct10n_v14_sh3ll_m3t4ch4rs}")

try:
    with open("/flag.txt", "w") as f:
        f.write(FLAG + "\n")
except PermissionError:
    # /flag.txt is already baked into the image at build time (see
    # Dockerfile) with the same default flag, so this is a harmless no-op
    # when the container filesystem is read-only at runtime.
    pass

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VOIDLAB · cmdi-lab</title>
  <style>
    body { background:#0a0e14; color:#e7e9ee; font-family:'JetBrains Mono',monospace; padding:40px; }
    input { padding:10px; width:320px; background:#12161f; border:1px solid #2a2f3a; color:#e7e9ee; }
    button { padding:10px 16px; background:#7c5cff; border:none; color:#fff; border-radius:4px; }
    pre { background:#12161f; border:1px solid #2a2f3a; padding:16px; white-space:pre-wrap; color:#8b93a7; }
  </style>
</head>
<body>
  <h1>&gt; VOIDLAB // network diagnostics</h1>
  <form method="get" action="/ping">
    <input type="text" name="host" placeholder="host to ping, e.g. 127.0.0.1" value="{{ host }}">
    <button type="submit">ping</button>
  </form>
  {% if output is not none %}<pre>{{ output }}</pre>{% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET"])
@app.route("/ping", methods=["GET"])
def ping():
    host = request.args.get("host")
    output = None
    if host:
        # --- VULNERABLE ON PURPOSE: shell metacharacters are not neutralized
        output = os.popen(f"ping -c 1 -W 2 {host}").read()
        # ---------------------------------------------------------------------
    return render_template_string(PAGE, host=host or "", output=output)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
