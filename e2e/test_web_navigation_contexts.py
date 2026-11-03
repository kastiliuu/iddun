"""PR 1 do programa IDDUN 2.0 — navegação global e contextos no navegador.

- Telas logadas usam o cabeçalho único: Início, Explorar, Reservas,
  Favoritos, Notificações e o menu Eu (FE-DEC-021, 030; D-SOC-04).
- O menu Eu lista só os contextos da conta e leva ao painel de cada um
  (DEC-ID-077).
- Pro e Business têm cinco destinos com "Mais" acessível por teclado
  (FE-DEC-023, 024).
- Chamadas JSON feitas com a sessão da Web levam o token CSRF (AUD-04).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_EMAIL, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login
from e2e.test_web_pro_onboarding import _register

NAV_LABELS = ["Início", "Explorar", "Reservas", "Favoritos", "Notificações"]


def _header_nav(page: Page):
    return page.locator("[data-app-header]").get_by_role("navigation", name="Navegação principal")


MENU_TEXT = """
(root) => [...document.querySelectorAll(`${root} :is(span,strong,small,a,button,li)`)]
  .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
  .filter((el) => el.getBoundingClientRect().width > 0)
  .map((el) => ({ text: el.innerText.trim().slice(0, 30), size: parseFloat(getComputedStyle(el).fontSize) }))
  .filter((item) => item.size < 12)
"""


def _readable(page: Page, root: str):
    """Mede só o menu aberto; o corpo de cada página tem auditoria própria."""
    assert page.evaluate(MENU_TEXT, root) == []
    failing = [
        item for item in page.evaluate(CONTRAST, f"{root} :is(span,strong,small,a,button)")
        if item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]


@pytest.mark.parametrize("path", ["/feed", "/minha-conta", "/minhas-reservas", "/experiencias", "/profissionais"])
def test_every_logged_in_page_has_the_same_header(page: Page, path):
    _login(page, E2E_EMAIL)
    page.goto(path)
    nav = _header_nav(page)
    for label in NAV_LABELS:
        expect(nav.get_by_text(label, exact=True)).to_be_visible()
    expect(page.locator("[data-app-header]")).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


def test_active_destination_and_explore_tabs(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/minhas-reservas")
    nav = _header_nav(page)
    expect(nav.locator('[aria-current="page"]')).to_have_text(re.compile("Reservas"))

    page.goto("/experiencias")
    tabs = page.get_by_role("navigation", name="Explorar")
    expect(tabs.locator('[aria-current="page"]')).to_have_text("Serviços")
    tabs.get_by_role("link", name="Profissionais").click()
    expect(page).to_have_url(re.compile(r"/profissionais$"))
    expect(page.get_by_role("navigation", name="Explorar").locator('[aria-current="page"]')).to_have_text("Profissionais")


def test_client_menu_shows_only_the_client_context(page: Page):
    # Conta nova: outras specs criam rascunhos para o cliente semeado.
    _register(page, name="Cliente Contextos")
    page.goto("/minha-conta")
    page.locator("[data-account-menu-trigger]").click()
    contexts = page.locator("[data-account-contexts] a")
    expect(contexts).to_have_count(1)
    expect(contexts.first).to_have_attribute("aria-current", "true")
    expect(page.get_by_role("link", name=re.compile("Tornar-me profissional"))).to_be_visible()
    _readable(page, "[data-account-menu]")
    page.keyboard.press("Escape")
    expect(page.locator("[data-account-menu]")).to_be_hidden()


def test_professional_switches_context_and_uses_the_pro_and_business_bars(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.locator("[data-account-menu-trigger]").click()
    contexts = page.locator("[data-account-contexts] a")
    expect(contexts).to_have_count(3)
    expect(contexts.nth(1)).to_contain_text("Profissional")
    expect(contexts.nth(2)).to_contain_text("Espaço QA Navegador")

    contexts.nth(1).click()
    expect(page).to_have_url(re.compile(r"/pro/painel$"))
    page.wait_for_load_state()
    pro_nav = page.get_by_role("navigation", name="Navegação IDDUN Pro")
    for label in ["Painel", "Agenda", "Serviços", "Clientes", "Mais"]:
        expect(pro_nav.get_by_text(label, exact=True)).to_be_visible()

    more = pro_nav.get_by_role("button", name="Mais")
    more.focus()
    page.keyboard.press("Enter")
    expect(more).to_have_attribute("aria-expanded", "true")
    expect(page.locator("#pro-more-menu").get_by_role("link", name="Insights")).to_be_focused()
    _readable(page, "#pro-more-menu")
    page.keyboard.press("Escape")
    expect(page.locator("#pro-more-menu")).to_be_hidden()
    expect(more).to_be_focused()

    page.locator("[data-account-menu-trigger]").click()
    page.locator("[data-account-contexts] a").nth(2).click()
    expect(page).to_have_url(re.compile(rf"/business/{E2E_BUSINESS_SLUG}/painel$"))
    page.wait_for_load_state()
    business_nav = page.get_by_role("navigation", name="Seções do painel Business")
    for label in ["Painel", "Agenda", "Equipe", "Serviços", "Mais"]:
        expect(business_nav.get_by_text(label, exact=True)).to_be_visible()
    business_nav.get_by_role("link", name="Agenda").click()
    expect(page).to_have_url(re.compile(rf"/business/{E2E_BUSINESS_SLUG}/reservas$"))
    expect(page.get_by_role("navigation", name="Seções do painel Business").locator('[aria-current="page"]')).to_have_text(re.compile("Agenda"))


def test_phone_has_bell_avatar_and_five_destinations(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_EMAIL)
    page.goto("/minhas-reservas")
    bell = page.locator(".feed-header__mobile-bell")
    expect(bell).to_be_visible()
    box = bell.bounding_box()
    assert box is not None and box["height"] >= 44
    bottom = page.locator("[data-mobile-bottom-nav] a")
    expect(bottom).to_have_count(5)
    expect(page.locator("[data-mobile-bottom-nav] [aria-current='page']")).to_contain_text("Reservas")
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0
    bell.click()
    expect(page).to_have_url(re.compile(r"/feed#feed-notification-panel$"))
    expect(page.locator("[data-notification-panel]")).to_be_visible()


def test_cookie_json_calls_need_the_csrf_token(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/feed")
    page.wait_for_load_state()
    without = page.evaluate(
        """async () => {
          const r = await fetch('/api/v1/notifications/read-all', {method: 'PUT', headers: {Accept: 'application/json'}});
          return {status: r.status, body: await r.json()};
        }"""
    )
    assert without["status"] == 400
    assert without["body"]["error"]["code"] == "csrf_failed"

    with_token = page.evaluate(
        """async () => {
          const r = await window.IDDUN.fetchWithCsrf('/api/v1/notifications/read-all', {method: 'PUT'});
          return r.status;
        }"""
    )
    assert with_token == 200
