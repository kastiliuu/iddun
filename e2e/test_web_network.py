"""PR 2 do programa IDDUN 2.0 — rede real no navegador (D-SOC-05, 06, 07).

- Seguir grava na conta: vale depois de recarregar e aparece na API que o
  app usa (outro aparelho).
- Visitante vai ao login e volta para o mesmo perfil.
- Sem Seguir no próprio perfil e na própria empresa.
- Salvar um serviço grava na conta e aparece em Favoritos.
- Favoritos antigos do navegador passam para a conta uma vez.
- Favoritos legível em 390 e 1280 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PASSWORD, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login
from e2e.test_web_pro_onboarding import _register
from e2e.test_web_readable_text import SMALL_TEXT

PRO_PATH = "/profissionais/profissional-qa-navegador"
SERVICE_SLUG = "coloracao-qa-navegador"
# Outras specs publicam serviços; o coração é o do serviço semeado.
SERVICE_HEART = '[data-save-button][data-save-title="experiência Coloração QA"]'


def _following(page: Page):
    response = page.request.get("/api/v1/graph/following")
    assert response.ok, response.status
    return [item["slug"] for item in response.json()["items"]]


def _saved_slugs(page: Page):
    response = page.request.get("/api/v1/graph/saved-items")
    assert response.ok, response.status
    return [item["id"] for item in response.json()["experiences"]]


def _click_and_wait(page: Page, locator, path_part):
    """O botão muda na hora; a conferência na API espera a gravação."""
    with page.expect_response(
        lambda r: path_part in r.url and r.request.method in {"PUT", "DELETE"}
    ) as response:
        locator.click()
    assert response.value.ok, response.value.status


def test_follow_is_saved_in_the_account(page: Page):
    _register(page, name="Cliente Rede")
    page.goto(PRO_PATH)
    page.wait_for_load_state()

    follow = page.locator("[data-follow-button]")
    count = page.locator("[data-follower-count]")
    before = int(count.get_attribute("data-count"))
    expect(follow).to_have_attribute("aria-pressed", "false")

    _click_and_wait(page, follow, "/api/v1/graph/follows/")
    expect(follow).to_have_attribute("aria-pressed", "true")
    expect(follow).to_contain_text("Seguindo")
    expect(count).to_have_attribute("data-count", str(before + 1))

    page.reload()
    expect(page.locator("[data-follow-button]")).to_have_attribute("aria-pressed", "true")
    assert "profissional-qa-navegador" in _following(page)

    page.goto("/favoritos")
    row = page.locator(".favorites-row", has_text="Profissional QA Navegador")
    expect(row).to_be_visible()
    _click_and_wait(page, row.locator("[data-follow-button]"), "/api/v1/graph/follows/")
    expect(row.locator("[data-follow-button]")).to_have_attribute("aria-pressed", "false")
    assert "profissional-qa-navegador" not in _following(page)


def test_visitor_goes_to_login_and_comes_back(page: Page):
    page.goto(PRO_PATH)
    page.wait_for_load_state()
    page.locator("[data-follow-button]").click()
    expect(page).to_have_url(re.compile(r"/login\?next=/profissionais/profissional-qa-navegador$"))

    page.locator('input[name="email"]').fill(E2E_PRO_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()
    expect(page).to_have_url(re.compile(rf"{PRO_PATH}$"))


def test_no_follow_on_own_profile_or_own_business(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto(PRO_PATH)
    expect(page.locator("h1")).to_have_text("Profissional QA Navegador")
    expect(page.locator("[data-follow-button]")).to_have_count(0)
    expect(page.locator("[data-follower-count]")).to_be_visible()

    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}")
    expect(page.locator("[data-follow-button]")).to_have_count(0)


def test_saving_a_service_shows_in_favorites(page: Page):
    _register(page, name="Cliente Salvos")
    page.goto("/experiencias")
    page.wait_for_load_state()

    heart = page.locator(SERVICE_HEART).first
    expect(heart).to_have_attribute("aria-pressed", "false")
    _click_and_wait(page, heart, "/api/v1/graph/saves/")
    expect(heart).to_have_attribute("aria-pressed", "true")
    assert SERVICE_SLUG in _saved_slugs(page)

    page.reload()
    expect(page.locator(SERVICE_HEART).first).to_have_attribute("aria-pressed", "true")

    page.goto("/favoritos?aba=salvos")
    card = page.locator(".favorites-card", has_text="Coloração QA")
    expect(card).to_be_visible()
    _click_and_wait(page, card.locator("[data-save-button]"), "/api/v1/graph/saves/")
    expect(card.locator("[data-save-button]")).to_have_attribute("aria-pressed", "false")
    assert SERVICE_SLUG not in _saved_slugs(page)


def test_old_browser_favorites_move_to_the_account(page: Page):
    _register(page, name="Cliente Legado")
    page.evaluate(
        """() => {
          localStorage.setItem('iddun:favorites:v2', JSON.stringify(['coloracao-qa-navegador']));
          localStorage.setItem('iddun:favorites:v1', JSON.stringify(['prototipo-que-nao-existe']));
        }"""
    )

    with page.expect_response(lambda r: r.url.endswith("/api/v1/graph/reconcile")) as reconcile:
        page.goto("/experiencias")
    assert reconcile.value.ok

    expect(page.locator(SERVICE_HEART).first).to_have_attribute("aria-pressed", "true")
    assert page.evaluate("localStorage.getItem('iddun:favorites:v2')") is None
    assert page.evaluate("localStorage.getItem('iddun:favorites:v1')") is None
    assert SERVICE_SLUG in _saved_slugs(page)


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_favorites_page_is_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _register(page, name="Cliente Leitura")
    page.goto(PRO_PATH)
    page.wait_for_load_state()
    _click_and_wait(page, page.locator("[data-follow-button]"), "/api/v1/graph/follows/")

    for path in ("/favoritos", "/favoritos?aba=salvos"):
        page.goto(path)
        expect(page.get_by_role("heading", level=1)).to_have_text("Favoritos")
        tabs = page.get_by_role("navigation", name="Favoritos")
        expect(tabs.locator('[aria-current="page"]')).to_have_count(1)
        assert page.evaluate(SMALL_TEXT) == []
        failing = [
            item for item in page.evaluate(CONTRAST, None)
            if item["ratio"] < (3 if item["large"] else 4.5)
        ]
        assert failing == [], failing[:5]
        assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0
