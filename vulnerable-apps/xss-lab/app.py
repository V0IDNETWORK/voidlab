"""
VOIDLAB · xss-lab

Deliberately vulnerable Flask app for the "Reflected XSS: Cookie Heist" lab
(OWASP A05:2025 - Injection). Isolated, non-privileged container; the only
"session" here is a decoy value seeded per visit, and the collector only
ever talks to this same container — nothing leaves the lab network.

THE VULNERABILITY IS INTENTIONAL: /search renders the `q` parameter straight
into the page with Python f-strings, bypassing Jinja2's autoescaping on
purpose (render_template_string is called on unescaped, pre-built HTML) so
that a reflected-XSS payload actually executes in the lab browser.
"""
import os
import uuid

from flask import Flask, make_response, render_template_string, request

app = Flask(__name__)
FLAG = os.environ.get("LAB_FLAG", "VOIDLAB{xss_st33ls_s3ss10ns_s1l3ntly}")

# In-memory "collector" log — resets whenever the container restarts, which
# is exactly right for a disposable training lab.
COLLECTED_COOKIES = []

PAGE_SHELL = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VOIDLAB · xss-lab search</title>
  <style>
    body {{ background:#0a0e14; color:#e7e9ee; font-family:'JetBrains Mono',monospace; padding:40px; }}
    input {{ padding:10px; width:320px; background:#12161f; border:1px solid #2a2f3a; color:#e7e9ee; }}
    button {{ padding:10px 16px; background:#7c5cff; border:none; color:#fff; border-radius:4px; }}
    .result {{ margin-top:20px; color:#8b93a7; }}
  </style>
</head>
<body>
  <h1>&gt; VOIDLAB // knowledge base search</h1>
  <form method="get">
    <input type="text" name="q" placeholder="search articles..." value="{q_for_input}">
    <button type="submit">search</button>
  </form>
  <div class="result">{result}</div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(PAGE_SHELL.format(q_for_input="", result="Try searching for something."))


@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "")
    # --- VULNERABLE ON PURPOSE: q is reflected with no output encoding ----
    result_html = f"No articles found for: {q}" if q else "Try searching for something."
    page = PAGE_SHELL.format(q_for_input=q, result=result_html)
    # -----------------------------------------------------------------------

    resp = make_response(page)
    # A real app would mark this HttpOnly; the lab intentionally leaves it
    # readable from JS so the exploit path is demonstrable end-to-end.
    resp.set_cookie("session_id", request.cookies.get("session_id", str(uuid.uuid4())))
    return resp


@app.route("/collector", methods=["GET"])
def collector():
    cookie_value = request.args.get("c")
    if cookie_value:
        COLLECTED_COOKIES.append(cookie_value)
    return {"logged": bool(cookie_value)}, 200


@app.route("/collector/log", methods=["GET"])
def collector_log():
    if COLLECTED_COOKIES:
        return {"captured_cookies": COLLECTED_COOKIES, "flag": FLAG}, 200
    return {"captured_cookies": [], "flag": None, "hint": "No cookie captured yet — get your payload to fire first."}, 200


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
