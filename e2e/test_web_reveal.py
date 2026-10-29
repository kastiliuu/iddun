"""V-01 — nenhum conteúdo fica invisível por causa da animação de entrada.

O `motion.js` revela `[data-reveal]` e `[data-reveal-stagger]` ao rolar.
A grade do Explorar no celular é mais alta do que cabe na tela, então um
limiar proporcional à altura do bloco nunca era atingido e os cards
ficavam com opacidade 0 (D-VIS-01: a galeria precisa estar visível).
"""

import pytest
from playwright.sync_api import Page

PAGES = [
    "/experiencias",
    "/profissionais",
    "/estabelecimentos",
    "/para-profissionais",
]

VIEWPORTS = [(375, 667), (390, 844), (1440, 900)]

HIDDEN = """
() => {
  const targets = [
    ...document.querySelectorAll('[data-reveal]'),
    ...[...document.querySelectorAll('[data-reveal-stagger]')]
      .flatMap((group) => [...group.children]),
  ];
  return targets
    .filter((el) => el.getBoundingClientRect().height > 0)
    .filter((el) => getComputedStyle(el).opacity !== '1')
    .map((el) => `${el.tagName.toLowerCase()}.${el.className}`.slice(0, 60));
}
"""


def _scroll_through(page: Page):
    """Rola como uma pessoa: passos de meia tela até o fim da página."""
    step = page.viewport_size["height"] // 2
    position = 0
    while position < page.evaluate("document.documentElement.scrollHeight"):
        position += step
        page.evaluate(f"window.scrollTo(0, {position})")
        page.wait_for_timeout(60)


def _hidden_after_settling(page: Page):
    try:
        page.wait_for_function(f"() => ({HIDDEN.strip()})().length === 0", timeout=3000)
    except Exception:  # noqa: BLE001 — a mensagem do assert mostra o que sobrou
        pass
    return page.evaluate(HIDDEN)


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: f"{v[0]}x{v[1]}")
@pytest.mark.parametrize("path", PAGES)
def test_scrolling_reveals_every_block(page: Page, path, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto(path)

    _scroll_through(page)

    hidden = _hidden_after_settling(page)
    assert hidden == [], f"{path} {viewport}: conteúdo invisível {hidden[:5]}"


def test_explore_cards_appear_on_a_small_phone(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("/experiencias")

    grid = page.locator(".catalog-grid[data-reveal-stagger]")
    grid.scroll_into_view_if_needed()
    page.evaluate("window.scrollBy(0, 200)")

    first_card = grid.locator(":scope > *").first
    page.wait_for_function(
        "(el) => getComputedStyle(el).opacity === '1'",
        arg=first_card.element_handle(),
        timeout=3000,
    )


@pytest.mark.parametrize("path", PAGES)
def test_reduced_motion_shows_everything_without_scrolling(page: Page, path):
    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(path)

    not_marked = page.evaluate(
        "() => [...document.querySelectorAll('[data-reveal],[data-reveal-stagger]')]"
        ".filter((el) => !el.classList.contains('is-visible')).length"
    )
    assert not_marked == 0
