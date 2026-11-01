"""PR 3 do onboarding — cadastro de Estabelecimento por etapas no navegador.

Uma pergunta por tela, salva no servidor; erros em português ao lado do
campo; endereço só para físico ou híbrido (F2); apresentação 40+ (D-ONB-04);
e-mail da conta só como sugestão (D-ONB-05); publicação explícita (F1);
empresa sem logo aparece com iniciais (DEC-ID-101).
"""

import re
import uuid

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL, E2E_PASSWORD
from e2e.test_web_readable_text import CONTRAST, SMALL_TEXT

DESCRIPTION = "Um espaço dedicado a coloração autoral e atendimento sem pressa."


def _login(page: Page):
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()
    expect(page).to_have_url(re.compile(r"/feed(?:\?.*)?$"))


def start_business_draft(page: Page, name: str) -> str:
    """Cria um rascunho pela etapa 1 e devolve o id."""
    page.goto("/business/onboarding/novo")
    page.locator("#name").fill(name)
    page.locator(".onb__choice", has_text="Salão de beleza").click()
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/business/onboarding/\d+/atendimento$"))
    return re.search(r"/business/onboarding/(\d+)/", page.url).group(1)


def _readable(page: Page):
    assert page.evaluate(SMALL_TEXT) == []
    failing = [
        item for item in page.evaluate(CONTRAST, None)
        if item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]


def test_business_steps_validate_skip_address_and_publish_explicitly(page: Page):
    _login(page)
    page.goto("/business/onboarding/novo")
    expect(page.locator(".onb__count")).to_have_text("Etapa 1 de 7")

    page.get_by_role("button", name="Continuar").click()
    expect(page.locator("#name-errors")).to_have_text("Informe o nome do estabelecimento.")
    expect(page.locator("#name")).to_be_focused()
    expect(page.locator("#category-errors")).to_have_text("Escolha o tipo de estabelecimento.")

    name = f"Studio Ensaio {uuid.uuid4().hex[:4]}"
    page.locator("#name").fill(name)
    page.locator(".onb__choice", has_text="Salão de beleza").click()
    page.locator("#city").fill("Curitiba")
    page.locator("#state").fill("PR")
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/atendimento$"))

    page.locator(".onb__choice", has_text="No endereço do cliente").click()
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/funcionamento$"))
    expect(page.locator(".onb__count")).to_have_text("Etapa 4 de 7")

    page.locator(".onb__choice", has_text="Sob agendamento").click()
    expect(page.locator("[data-hours-panel]")).to_be_hidden()
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/contato$"))

    expect(page.locator("#email")).to_have_value(E2E_EMAIL)
    page.locator("#description").fill("Curta.")
    page.get_by_role("button", name="Continuar").click()
    expect(page.locator("#description-errors")).to_contain_text("Use entre 40 e 2000 caracteres.")
    expect(page.locator("#description")).to_be_focused()
    page.locator("#description").fill(DESCRIPTION)
    page.get_by_role("button", name="Continuar").click()
    expect(page).to_have_url(re.compile(r"/fotos$"))

    page.get_by_role("link", name="Fazer depois").click()
    expect(page).to_have_url(re.compile(r"/revisar$"))
    expect(page.get_by_text("Endereço comercial", exact=True)).to_have_count(0)
    _readable(page)
    page.get_by_role("button", name="Publicar página").click()

    expect(page).to_have_url(re.compile(r"/concluido$"))
    expect(page.get_by_role("heading", level=1)).to_contain_text("está no ar.")
    _readable(page)
    page.get_by_role("link", name="Ir para o painel").click()
    expect(page).to_have_url(re.compile(r"/business/[^/]+/painel$"))
    expect(page.locator(".platform-dashboard-avatar .ds-avatar-initials")).to_have_text("SE")


def test_owner_can_leave_and_continue_a_draft(page: Page):
    _login(page)
    name = f"Studio Pausa {uuid.uuid4().hex[:4]}"
    draft_id = start_business_draft(page, name)

    page.get_by_role("link", name="Sair e continuar depois").click()
    page.goto("/business/onboarding")
    page.get_by_role("link", name=f"Continuar {name}").click()
    expect(page).to_have_url(re.compile(rf"/business/onboarding/{draft_id}/atendimento$"))
    expect(page.locator(".onb__count")).to_have_text("Etapa 2 de 7")
