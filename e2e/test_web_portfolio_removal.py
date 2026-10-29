"""V-03 (BUG-005) — remover trabalho do portfólio e imagem da galeria.

- Pede confirmação; cancelar não remove nada (FE-DEC-046).
- Confirmar volta para a própria seção, visível e com foco, com a contagem
  atualizada e o aviso de sucesso (FE-DEC-042).
- Botão de remover com área de toque de 44 px e rótulo por item.
"""

import re

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login

IN_VIEW = """
(id) => {
  const rect = document.getElementById(id).getBoundingClientRect();
  return rect.top >= 0 && rect.top < window.innerHeight / 2;
}
"""


def _remove_buttons(page: Page, section: str):
    return page.locator(f"#{section} .platform-manage-gallery__item button")


def test_pro_removal_confirms_and_returns_to_portfolio(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    buttons = _remove_buttons(page, "portfolio")
    expect(buttons).to_have_count(2)
    for button in buttons.all():
        box = button.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44
    expect(buttons.first).to_have_attribute("aria-label", "Remover trabalho 1 de 2")

    # Cancelar a confirmação não remove nada.
    page.once("dialog", lambda dialog: dialog.dismiss())
    buttons.first.click()
    page.wait_for_timeout(300)
    expect(page).to_have_url(re.compile(r"/pro/perfil/editar$"))
    expect(buttons).to_have_count(2)

    page.once("dialog", lambda dialog: dialog.accept())
    with page.expect_navigation():
        buttons.first.click()

    expect(page).to_have_url(re.compile(r"/pro/perfil/editar#portfolio$"))
    expect(page.locator("#portfolio-title")).to_have_text(re.compile(r"^\s*1 trabalho\s*$"))
    expect(page.get_by_text("Imagem removida do portfólio.")).to_be_visible()
    assert page.evaluate("document.activeElement.id") == "portfolio"
    # A rolagem até a âncora é suave (scroll-behavior: smooth).
    page.wait_for_function(IN_VIEW, arg="portfolio", timeout=3000)


def test_business_removal_returns_to_gallery_with_empty_state(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/editar")

    buttons = _remove_buttons(page, "galeria")
    expect(buttons).to_have_count(1)
    expect(buttons.first).to_have_attribute("aria-label", "Remover imagem 1 de 1")

    page.once("dialog", lambda dialog: dialog.accept())
    with page.expect_navigation():
        buttons.first.click()

    expect(page).to_have_url(re.compile(rf"/business/{E2E_BUSINESS_SLUG}/editar#galeria$"))
    expect(page.locator("#galeria")).to_contain_text("Nenhuma imagem na galeria ainda")
    assert page.evaluate("document.activeElement.id") == "galeria"
    page.wait_for_function(IN_VIEW, arg="galeria", timeout=3000)
