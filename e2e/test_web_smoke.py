"""Browser-level smoke coverage against an isolated Flask instance.

Run only in the dedicated Playwright CI job, never against production.
"""

import re

from playwright.sync_api import Page, expect


def test_public_home_links_to_discovery(page: Page):
    page.goto("/")
    expect(page.locator("body")).to_be_visible()
    expect(page.get_by_role("link", name="Cadastre-se")).to_be_visible()
    expect(page.get_by_role("link", name="Entrar", exact=True).first).to_be_visible()
    expect(page.get_by_role("link", name="Política de privacidade")).to_be_visible()
    expect(page.get_by_role("link", name="Termos de uso")).to_be_visible()
    page.get_by_role("link", name="Cadastre-se").click()
    expect(page).to_have_url(re.compile(r"/cadastro(?:\?.*)?$"))

    # Discovery remains available at its existing public route.
    page.goto("/experiencias")
    expect(page.locator("body")).to_be_visible()


def test_login_invalid_credentials_stay_unauthenticated(page: Page):
    page.goto("/login")
    expect(page.get_by_role("heading", name="Bem-vindo de volta")).to_be_visible()
    page.locator('input[name="email"]').fill("not-registered@example.com")
    page.locator('input[name="password"]').fill("not-the-password")
    page.locator('button[type="submit"][data-submit]').click()

    expect(page.get_by_text("E-mail ou senha incorretos.")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login(?:\?.*)?$"))


def test_login_and_signup_navigation(page: Page):
    page.goto("/login")
    page.get_by_role("link", name="Criar minha conta").click()
    expect(page).to_have_url(re.compile(r"/cadastro(?:\\?.*)?$"))
    expect(page.get_by_role("heading", name="Crie sua conta")).to_be_visible()
    page.get_by_role("link", name="Entrar", exact=True).last.click()
    expect(page).to_have_url(re.compile(r"/login(?:\?.*)?$"))


def test_nv06_strict_script_csp_and_auto_submit_filter(page: Page):
    page.goto("/experiencias")
    # The original onchange="this.form.submit()" now lives in an external listener.
    sort = page.locator('select[name="ordem"][data-auto-submit="true"]').first
    sort.select_option("lowest_price")
    expect(page).to_have_url(re.compile(r"ordem=lowest_price"))


def test_nv06_confirmation_listener_prevents_cancelled_submit(page: Page):
    page.goto("/experiencias")
    page.evaluate("""() => {
      const form = document.createElement('form');
      form.action = '/nv06-unreachable-form-target';
      form.method = 'post';
      form.setAttribute('data-confirm-submit', 'Confirmar alteração?');
      const button = document.createElement('button');
      button.textContent = 'Enviar ação de teste';
      button.type = 'submit';
      form.appendChild(button);
      document.body.appendChild(form);
    }""")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Enviar ação de teste").click()
    expect(page).to_have_url(re.compile(r"/experiencias(?:\?.*)?$"))


def test_nv06_confirmed_form_submits_once(page: Page):
    page.goto("/experiencias")
    page.evaluate("""() => {
      const form = document.createElement('form');
      form.action = '/experiencias';
      form.method = 'get';
      form.setAttribute('data-confirm-submit', 'Confirmar alteração?');
      const marker = document.createElement('input');
      marker.name = 'nv06_confirmed';
      marker.value = '1';
      form.appendChild(marker);
      const button = document.createElement('button');
      button.textContent = 'Confirmar ação de teste';
      button.type = 'submit';
      form.appendChild(button);
      document.body.appendChild(form);
    }""")
    requests = []
    page.on("request", lambda request: requests.append(request.url)
            if "nv06_confirmed=1" in request.url else None)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Confirmar ação de teste").click()
    expect(page).to_have_url(re.compile(r"nv06_confirmed=1"))
    assert len(requests) == 1
