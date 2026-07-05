"""
Seeds VOIDLAB with the OWASP Top 10:2025 categories and its lab catalog.

Run via: python manage.py seed_labs
Idempotent — safe to re-run; existing rows are updated in place by slug/code.

NOTE ON SCOPE: this ships 21 fully-defined labs spanning all ten 2025
categories (some categories get 2-3 labs given their real-world weight,
e.g. Broken Access Control and Injection). Five labs run against genuinely
live, isolated vulnerable containers (sqli-lab, xss-lab, cmdi-lab, idor-lab,
ssrf-lab). The rest are self-contained "analysis" challenges — a realistic
artifact (code snippet, log excerpt, encoded config) is embedded directly in
the briefing, in the same spirit as jeopardy-style CTF "misc/crypto/forensics"
categories that don't require a dedicated backend. To reach 30+, duplicate a
LAB_CATALOG entry, point it at a new/existing target_app + target_path, and
write a new flag — the pattern is identical for every entry below.
"""
import base64

from django.core.management.base import BaseCommand

from apps.labs.models import Category, Hint, Lab, Solution

CATEGORIES = [
    dict(code="A01", name="Broken Access Control", short_name="Access Control",
         icon="lock-open",
         description="Failures that let a user act outside their intended permissions — IDOR, "
                     "broken function-level authorization, path traversal, and SSRF are now all "
                     "grouped here in the 2025 list."),
    dict(code="A02", name="Security Misconfiguration", short_name="Misconfiguration",
         icon="settings",
         description="Insecure defaults, verbose errors, exposed debug tooling, and permissive "
                     "cloud/storage configuration — the fastest-growing risk category in 2025."),
    dict(code="A03", name="Software Supply Chain Failures", short_name="Supply Chain",
         icon="package",
         description="Risk introduced by third-party dependencies, build tooling, and CI/CD "
                     "pipelines — dependency confusion, typosquatting, and unsigned artifacts."),
    dict(code="A04", name="Cryptographic Failures", short_name="Crypto Failures",
         icon="key",
         description="Weak, misused, or missing cryptography that exposes sensitive data — "
                     "hardcoded keys, fast password hashes, forgeable tokens."),
    dict(code="A05", name="Injection", short_name="Injection",
         icon="terminal",
         description="Untrusted input interpreted as code or commands by an interpreter — SQL, "
                     "OS command, and Cross-Site Scripting all live here."),
    dict(code="A06", name="Insecure Design", short_name="Insecure Design",
         icon="drafting-compass",
         description="Missing or ineffective security controls at the architecture level — "
                     "business-logic flaws that no amount of clean code alone will fix."),
    dict(code="A07", name="Authentication Failures", short_name="Auth Failures",
         icon="fingerprint",
         description="Weaknesses in how identity is proven and sessions are managed — "
                     "credential stuffing, session fixation, missing lockouts."),
    dict(code="A08", name="Software or Data Integrity Failures", short_name="Integrity Failures",
         icon="shield-alert",
         description="Code and data that isn't verified before it's trusted — insecure "
                     "deserialization, unsigned updates, tampered CI/CD artifacts."),
    dict(code="A09", name="Security Logging and Alerting Failures", short_name="Logging Failures",
         icon="file-warning",
         description="Insufficient logging, monitoring, and — new emphasis in 2025 — alerting, "
                     "that lets breaches go undetected long enough to matter."),
    dict(code="A10", name="Mishandling of Exceptional Conditions", short_name="Exception Handling",
         icon="alert-triangle",
         description="Brand-new for 2025: improper error handling, fail-open logic, race "
                     "conditions, and other bugs that surface only in edge cases."),
]


def b64(raw: str) -> str:
    return base64.b64encode(raw.encode()).decode()


# Each entry: category_code, title, difficulty, points, summary, briefing, objective,
# target_app (blank = static analysis challenge), target_path, flag, hints[(text, penalty)], solution
LAB_CATALOG = [
    # ---------------------------------------------------------------- A01
    dict(cat="A01", title="Profile Peeper", difficulty="easy", points=100,
         target_app="idor-lab", target_path="/profile/1001",
         summary="A user dashboard trusts the ID in the URL a little too much.",
         objective="Read another operative's private profile without ever logging in as them.",
         briefing="VOIDLAB's internal HR portal shows your own profile at `/profile/<id>`. "
                   "Nothing on the server checks that the `<id>` in the URL belongs to your "
                   "session. Find the administrator's record and recover the flag stored on "
                   "their profile page.",
         flag="VOIDLAB{1d0r_numb3rs_dont_l13}",
         hints=[("IDs are sequential. What happens if you count down from your own ID?", 5),
                ("Try requesting /profile/1 through /profile/10 — admin accounts are seeded first.", 10)],
         solution="The profile endpoint authenticates the request (a valid session is required) "
                  "but never authorizes it (it never checks session.user_id == requested id). "
                  "Walking the numeric ID space (IDOR) exposes every other user's record, "
                  "including the seeded admin account at id=1, whose bio field holds the flag. "
                  "Fix: derive the profile to render from the authenticated session, never from "
                  "a client-supplied identifier — or enforce an object-level ACL check server-side."),
    dict(cat="A01", title="Admin By Accident", difficulty="medium", points=150,
         target_app="idor-lab", target_path="/admin",
         summary="A hidden admin panel that was never actually hidden.",
         objective="Reach a 'staff-only' function-level endpoint as a plain registered user.",
         briefing="The portal's navbar never links to `/admin`, and the login form only issues "
                   "'member' role tokens — but the route is very much alive server-side and "
                   "never re-checks the caller's role. Broken Function Level Authorization "
                   "(BFLA) is one of the two API patterns the 2025 Top 10 folded explicitly "
                   "into Broken Access Control.",
         flag="VOIDLAB{bfla_h1dden_isnt_pr0tected}",
         hints=[("Client-side routing hiding a link is not server-side access control.", 5),
                ("Inspect the app's bundled JS or try common admin paths directly.", 10)],
         solution="`/admin` only checks `is_authenticated`, never `is_staff` — a textbook BFLA "
                  "gap. Any logged-in member can call it directly, bypassing UI-level hiding "
                  "entirely. Fix: apply a role/permission check on every privileged view, "
                  "enforced by middleware or a decorator, never inferred from what the UI shows."),
    dict(cat="A01", title="Metadata Reach", difficulty="hard", points=200,
         target_app="ssrf-lab", target_path="/preview",
         summary="An avatar-preview feature that will fetch anything you ask it to.",
         objective="Abuse a server-side fetch feature to reach an internal-only endpoint.",
         briefing="VOIDLAB's 'preview my avatar URL' feature fetches whatever URL you give it "
                   "and renders the response. The container also runs a small internal-only "
                   "metadata service on `169.254.169.254`-style loopback that should never be "
                   "reachable from outside. SSRF was merged into Broken Access Control in the "
                   "2025 list precisely because this is fundamentally an authorization failure: "
                   "the server reaches somewhere the *user* should not be able to reach.",
         flag="VOIDLAB{ssrf_is_acc3ss_c0ntrol_t00}",
         hints=[("The preview endpoint doesn't restrict scheme or host at all.", 5),
                ("The lab container exposes its internal metadata service on localhost:9000/latest/flag.", 10)],
         solution="The preview feature performs a server-side HTTP GET on any user-supplied URL "
                  "with no allowlist for scheme or destination host. Pointing it at "
                  "`http://127.0.0.1:9000/latest/flag` makes the *server* fetch an internal-only "
                  "resource on the attacker's behalf. Fix: allowlist outbound destinations, block "
                  "requests to loopback/link-local ranges, and never let user input choose the "
                  "target host of a server-side request outright."),
    # ---------------------------------------------------------------- A02
    dict(cat="A02", title="Debug Left On", difficulty="easy", points=100,
         target_app="", target_path="",
         summary="A stack trace that says a lot more than it should.",
         objective="Read a production error page and extract a secret it accidentally reveals.",
         briefing="A teammate pasted this error page from a staging deploy that was accidentally "
                   "pushed live with debug mode on. Framework debug pages typically dump local "
                   "variables, settings, and file paths straight into the HTTP response:\n\n"
                   "```\nInternalError at /checkout/apply-coupon\nKeyError: 'FLAG'\n\n"
                   "Local vars:\n  SETTINGS.SECRET_KEY = 'a1b2***redacted***'\n"
                   "  SETTINGS.DEBUG_FLAG_B64 = '" + b64("VOIDLAB{d3bug_m0de_l3aks_ev3ryth1ng}") + "'\n"
                   "  request.path = '/checkout/apply-coupon'\n```\n"
                   "Decode `SETTINGS.DEBUG_FLAG_B64` to recover the flag.",
         flag="VOIDLAB{d3bug_m0de_l3aks_ev3ryth1ng}",
         hints=[("That value is Base64, not the flag itself.", 5)],
         solution="Framework debug pages (Django's DEBUG=True page, Flask's Werkzeug debugger, "
                  "etc.) exist to help developers, but they dump local variable state — "
                  "including secrets — straight into an HTTP response anyone can view. Fix: "
                  "DEBUG must always be False in any environment reachable outside localhost, "
                  "and error responses in production should render a generic message plus a "
                  "correlation ID, with details only in server-side logs."),
    dict(cat="A02", title="Bucket Left Open", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="Cloud object storage with directory listing turned on.",
         objective="Enumerate a misconfigured storage bucket's file listing to find the flag file.",
         briefing="An intern configured VOIDLAB's asset bucket as publicly *listable*, not just "
                  "publicly readable — a distinct and much worse misconfiguration. Here is the "
                  "raw XML listing response:\n\n"
                  "```xml\n<ListBucketResult>\n"
                  "  <Contents><Key>assets/logo.png</Key></Contents>\n"
                  "  <Contents><Key>assets/banner.jpg</Key></Contents>\n"
                  "  <Contents><Key>backups/2026-06-01-notes.txt</Key></Contents>\n"
                  "  <Contents><Key>backups/flag_" + b64("VOIDLAB{public_l1st1ng_1s_a_l3ak}")[:10] + ".txt</Key></Contents>\n"
                  "</ListBucketResult>\n```\n"
                  "The flag file's name itself is a Base64 fragment. Recognize the encoding, "
                  "reconstruct it, and decode it.",
         flag="VOIDLAB{public_l1st1ng_1s_a_l3ak}",
         hints=[("Object storage should almost never allow anonymous ListBucket, even if "
                 "individual objects require a signed URL to read.", 5)],
         solution="Public *read* access to individual objects is sometimes intentional (e.g. a "
                  "CDN-fronted assets bucket); public *list* access is very rarely intentional, "
                  "because it turns 'guess an object key' into 'read the entire directory "
                  "structure.' Fix: deny `s3:ListBucket`-equivalent permissions to anonymous "
                  "principals, and keep backups in a separate, non-public bucket entirely."),
    # ---------------------------------------------------------------- A03
    dict(cat="A03", title="Typosquat Trap", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A one-character typo in a package.json that isn't a typo at all.",
         objective="Spot the typosquatted dependency hiding in a real-looking lockfile diff.",
         briefing="A pull request quietly changed one line of `package.json`. Find it:\n\n"
                   "```diff\n"
                   "  \"dependencies\": {\n"
                   "    \"express\": \"^4.19.2\",\n"
                   "    \"lodash\": \"^4.17.21\",\n"
                   "-   \"cross-env\": \"^7.0.3\",\n"
                   "+   \"cross-envs\": \"^7.0.3\",\n"
                   "    \"dotenv\": \"^16.4.5\"\n"
                   "  }\n```\n"
                   "`cross-envs` (plural) is not the real package — it's a typosquat registered "
                   "by an attacker banking on exactly this kind of one-letter review miss. The "
                   "real package's install script, on the malicious version, would exfiltrate "
                   "`process.env` to an attacker server. The flag is the SHA-256-style short "
                   "hash the malicious package prints on install: "
                   "`VOIDLAB{typ0squat_r3v1ew_y0ur_d1ffs}`.",
         flag="VOIDLAB{typ0squat_r3v1ew_y0ur_d1ffs}",
         hints=[("Diff every dependency name character-by-character against the real registry, "
                 "don't skim.", 5)],
         solution="Typosquatting relies on a reviewer's eye skipping past a near-identical "
                  "package name during code review. Fix: pin dependencies with a lockfile *and* "
                  "verify integrity hashes, restrict which registries CI is allowed to install "
                  "from, and treat any new dependency in a PR as requiring explicit sign-off, "
                  "not a rubber stamp."),
    dict(cat="A03", title="Unsigned Update", difficulty="hard", points=200,
         target_app="", target_path="",
         summary="An auto-updater that installs whatever it's given.",
         objective="Identify why a tampered update artifact was accepted as legitimate.",
         briefing="VOIDLAB's desktop agent auto-updates by downloading a `.tar.gz` from a CDN "
                  "and running its installer script — with no signature verification step "
                  "anywhere in the update client's source:\n\n"
                  "```python\n"
                  "resp = requests.get(update_url)\n"
                  "with open('update.tar.gz', 'wb') as f:\n"
                  "    f.write(resp.content)\n"
                  "# NOTE: no checksum / signature check before this next line\n"
                  "subprocess.run(['tar', '-xzf', 'update.tar.gz', '-C', '/opt/agent'])\n```\n"
                  "An attacker who compromises the CDN (or performs a MITM on an "
                  "unauthenticated HTTP download) can swap the artifact for anything they like. "
                  "The flag was left in the vulnerable commit's message: "
                  "`VOIDLAB{" + "verify_before_you_trust" + "}`.",
         flag="VOIDLAB{verify_before_you_trust}",
         hints=[("Look for the single missing step between download and execution.", 5)],
         solution="Software/Data Integrity Failures (A08) and Supply Chain Failures (A03) "
                  "overlap deliberately here: trusting a downloaded artifact without verifying "
                  "a cryptographic signature (not just a checksum served from the same "
                  "compromisable source) means the update channel itself becomes the attack "
                  "surface. Fix: sign releases with a key kept offline from the build server, "
                  "verify that signature client-side before extraction, and serve updates over "
                  "TLS with certificate pinning where feasible."),
    # ---------------------------------------------------------------- A04
    dict(cat="A04", title="Weak Hash Cracker", difficulty="easy", points=100,
         target_app="", target_path="",
         summary="A password 'hashed' with a 1990s-era algorithm and no salt.",
         objective="Recover a plaintext password from an unsalted MD5 hash.",
         briefing="A leaked user table row: `admin:5f4dcc3b5aa765d61d8327deb882cf99`. That's a "
                   "bare, unsalted MD5 hash — fast to compute, fast to brute-force, and long "
                   "since removed from any credible password-hashing recommendation. Crack it "
                   "offline (a local dictionary attack is enough; this exact hash is one of the "
                   "most commonly seen test values in the world) and submit "
                   "`VOIDLAB{<the plaintext password>}` — for example, if the password were "
                   "'hunter2' you'd submit `VOIDLAB{hunter2}`.",
         flag="VOIDLAB{password}",
         hints=[("MD5 has no built-in salt, so identical passwords always hash identically — "
                 "which means this exact hash is extremely well documented.", 5)],
         solution="MD5 is a fast, general-purpose hash never designed for password storage — "
                  "billions of hashes/sec on commodity GPUs make brute force trivial, and no "
                  "salt means precomputed rainbow tables work instantly. Fix: use a slow, "
                  "memory-hard, salted KDF designed for passwords — Argon2id, scrypt, or bcrypt "
                  "— never a general-purpose hash function."),
    dict(cat="A04", title="None Alg JWT", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A JSON Web Token that will believe whatever algorithm you tell it to use.",
         objective="Forge a valid-looking admin JWT by abusing the 'none' algorithm.",
         briefing="VOIDLAB's API issues session JWTs and its verifier does this:\n\n"
                   "```python\n"
                   "payload = jwt.decode(token, key=SECRET, algorithms=['HS256', 'none'])\n```\n"
                   "Allowing `\"none\"` as a valid algorithm means a token can declare "
                   "`{\"alg\": \"none\"}` in its header and skip signature verification "
                   "entirely. Given a real user token's header/payload structure below, craft a "
                   "`none`-alg token claiming `\"role\": \"admin\"` and decode this response the "
                   "vulnerable server would send back to a forged admin token to get the flag: "
                   "the server returns the flag Base64-encoded as "
                   "`" + b64("VOIDLAB{n0ne_sh4ll_p4ss_v3rif1cation}") + "`.",
         flag="VOIDLAB{n0ne_sh4ll_p4ss_v3rif1cation}",
         hints=[("The vulnerability is entirely in accepting 'none' as an allowed algorithm at "
                 "verification time — the attacker never needs the real signing secret.", 5)],
         solution="Never accept the algorithm a token claims for itself — an attacker fully "
                  "controls the header of a token they forge. Fix: hardcode the expected "
                  "algorithm on the verifying side (e.g. always require and only accept HS256, "
                  "or better, an asymmetric algorithm like RS256/ES256 where the verifier only "
                  "ever holds a public key), and reject any token whose header doesn't match."),
    # ---------------------------------------------------------------- A05
    dict(cat="A05", title="SQL Injection: Login Bypass", difficulty="easy", points=100,
         target_app="sqli-lab", target_path="/login",
         summary="A login form that concatenates your username straight into SQL.",
         objective="Bypass authentication on the login form without ever knowing a valid password.",
         briefing="VOIDLAB's login form builds its query with plain string concatenation. Log "
                  "in as `admin` without knowing the admin password, and the dashboard will "
                  "show you the flag.",
         flag="VOIDLAB{sql1_c0mm3nt_th3_p4ssw0rd_away}",
         hints=[("A single quote in the username field will break the SQL syntax — what does "
                 "the resulting database error tell you?", 5),
                ("Try a username like admin' -- to comment out the rest of the query.", 10)],
         solution="The query is built as "
                  "`SELECT * FROM users WHERE username = '<input>' AND password = '<input>'`. "
                  "Submitting `admin' -- ` as the username turns the query into "
                  "`... WHERE username = 'admin' -- ' AND password = '...'` — everything after "
                  "`--` becomes a SQL comment, so the password check never runs. Fix: use "
                  "parameterized queries / an ORM everywhere, never string-format user input "
                  "into SQL."),
    dict(cat="A05", title="Reflected XSS: Cookie Heist", difficulty="medium", points=150,
         target_app="xss-lab", target_path="/search",
         summary="A search page that renders your query back into the page, unescaped.",
         objective="Inject a script that runs in the isolated lab browser and posts the session token to a local collector, then read it from the collector's log.",
         briefing="The search page reflects `?q=` straight into the HTML response with no "
                  "output encoding. The lab container also runs a tiny local 'collector' "
                  "endpoint at `/collector` that just logs whatever it receives — this is where "
                  "your payload should send the `document.cookie` value. Once the collector logs "
                  "a captured cookie, visit `/collector/log` to read the flag it reveals.",
         flag="VOIDLAB{xss_st33ls_s3ss10ns_s1l3ntly}",
         hints=[("Try `<script>` first — most modern browsers block inline script injected this "
                 "way via reflected XSS protections; an `<img onerror=...>` payload is more "
                 "reliable here.", 5),
                ("Payload shape: <img src=x onerror=\"fetch('/collector?c='+document.cookie)\">", 10)],
         solution="Output that is reflected into HTML without contextual encoding lets an "
                  "attacker-supplied `<script>`/event-handler run in the victim's browser with "
                  "full access to that origin's cookies, DOM, and storage. Fix: encode all "
                  "untrusted output for the context it's rendered in (HTML entity encoding by "
                  "default), set cookies `HttpOnly` so JavaScript can't read them at all, and "
                  "apply a Content-Security-Policy that blocks inline script."),
    dict(cat="A05", title="OS Command Injection: Ping Sweep Gone Wrong", difficulty="hard", points=200,
         target_app="cmdi-lab", target_path="/ping",
         summary="A network diagnostics tool that shells out to the OS ping command.",
         objective="Chain a shell metacharacter onto the host field to run an arbitrary command.",
         briefing="VOIDLAB's 'network diagnostics' page runs `ping -c 1 <your input>` via the "
                   "OS shell so operators can sanity-check connectivity to a host. The flag is "
                   "sitting in `/flag.txt` in the container. This lab runs entirely inside its "
                   "own isolated, non-privileged Docker container with no access to the host or "
                   "to any other service.",
         flag="VOIDLAB{c0mm4nd_1nj3ct10n_v14_sh3ll_m3t4ch4rs}",
         hints=[("Shell metacharacters like `;`, `&&`, or `|` let you chain a second command "
                 "after the intended one.", 5),
                ("Try a host value of: 127.0.0.1; cat /flag.txt", 10)],
         solution="Passing user input to a shell (`os.system`, `subprocess` with `shell=True`, "
                  "backticks, etc.) means any shell metacharacter in that input chains "
                  "additional, fully attacker-controlled commands. Fix: never invoke a shell "
                  "with untrusted input — call the underlying binary directly with an argument "
                  "array (e.g. `subprocess.run(['ping', '-c', '1', host], shell=False)`) and "
                  "validate the host against a strict allow-pattern regardless."),
    # ---------------------------------------------------------------- A06
    dict(cat="A06", title="Negative Quantity", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A checkout flow that trusts the client to do arithmetic honestly.",
         objective="Spot the missing server-side validation that lets a cart total go negative.",
         briefing="VOIDLAB's shop checkout API accepts a quantity field and multiplies it by "
                  "unit price entirely client-side before submitting the final total for "
                  "charging:\n\n"
                  "```json\n"
                  "POST /api/checkout\n"
                  "{ \"item_id\": 42, \"quantity\": -3, \"unit_price\": 19.99, "
                  "\"client_total\": -59.97 }\n```\n"
                  "```python\n"
                  "# server\n"
                  "order.total = request.data['client_total']   # trusts the client entirely\n"
                  "charge_card(order.total)\n```\n"
                  "A negative quantity produces a negative total, which many naive payment "
                  "integrations interpret as a *refund* to the attacker's card. This is a "
                  "design flaw, not a code typo — no amount of input sanitization fixes 'the "
                  "server trusts a client-computed price.' Flag: "
                  "`VOIDLAB{tru5t_n0th1ng_fr0m_th3_cl13nt}`.",
         flag="VOIDLAB{tru5t_n0th1ng_fr0m_th3_cl13nt}",
         hints=[("The bug isn't a missing regex — it's an entire trust boundary drawn in the "
                 "wrong place.", 5)],
         solution="Insecure Design failures can't be patched with a single validation rule "
                  "because the *architecture* trusts the wrong party. Fix: the server must look "
                  "up authoritative prices and quantities itself and compute the total "
                  "server-side, treating every client-supplied number as a request to validate, "
                  "never a fact to act on. Threat-model checkout/payment flows explicitly for "
                  "'what if the client lies.'"),
    dict(cat="A06", title="No Rate Limit, No Problem (For Attackers)", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A password-reset flow with an unlimited number of guesses.",
         objective="Recognize why an unthrottled 6-digit reset code is a design-level flaw.",
         briefing="```python\n"
                   "@app.route('/reset/verify', methods=['POST'])\n"
                   "def verify_reset_code():\n"
                   "    code = request.form['code']       # 6 digits, 000000-999999\n"
                   "    if code == session['reset_code']:  # no attempt counter anywhere\n"
                   "        return issue_reset_token()\n"
                   "    return 'invalid code', 400\n```\n"
                   "A 6-digit code has one million possibilities — trivially brute-forceable in "
                   "minutes at a few hundred requests/second, and nothing here limits attempts, "
                   "adds delay, or expires the code quickly. Flag: "
                   "`VOIDLAB{unthr0ttl3d_1s_und3f3nd3d}`.",
         flag="VOIDLAB{unthr0ttl3d_1s_und3f3nd3d}",
         hints=[("Calculate how long a brute force actually takes against 1,000,000 "
                 "possibilities with no throttling at all.", 5)],
         solution="This is a design-level gap: the *concept* of a 6-digit numeric code assumes "
                  "an attempt limit and short expiry that were never built. Fix: rate-limit and "
                  "lock out after a handful of failed attempts, expire codes quickly (minutes, "
                  "not hours), and prefer a high-entropy, single-use token delivered out of band "
                  "over a short numeric code wherever possible."),
    # ---------------------------------------------------------------- A07
    dict(cat="A07", title="Session Fixation", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A session ID that never changes when you log in.",
         objective="Explain and identify why reusing a pre-login session ID after authentication is exploitable.",
         briefing="```python\n"
                   "@app.route('/login', methods=['POST'])\n"
                   "def login():\n"
                   "    user = authenticate(request.form)\n"
                   "    session['user_id'] = user.id   # note: no session.regenerate() call\n"
                   "    return redirect('/dashboard')\n```\n"
                   "The session cookie issued *before* login is the exact same one used *after* "
                   "login — the server never rotates the session identifier at the privilege "
                   "boundary. An attacker who can plant a known session ID in a victim's browser "
                   "(e.g. via a subdomain that shares the cookie's domain scope) can log in "
                   "using that same ID once the victim authenticates. Flag: "
                   "`VOIDLAB{r0t4t3_s3ss10ns_0n_l0g1n}`.",
         flag="VOIDLAB{r0t4t3_s3ss10ns_0n_l0g1n}",
         hints=[("Compare the session cookie's value before and after the login POST — it "
                 "should never be the same value.", 5)],
         solution="Session fixation exploits a server that accepts a pre-existing session "
                  "identifier as valid post-authentication. Fix: always issue a brand-new "
                  "session ID at every privilege change (login, logout, privilege escalation), "
                  "invalidating the old one — most frameworks expose this as "
                  "`session.regenerate()`/`cycle_key()`; call it explicitly in the login view."),
    dict(cat="A07", title="Brute-Forceable Login", difficulty="easy", points=100,
         target_app="", target_path="",
         summary="A login endpoint with no lockout, delay, or CAPTCHA after failed attempts.",
         objective="Identify the missing control that turns a login form into an open invitation for credential stuffing.",
         briefing="```python\n"
                   "@app.route('/login', methods=['POST'])\n"
                   "def login():\n"
                   "    user = User.query.filter_by(username=request.form['u']).first()\n"
                   "    if user and check_password(user, request.form['p']):\n"
                   "        return issue_session(user)\n"
                   "    return 'invalid credentials', 401   # nothing tracks failure count\n```\n"
                   "There is no failed-attempt counter, no exponential backoff, no account "
                   "lockout, and no CAPTCHA — an attacker with a leaked credential list from "
                   "another breach can attempt every combination against this endpoint at full "
                   "speed. Flag: `VOIDLAB{l0ck0uts_st0p_stuff1ng}`.",
         flag="VOIDLAB{l0ck0uts_st0p_stuff1ng}",
         hints=[("What, specifically, is tracked between one failed login attempt and the "
                 "next? Look for state, not error messages.", 5)],
         solution="Nothing in this handler persists failure counts anywhere, so every request "
                  "is evaluated in total isolation from the last. Fix: track failed attempts per "
                  "account and per source IP, apply increasing delay or temporary lockout after "
                  "a small threshold, and require MFA or a CAPTCHA once anomalous attempt volume "
                  "is detected."),
    # ---------------------------------------------------------------- A08
    dict(cat="A08", title="Insecure Deserialization", difficulty="hard", points=200,
         target_app="", target_path="",
         summary="An app that deserializes a user-controlled blob with a format that supports code execution.",
         objective="Understand why deserializing an untrusted, code-executing format is dangerous, without needing a working exploit chain.",
         briefing="```python\n"
                   "@app.route('/import-settings', methods=['POST'])\n"
                   "def import_settings():\n"
                   "    blob = base64.b64decode(request.form['data'])\n"
                   "    settings = pickle.loads(blob)   # <-- deserializes ANY object graph\n"
                   "    apply_settings(settings)\n```\n"
                   "Python's `pickle` format isn't just data — it can encode instructions to "
                   "construct arbitrary objects and call arbitrary callables during "
                   "deserialization, which is why 'never unpickle data from an untrusted source' "
                   "is a direct line in Python's own documentation. We won't hand you a working "
                   "exploit chain here (that's real offensive tooling, out of scope for a "
                   "training flag) — instead, identify *why* this line is the vulnerability, not "
                   "the `apply_settings()` call after it. The flag was left by whoever wrote this "
                   "vulnerable route, base64-encoded in a comment they forgot to remove: "
                   "`" + b64("VOIDLAB{n3v3r_unp1ckl3_untrust3d_d4ta}") + "`.",
         flag="VOIDLAB{n3v3r_unp1ckl3_untrust3d_d4ta}",
         hints=[("The vulnerability is the deserialization call itself — decide that before "
                 "looking at anything downstream of it.", 5)],
         solution="Formats like Python `pickle`, Java's native serialization, or PHP's "
                  "`unserialize()` can execute code as a side effect of reconstructing an "
                  "object graph — deserializing attacker-controlled bytes with these formats is "
                  "close to handing over code execution directly. Fix: never deserialize "
                  "untrusted data with a format capable of arbitrary object construction; use a "
                  "data-only format (JSON, and validate the resulting structure against a "
                  "strict schema) for anything crossing a trust boundary."),
    dict(cat="A08", title="Tampered Update, Take Two", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A CI pipeline artifact whose checksum is verified against a file the attacker also controls.",
         objective="Spot why 'we check a checksum' isn't the same as 'we verify integrity'.",
         briefing="```yaml\n"
                   "# release.yml\n"
                   "- run: curl -o app.tar.gz https://cdn.example/app.tar.gz\n"
                   "- run: curl -o app.tar.gz.sha256 https://cdn.example/app.tar.gz.sha256\n"
                   "- run: sha256sum -c app.tar.gz.sha256\n```\n"
                   "The checksum file is downloaded from the exact same, single, unauthenticated "
                   "CDN as the artifact it's meant to verify — if an attacker can replace one, "
                   "they can trivially replace the other to match. A matching checksum here only "
                   "proves the file wasn't corrupted in transit; it proves nothing about who "
                   "produced it. Flag: `VOIDLAB{ch3cksum_1s_n0t_a_s1gnatur3}`.",
         flag="VOIDLAB{ch3cksum_1s_n0t_a_s1gnatur3}",
         hints=[("Ask: who controls the value being compared against? If the answer is 'the "
                 "same party who could tamper with the artifact,' the check proves nothing "
                 "about authenticity.", 5)],
         solution="A checksum only detects accidental corruption unless it's cryptographically "
                  "signed by a key the attacker doesn't control, and verified against that "
                  "signature — not against another file fetched from the same untrusted "
                  "channel. Fix: sign build artifacts with a key held outside the CI "
                  "environment that produces them, and verify that signature (not a co-located "
                  "checksum file) before trusting or executing the artifact."),
    # ---------------------------------------------------------------- A09
    dict(cat="A09", title="Silent Intruder", difficulty="medium", points=150,
         target_app="", target_path="",
         summary="A successful break-in that produced logs, but never an alert.",
         objective="Find the exact log line that shows privilege escalation slipping past unnoticed.",
         briefing="Here is an excerpt from VOIDLAB's auth service log for one account over 90 "
                   "seconds. Logging was on the whole time — alerting was not configured for "
                   "any of these event types:\n\n"
                   "```\n"
                   "09:14:02 INFO  login_failed  user=jsmith ip=203.0.113.9\n"
                   "09:14:05 INFO  login_failed  user=jsmith ip=203.0.113.9\n"
                   "09:14:09 INFO  login_failed  user=jsmith ip=203.0.113.9\n"
                   "09:14:14 INFO  login_success user=jsmith ip=203.0.113.9\n"
                   "09:14:20 INFO  role_change   user=jsmith old=member new=admin actor=jsmith\n"
                   "09:14:31 INFO  export_data   user=jsmith table=all_users rows=48213\n```\n"
                   "Every one of these events was logged correctly. The failure isn't in "
                   "logging — it's that nothing was watching. Which single line should have "
                   "fired an immediate, high-priority alert regardless of any other context? "
                   "Flag: `VOIDLAB{l0gg1ng_w1th0ut_al3rt1ng_1s_bl1nd}`.",
         flag="VOIDLAB{l0gg1ng_w1th0ut_al3rt1ng_1s_bl1nd}",
         hints=[("A user granting *themselves* a higher role (actor == user, old != new) is "
                 "essentially never legitimate.", 5)],
         solution="A@09:2025 was renamed from 'Logging and Monitoring' to 'Logging and "
                  "Alerting' specifically to call out this gap: comprehensive logs are worthless "
                  "for incident response if nothing evaluates them in real time. `role_change` "
                  "where `actor == user` and the role increases is a near-universal red flag "
                  "that should page someone immediately, not wait for a manual audit. Fix: define "
                  "alerting rules for security-relevant event patterns (self-privilege-escalation, "
                  "mass data export, impossible-travel logins) and route them to an on-call "
                  "channel, not just a log index."),
    # ---------------------------------------------------------------- A10
    dict(cat="A10", title="Fail Open", difficulty="hard", points=200,
         target_app="", target_path="",
         summary="An authorization check that grants access when the check itself throws.",
         objective="Find the exception path that defaults to 'allow' instead of 'deny'.",
         briefing="```python\n"
                   "def can_access(user, document):\n"
                   "    try:\n"
                   "        acl = fetch_acl(document.id)         # network call to ACL service\n"
                   "        return user.id in acl.allowed_users\n"
                   "    except ACLServiceTimeout:\n"
                   "        return True   # <-- 'don't block users if the ACL service is slow'\n```\n"
                   "This exception handler was written to protect uptime during an ACL service "
                   "outage — but it silently converts *any* failure of the authorization check "
                   "(timeout, crash, malformed response) into full access for every document, "
                   "for every user, for as long as the failure lasts. This is a brand-new 2025 "
                   "category precisely because 'what happens when things fail' is so often left "
                   "unspecified. Flag: `VOIDLAB{f41l_cl0s3d_n0t_0p3n}`.",
         flag="VOIDLAB{f41l_cl0s3d_n0t_0p3n}",
         hints=[("Ask what the *safe* default should be when a security-relevant check cannot "
                 "complete at all.", 5)],
         solution="Any control whose failure mode defaults to granting access converts every "
                  "outage, timeout, or bug in that control into a total bypass. Fix: exceptional "
                  "conditions in security-relevant code paths must fail closed (deny by default) "
                  "and raise loudly (log + alert), never silently fail open for the sake of "
                  "uptime — uptime with an open door isn't actually up."),
    dict(cat="A10", title="Race Condition Redeem", difficulty="insane", points=250,
         target_app="", target_path="",
         summary="A single-use coupon code that can be redeemed more than once, if you're fast enough.",
         objective="Explain the TOCTOU (time-of-check to time-of-use) gap that allows a double-redeem.",
         briefing="```python\n"
                   "def redeem(coupon_code, user):\n"
                   "    coupon = Coupon.objects.get(code=coupon_code)\n"
                   "    if coupon.redeemed:                 # (1) CHECK\n"
                   "        raise AlreadyRedeemed()\n"
                   "    apply_discount(user, coupon.value)   # ... time passes ...\n"
                   "    coupon.redeemed = True                # (2) USE\n"
                   "    coupon.save()\n```\n"
                   "Between step (1) and step (2) there is a window where two concurrent "
                   "requests can both read `coupon.redeemed = False` before either has written "
                   "`True` back — both get the discount applied. Firing the redeem request "
                   "twice in rapid parallel succession (a classic race condition / "
                   "time-of-check-to-time-of-use bug) doubles the payout. Flag: "
                   "`VOIDLAB{r4c3_c0nd1t10ns_ar3nt_th30r3t1cal}`.",
         flag="VOIDLAB{r4c3_c0nd1t10ns_ar3nt_th30r3t1cal}",
         hints=[("The bug isn't in the logic of either line alone — it's in the gap in time "
                 "between them, under concurrency.", 5),
                ("What single database feature would make the check-then-use atomic instead "
                 "of two separate steps?", 10)],
         solution="This is a textbook TOCTOU bug: the check and the state update are two "
                  "separate, non-atomic operations, so concurrent requests can both pass the "
                  "check before either commits the update. Fix: make the check-and-update "
                  "atomic — a single `UPDATE coupons SET redeemed=true WHERE code=%s AND "
                  "redeemed=false` (checking the affected row count) or a `SELECT ... FOR "
                  "UPDATE` row lock inside a transaction — so only one concurrent request can "
                  "ever win the redemption."),
]


class Command(BaseCommand):
    help = "Seed OWASP Top 10:2025 categories and the VOIDLAB lab catalog (idempotent)."

    def handle(self, *args, **options):
        cat_by_code = {}
        for i, cat in enumerate(CATEGORIES):
            obj, created = Category.objects.update_or_create(
                code=cat["code"], defaults={**cat, "order": i}
            )
            cat_by_code[cat["code"]] = obj
            self.stdout.write(f"{'+' if created else '='} category {obj.code}")

        for i, entry in enumerate(LAB_CATALOG):
            lab, created = Lab.objects.update_or_create(
                title=entry["title"],
                defaults=dict(
                    category=cat_by_code[entry["cat"]],
                    difficulty=entry["difficulty"],
                    status=Lab.Status.PUBLISHED,
                    summary=entry["summary"],
                    briefing=entry["briefing"],
                    objective=entry["objective"],
                    points=entry["points"],
                    target_app=entry["target_app"],
                    target_path=entry["target_path"] or "/",
                    order=i,
                ),
            )
            lab.set_flag(entry["flag"])
            lab.save(update_fields=["flag_hash"])

            lab.hints.all().delete()
            for order, (text, penalty) in enumerate(entry["hints"], start=1):
                Hint.objects.create(lab=lab, order=order, text=text, point_penalty=penalty)

            Solution.objects.update_or_create(lab=lab, defaults={"content": entry["solution"]})
            self.stdout.write(f"{'+' if created else '='} lab {lab.category.code} · {lab.title}")

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CATEGORIES)} categories and {len(LAB_CATALOG)} labs."
        ))
