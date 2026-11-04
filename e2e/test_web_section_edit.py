"""PR 4b do programa IDDUN 2.0 — edição por seção no navegador (D-SOC-15, 16).

- Salvar uma seção volta para ela, com aviso e foco, sem mexer nas outras.
- O dono vê na própria página o aviso e os atalhos Editar por seção.
- Editor e modo dono legíveis, sem rolagem lateral, em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login

BIO = "Colorista dedicada a loiros naturais, com diagnóstico do fio antes de qualquer química."

NEW_PARTS = ".profile-editor__index, .profile-owner-bar, .profile-edit-link, .profile-editor__alert"
TEXT = ":is(a, p, span, li, h2, strong)"


def _readable(page: Page):
    selector = ", ".join(f"{part.strip()} {TEXT}, {part.strip()}" for part in NEW_PARTS.split(","))
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


def test_saving_one_section_returns_to_it(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    about = page.locator("section#sobre")
    about.locator("#bio").fill(BIO)
    with page.expect_navigation():
        about.get_by_role("button", name="Salvar apresentação").click()

    expect(page).to_have_url(re.compile(r"/pro/perfil/editar#sobre$"))
    expect(page.get_by_text("Sobre: alterações salvas.")).to_be_visible()
    page.wait_for_function("document.activeElement && document.activeElement.id === 'sobre'")
    expect(page.locator("#bio")).to_have_value(BIO)
    # As outras seções continuam com o que estava salvo.
    expect(page.locator("#display_name")).to_have_value("Profissional QA Navegador")


def test_section_error_is_shown_inside_the_section(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    about = page.locator("section#sobre")
    about.locator("#bio").fill("curto")
    with page.expect_navigation():
        about.get_by_role("button", name="Salvar apresentação").click()

    expect(about.get_by_role("alert")).to_contain_text("Sobre você")
    expect(page.locator("section#identidade").get_by_role("alert")).to_have_count(0)
    expect(page.locator("#bio")).to_have_value("curto")
    assert page.evaluate("document.activeElement.id") == "bio"


def test_business_owner_sees_edit_shortcuts(page: Page):
    _login(page, E2E_PRO_EMAIL)  # dona do espaço semeado
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}/sobre")

    expect(page.get_by_text("Você está vendo a página da sua empresa como o público vê.")).to_be_visible()
    page.get_by_role("link", name="Editar horários").click()
    expect(page).to_have_url(re.compile(rf"/business/{E2E_BUSINESS_SLUG}/editar#funcionamento$"))

    hours = page.locator("section#funcionamento")
    hours.locator("#business_hours_mode").select_option("fixed_hours")
    hours.locator("#monday_start").fill("09:00")
    hours.locator("#monday_end").fill("18:00")
    with page.expect_navigation():
        hours.get_by_role("button", name="Salvar funcionamento").click()
    expect(page.get_by_text("Funcionamento: alterações salvas.")).to_be_visible()

    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}/sobre")
    expect(page.locator(".profile-hours")).to_contain_text("09:00–18:00")


def test_visitor_sees_no_edit_shortcuts(page: Page):
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}/sobre")
    expect(page.locator(".profile-owner-bar")).to_have_count(0)
    expect(page.locator(".profile-edit-link")).to_have_count(0)


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_editors_and_owner_mode_are_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_PRO_EMAIL)
    for path in ("/pro/perfil/editar", f"/business/{E2E_BUSINESS_SLUG}/editar",
                 f"/estabelecimentos/{E2E_BUSINESS_SLUG}", f"/estabelecimentos/{E2E_BUSINESS_SLUG}/sobre"):
        assert page.goto(path).status == 200, path
        page.evaluate("document.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-visible'))")
        page.wait_for_timeout(300)
        _readable(page)
