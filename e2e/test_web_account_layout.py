"""BUG-UI-001 — /minha-conta sem rolagem lateral (FE-DEC-011/020, Notion 89).

Até 760 px, os cards de atividade formam um carrossel com rolagem própria
(intencional). Ele não pode alargar a página: só o carrossel rola.
Em 768 e 1280 px a grade tem 3 colunas e nada rola.
"""

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_PASSWORD, E2E_TYPO_CLIENT_EMAIL
from e2e.test_web_platform_contrast import CONTRAST

GRID = ".account-activity-grid"
CARDS = ".account-activity-card"

# Elementos fora da tela que não estão recortados nem dentro de um contêiner
# de rolagem interna (decorações recortadas pelo pai não alargam a página).
LEAKS = r"""() => {
  const vw = document.documentElement.clientWidth;
  const scrolls = (el) => /auto|scroll|hidden|clip/.test(getComputedStyle(el).overflowX);
  return [...document.querySelectorAll('body *')]
    .filter((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || (r.right <= vw + 0.5 && r.left >= -0.5)) return false;
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        if (scrolls(p)) return false;
      }
      return getComputedStyle(el).position !== 'fixed';
    })
    .map((el) => el.tagName.toLowerCase() + '.' + [...el.classList].join('.'))
    .slice(0, 5);
}"""


def _open_account(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 844})
    # Sem animação de entrada: as medidas não dependem do tempo.
    page.emulate_media(reduced_motion="reduce")
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_TYPO_CLIENT_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()
    page.goto("/minha-conta")
    page.evaluate(
        "() => document.querySelectorAll('[data-reveal],[data-reveal-stagger]')"
        ".forEach((el) => el.classList.add('is-visible'))"
    )
    # Espera a animação de entrada terminar antes de medir contraste.
    page.wait_for_function(
        "() => [...document.querySelectorAll('.account-activity, .account-activity-card')]"
        ".every((el) => getComputedStyle(el).opacity === '1')"
    )


@pytest.mark.parametrize("width", [320, 360, 390, 768, 1280])
def test_account_page_never_scrolls_sideways(page: Page, width):
    _open_account(page, width)
    assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0
    assert page.evaluate(LEAKS) == []

    grid = page.locator(GRID)
    cards = page.locator(CARDS)
    expect(cards).to_have_count(3)
    for name in ("Experiências", "Favoritos", "Reservas"):
        expect(grid.get_by_role("link", name=name)).to_have_count(1)

    sizes = grid.evaluate("(el) => ({client: el.clientWidth, scroll: el.scrollWidth})")
    panel = page.locator(".account-activity").evaluate("(el) => el.getBoundingClientRect().width")
    assert panel <= width
    if width <= 760:
        # Carrossel: rola por dentro e cabe na tela.
        assert sizes["scroll"] > sizes["client"], sizes
        assert sizes["client"] <= width
    else:
        # Grade de 3 colunas, sem rolagem interna.
        assert sizes["scroll"] <= sizes["client"], sizes
        columns = grid.evaluate("(el) => getComputedStyle(el).gridTemplateColumns.split(' ').length")
        assert columns == 3

    # Toque: cada card é um alvo grande.
    for box in cards.evaluate_all("(els) => els.map((el) => el.getBoundingClientRect().toJSON())"):
        assert box["width"] >= 44 and box["height"] >= 44, box

    # Contraste AA dos textos do painel.
    failing = [
        item for item in page.evaluate(CONTRAST, ".account-activity :is(span, strong, small, h2, p, a)")
        if item["text"] and item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing


@pytest.mark.parametrize("width", [320, 390])
def test_keyboard_reaches_every_activity_card(page: Page, width):
    _open_account(page, width)
    last = page.locator(CARDS).last
    last.focus()
    expect(last).to_be_focused()
    # O foco traz o último card para dentro da área visível do carrossel.
    inside = page.evaluate(
        """() => {
          const grid = document.querySelector('.account-activity-grid').getBoundingClientRect();
          const card = [...document.querySelectorAll('.account-activity-card')].pop().getBoundingClientRect();
          return card.left >= grid.left - 1 && card.right <= grid.right + 1;
        }"""
    )
    assert inside
    outline = last.evaluate("(el) => getComputedStyle(el).outlineStyle")
    assert outline != "none"
    assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0
