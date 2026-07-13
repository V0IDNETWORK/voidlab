"""
GUI test for the theme/stylesheet bug fix.

This is the test that would have caught
``KeyError: '\\n    font-family'`` /
``ValueError: Single '}' encountered in format string`` directly: it
builds the real stylesheet and applies it to a real (offscreen)
QApplication, exactly like the application does at startup.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.gui


def test_build_stylesheet_does_not_raise() -> None:
    from voidremote.ui.theme import build_stylesheet
    css = build_stylesheet()
    assert len(css) > 1000


def test_stylesheet_has_no_leftover_template_tokens() -> None:
    from voidremote.ui.theme import build_stylesheet
    css = build_stylesheet()
    assert "$" not in css
    assert "{TEXT_PRIMARY}" not in css
    assert "{BG_BASE}" not in css


def test_apply_dark_theme_to_real_qapplication(qapp) -> None:  # noqa: ANN001
    """
    The end-to-end version of the bug: apply the theme to a real
    QApplication via ``QApplication.setStyleSheet()``, which is exactly
    what raised the original KeyError/ValueError at application startup.
    """
    from voidremote.ui.theme import apply_dark_theme
    apply_dark_theme(qapp)  # must not raise
    assert len(qapp.styleSheet()) > 1000


def test_all_css_rule_blocks_are_well_formed() -> None:
    import re
    from voidremote.ui.theme import build_stylesheet
    css = build_stylesheet()
    assert css.count("{") == css.count("}")
    blocks = re.findall(r"\{[^{}]*\}", css)
    assert len(blocks) > 50
