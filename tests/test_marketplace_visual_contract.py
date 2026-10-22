"""Guard the public discovery layout from unnecessary empty space."""

from pathlib import Path
import re


CSS = Path(__file__).resolve().parents[1] / "app/static/css/marketplace.css"


def test_marketplace_results_has_no_fixed_minimum_height():
    css = CSS.read_text(encoding="utf-8")
    assert re.search(r"\.marketplace-results\s*\{\s*min-height:\s*0;", css)


def test_featured_media_uses_proportional_dimensions():
    css = CSS.read_text(encoding="utf-8")
    assert re.search(
        r"\.catalog-featured__media\s*\{[^}]*aspect-ratio:\s*4\s*/\s*3;",
        css,
    )
