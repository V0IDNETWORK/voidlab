"""
VOIDLAB · ssrf-lab

Deliberately vulnerable Flask app for the "Metadata Reach" lab (OWASP
A01:2025 - Broken Access Control; SSRF was folded into this category in the
2025 refresh). Runs two tiny services in one container: the public-facing
"preview" app on :5000, and a fake internal-only "metadata" service on
:9000 that should never be reachable from outside this box — reaching it at
all *is* the vulnerability, which is why SSRF now lives under access
control rather than its own category.

THE VULNERABILITY IS INTENTIONAL: /preview performs a server-side HTTP GET
on any URL the client provides, with no allowlist on scheme or destination
host — including the loopback-only metadata service below.
"""
import os
import threading

import requests
from flask import Flask, jsonify, render_template_string, request

FLAG = os.environ.get("LAB_FLAG", "VOIDLAB{ssrf_is_acc3ss_c0ntrol_t00}")

# --- fake "internal metadata service", intentionally bound to loopback only
metadata_app = Flask("metadata")


@metadata_app.route("/latest/flag")
def metadata_flag():
    return jsonify(flag=FLAG)


def run_metadata_service():
    metadata_app.run(host="127.0.0.1", port=9000)


threading.Thread(target=run_metadata_service, daemon=True).start()
# ---------------------------------------------------------------------------

app = Flask(__name__)

PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>VOIDLAB · ssrf-lab</title>
<style>body{background:#0a0e14;color:#e7e9ee;font-family:'JetBrains Mono',monospace;padding:40px}
input{padding:10px;width:420px;background:#12161f;border:1px solid #2a2f3a;color:#e7e9ee}
button{padding:10px 16px;background:#7c5cff;border:none;color:#fff;border-radius:4px}
pre{background:#12161f;border:1px solid #2a2f3a;padding:16px;white-space:pre-wrap;color:#8b93a7;max-width:600px}</style>
</head><body>
<h1>&gt; VOIDLAB // avatar preview</h1>
<p>Paste any image URL and we'll fetch + show you a preview of the response, server-side.</p>
<form method="get" action="/preview">
  <input name="url" placeholder="https://example.com/avatar.png" value="{{ url }}">
  <button type="submit">preview</button>
</form>
{% if body is not none %}<pre>{{ body }}</pre>{% endif %}
</body></html>
"""


@app.route("/", methods=["GET"])
@app.route("/preview", methods=["GET"])
def preview():
    url = request.args.get("url")
    body = None
    if url:
        try:
            # --- VULNERABLE ON PURPOSE: no scheme/host allowlist, no block
            # on loopback/link-local destinations.
            resp = requests.get(url, timeout=5)
            body = resp.text[:2000]
            # ---------------------------------------------------------------
        except requests.RequestException as exc:
            body = f"(fetch failed: {exc})"
    return render_template_string(PAGE, url=url or "", body=body)


@app.route("/healthz")
def healthz():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
