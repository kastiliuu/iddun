"""PR 5a do programa IDDUN 2.0 — Explorar no navegador (D-SOC-18).

- A busca do cabeçalho leva aos resultados unificados, com abas e contagens.
- Filtros ficam no endereço e continuam ao voltar de um resultado.
- Sem resultados, Limpar filtros mantém a busca.
- Página legível e sem rolagem lateral em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login

TEXT = ":is(a, p, span, strong, h1, h2, label, legend, summary, button)"


def _readable(page: Page):
    selector = f".explore {TEXT}"
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


def test_header_search_opens_unified_results(page: Page):
    _login(page, E2E_EMAIL)
    page.wait_for_load_state("load")  # o script do cabeçalho é defer
    field = page.locator("[data-feed-search-input]")
    field.fill("QA")
    see_all = page.locator(".feed-search-results__all")
    expect(see_all).to_have_text("Ver todos os resultados para “QA”")
    see_all.click()

    expect(page).to_have_url(re.compile(r"/explorar\?q=QA$"))
    tabs = page.get_by_role("navigation", name="Tipos de resultado")
    expect(tabs.locator('[aria-current="page"]')).to_contain_text("Todos")
    expect(page.locator(".explore-section h2").first).to_be_visible()

    tabs.get_by_role("link", name=re.compile(r"^Serviços")).click()
    expect(page).to_have_url(re.compile(r"/explorar\?q=QA&tipo=servicos$"))
    expect(tabs.locator('[aria-current="page"]')).to_contain_text("Serviços")
    expect(page.locator(".explore-card").first).to_contain_text("Coloração QA")


def test_filters_survive_opening_a_result(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/explorar?q=QA&tipo=servicos")
    page.locator('input[name="preco_max"]').fill("500")
    with page.expect_navigation():
        page.get_by_role("button", name="Aplicar filtros").click()
    expect(page).to_have_url(re.compile(r"preco_max=500"))

    page.locator(".explore-card").first.click()
    expect(page).to_have_url(re.compile(r"/experiencias/"))
    page.go_back()
    expect(page.locator('input[name="preco_max"]')).to_have_value("500")


def test_zero_results_offers_clear_filters(page: Page):
    page.goto("/explorar?q=QA&local=Lugar%20Inexistente")
    expect(page.get_by_role("heading", name="Nada encontrado com esta busca.")).to_be_visible()
    page.locator(".explore-empty").get_by_role("link", name="Limpar filtros").click()
    expect(page).to_have_url(re.compile(r"/explorar\?q=QA$"))
    expect(page.locator(".explore-card").first).to_be_visible()


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_explore_is_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_EMAIL)
    for path in ("/explorar?q=QA", "/explorar?q=QA&tipo=servicos", "/explorar?q=QA&local=Nenhum"):
        page.goto(path)
        _readable(page)
