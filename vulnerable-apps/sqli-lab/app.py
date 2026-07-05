"""
VOIDLAB · sqli-lab

Deliberately vulnerable Flask + SQLite app for the "SQL Injection: Login
Bypass" lab (OWASP A05:2025 - Injection). Runs in its own isolated,
non-privileged container with a throwaway, in-memory-reset SQLite database —
there is nothing of value in here beyond the lab's own flag, and the
container has no network route to anything outside the vulnerable-apps
segment.

THE VULNERABILITY IS INTENTIONAL AND CONTAINED TO THIS CONTAINER: the /login
route builds its SQL query with plain Python string formatting instead of
parameterized queries. Do not copy this pattern into real code — that's
the entire point of the lab.
"""
import os
import sqlite3

from flask import Flask, g, redirect, render_template, request, url_for

app = Flask(__name__)
DB_PATH = "/tmp/sqli_lab.db"
FLAG = os.environ.get("LAB_FLAG", "VOIDLAB{sql1_c0mm3nt_th3_p4ssw0rd_away}")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        DROP TABLE IF EXISTS users;
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
        """
    )
    # A genuinely long random password the learner cannot guess or brute
    # force — the lab is solved by bypassing the check, not cracking it.
    db.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", os.urandom(16).hex(), "admin"),
    )
    db.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("guest", "guest123", "member"),
    )
    db.commit()
    db.close()


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # --- VULNERABLE ON PURPOSE ---------------------------------------
        # String-concatenated SQL. A username of  admin' --  turns this into
        #   SELECT * FROM users WHERE username = 'admin' --' AND password='...'
        # which comments out the password check entirely.
        query = (
            f"SELECT * FROM users WHERE username = '{username}' "
            f"AND password = '{password}'"
        )
        db = get_db()
        try:
            row = db.execute(query).fetchone()
        except sqlite3.OperationalError:
            row = None
        # -------------------------------------------------------------------

        if row is not None:
            if row["role"] == "admin":
                return render_template("dashboard.html", flag=FLAG, username=row["username"])
            return render_template("dashboard.html", flag=None, username=row["username"])
        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
