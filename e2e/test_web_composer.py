"""ID-SOC-R1-01/05 — compositor com identidade única, no navegador.

- Pro publica pelo feed como a pessoa: sem seletor "Publicar como", com o
  @ dela; o post aparece com o nome da conta e o selo Pro.
- Vídeo fica inativo ("Em breve") e não envia nada.
- O botão Serviço abre o serviço do próprio perfil Pro.
- A página da empresa abre o compositor como a empresa.
- Outra pessoa segue a autora pela pessoa (data-target-type="person").
- Compositor legível e sem rolagem lateral em 390 px.
"""

import re
import uuid

from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import _login
from e2e.test_web_pro_onboarding import _register
from e2e.test_web_social_feed import _open_composer, _post_id, _publish, _readable


def test_pro_publishes_as_the_person_with_own_service(page: Page):
    _login(page, E2E_PRO_EMAIL)
    _open_composer(page)
    form = page.locator("[data-composer-form]")

    expect(form.get_by_label("Publicar como")).to_have_count(0)
    identity = form.locator("[data-composer-identity]")
    expect(identity).to_contain_text("Profissional QA Navegador")
    expect(identity).to_contain_text(re.compile(r"@[a-z0-9._]+"))
    expect(form.locator('input[name="author"]')).to_have_attribute("value", re.compile(r"^client:\d+$"))

    # Vídeo: inativo, avisa e não publica.
    requests = []
    page.on("request", lambda request: requests.append(request.url) if request.method == "POST" else None)
    video = form.get_by_role("button", name=re.compile("Vídeo"))
    expect(video).to_have_attribute("aria-disabled", "true")
    # aria-disabled mantém o botão focável; o Playwright exige force.
    video.click(force=True)
    expect(page.locator("[data-feed-toast]")).to_contain_text("Vídeo chega em breve")
    assert requests == []

    # Serviço: fechado até pedir; abre o serviço do próprio perfil Pro.
    service = form.locator("[data-composer-service]")
    expect(service).to_be_hidden()
    toggle = form.get_by_role("button", name="Serviço")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    service.locator("select").select_option(label="Coloração QA")

    form.locator("[data-composer-caption]").fill(f"Post pessoal {uuid.uuid4().hex[:6]}")
    _publish(page)
    card = page.locator(f"#post-{_post_id(page)}")
    expect(card.locator(".feed-card__author")).to_contain_text("Profissional QA Navegador")
    expect(card.locator(".feed-card__author")).to_contain_text("· Colorista")
    expect(card.locator("a[href^='/@']").first).to_be_visible()
    # Sem Seguir em si mesma.
    expect(card.locator("[data-follow-button]")).to_have_count(0)
    payload = page.request.get(f"/api/v1/posts/{_post_id(page)}").json()
    assert payload["authorKind"] == "client" and payload["author"]["identity"] == "person"
    assert payload["service"]["id"] == "coloracao-qa-navegador"


def test_company_page_opens_composer_as_the_company(page: Page):
    _login(page, E2E_PRO_EMAIL)
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}")
    with page.expect_navigation():
        page.locator(".profile-edit-link a", has_text="Publicar").first.click()
    form = page.locator("[data-composer-form]")
    expect(form).to_be_visible()
    expect(form.locator('input[name="author"]')).to_have_attribute(
        "value", re.compile(r"^establishment:\d+$")
    )
    expect(form.locator("[data-composer-identity]")).to_contain_text("Espaço QA Navegador")

    form.locator("[data-composer-caption]").fill("Novidade da empresa")
    _publish(page)
    card = page.locator(f"#post-{_post_id(page)}")
    expect(card.locator(".feed-card__author")).to_contain_text("Espaço QA Navegador")

    # Voltar à pessoa pelo link do compositor.
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}")
    with page.expect_navigation():
        page.locator(".profile-edit-link a", has_text="Publicar").first.click()
    with page.expect_navigation():
        form.get_by_role("link", name="Publicar como você").click()
    page.locator(".post-composer__summary").click()
    expect(form.locator('input[name="author"]')).to_have_attribute("value", re.compile(r"^client:\d+$"))


def test_someone_else_follows_the_author_as_a_person(page: Page):
    _register(page, name="Autora Pessoa")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Post para seguir a pessoa")
    _publish(page)
    post_id = _post_id(page)
    author = page.request.get(f"/api/v1/posts/{post_id}").json()["followTarget"]
    assert author["type"] == "person"
    page.context.clear_cookies()

    _register(page, name="Leitora Segue")
    page.goto(f"/publicacoes/{post_id}")
    button = page.locator(f'[data-follow-button][data-target-type="person"][data-target-id="{author["id"]}"]').first
    expect(button).to_be_visible()
    with page.expect_response(lambda r: f"/api/v1/graph/follows/person/{author['id']}" in r.url):
        button.click()
    expect(button).to_have_attribute("aria-pressed", "true")


def test_composer_is_readable_on_a_phone(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    _login(page, E2E_PRO_EMAIL)
    _open_composer(page)
    page.get_by_role("button", name="Serviço").click()
    actions = page.locator(".post-composer__action")
    for index in range(actions.count()):
        box = actions.nth(index).bounding_box()
        assert box and box["height"] >= 44, box
    _readable(page)


def test_composer_works_without_javascript(browser, base_url):
    context = browser.new_context(java_script_enabled=False, base_url=base_url)
    page = context.new_page()
    try:
        _login_no_js(page)
        page.goto("/feed")
        page.locator(".post-composer__summary").click()
        form = page.locator("[data-composer-form]")
        # Sem JavaScript o serviço já fica à vista e o botão some.
        expect(form.locator("[data-composer-service]")).to_be_visible()
        expect(form.locator("[data-composer-service-toggle]")).to_be_hidden()
        form.locator("[data-composer-caption]").fill("Post sem JavaScript")
        with page.expect_navigation():
            form.locator("[data-composer-submit]").click()
        expect(page.locator(".flash-message")).to_contain_text("Sua publicação está no ar.")
    finally:
        context.close()


def _login_no_js(page: Page):
    from e2e.seed_client import E2E_PASSWORD

    page.goto("/login")
    page.locator('input[name="email"]').fill(E2E_PRO_EMAIL)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    with page.expect_navigation():
        page.locator('button[type="submit"][data-submit]').click()
