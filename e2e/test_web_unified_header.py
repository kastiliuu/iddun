"""DS-V1-01-D01 — mesmo contrato de cabeçalho em Cliente, Pro e Business.

- Fundo preto nas três áreas logadas, mesmo com a página clara.
- Sino de notificações com as não lidas reais e menu Eu com a identidade
  da pessoa nas três áreas; no Pro eles não existiam.
- Os ícones de Favoritos e Notificações continuam visíveis entre 901 e
  1240 px (antes sumiam: a regra que escondia o rótulo escondia o ícone).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login

AREAS = [
    ("/feed", "header.feed-header"),
    (f"/business/{E2E_BUSINESS_SLUG}/painel", "header.feed-header"),
    ("/pro/painel", "header.pro-header"),
]


def _luminance(color):
    red, green, blue = (int(value) for value in re.findall(r"\d+", color)[:3])
    return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255


@pytest.mark.parametrize("path, header", AREAS)
@pytest.mark.parametrize("width", [390, 1100, 1440])
def test_header_is_black_with_bell_and_account_in_every_area(page: Page, path, header, width):
    page.set_viewport_size({"width": width, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    page.goto(path)
    bar = page.locator(header)
    expect(bar).to_be_visible()
    assert _luminance(bar.evaluate("el => getComputedStyle(el).backgroundColor")) < 0.08

    bell = bar.get_by_role("link", name=re.compile(r"^Notificações")).or_(
        bar.get_by_role("button", name=re.compile(r"^Notificações"))
    ).locator("visible=true").first
    expect(bell).to_be_visible()
    icon = bell.locator("svg").first.bounding_box()
    assert icon and icon["width"] >= 16 and icon["height"] >= 16, icon
    box = bell.bounding_box()
    assert box["width"] >= 40 and box["height"] >= 40, box

    account = bar.get_by_role("button", name=re.compile(r"^Eu: conta")).locator("visible=true").first
    expect(account).to_be_visible()
    account.click()
    menu = page.locator(".feed-account-menu").locator("visible=true").first
    # Uma identidade pessoal só, com o contexto em que a pessoa está.
    expect(menu).to_contain_text("Profissional QA Navegador")
    expect(menu).to_contain_text("Conta pessoal")
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


def test_all_header_icons_stay_visible_between_tablet_and_desktop(page: Page):
    page.set_viewport_size({"width": 1100, "height": 800})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/feed")
    widths = page.evaluate(
        """() => [...document.querySelectorAll('.feed-header__nav-item')]
          .map((el) => [el.getAttribute('aria-label') || el.textContent.trim(),
                        Math.round(el.querySelector('svg').getBoundingClientRect().width)])"""
    )
    assert len(widths) == 5 and all(width >= 16 for _, width in widths), widths
