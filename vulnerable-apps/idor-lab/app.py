"""
VOIDLAB · idor-lab

Deliberately vulnerable Flask app covering two Broken Access Control labs
(OWASP A01:2025): "Profile Peeper" (IDOR) and "Admin By Accident" (BFLA).
Isolated, non-privileged container; every "user" here is fake seed data
created fresh on each container start.

THE VULNERABILITIES ARE INTENTIONAL:
  * /profile/<id> only checks that *a* session exists, never that the
    session's user matches the requested id (IDOR).
  * /admin only checks `is_authenticated`, never role/permission (BFLA) —
    and it isn't linked from the UI, which is not the same as being
    protected.
"""
import os
import uuid

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.urandom(24)
IDOR_FLAG = os.environ.get("IDOR_FLAG", "VOIDLAB{1d0r_numb3rs_dont_l13}")
BFLA_FLAG = os.environ.get("BFLA_FLAG", "VOIDLAB{bfla_h1dden_isnt_pr0tected}")

USERS = {
    1: {"username": "admin", "bio": f"System administrator. Internal note: {IDOR_FLAG}", "role": "admin"},
    2: {"username": "j.torres", "bio": "DevOps engineer, loves cats.", "role": "member"},
    3: {"username": "a.chen", "bio": "Frontend dev, coffee enthusiast.", "role": "member"},
}

LOGIN_PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>VOIDLAB · idor-lab</title>
<style>body{background:#0a0e14;color:#e7e9ee;font-family:'JetBrains Mono',monospace;padding:40px}
input{padding:10px;width:280px;background:#12161f;border:1px solid #2a2f3a;color:#e7e9ee}
button{padding:10px 16px;background:#7c5cff;border:none;color:#fff;border-radius:4px}</style>
</head><body>
<h1>&gt; VOIDLAB // HR portal</h1>
<p>Log in as any member (this account is intentionally not privileged).</p>
<form method="post" action="/login">
  <input name="username" placeholder="username" value="j.torres"><br><br>
  <button type="submit">log in as member</button>
</form>
</body></html>
"""

PROFILE_PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>Profile {{ user_id }}</title>
<style>body{background:#0a0e14;color:#e7e9ee;font-family:'JetBrains Mono',monospace;padding:40px}
.card{background:#12161f;border:1px solid #2a2f3a;border-radius:8px;padding:24px;max-width:480px}</style>
</head><body>
<h1>&gt; profile #{{ user_id }}</h1>
<div class="card">
  <p><b>username:</b> {{ user.username }}</p>
  <p><b>role:</b> {{ user.role }}</p>
  <p><b>bio:</b> {{ user.bio }}</p>
</div>
<p>You are logged in as <b>{{ me }}</b> (id={{ my_id }}). Nothing here checked whether {{ user_id }} == {{ my_id }}.</p>
</body></html>
"""

ADMIN_PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>Admin</title>
<style>body{background:#0a0e14;color:#29f1c3;font-family:'JetBrains Mono',monospace;padding:40px}</style>
</head><body>
<h1>&gt; admin control panel</h1>
<p>Congratulations — you reached a staff-only function-level endpoint as a regular member.</p>
<p>Flag: {{ flag }}</p>
</body></html>
"""


@app.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for("profile", user_id=session["user_id"]))
    return render_template_string(LOGIN_PAGE)


@app.route("/login", methods=["POST"])
def login():
    # Anyone can "log in" as a plain member — this lab is about what
    # happens *after* that, not about breaking the login itself.
    session["user_id"] = 2
    session["role"] = "member"
    return redirect(url_for("profile", user_id=2))


@app.route("/profile/<int:user_id>", methods=["GET"])
def profile(user_id):
    if "user_id" not in session:
        return redirect(url_for("index"))

    # --- VULNERABLE ON PURPOSE: no check that user_id == session["user_id"]
    user = USERS.get(user_id)
    # -----------------------------------------------------------------------
    if user is None:
        return jsonify(error="not found"), 404

    return render_template_string(
        PROFILE_PAGE, user_id=user_id, user=user, me=USERS[session["user_id"]]["username"], my_id=session["user_id"]
    )


@app.route("/admin", methods=["GET"])
def admin():
    # --- VULNERABLE ON PURPOSE: checks login, never role (BFLA) -----------
    if "user_id" not in session:
        return redirect(url_for("index"))
    # -----------------------------------------------------------------------
    return render_template_string(ADMIN_PAGE, flag=BFLA_FLAG)


@app.route("/healthz")
def healthz():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
