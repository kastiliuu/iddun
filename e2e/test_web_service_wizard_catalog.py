"""P-002 (Wizard A) e P-003 (Catálogo C) no navegador — V1 PR 2.

- O Wizard mostra uma etapa por vez, só avança com a etapa válida, guarda o
  que foi digitado ao voltar, mostra a imagem escolhida antes de enviar e
  salva um rascunho privado.
- Sem JavaScript, as cinco etapas aparecem em sequência e o envio funciona.
- O catálogo tem lista e painel lado a lado no desktop; no celular, lista →
  detalhe → janela de horário, com volta para a lista.
- Abrir horário acontece numa janela sob demanda, com foco e Esc.
"""

import re
import uuid
from io import BytesIO

from PIL import Image
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_PASSWORD, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login

TEXT = ":is(label, small, span, strong, button, a, p, h1, h2, h3, h4, dt, dd, li, legend)"


def _png():
    output = BytesIO()
    Image.new("RGB", (160, 90), (120, 80, 140)).save(output, format="PNG")
    return output.getvalue()


def _readable(page: Page, parts: str):
    selector = ", ".join(f"{part.strip()} {TEXT}" for part in parts.split(","))
    small = page.evaluate(
        """(selector) => [...document.querySelectorAll(selector)]
          .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
          .filter((el) => el.getBoundingClientRect().width > 0 && !el.closest('[hidden], .sr-only'))
          .map((el) => ({ text: el.innerText.trim().slice(0, 30), size: parseFloat(getComputedStyle(el).fontSize) }))
          .filter((item) => item.size < 12)""",
        selector,
    )
    assert small == [], small[:5]
    failing = [
        item for item in page.evaluate(CONTRAST, selector)
        if item["text"] and item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


def _visible_step(page: Page):
    return page.locator("[data-step]:visible")


def test_wizard_walks_five_steps_and_saves_a_private_draft(page: Page):
    page.set_viewport_size({"width": 1440, "height": 900})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/servicos/novo")
    title = f"Mechas QA {uuid.uuid4().hex[:6]}"

    expect(_visible_step(page)).to_have_count(1)
    expect(_visible_step(page)).to_have_attribute("data-step", "basico")
    expect(page.locator('[data-progress="basico"] a')).to_have_attribute("aria-current", "step")
    expect(page.get_by_role("button", name="Salvar rascunho")).to_be_hidden()
    _readable(page, ".service-wizard")

    # Sem nome, não avança.
    page.get_by_role("button", name="Continuar").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "basico")
    expect(page.get_by_label("Nome do serviço")).to_be_focused()

    page.get_by_label("Nome do serviço").fill(title)
    page.get_by_label("Categoria").select_option("cabelo")
    page.get_by_label("Descrição resumida").fill("Mechas com tonalização.")
    expect(page.locator(".service-wizard__preview-title")).to_have_text(title)
    page.get_by_role("button", name="Continuar").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "preco")
    expect(page.locator('[data-progress="basico"]')).to_have_class(re.compile("is-done"))

    # Preço IDDUN acima do regular é barrado antes de enviar.
    page.get_by_label("Preço regular (R$)").fill("300")
    page.get_by_label("Preço IDDUN (R$)").fill("320")
    page.get_by_label("Duração em minutos").fill("150")
    page.get_by_role("button", name="Continuar").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "preco")
    page.get_by_label("Preço IDDUN (R$)").fill("280")
    page.get_by_role("button", name="Continuar").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "local")
    expect(page.get_by_text("Salvar não abre horários.", exact=False)).to_be_visible()

    # Voltar preserva o que foi digitado.
    page.get_by_role("button", name="Voltar").click()
    expect(page.get_by_label("Preço IDDUN (R$)")).to_have_value("280")
    page.get_by_role("button", name="Continuar").click()
    page.get_by_role("button", name="Continuar").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "imagem")

    # Prévia local da imagem, com opção de remover a escolha.
    page.get_by_label("Imagem de capa do serviço").set_input_files(
        {"name": "capa.png", "mimeType": "image/png", "buffer": _png()}
    )
    expect(page.locator("[data-image-preview]")).to_be_visible()
    page.get_by_role("button", name="Remover imagem escolhida").click()
    expect(page.locator("[data-image-preview]")).to_be_hidden()
    expect(page.locator("[data-image-fallback]")).to_be_visible()
    page.get_by_role("button", name="Continuar").click()

    review = _visible_step(page)
    expect(review).to_have_attribute("data-step", "revisao")
    expect(review.locator('[data-review="title"]')).to_have_text(title)
    expect(review.locator('[data-review="price"]')).to_have_text("R$ 280,00")
    expect(review.locator('[data-review="regular_price"]')).to_have_text("R$ 300,00")
    expect(review.locator('[data-review="duration_minutes"]')).to_have_text("150 min")
    expect(review.locator('[data-review="image_file"]')).to_have_text("Sem imagem")

    # Editar a partir da revisão volta à etapa e mantém o resto.
    review.get_by_role("link", name="Editar nome").click()
    expect(_visible_step(page)).to_have_attribute("data-step", "basico")
    for _ in range(4):
        page.get_by_role("button", name="Continuar").click()
    expect(page.get_by_role("button", name="Salvar rascunho")).to_be_visible()
    _readable(page, ".service-wizard")

    with page.expect_navigation():
        page.get_by_role("button", name="Salvar rascunho").click()
    expect(page).to_have_url(re.compile(r"/pro/servicos$"))
    expect(page.locator(".flash-message")).to_contain_text("Rascunho do serviço criado")
    detail = page.locator("#servico-selecionado")
    expect(detail.get_by_role("heading", level=2)).to_have_text(title)
    expect(detail.locator(".pro-catalog-status")).to_have_text("Rascunho")
    expect(detail.get_by_role("button", name="Publicar serviço")).to_be_visible()
    expect(detail.get_by_role("link", name="Abrir horário", exact=True)).to_have_count(0)


def test_wizard_shows_every_step_without_javascript(browser, base_url):
    context = browser.new_context(java_script_enabled=False, base_url=base_url)
    page = context.new_page()
    try:
        page.goto("/login")
        page.locator('input[name="email"]').fill(E2E_PRO_EMAIL)
        page.locator('input[name="password"]').fill(E2E_PASSWORD)
        with page.expect_navigation():
            page.locator('button[type="submit"][data-submit]').click()
        page.goto("/pro/servicos/novo")
        expect(page.locator("[data-step]:visible")).to_have_count(5)
        expect(page.get_by_role("button", name="Continuar")).to_be_hidden()
        expect(page.get_by_role("button", name="Salvar rascunho")).to_be_visible()
    finally:
        context.close()


def test_catalog_is_list_and_panel_on_desktop_and_opens_slot_dialog(page: Page):
    page.set_viewport_size({"width": 1440, "height": 900})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/servicos")
    page.get_by_role("link", name=re.compile("Coloração QA")).first.click()
    expect(page).to_have_url(re.compile(r"/pro/servicos\?servico=\d+#servico-selecionado$"))

    index = page.locator(".pro-catalog-index").bounding_box()
    detail = page.locator(".pro-catalog-detail").bounding_box()
    assert index["x"] < detail["x"] and detail["width"] > index["width"]
    expect(page.locator(".pro-catalog-detail h2")).to_have_text("Coloração QA")
    expect(page.locator(".pro-catalog-detail")).to_contain_text("Espaço QA Navegador")
    # Só os formulários do selecionado; nada aberto até pedir.
    expect(page.locator("dialog[data-dialog]")).to_have_count(3)
    expect(page.locator("#slot-dialog-horario")).to_be_hidden()
    _readable(page, ".pro-catalog-index, .pro-catalog-detail")

    opener = page.get_by_role("link", name="Abrir horário", exact=True)
    opener.click()
    dialog = page.locator("#slot-dialog-horario")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_label("Data")).to_be_focused()
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    expect(opener).to_be_focused()

    page.get_by_role("link", name=re.compile("Abrir horários em lote")).click()
    expect(page.locator("#slot-dialog-lote")).to_be_visible()
    _readable(page, "#slot-dialog-lote")
    page.locator("#slot-dialog-lote").get_by_role("link", name="Cancelar").click()
    expect(page.locator("#slot-dialog-lote")).to_be_hidden()


def test_catalog_on_a_phone_goes_list_then_detail_then_back(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/servicos")
    expect(page.locator(".pro-catalog-index")).to_be_visible()
    expect(page.locator(".pro-catalog-detail")).to_be_hidden()
    _readable(page, ".pro-catalog-index")

    item = page.locator(".pro-catalog-item").filter(has_text="Coloração QA")
    assert item.bounding_box()["height"] >= 44
    with page.expect_navigation():
        item.click()
    expect(page.locator(".pro-catalog-index")).to_be_hidden()
    expect(page.locator(".pro-catalog-detail")).to_be_visible()
    _readable(page, ".pro-catalog-detail")
    for name in ("Abrir horário", "Todos os serviços"):
        box = page.get_by_role("link", name=name, exact=True).bounding_box()
        assert box["height"] >= 44, (name, box)

    with page.expect_navigation():
        page.get_by_role("link", name="Todos os serviços").click()
    expect(page.locator(".pro-catalog-index")).to_be_visible()
