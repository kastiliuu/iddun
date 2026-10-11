"""Browser-level smoke coverage against an isolated Flask instance.

Run only in the dedicated Playwright CI job, never against production.
"""

import re

from playwright.sync_api import Page, expect


def test_public_home_links_to_discovery(page: Page):
    page.goto("/")
    expect(page.locator("body")).to_be_visible()
    expect(page.get_by_role("link", name="Descobrir", exact=True).first).to_be_visible()
    page.get_by_role("link", name="Descobrir", exact=True).first.click()
    expect(page).to_have_url(re.compile(r"/experiencias(?:\?.*)?$"))


def test_login_invalid_credentials_stay_unauthenticated(page: Page):
    page.goto("/login")
    expect(page.get_by_role("heading", name="Bem-vindo de volta")).to_be_visible()
    page.locator('input[name="email"]').fill("not-registered@iddun.invalid")
    page.locator('input[name="password"]').fill("not-the-password")
    page.locator('button[type="submit"][data-submit]').click()

    expect(page.get_by_text("E-mail ou senha incorretos.")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login(?:\?.*)?$"))


def test_login_and_signup_navigation(page: Page):
    page.goto("/login")
    page.get_by_role("link", name="Criar conta").last.click()
    expect(page).to_have_url(re.compile(r"/cadastro|/registrar|/register"))
    expect(page.get_by_role("heading", name="Crie sua conta")).to_be_visible()
    page.get_by_role("link", name="Entrar", exact=True).last.click()
    expect(page).to_have_url(re.compile(r"/login(?:\?.*)?$"))
