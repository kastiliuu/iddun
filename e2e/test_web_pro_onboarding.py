"""PR 2 do onboarding — cadastro Profissional por etapas no navegador.

Uma pergunta por tela, salvo no servidor a cada "Continuar", retomada depois
de sair, revisão com pendências e publicação explícita (F1).
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_PASSWORD
from e2e.test_web_readable_text import CONTRAST, SMALL_TEXT

BIO = "Trabalho com unhas naturais e alongamento em gel há seis anos, com cuidado."


def _register(page: Page, name="Pro Etapas Navegador"):
    page.goto("/cadastro")
    page.locator("#name").fill(name)
    page.locator("#email").fill(f"qa-etapas-{uuid.uuid4().hex[:8]}@example.com")
    page.locator("#password").fill(E2E_PASSWORD)
    page.locator("#confirm_password").fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.get_by_role("button", name="Criar minha conta").click()


def _continue(page: Page, expected_slug: str):
    page.get_by_role("button", name=re.compile(r"^(Continuar|Salvar e continuar)$")).click()
    expect(page).to_have_url(re.compile(rf"/pro/onboarding/{expected_slug}$"))


def _no_horizontal_scroll(page: Page):
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


def _readable(page: Page):
    """Mesmo critério da V-04: texto >= 12 px e contraste AA."""
    assert page.evaluate(SMALL_TEXT) == []
    failing = [
        item for item in page.evaluate(CONTRAST, None)
        if item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]


def test_full_journey_publishes_only_when_asked(page: Page):
    _register(page)
    page.goto("/pro/onboarding")
    expect(page).to_have_url(re.compile(r"/pro/onboarding/nome$"))
    expect(page.locator("#display_name")).to_have_value("Pro Etapas Navegador")
    expect(page.locator(".onb__count")).to_have_text("Etapa 1 de 7")
    expect(page.locator('.onb__segment[aria-current="step"]')).to_have_count(1)

    _continue(page, "cidade")
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("pr")
    _continue(page, "especialidade")
    page.locator("#primary_specialty").fill("Nail designer")
    unhas = page.locator('input[name="categories"][value="unhas"]')
    unhas.focus()
    page.keyboard.press("Space")
    expect(unhas).to_be_checked()
    _continue(page, "atendimento")
    page.locator(".onb__choice", has_text="Em espaço próprio").click()
    _continue(page, "apresentacao")

    page.locator("#bio").fill("Curta.")
    page.get_by_role("button", name="Continuar").click()
    expect(page.locator("#bio-errors")).to_contain_text("Use entre 40 e 2000 caracteres.")
    expect(page.locator("#bio")).to_be_focused()
    page.locator("#bio").fill(BIO)
    expect(page.locator('[data-onb-count="bio"]')).to_have_text(f"{len(BIO)} de 2000 caracteres.")
    _continue(page, "fotos")

    page.get_by_role("link", name="Fazer depois").click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/revisar$"))
    expect(page.locator(".onb__pending")).to_have_count(0)
    _readable(page)
    publish = page.get_by_role("button", name="Publicar perfil")
    expect(publish).to_be_enabled()
    publish.click()

    expect(page).to_have_url(re.compile(r"/pro/onboarding/concluido$"))
    expect(page.get_by_role("heading", level=1)).to_have_text("Seu perfil está no ar.")
    expect(page.get_by_text("Reservas ainda não estão abertas", exact=False)).to_be_visible()
    _readable(page)
    page.get_by_role("link", name="Ver meu perfil público").click()
    expect(page.get_by_text("Pro Etapas Navegador").first).to_be_visible()


def test_review_shows_what_is_missing_and_returns_after_fixing(page: Page):
    _register(page, name="Pro Revisão")
    page.goto("/pro/onboarding/nome")
    _continue(page, "cidade")
    page.goto("/pro/onboarding/revisar")

    expect(page.locator(".onb__pending")).to_contain_text("Informe a cidade onde você atende.")
    expect(page.get_by_role("button", name="Publicar perfil")).to_be_disabled()
    _readable(page)

    page.get_by_role("link", name=re.compile(r"Completar Onde você atende")).click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/cidade\?retorno=revisar$"))
    page.locator("#city").fill("Londrina")
    page.locator("#state").fill("PR")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/revisar$"))
    expect(page.locator(".onb__pending")).not_to_contain_text("Informe a cidade")


@pytest.mark.parametrize("viewport", [(390, 844)], ids=["mobile"])
def test_leaving_and_resuming_on_a_phone(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _register(page, name="Pro Celular")
    page.goto("/pro/onboarding")
    _no_horizontal_scroll(page)
    _continue(page, "cidade")
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    _continue(page, "especialidade")
    _no_horizontal_scroll(page)
    submit = page.get_by_role("button", name="Continuar")
    box = submit.bounding_box()
    assert box is not None and box["height"] >= 44

    page.get_by_role("link", name="Sair e continuar depois").click()
    page.get_by_role("link", name=re.compile("Continuar cadastro profissional")).click()
    expect(page).to_have_url(re.compile(r"/pro/onboarding/especialidade$"))
    expect(page.locator(".onb__count")).to_have_text("Etapa 3 de 7")
    _no_horizontal_scroll(page)
