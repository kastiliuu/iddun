"""PR-2 (BUG-015 / BUG-017) — assistente Business no navegador.

- "Criar página da empresa" só aparece na última etapa;
- erros em português ao lado do campo, sem balão nativo;
- Enter numa etapa inicial não envia o formulário incompleto: abre a etapa
  com o primeiro problema;
- a empresa é criada sem logo (DEC-ID-101) e aparece com iniciais.
"""

import re

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL, E2E_PASSWORD


def _login(page: Page):
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()
    expect(page).to_have_url(re.compile(r"/feed(?:\?.*)?$"))


def _step(page: Page, number: int):
    return page.locator(f'[data-wizard-step="{number}"]')


def test_business_wizard_validates_in_portuguese_and_creates_without_logo(page: Page):
    _login(page)
    page.goto("/business/onboarding")

    submit = page.locator("[data-wizard-submit]")
    next_button = page.locator("[data-wizard-next]")
    expect(submit).to_be_hidden()

    # Etapa 1 sem nome: mensagem junto ao campo, sem avançar.
    next_button.click()
    expect(_step(page, 1)).to_be_visible()
    expect(page.locator("#name-client-error")).to_have_text("Preencha este campo.")
    expect(page.locator("#name")).to_have_attribute("aria-invalid", "true")

    page.locator("#name").fill("Studio Ensaio")
    expect(page.locator("#name-client-error")).to_have_count(0)

    # Enter com as etapas seguintes vazias não envia: abre a etapa 2.
    page.locator("#name").press("Enter")
    expect(_step(page, 2)).to_be_visible()
    expect(page.locator("#description-client-error")).to_have_text("Preencha este campo.")
    expect(page).to_have_url(re.compile(r"/business/onboarding$"))

    page.locator("#description").fill("Curta.")
    next_button.click()
    expect(page.locator("#description-client-error")).to_contain_text(
        "Use pelo menos 40 caracteres"
    )
    page.locator("#description").fill(
        "Um espaço dedicado a coloração autoral e atendimento sem pressa."
    )
    next_button.click()

    expect(_step(page, 3)).to_be_visible()
    page.locator("#address_line1").fill("Rua Teste, 100")
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    next_button.click()

    expect(_step(page, 4)).to_be_visible()
    expect(submit).to_be_hidden()
    next_button.click()

    expect(_step(page, 5)).to_be_visible()
    expect(submit).to_be_visible()
    submit.click()

    expect(page).to_have_url(re.compile(r"/business/[^/]+/painel$"))
    expect(page.locator(".platform-dashboard-avatar .ds-avatar-initials")).to_have_text("SE")
