# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ |
| < 1.0   | ❌ |

## Reporting a vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

Email **ilianothingg@gmail.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce, or a proof-of-concept
- Affected version(s)

You should get an initial response within 5 business days. We'll work
with you to understand and address the issue, and credit you in the
fix's changelog entry unless you'd prefer otherwise.

## Scope

VoidRemote shells out to the `adb` binary and executes ADB shell
commands, so its main attack surface is **command injection through
user-supplied input** (device paths, package names, shell arguments,
hostnames, pairing codes). Relevant code:

- `voidremote/utils/security.py` — all input validation
- `voidremote/adb/client.py` — every point a subprocess is spawned

If you find a way to get shell metacharacters, path traversal, or
unvalidated input through to a subprocess call, that's a valid report
regardless of how contrived the trigger is.

## Not in scope

- Vulnerabilities in the `adb` binary itself — report those to the
  [Android Open Source Project](https://source.android.com/).
- Vulnerabilities requiring physical access to an already-unlocked,
  already-debugging-enabled device.
- Denial of service against your own machine by running VoidRemote
  against a device you already fully control.
