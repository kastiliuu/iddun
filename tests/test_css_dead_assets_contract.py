"""CLEAN-CSS-001: only stylesheet assets referenced by the runtime should remain."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
CSS = APP / "static" / "css"
HOME = APP / "templates" / "public" / "home.html"

# Search executable/template resources, not historical Markdown audit records.
RUNTIME_SUFFIXES = {".py", ".html", ".js", ".css"}


def test_legacy_home_styles_are_not_shipped_or_runtime_referenced():
    home = HOME.read_text(encoding="utf-8")
    assert "css/landing.css" in home

    legacy = ("home.css", "home-stats.css")
    for name in legacy:
        assert not (CSS / name).exists(), f"Inactive stylesheet still shipped: {name}"

    references = [
        str(path.relative_to(ROOT))
        for path in APP.rglob("*")
        if path.is_file()
        and path.suffix in RUNTIME_SUFFIXES
        and any(name in path.read_text(encoding="utf-8") for name in legacy)
    ]
    assert references == [], f"Legacy CSS runtime references: {references}"


def test_booking_card_keeps_active_footer_without_dead_span_rule():
    css = (CSS / "booking.css").read_text(encoding="utf-8")
    assert ".booking-card__foot {" in css
    assert ".booking-card__foot button {" in css
    assert ".booking-card__foot > span {" not in css
