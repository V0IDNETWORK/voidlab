"""
Packaging tests: verify the project actually builds and installs, not
just that pyproject.toml parses as valid TOML. These are the tests
that would have caught the reported
``BackendUnavailable: Cannot import setuptools.backends.legacy`` bug —
a bogus build-backend path is invisible to TOML validation and only
surfaces when something actually tries to build the package.
"""
