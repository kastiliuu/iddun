"""V1-CONV-D05 no navegador: piloto de recrutamento e vagas na Web.

Fluxo da homologação, ponta a ponta:
1. a dona vê "Recrutamento ainda não habilitado" e nenhum formulário de vaga;
2. o admin do IDDUN habilita com motivo e o histórico registra;
3. a dona cria o rascunho, publica e a vaga aparece em /vagas;
4. o admin revoga: "Nova vaga" some e a vaga publicada continua no ar.
Tudo legível (AA, texto ≥ 12 px) em 1440 e 390 px.
"""

import re
import uuid

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PASSWORD, E2E_PRO_EMAIL, E2E_TYPO_ADMIN_EMAIL
from e2e.test_web_platform_contrast import _login
from e2e.test_web_service_wizard_catalog import _readable


def _logout(page: Page):
    page.context.clear_cookies()


def _admin_set(page: Page, establishment_id: str, action: str, reason: str):
    _logout(page)
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_TYPO_ADMIN_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()
    page.goto(f"/admin/estabelecimentos/{establishment_id}/recrutamento")
    button = page.get_by_role("button", name=f"{action} recrutamento")
    if button.count() == 0:
        return
    page.get_by_label("Motivo").fill(reason)
    with page.expect_navigation():
        button.click()
    expect(page.get_by_text(reason)).to_be_visible()


def _establishment_id(page: Page):
    _logout(page)
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_TYPO_ADMIN_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()
    page.goto("/admin/estabelecimentos")
    href = page.locator("tr", has_text="Espaço QA Navegador").locator(
        "a[href*='/recrutamento']"
    ).first.get_attribute("href")
    return re.search(r"/estabelecimentos/(\d+)/recrutamento", href).group(1)


def test_pilot_controls_new_jobs_and_keeps_published_ones_online(page: Page):
    page.set_viewport_size({"width": 1440, "height": 900})
    establishment_id = _establishment_id(page)
    _admin_set(page, establishment_id, "Revogar", "Estado inicial do teste de navegador.")

    _logout(page)
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/vagas")
    expect(page.get_by_role("heading", name="Recrutamento ainda não habilitado")).to_be_visible()
    expect(page.get_by_role("heading", name="Nova vaga")).to_have_count(0)
    expect(page.get_by_role("heading", name="Gerentes e recrutamento")).to_be_visible()
    _readable(page, ".recruit-layout")

    _admin_set(page, establishment_id, "Habilitar", "Piloto aprovado na homologação.")
    expect(page.locator("[data-recruitment-status]")).to_have_text("Habilitado")

    _logout(page)
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/vagas")
    expect(page.get_by_role("heading", name="Recrutamento habilitado")).to_be_visible()
    title = f"Colorista QA {uuid.uuid4().hex[:6]}"
    page.get_by_label("Título da vaga").fill(title)
    page.get_by_label("Descrição").fill("Atendimento de coloração em salão parceiro.")
    page.get_by_label("Modelo de trabalho").fill("Parceria")
    with page.expect_navigation():
        page.get_by_role("button", name="Criar rascunho").click()
    card = page.locator(".recruit-card", has_text=title)
    expect(card.locator(".recruit-status")).to_have_text("Rascunho")
    with page.expect_navigation():
        card.get_by_role("button", name="Publicar").click()
    card = page.locator(".recruit-card", has_text=title)
    expect(card.locator(".recruit-status")).to_have_text("Publicada")
    _readable(page, ".recruit-layout")

    page.goto("/vagas")
    expect(page.get_by_role("link", name=re.compile(title))).to_be_visible()
    page.get_by_role("link", name=re.compile(title)).click()
    expect(page.get_by_role("heading", level=1)).to_have_text(title)
    _readable(page, ".recruit-layout")

    _admin_set(page, establishment_id, "Revogar", "Fim do teste de navegador.")
    _logout(page)
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/business/{E2E_BUSINESS_SLUG}/vagas")
    expect(page.get_by_role("heading", name="Nova vaga")).to_have_count(0)
    expect(page.locator(".recruit-card", has_text=title).locator(".recruit-status")).to_have_text("Publicada")
    page.goto("/vagas")
    expect(page.get_by_role("link", name=re.compile(title))).to_be_visible()


def test_jobs_pages_fit_a_phone(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    for path in ("/vagas", "/minhas-candidaturas", f"/business/{E2E_BUSINESS_SLUG}/vagas"):
        page.goto(path)
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        _readable(page, ".recruit-layout")
