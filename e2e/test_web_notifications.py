"""PR 6a do programa IDDUN 2.0 — central de notificações no navegador (D-SOC-22).

- Seguir a empresa avisa a dona: sino com contagem, aviso em Social com o
  nome da empresa; abrir leva à página e marca como lido.
- Marcar todas como lidas é explícito.
- Central legível e sem rolagem lateral em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_EMAIL, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login

TEXT = ":is(a, p, span, strong, small, h1, h2, label, button, time)"


def _readable(page: Page):
    selector = f".notifications {TEXT}"
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


def _follow_business(browser, base_url):
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    _login(page, E2E_EMAIL)
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}")
    follow = page.locator(".public-profile-hero__actions").get_by_role("button", name=re.compile("Seguir"))
    if follow.count():
        with page.expect_response(re.compile(r"/api/v1/graph/follows/")):
            follow.first.click()
    context.close()


def test_owner_is_notified_and_opens_the_notice(page: Page, browser, base_url):
    _follow_business(browser, base_url)

    _login(page, E2E_PRO_EMAIL)
    page.goto("/notificacoes?aba=social")
    notice = page.locator(".notification", has_text="Novo seguidor").first
    expect(notice).to_be_visible()
    expect(notice.locator(".notification__context")).to_have_text("Espaço QA Navegador")
    expect(notice.get_by_role("link", name=re.compile("Abrir como Espaço QA Navegador"))).to_be_visible()

    notice_id = notice.get_attribute("id")
    notice.locator(".notification__link").click()
    expect(page).to_have_url(re.compile(rf"/estabelecimentos/{E2E_BUSINESS_SLUG}$"))

    # Abrir marcou só este aviso como lido (outros testes podem ter criado mais).
    page.goto("/notificacoes?aba=social&nao_lidas=1")
    expect(page.locator(f"#{notice_id}")).to_have_count(0)
    page.goto("/notificacoes?aba=social")
    expect(page.locator(f"#{notice_id}")).not_to_have_class(re.compile("is-unread"))


def test_mark_all_is_explicit(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto("/notificacoes")
    button = page.get_by_role("button", name="Marcar todas como lidas")
    if button.count():
        with page.expect_navigation():
            button.click()
        expect(page.get_by_text("Todas as notificações foram marcadas como lidas.")).to_be_visible()
    expect(page.locator(".notification.is-unread")).to_have_count(0)


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_center_is_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_PRO_EMAIL)
    for path in ("/notificacoes", "/notificacoes?aba=social", "/notificacoes?nao_lidas=1"):
        page.goto(path)
        _readable(page)
