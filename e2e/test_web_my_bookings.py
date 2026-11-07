"""UX-BOOKINGS-001 — Minhas reservas em linhas recolhidas.

- Cada reserva começa fechada, com chevron à direita, e abre por clique ou
  teclado (details/summary nativo).
- Fechada, mostra data, serviço, quem atende, status, preço e código;
  pendências aparecem sem abrir.
- Aberta, mantém todas as ações atuais.
- Âncoras e formulários reabrem a mesma reserva e põem o foco nela.
- Legível e sem rolagem lateral em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_PASSWORD, E2E_TYPO_CLIENT_EMAIL
from e2e.test_web_platform_contrast import CONTRAST

ROW = ".booking-row"


def _login(page: Page):
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_TYPO_CLIENT_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()


def _row(page: Page):
    return page.locator(ROW, has_text="Escova Tipografia").first


def _readable(page: Page):
    selector = ".my-bookings-list :is(a, p, span, strong, small, h3, h4, dt, dd, label, button, time, li)"
    failing = [
        item for item in page.evaluate(CONTRAST, selector)
        if item["text"] and item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]
    small = page.evaluate(
        """(s) => [...document.querySelectorAll(s)]
          .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
          .filter((el) => el.getBoundingClientRect().width > 0)
          .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 12)
          .map((el) => el.textContent.trim().slice(0, 30))""",
        selector,
    )
    assert small == [], small
    targets = page.evaluate(
        """() => [...document.querySelectorAll(
            '.my-bookings-list summary, .my-bookings-list button, .my-bookings-list a,'
            + ' .my-bookings-list select, .my-bookings-list input:not([type=hidden]), .my-bookings-list textarea')]
          .filter((el) => el.getBoundingClientRect().width > 0)
          .filter((el) => el.getBoundingClientRect().height < 44)
          .map((el) => (el.textContent || el.name || '').trim().slice(0, 30))"""
    )
    assert targets == [], targets
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


@pytest.mark.parametrize("viewport", [(1280, 900), (390, 844)], ids=["desktop", "mobile"])
def test_rows_start_closed_and_open_with_chevron(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page)
    page.goto("/minhas-reservas")

    row = _row(page)
    details = row.locator("details")
    summary = row.locator("summary")
    expect(details).not_to_have_attribute("open", re.compile(".*"))
    # Fechada: tudo o que identifica a reserva, sem abrir.
    for text in ("16:30", "Escova Tipografia", "Pro Tipografia", "Confirmada", "R$ 150,00", "Reserva #"):
        expect(summary).to_contain_text(text)
    expect(row.locator(".booking-row__toggle")).to_be_visible()
    expect(row.locator(".booking-detail__content")).to_be_hidden()
    assert row.evaluate("(el) => Math.round(el.getBoundingClientRect().width)") >= viewport[0] - 48

    summary.click()
    expect(details).to_have_attribute("open", "")
    angle = row.locator(".booking-row__toggle .icon").evaluate("(el) => getComputedStyle(el).transform")
    assert angle != "none"
    # Aberta: as ações de sempre continuam lá.
    panel = row.locator(".booking-detail__content")
    expect(panel.get_by_role("link", name=re.compile("Adicionar ao calendário"))).to_be_visible()
    expect(panel.get_by_role("link", name=re.compile("Compartilhar reserva"))).to_be_visible()
    expect(panel.get_by_role("button", name="Solicitar reagendamento")).to_be_visible()
    expect(panel.get_by_role("button", name="Solicitar cancelamento")).to_be_visible()
    expect(panel.get_by_role("heading", name="Histórico de eventos")).to_be_visible()
    _readable(page)


def test_keyboard_toggles_the_row(page: Page):
    _login(page)
    page.goto("/minhas-reservas")
    row = _row(page)
    row.locator("summary").focus()
    page.keyboard.press("Enter")
    expect(row.locator("details")).to_have_attribute("open", "")
    page.keyboard.press("Space")
    expect(row.locator("details")).not_to_have_attribute("open", re.compile(".*"))


def test_anchor_from_notifications_opens_the_booking(page: Page):
    _login(page)
    page.goto("/minhas-reservas")
    booking_id = _row(page).locator("details").get_attribute("data-booking-id")
    page.goto(f"/minhas-reservas#booking-title-{booking_id}")
    row = _row(page)
    expect(row.locator("details")).to_have_attribute("open", "")
    expect(row.locator("summary")).to_be_focused()


def test_form_post_reopens_the_same_booking_and_flags_it(page: Page):
    _login(page)
    page.goto("/minhas-reservas")
    row = _row(page)
    row.locator("summary").click()
    row.get_by_label("Motivo (opcional)").last.fill("Teste de navegador")
    with page.expect_navigation():
        row.get_by_role("button", name="Solicitar cancelamento").click()

    row = _row(page)
    expect(row.locator("details")).to_have_attribute("open", "")
    expect(row.locator("summary")).to_be_focused()
    flash = page.locator("[data-flash-message]").first
    expect(flash).to_contain_text("Solicitação enviada")
    expect(row.locator("summary")).to_have_attribute("aria-describedby", flash.get_attribute("id"))

    # Fechada, a pendência continua visível.
    row.locator("summary").click()
    expect(row.locator(".booking-row__flag")).to_contain_text("Cancelamento solicitado")
    expect(row).to_have_class(re.compile("booking-row--attention"))

    # Desfaz para não mudar os dados das outras jornadas.
    row.locator("summary").click()
    with page.expect_navigation():
        row.get_by_role("button", name="Retirar solicitação").click()
    row = _row(page)
    expect(row.locator(".booking-row__flag")).to_have_count(0)
