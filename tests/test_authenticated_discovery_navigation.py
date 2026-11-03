"""Regression contracts for the client journey from Feed to directories."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "app/templates/components/header.html").read_text(encoding="utf-8")
PROS = (ROOT / "app/templates/public/professionals.html").read_text(encoding="utf-8")
BUSINESSES = (ROOT / "app/templates/public/establishments.html").read_text(encoding="utf-8")
FEED = (ROOT / "app/templates/feed/index.html").read_text(encoding="utf-8")
# PR 1 (D-SOC-04): telas logadas usam o cabeçalho único, o menu Eu e as abas
# de Explorar; o header.html ficou para visitantes e para a Home pública.
APP_HEADER = (ROOT / "app/templates/components/app-header.html").read_text(encoding="utf-8")
ACCOUNT_MENU = (ROOT / "app/templates/components/_account_menu.html").read_text(encoding="utf-8")
EXPLORE_TABS = (ROOT / "app/templates/components/explore-tabs.html").read_text(encoding="utf-8")


def test_authenticated_directory_keeps_client_navigation_destinations():
    assert "current_user.is_authenticated and current_page != 'home'" in HEADER
    assert "{% include 'components/app-header.html' %}" in HEADER
    authenticated_navigation = APP_HEADER + ACCOUNT_MENU + EXPLORE_TABS
    for route in ("feed.home", "public.experiences", "public.professionals",
                  "public.establishments", "bookings.mine", "account.dashboard"):
        assert "url_for('" + route + "')" in authenticated_navigation
    for template in (PROS, BUSINESSES):
        assert "components/explore-tabs.html" in template


def test_directories_have_authenticated_context_without_new_urls():
    for template in (PROS, BUSINESSES):
        assert "authenticated-discovery-page" in template
        assert "current_user.is_authenticated" in template
    assert "url_for('public.professionals')" in FEED
    assert "url_for('public.establishments')" in FEED


def test_public_navigation_still_has_guest_branch():
    assert "{% if current_page == 'home' %}" in HEADER
    assert "{% else %}" in HEADER
    assert "url_for('auth.login')" in HEADER
