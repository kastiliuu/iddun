"""Static contract for the client feed layout and typography tokens."""

from pathlib import Path
import re


FEED_CSS = Path(__file__).resolve().parents[1] / "app/static/css/feed.css"


def test_feed_masonry_prioritizes_readable_card_width():
    content = FEED_CSS.read_text(encoding="utf-8")
    assert re.search(
        r"\.feed-masonry\s*\{[^}]*columns:\s*2;",
        content,
    )


def test_feed_has_no_sub_caption_literal_rem_type():
    content = FEED_CSS.read_text(encoding="utf-8")
    rem_sizes = re.findall(r"font-size:\s*(0?\.\d+)rem;", content)
    assert all(float(size) >= 0.75 for size in rem_sizes)
