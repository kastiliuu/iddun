"""PR 4a do programa IDDUN 2.0 — perfis sociais no navegador (D-SOC-12, 13).

- O nome da Cliente no feed leva à página dela, com a publicação.
- Perfil Pro na ordem aprovada; abas da empresa com endereço próprio.
- Partes novas legíveis e sem rolagem lateral em 1280 e 390 px.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_PROFILE_SLUG
from e2e.test_web_platform_contrast import CONTRAST
from e2e.test_web_pro_onboarding import _register
from e2e.test_web_social_feed import _open_composer, _publish

PRO_SLUG = E2E_PROFILE_SLUG

# Partes novas desta PR. O rótulo de seção (kicker) é anterior e tem 9,92 px;
# fica registrado como achado para a PR 8.
NEW_PARTS = (
    ".client-profile-head, .profile-tabs, "
    ".profile-read-more, .profile-subhead, .profile-badge, .post-tiles, "
    ".profile-see-all, .profile-facts, .profile-hours, .profile-contacts, .profile-posts"
)
TEXT = ":is(small, span, strong, a, p, h1, h2, h3, dt, dd, th, td, li, summary, em)"


def _readable(page: Page):
    selector = ", ".join(f"{part.strip()} {TEXT}, {part.strip()}" for part in NEW_PARTS.split(","))
    small = page.evaluate(
        """(selector) => [...document.querySelectorAll(selector)]
          .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
          .filter((el) => el.getBoundingClientRect().width > 0 && !el.closest('[hidden], .sr-only'))
          .map((el) => ({ text: el.innerText.trim().slice(0, 30), size: parseFloat(getComputedStyle(el).fontSize) }))
          .filter((item) => item.size < 12)""",
        selector,
    )
    assert small == [], small[:5]
    failing = [
        item for item in page.evaluate(CONTRAST, selector)
        if item["text"] and item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], failing[:5]
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


def test_client_name_in_the_feed_opens_her_page(page: Page):
    _register(page, name="Cliente Perfil Público")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Cachos definidos depois do corte.")
    _publish(page)

    card = page.locator("article.feed-card").filter(has_text="Cachos definidos depois do corte.").first
    link = card.get_by_role("link", name="Cliente Perfil Público").first
    href = link.get_attribute("href")
    assert re.fullmatch(r"/clientes/\d+", href), href
    link.click()

    expect(page).to_have_url(re.compile(r"/clientes/\d+$"))
    expect(page.get_by_role("heading", level=1)).to_have_text("Cliente Perfil Público")
    expect(page.locator(".client-profile-head")).to_contain_text("Cliente IDDUN · 1 publicação")
    expect(page.get_by_text("Cachos definidos depois do corte.")).to_be_visible()

    assert page.request.get("/clientes/999999").status == 404


def test_professional_sections_follow_the_approved_order(page: Page):
    page.goto(f"/profissionais/{PRO_SLUG}")
    kickers = page.locator(".public-profile-section__kicker").all_inner_texts()
    order = ["PORTFÓLIO", "SERVIÇOS", "PUBLICAÇÕES", "EXPERIÊNCIA & FORMAÇÃO",
             "AVALIAÇÕES & RECOMENDAÇÕES", "ONDE ATENDE"]
    assert [item for item in kickers if item in order] == order
    expect(page.get_by_text("Ler mais").first).to_be_visible()
    expect(page.locator(".post-tile")).to_have_count(6)
    expect(page.get_by_role("link", name="Ver todas (7)")).to_be_visible()
    expect(page.locator(".profile-badge").first).to_have_text("Declarado pelo profissional")


def test_business_tabs_navigate_by_address(page: Page):
    page.goto(f"/estabelecimentos/{E2E_BUSINESS_SLUG}")
    tabs = page.locator(".profile-tabs")
    expect(tabs.locator('[aria-current="page"]')).to_have_text("Início")

    for label, suffix in (("Serviços", "/servicos"), ("Equipe", "/equipe"),
                          ("Publicações", "/publicacoes"), ("Sobre", "/sobre")):
        tabs.get_by_role("link", name=label, exact=True).click()
        expect(page).to_have_url(re.compile(re.escape(f"/estabelecimentos/{E2E_BUSINESS_SLUG}{suffix}") + "$"))
        expect(tabs.locator('[aria-current="page"]')).to_have_text(label)

    page.go_back()
    expect(tabs.locator('[aria-current="page"]')).to_have_text("Publicações")


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_profile_pages_are_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    for path in (
        f"/profissionais/{PRO_SLUG}",
        f"/profissionais/{PRO_SLUG}/publicacoes",
        *(f"/estabelecimentos/{E2E_BUSINESS_SLUG}{suffix}"
          for suffix in ("", "/servicos", "/equipe", "/publicacoes", "/sobre")),
    ):
        assert page.goto(path).status == 200, path
        _readable(page)

    _register(page, name="Cliente Leitura Perfil")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Post para leitura do perfil")
    _publish(page)
    href = page.locator("article.feed-card").first.get_by_role("link", name="Cliente Leitura Perfil").first.get_attribute("href")
    page.goto(href)
    _readable(page)
