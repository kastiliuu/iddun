"""PR 4 do onboarding — fechamento: todas as telas e os caminhos críticos.

Cada tela do cadastro Profissional e do Estabelecimento é medida no
Chromium a 390 px e a 1280 px, com o mesmo critério da V-04:
- texto >= 12 px e contraste AA (4,5:1; 3:1 para texto grande);
- nenhuma rolagem horizontal;
- um único h1 e, nas etapas, uma única etapa com aria-current="step";
- foco visível em quem recebe o Tab.

Caminhos críticos: Profissional e Estabelecimento até publicar, sair e
retomar pelo painel, outra conta sem acesso e página publicada intocada.
"""

import re
import uuid

from playwright.sync_api import Page, expect

from e2e.test_web_pro_onboarding import BIO, _continue, _register
from e2e.test_web_readable_text import CONTRAST, SMALL_TEXT

DESCRIPTION = "Espaço de coloração autoral, atendimento com hora marcada e sem pressa."
VIEWPORTS = ((390, 844), (1280, 900))

FOCUS_RING = """
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  // Rádios e caixas do cartão ficam transparentes: o anel fica no rótulo.
  const target = parseFloat(getComputedStyle(el).opacity) === 0 ? (el.closest('label') || el) : el;
  const style = getComputedStyle(target);
  const outline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
  return { tag: el.tagName, text: (el.innerText || el.value || '').trim().slice(0, 30),
           visible: outline || style.boxShadow !== 'none' };
}
"""


def _check_screen(page: Page, *, step: bool = True):
    """Mede a tela atual nos dois tamanhos e volta ao desktop."""
    for width, height in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        label = f"{page.url} @ {width}px"
        assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0, label
        assert page.evaluate(SMALL_TEXT) == [], label
        failing = [
            item for item in page.evaluate(CONTRAST, None)
            if item["ratio"] < (3 if item["large"] else 4.5)
        ]
        assert failing == [], (label, failing[:5])
        expect(page.locator("h1")).to_have_count(1)
        if step:
            expect(page.locator('.onb__segment[aria-current="step"]')).to_have_count(1)
            submit = page.locator(".onb__form .onb__submit").last
            box = submit.bounding_box()
            assert box is not None and box["height"] >= 44, label
    _check_focus(page)


def _check_focus(page: Page):
    """Os primeiros elementos alcançados pelo Tab mostram o foco."""
    page.locator("h1").click()
    for _ in range(6):
        page.keyboard.press("Tab")
        state = page.evaluate(FOCUS_RING)
        if state is not None:
            assert state["visible"], (page.url, state)


def _new_account(page: Page, name: str):
    _register(page, name=name)


def test_every_professional_screen_is_readable_and_reaches_publication(page: Page):
    _new_account(page, "Pro Fechamento")
    page.goto("/pro/onboarding")
    expect(page).to_have_url(re.compile(r"/pro/onboarding/nome$"))
    _check_screen(page)

    _continue(page, "cidade")
    _check_screen(page)
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    _continue(page, "especialidade")
    _check_screen(page)
    page.locator("#primary_specialty").fill("Colorista")
    page.locator('input[name="categories"][value="cabelo"]').check()
    _continue(page, "atendimento")
    _check_screen(page)
    page.locator(".onb__choice", has_text="Em espaço próprio").click()
    _continue(page, "apresentacao")
    _check_screen(page)
    page.locator("#bio").fill(BIO)
    _continue(page, "fotos")
    _check_screen(page)
    page.get_by_role("link", name="Fazer depois").click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/revisar$"))
    _check_screen(page)

    page.get_by_role("button", name="Publicar perfil").click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/concluido$"))
    _check_screen(page, step=False)

    # Publicado não volta ao cadastro.
    page.goto("/pro/onboarding/nome")
    expect(page).to_have_url(re.compile(r"/pro/painel$"))
    expect(page.get_by_text("Seu perfil já está publicado.", exact=False)).to_be_visible()


def test_every_business_screen_is_readable_and_reaches_publication(page: Page):
    _new_account(page, "Dona Fechamento")
    page.goto("/business/onboarding")
    expect(page).to_have_url(re.compile(r"/business/onboarding/novo$"))
    _check_screen(page)

    page.locator("#name").fill(f"Atelier Fechamento {uuid.uuid4().hex[:4]}")
    page.locator(".onb__choice", has_text="Salão de beleza").click()
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/business/onboarding/\d+/atendimento$"))
    draft_url = re.search(r"(/business/onboarding/\d+)/", page.url).group(1)
    _check_screen(page)

    page.locator(".onb__choice", has_text="No estabelecimento").click()
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/endereco$"))
    _check_screen(page)
    page.locator("#address_line1").fill("Rua das Flores, 120")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/funcionamento$"))
    _check_screen(page)
    page.locator(".onb__choice", has_text="Sob agendamento").click()
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/contato$"))
    _check_screen(page)
    page.locator("#description").fill(DESCRIPTION)
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/fotos$"))
    _check_screen(page)
    page.get_by_role("link", name="Fazer depois").click()
    expect(page).to_have_url(re.compile(r"/revisar$"))
    _check_screen(page)

    # Sair, e retomar pelo atalho do painel e de Minha conta (PR 4).
    page.get_by_role("link", name="Sair e continuar depois").click()
    page.goto("/minha-conta")
    page.get_by_role("link", name=re.compile(r"Continuar cadastro: Atelier Fechamento")).click()
    expect(page).to_have_url(re.compile(rf"{draft_url}/revisar$"))

    page.get_by_role("button", name="Publicar página").click()
    expect(page).to_have_url(re.compile(r"/concluido$"))
    _check_screen(page, step=False)

    # Publicada não volta ao cadastro nem muda pelo atalho antigo.
    page.goto(f"{draft_url}/contato")
    expect(page).to_have_url(re.compile(r"/business/[^/]+/painel$"))
    expect(page.get_by_text("Esta página já está publicada.", exact=False)).to_be_visible()


def test_business_chooser_lists_drafts_and_other_account_has_no_access(page: Page, browser):
    _new_account(page, "Dona Rascunhos")
    first_name = f"Studio Um {uuid.uuid4().hex[:4]}"
    page.goto("/business/onboarding/novo")
    page.locator("#name").fill(first_name)
    page.locator(".onb__choice", has_text="Barbearia").click()
    page.locator("#city").fill("Londrina")
    page.locator("#state").fill("PR")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/atendimento$"))
    draft_url = re.search(r"(/business/onboarding/\d+)/", page.url).group(1)

    page.goto("/business/onboarding")
    expect(page.get_by_role("link", name=re.compile(f"Continuar {first_name}"))).to_be_visible()
    _check_screen(page, step=False)

    other = browser.new_context(base_url=page.url.split("/business")[0])
    try:
        stranger = other.new_page()
        _register(stranger, name="Conta Estranha")
        for path in (draft_url, f"{draft_url}/contato", f"{draft_url}/revisar"):
            response = stranger.goto(path)
            assert response is not None and response.status == 404, path
    finally:
        other.close()
