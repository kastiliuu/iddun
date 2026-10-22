"""Static regression guard for shared and authenticated navigation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "app/templates/components/header.html"
FEED_CSS = ROOT / "app/static/css/feed.css"


def test_shared_header_marks_active_feed_link():
    template = HEADER.read_text(encoding="utf-8")
    assert """{% if current_page == 'feed' %}aria-current="page"{% endif %}""" in template


def test_feed_navigation_respects_design_system_control_target():
    css = FEED_CSS.read_text(encoding="utf-8")
    assert "min-height: var(--ds-control-min-target);" in css
    assert "font: 500 var(--ds-type-secondary)/1 var(--font-body);" in css
