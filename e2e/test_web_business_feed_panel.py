"""P-004 / F16 e ID-SOC-R1-06 — painel Business em feed, no navegador.

- Três colunas no desktop: identidade, feed da empresa e cartões de
  equipe, operação e reputação; uma coluna no celular, sem rolagem lateral.
- A dona publica como a empresa e continua no painel.
- "Convidar profissional" e "Gerenciar equipe" abrem janelas sob demanda,
  com foco, Esc e retorno ao botão; o erro do convite reabre a janela.
- Sem JavaScript, os mesmos links abrem a janela pelo servidor.
"""

import re
import uuid

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PASSWORD, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login
from e2e.test_web_social_feed import _readable

PANEL = f"/business/{E2E_BUSINESS_SLUG}/painel"


def _open_panel(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto(PANEL)
    page.wait_for_load_state()


def test_panel_is_a_three_column_feed_on_desktop(page: Page):
    page.set_viewport_size({"width": 1440, "height": 900})
    _open_panel(page)

    left = page.locator(".business-feed > .feed-sidebar").bounding_box()
    center = page.locator(".business-feed > .feed-main").bounding_box()
    right = page.locator(".business-feed > .feed-rail").bounding_box()
    assert left["x"] < center["x"] < right["x"]
    assert center["width"] > left["width"] and center["width"] > right["width"]

    expect(page.get_by_role("heading", level=1)).to_have_text("Espaço QA Navegador")
    expect(page.get_by_role("heading", level=1)).to_have_css("font-family", re.compile(r"^\"?Inter"))
    expect(page.get_by_role("navigation", name="Seções do painel Business")).to_be_visible()
    # Os formulários de equipe não ficam mais abertos na página.
    expect(page.locator("#business-team form")).to_have_count(0)
    expect(page.locator("#business-team-invite")).to_be_hidden()
    expect(page.locator("#business-team-manage")).to_be_hidden()


def test_owner_publishes_as_the_company_and_stays_on_the_panel(page: Page):
    _open_panel(page)
    caption = f"Novidade do painel {uuid.uuid4().hex[:6]}"
    page.locator(".post-composer__summary").click()
    form = page.locator("[data-composer-form]")
    expect(form.locator('input[name="author"]')).to_have_attribute("value", re.compile(r"^establishment:\d+$"))
    expect(form.get_by_role("link", name="Publicar como você")).to_have_count(0)
    form.locator("[data-composer-caption]").fill(caption)
    with page.expect_navigation():
        form.locator("[data-composer-submit]").click()

    expect(page).to_have_url(re.compile(rf"{PANEL}#post-\d+$"))
    expect(page.locator(".flash-message")).to_contain_text("Sua publicação está no ar.")
    card = page.locator("article.feed-card").filter(has_text=caption)
    expect(card.locator(".feed-card__author")).to_contain_text("Espaço QA Navegador")
    # Na própria empresa não há Seguir.
    expect(card.locator("[data-follow-button]")).to_have_count(0)


def test_team_dialogs_open_on_demand_and_return_focus(page: Page):
    _open_panel(page)
    invite_button = page.locator("#business-team").get_by_role("link", name="Convidar profissional")
    invite = page.locator("#business-team-invite")

    invite_button.click()
    expect(invite).to_be_visible()
    assert invite.evaluate("el => el.matches(':modal')")
    expect(invite.get_by_label("E-mail")).to_be_focused()
    # Abrir a janela não muda o endereço nem recarrega.
    expect(page).to_have_url(re.compile(rf"{PANEL}$"))

    page.keyboard.press("Escape")
    expect(invite).to_be_hidden()
    expect(invite_button).to_be_focused()

    # Convite com e-mail sem perfil profissional: a mesma validação, e a
    # janela volta aberta com o erro.
    invite_button.click()
    invite.get_by_label("E-mail").fill(f"sem-perfil-{uuid.uuid4().hex[:6]}@example.com")
    with page.expect_navigation():
        invite.get_by_role("button", name=re.compile("Enviar|Convidar|Adicionar")).click()
    expect(invite).to_be_visible()
    expect(invite).to_contain_text("ainda não possui um perfil profissional IDDUN")
    invite.get_by_role("link", name="Cancelar").click()
    expect(invite).to_be_hidden()

    page.locator("#business-team").get_by_role("link", name="Gerenciar equipe").click()
    manage = page.locator("#business-team-manage")
    expect(manage).to_be_visible()
    expect(manage.get_by_role("heading", level=2)).to_contain_text("Equipe de Espaço QA Navegador")
    manage.get_by_role("link", name="Convidar profissional").click()
    expect(manage).to_be_hidden()
    expect(invite).to_be_visible()


def test_team_dialog_opens_from_the_server_without_javascript(browser, base_url):
    context = browser.new_context(java_script_enabled=False, base_url=base_url)
    page = context.new_page()
    try:
        page.goto("/login")
        page.locator('input[name="email"]').fill(E2E_PRO_EMAIL)
        page.locator('input[name="password"]').fill(E2E_PASSWORD)
        with page.expect_navigation():
            page.locator('button[type="submit"][data-submit]').click()
        page.goto(PANEL)
        expect(page.locator("#business-team-invite")).to_be_hidden()
        with page.expect_navigation():
            page.locator("#business-team").get_by_role("link", name="Convidar profissional").click()
        expect(page).to_have_url(re.compile(r"equipe=convidar#business-team$"))
        invite = page.locator("#business-team-invite")
        expect(invite).to_be_visible()
        with page.expect_navigation():
            invite.get_by_role("link", name="Cancelar").click()
        expect(page.locator("#business-team-invite")).to_be_hidden()
    finally:
        context.close()


def test_panel_is_readable_in_one_column_on_a_phone(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _open_panel(page)
    main = page.locator(".business-feed > .feed-main").bounding_box()
    rail = page.locator(".business-feed > .feed-rail").bounding_box()
    assert rail["y"] > main["y"] and main["width"] <= 390

    for name in ("Gerenciar equipe", "Convidar profissional"):
        box = page.locator("#business-team").get_by_role("link", name=name).bounding_box()
        assert box["height"] >= 44, (name, box)

    page.locator("#business-team").get_by_role("link", name="Convidar profissional").click()
    box = page.locator("#business-team-invite").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
    page.keyboard.press("Escape")
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0
    _readable(page)
