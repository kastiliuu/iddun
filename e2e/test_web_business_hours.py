"""NV-07 — horários fixos no cadastro Business (Web).

O bloco de horários só aparece quando o funcionamento é "Horários fixos"
e usa o seletor de hora do navegador, legível no desktop e no celular.
"""

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_hours_panel_appears_only_for_fixed_hours(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_EMAIL)
    page.goto("/business/onboarding")
    page.evaluate(
        "() => document.querySelectorAll('[data-wizard-step]').forEach((s) => { s.hidden = false; })"
    )

    panel = page.locator("[data-hours-panel]")
    mode = page.locator('select[name="business_hours_mode"]')
    expect(panel).to_be_hidden()

    mode.select_option("fixed_hours")
    expect(panel).to_be_visible()
    expect(panel.get_by_label("Abertura na segunda")).to_have_attribute("type", "time")

    panel.get_by_label("Abertura na segunda").fill("09:00")
    panel.get_by_label("Fechamento na segunda").fill("18:00")
    expect(panel.get_by_label("Fechamento na segunda")).to_have_value("18:00")

    small = page.evaluate(
        "() => [...document.querySelectorAll('[data-hours-panel] span, [data-hours-panel] legend, [data-hours-panel] p')]"
        ".filter((el) => parseFloat(getComputedStyle(el).fontSize) < 12).length"
    )
    assert small == 0
    for item in page.evaluate(CONTRAST, "[data-hours-panel] span, [data-hours-panel] p"):
        assert item["ratio"] >= 4.5, item
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0

    mode.select_option("scheduled")
    expect(panel).to_be_hidden()
