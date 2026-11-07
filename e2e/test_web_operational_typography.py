"""DS-TYPO-001 — dados operacionais em Inter com algarismos tabulares.

Horários, datas, preços, métricas e números deixam a Playfair Display
(FE-DEC-003/012, D-VIS-01). A Playfair continua nos títulos editoriais.
O teste lê o estilo calculado no navegador, em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import (
    E2E_BUSINESS_SLUG,
    E2E_PASSWORD,
    E2E_PRO_EMAIL,
    E2E_TYPO_ADMIN_EMAIL,
    E2E_TYPO_CLIENT_EMAIL,
    E2E_TYPO_SERVICE_SLUG,
)
from e2e.test_web_platform_contrast import CONTRAST

# Tamanhos dos tokens em px (raiz de 16 px).
TEXT_2XL = 28.8          # --text-2xl
HEADING_MD = 24          # --ds-type-heading-md
HEADING_SM = 20          # --ds-type-heading-sm
BODY = 16                # --ds-type-body

STYLE = """(selector) => [...document.querySelectorAll(selector)]
  .filter((el) => el.getBoundingClientRect().width > 0)
  .map((el) => {
    const cs = getComputedStyle(el);
    return {
      text: el.innerText.trim(),
      family: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
      numeric: cs.fontVariantNumeric,
      weight: cs.fontWeight,
      size: parseFloat(cs.fontSize),
    };
  })"""


def _login(page: Page, email: str):
    page.goto("/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()


def _reveal(page: Page):
    page.evaluate(
        "() => document.querySelectorAll('[data-reveal],[data-reveal-stagger]')"
        ".forEach((el) => el.classList.add('is-visible'))"
    )


def _assert_data(page: Page, selector: str, size: float, text: str | None = None, tabular: bool = True):
    items = page.evaluate(STYLE, selector)
    assert items, f"nenhum elemento visível para {selector}"
    for item in items:
        assert item["family"] == "Inter", (selector, item)
        if tabular:
            assert item["numeric"] == "tabular-nums", (selector, item)
        assert item["weight"] == "600", (selector, item)
        assert item["size"] == pytest.approx(size, abs=0.1), (selector, item)
    if text is not None:
        assert any(text in item["text"] for item in items), (selector, items)
    failing = [
        item for item in page.evaluate(CONTRAST, selector)
        if item["text"] and item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing


def _no_side_scroll(page: Page):
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


VIEWPORTS = pytest.mark.parametrize("viewport", [(1280, 900), (390, 844)], ids=["desktop", "mobile"])


@VIEWPORTS
def test_client_booking_time_and_price(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_TYPO_CLIENT_EMAIL)
    page.goto("/minhas-reservas")
    _reveal(page)
    # UX-BOOKINGS-001: a reserva é uma linha; horário 20 px e preço 16 px.
    _assert_data(page, ".booking-row__when strong", HEADING_SM, "16:30")
    _assert_data(page, ".booking-row__money strong", BODY, "R$ 150,00")
    # Na linha, o serviço é dado (Inter); a Playfair fica no título da página.
    _assert_data(page, ".booking-row__title", BODY, "Escova Tipografia", tabular=False)
    expect(page.locator(".my-bookings-hero h1")).to_have_css("font-family", re.compile(r"^\"?Playfair Display"))
    _no_side_scroll(page)


@VIEWPORTS
def test_service_price_and_calendar_days(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto(f"/experiencias/{E2E_TYPO_SERVICE_SLUG}")
    _reveal(page)
    _assert_data(page, ".experience-detail-price strong", TEXT_2XL, "R$ 150,00")
    _assert_data(page, ".slot-date-tab strong", HEADING_SM)
    if viewport[0] >= 1024:
        _assert_data(page, ".experience-booking-card__price strong", HEADING_MD, "R$ 150,00")
    else:
        _assert_data(page, ".experience-mobile-cta strong", HEADING_SM, "R$ 150,00")
    _no_side_scroll(page)


@VIEWPORTS
def test_catalog_price_and_home_numbers(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/experiencias")
    _reveal(page)
    _assert_data(page, ".catalog-card__price:not(.catalog-featured__price) > strong", HEADING_MD)
    # O destaque do catálogo mantém o tamanho maior, também em Inter tabular.
    featured = page.evaluate(STYLE, ".catalog-featured__price > strong")
    assert all(i["family"] == "Inter" and i["numeric"] == "tabular-nums" for i in featured), featured
    page.goto("/")
    _reveal(page)
    items = page.evaluate(STYLE, ".landing-stats strong")
    assert items and all(i["family"] == "Inter" and i["numeric"] == "tabular-nums" for i in items), items
    _no_side_scroll(page)


@VIEWPORTS
def test_admin_booking_time(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_TYPO_ADMIN_EMAIL)
    page.goto("/admin/reservas")
    _assert_data(page, ".admin-booking-card__date strong", TEXT_2XL, "16:30")
    page.goto("/admin/oportunidades")
    _assert_data(page, ".admin-opportunity-card__time strong", TEXT_2XL, "16:30")


def test_business_metrics_and_indicators(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/painel")
    _reveal(page)
    _assert_data(page, ".platform-metric-grid strong", TEXT_2XL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/indicadores")
    _reveal(page)
    _assert_data(page, ".platform-panel .platform-field > h3", HEADING_MD)
    # O título do painel segue editorial.
    expect(page.locator(".platform-panel__head h2").first).to_have_css(
        "font-family", re.compile(r"^\"?Playfair Display")
    )


def test_account_counts(page: Page):
    _login(page, E2E_TYPO_CLIENT_EMAIL)
    page.goto("/minha-conta")
    _reveal(page)
    _assert_data(page, ".account-activity-card__value", HEADING_MD)
    _assert_data(page, ".account-completion-card__top > strong", TEXT_2XL)
