"""Regression contracts for the client journey from Feed to directories."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "app/templates/components/header.html").read_text(encoding="utf-8")
PROS = (ROOT / "app/templates/public/professionals.html").read_text(encoding="utf-8")
BUSINESSES = (ROOT / "app/templates/public/establishments.html").read_text(encoding="utf-8")
FEED = (ROOT / "app/templates/feed/index.html").read_text(encoding="utf-8")


def test_authenticated_directory_keeps_client_navigation_destinations():
    assert "current_user.is_authenticated and current_page != 'home'" in HEADER
    for route in ("feed.home", "public.experiences", "public.professionals",
                  "public.establishments", "bookings.mine", "account.dashboard"):
        assert "url_for('" + route + "')" in HEADER


def test_directories_have_authenticated_context_without_new_urls():
    for template in (PROS, BUSINESSES):
        assert "authenticated-discovery-page" in template
        assert "current_user.is_authenticated" in template
    assert "url_for('public.professionals')" in FEED
    assert "url_for('public.establishments')" in FEED


def test_public_navigation_still_has_guest_branch():
    assert "{% elif current_page == 'home' %}" in HEADER
    assert "{% else %}" in HEADER
