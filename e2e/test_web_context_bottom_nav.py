"""NAV-W1: navegação contextual Business responsiva (FE-DEC-024)."""
import re
import pytest
from playwright.sync_api import Page, expect
from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login

@pytest.mark.parametrize("width", [320, 390, 760])
@pytest.mark.parametrize("path,active", [
    ("painel", "Painel"),
    ("reservas", "Agenda"),
    ("servicos", "Serviços"),
    ("indicadores", None),
])
def test_business_mobile_has_one_context_nav(page: Page, width, path, active):
    page.set_viewport_size({"width": width, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/{path}")
    nav = page.get_by_role("navigation", name="Navegação do estabelecimento")
    expect(nav).to_be_visible()
    expect(page.locator("[data-mobile-bottom-nav]")).to_have_count(0)
    expect(page.locator(".platform-mobile-nav")).to_have_count(0)
    expect(page.get_by_role("navigation", name="Seções do painel Business")).to_be_hidden()
    for name in ("Painel", "Agenda", "Equipe", "Serviços", "Mais"):
        expect(nav.get_by_text(name, exact=True)).to_be_visible()
    if active:
        expect(nav.locator('[aria-current="page"]')).to_have_text(active)
    else:
        nav.get_by_role("button", name="Mais opções do estabelecimento").click()
        expect(nav.get_by_role("link", name="Indicadores")).to_have_attribute("aria-current", "page")
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0

def test_business_more_menu_keyboard(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/painel")
    button = page.get_by_role("button", name="Mais opções do estabelecimento")
    button.focus()
    page.keyboard.press("Enter")
    expect(button).to_have_attribute("aria-expanded", "true")
    menu = page.locator("#business-mobile-more-menu")
    expect(menu).to_be_visible()
    expect(menu.get_by_role("link", name="Editar empresa")).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu).to_be_hidden()
    expect(button).to_be_focused()

def test_business_desktop_preserves_navigation(page: Page):
    page.set_viewport_size({"width": 1440, "height": 900})
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/reservas")
    expect(page.get_by_role("navigation", name="Seções do painel Business")).to_be_visible()
    expect(page.get_by_role("navigation", name="Navegação do estabelecimento")).to_be_hidden()
