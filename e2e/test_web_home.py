"""Home nova (D-HOME-04): topo claro com busca que abre o Explorar.

A busca funciona sem JavaScript (formulário GET com os filtros que o
Explorar já aceita) e o menu do celular é um <details>, sem script.
"""

import re

import pytest
from playwright.sync_api import Browser, Page, expect


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_home_search_opens_discovery(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/")

    search = page.get_by_role("search", name="Buscar serviços no IDDUN")
    search.get_by_placeholder("Serviço, profissional ou estilo").fill("Coloração")
    search.get_by_placeholder("Bairro ou cidade").fill("Curitiba")
    with page.expect_navigation():
        search.get_by_role("button", name="Buscar").click()

    expect(page).to_have_url(re.compile(r"/experiencias\?q=Colora%C3%A7%C3%A3o&bairro=Curitiba$"))


def test_home_search_and_menu_work_without_javascript(browser: Browser, base_url):
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844}, base_url=base_url)
    page = context.new_page()
    page.goto("/")

    page.locator(".landing-mobile-menu summary").click()
    expect(page.get_by_role("navigation", name="Menu mobile").get_by_role("link", name="Explorar")).to_be_visible()

    page.get_by_placeholder("Serviço, profissional ou estilo").fill("Corte")
    with page.expect_navigation():
        page.get_by_role("button", name="Buscar").click()
    expect(page).to_have_url(re.compile(r"/experiencias\?q=Corte&bairro=$"))
    context.close()


def test_category_shortcuts_lead_to_discovery(page: Page):
    page.goto("/")
    page.get_by_role("navigation", name="Explorar por categoria").get_by_role("link", name="Unhas").click()
    expect(page).to_have_url(re.compile(r"/experiencias\?categoria=unhas$"))
