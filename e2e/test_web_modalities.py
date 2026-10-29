"""V-02b (BUG-001) — "Onde você atende?" com caixas de seleção.

Sem Ctrl+clique: cada modalidade é uma caixa de seleção com área de toque
de pelo menos 44 px, acionável por clique e por teclado. No assistente Pro,
avançar sem escolher nenhuma mostra a mensagem junto ao grupo, que some
assim que uma opção é marcada.
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_PASSWORD, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login

MESSAGE = "Selecione pelo menos uma modalidade de atendimento."


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_edit_uses_touchable_checkboxes(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    assert page.locator('select[name="attendance_modalities"]').count() == 0
    group = page.get_by_role("group", name=re.compile("Onde você atende"))
    options = group.get_by_role("checkbox")
    expect(options).to_have_count(3)

    for box in page.locator(".platform-choice").all():
        assert box.bounding_box()["height"] >= 44

    own_space = group.get_by_role("checkbox", name="Em espaço próprio")
    page.locator(".platform-choice", has_text="Em espaço próprio").click()
    expect(own_space).to_be_checked()

    client_place = group.get_by_role("checkbox", name="No endereço do cliente")
    client_place.focus()
    page.keyboard.press("Space")
    expect(client_place).to_be_checked()
    expect(own_space).to_be_checked()


def test_wizard_requires_one_modality_next_to_the_group(page: Page):
    page.goto("/cadastro")
    page.locator("#name").fill("Pro Modalidade Navegador")
    page.locator("#email").fill(f"qa-modalidade-{uuid.uuid4().hex[:8]}@example.com")
    page.locator("#password").fill(E2E_PASSWORD)
    page.locator("#confirm_password").fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.get_by_role("button", name="Criar minha conta").click()

    page.goto("/pro/onboarding")
    next_button = page.locator("[data-wizard-next]")
    page.locator("#display_name").fill("Pro Modalidade Navegador")
    next_button.click()
    page.locator("#primary_specialty").fill("Colorista")
    next_button.click()

    error = page.locator("#attendance_modalities-0-client-error")
    expect(error).to_have_text(MESSAGE)
    expect(page.locator('[data-wizard-step="2"]')).to_be_visible()

    page.locator(".platform-choice", has_text="No endereço do cliente").click()
    expect(error).to_have_count(0)
    next_button.click()
    expect(page.locator('[data-wizard-step="3"]')).to_be_visible()
