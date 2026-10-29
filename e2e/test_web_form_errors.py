"""V-02a — o erro de formulário é o mesmo em toda a Web e é legível.

Mede no navegador: contraste AA (4,5:1) e texto de pelo menos 12 px na
mensagem de erro, em superfície clara (Pro, Business) e escura (cadastro);
o formulário de experiência não usa o balão nativo e leva o foco ao
primeiro campo com erro.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login

NATIVE_SUBMIT = "(selector) => HTMLFormElement.prototype.submit.call(document.querySelector(selector).form)"


def _assert_readable_error(page: Page, selector: str):
    expect(page.locator(selector).first).to_be_visible()
    measured = page.evaluate(CONTRAST, f"{selector} span")
    assert measured, f"nenhuma mensagem em {selector}"
    for item in measured:
        assert item["ratio"] >= 4.5, f"{selector}: {item}"
    size = page.evaluate(
        "(s) => parseFloat(getComputedStyle(document.querySelector(s)).fontSize)", selector
    )
    assert size >= 12, f"{selector}: {size}px"
    assert page.locator(f"{selector} svg.ds-field-errors__icon").count() >= 1
    assert "!" not in page.locator(selector).first.inner_text()


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_experience_form_reports_errors_next_to_fields(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    form = page.locator('form[action$="/experiencia-profissional/adicionar"]')
    form.locator("#role_title").fill("Colorista")
    with page.expect_navigation():
        form.get_by_role("button", name="Adicionar experiência").click()

    expect(page).to_have_url(re.compile(r"/experiencia-profissional/adicionar$"))
    _assert_readable_error(page, "#company_name-errors")
    expect(page.locator("#started_at-errors")).to_be_visible()
    expect(page.locator("#role_title")).to_have_value("Colorista")
    assert page.evaluate("document.activeElement.id") == "company_name"


def test_business_server_errors_are_readable(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/business/onboarding")
    page.locator("#name").fill("Studio Pressa")
    with page.expect_navigation():
        page.evaluate(NATIVE_SUBMIT, "#name")

    expect(page.locator("#description")).to_have_attribute("aria-invalid", "true")
    expect(page.locator("#description")).to_have_attribute("aria-describedby", re.compile("description-errors"))
    _assert_readable_error(page, "#description-errors")


def test_business_wizard_client_error_matches_server_error(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/business/onboarding")
    page.locator("#name").fill("")
    page.get_by_role("button", name="Continuar").click()

    _assert_readable_error(page, "#name-client-error")


def test_signup_errors_on_dark_surface_stay_readable(page: Page):
    page.goto("/cadastro")
    page.locator("#email").fill("nao-e-email")
    with page.expect_navigation():
        page.evaluate(NATIVE_SUBMIT, "#email")

    _assert_readable_error(page, "#email-errors")
    expect(page.locator("#email-errors")).to_contain_text("Informe um e-mail válido.")


def test_mode_choice_error_on_dark_entry_is_readable(page: Page):
    _login(page, E2E_EMAIL)
    page.goto("/pro/comecar")
    with page.expect_navigation():
        page.evaluate(
            "() => HTMLFormElement.prototype.submit.call(document.querySelector('form[data-mode-form]'))"
        )

    _assert_readable_error(page, "#mode-errors")
