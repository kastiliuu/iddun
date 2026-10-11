"""Authenticated browser journey with a disposable CI-created client account."""

import re

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL, E2E_PASSWORD


def test_real_client_login_feed_and_reservations(page: Page):
    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()

    expect(page).to_have_url(re.compile(r"/feed(?:\?.*)?$"))
    expect(page.get_by_role("navigation", name="Navegação do feed")).to_be_visible()
    expect(page.get_by_role("link", name="Reservas").first).to_be_visible()

    page.get_by_role("link", name="Reservas").first.click()
    expect(page).to_have_url(re.compile(r"/(minhas-reservas|reservas)(?:\?.*)?$"))

    # Authenticated user can return directly to the protected feed.
    page.goto("/feed")
    expect(page.get_by_role("navigation", name="Navegação do feed")).to_be_visible()


def test_anonymous_browser_is_redirected_from_private_feed(page: Page):
    page.goto("/feed")
    expect(page).to_have_url(re.compile(r"/login(?:\?.*)?$"))
    expect(page.get_by_role("heading", name="Bem-vindo de volta")).to_be_visible()
