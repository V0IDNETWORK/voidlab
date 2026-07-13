"""
GUI smoke tests. Require the ``gui`` extra (PySide6) and a Qt platform
plugin. Run with the offscreen platform so they work in headless CI:

    QT_QPA_PLATFORM=offscreen pytest -m gui

These are NOT executed as part of building this project — this sandbox
has no PySide6 and no display. They're written to be run for real by
whoever has both.
"""
