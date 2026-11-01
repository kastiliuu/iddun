"""NV-07 — horários fixos no cadastro de Estabelecimento por etapas (Web).

O bloco de horários só aparece para "Horários fixos" e usa o seletor de
hora do navegador, legível no desktop e no celular.
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL
from e2e.test_web_business_wizard import start_business_draft
from e2e.test_web_platform_contrast import CONTRAST, _login


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_hours_panel_appears_only_for_fixed_hours(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_EMAIL)
    draft_id = start_business_draft(page, f"Studio Horas {uuid.uuid4().hex[:4]}")
    page.goto(f"/business/onboarding/{draft_id}/funcionamento")

    panel = page.locator("[data-hours-panel]")
    expect(panel).to_be_hidden()

    page.locator(".onb__choice", has_text="Horários fixos").click()
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

    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/contato$"))
    page.goto(f"/business/onboarding/{draft_id}/funcionamento")
    expect(page.locator("[data-hours-panel]").get_by_label("Abertura na segunda")).to_have_value("09:00")

    page.locator(".onb__choice", has_text="Sob agendamento").click()
    expect(panel).to_be_hidden()
