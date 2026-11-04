"""PR 3 do programa IDDUN 2.0 — feed social no navegador (D-SOC-08 a 11).

- A Cliente publica só texto e um carrossel, na ordem e com o texto
  alternativo que escolheu.
- Curtir grava na conta e vale depois de recarregar.
- Comentário e resposta na página do post; visitante é convidado a entrar.
- Denúncia fecha a janela sem protocolo e não apaga o post.
- A autora remove o próprio post.
- Feed com compositor e página do post legíveis em 1280 e 390 px.
"""

import re
from io import BytesIO

import pytest
from PIL import Image
from playwright.sync_api import Page, expect

from e2e.test_web_platform_contrast import CONTRAST
from e2e.test_web_pro_onboarding import _register


def _png(color):
    output = BytesIO()
    Image.new("RGB", (120, 90), color).save(output, format="PNG")
    return output.getvalue()


def _open_composer(page: Page):
    page.goto("/feed")
    page.wait_for_load_state()
    page.locator(".post-composer__summary").click()
    expect(page.locator("[data-composer-form]")).to_be_visible()


def _publish(page: Page):
    with page.expect_navigation():
        page.locator("[data-composer-submit]").click()
    expect(page.locator(".flash-message")).to_contain_text("Sua publicação está no ar.")


def _post_id(page: Page):
    match = re.search(r"#post-(\d+)$", page.url)
    assert match, page.url
    return match.group(1)


# Partes novas desta PR. O restante do feed (abas, laterais) tem achados
# anteriores registrados para a PR 8 e não entra nesta medição.
NEW_PARTS = (
    ".post-composer, .post-actions, .post-menu__panel, .post-detail, "
    ".report-dialog, .feed-card__text, .feed-card__author"
)
TEXT = ":is(label, small, span, strong, button, a, p, h1, h2, li, legend, summary)"


def _readable(page: Page):
    selector = ", ".join(f"{part.strip()} {TEXT}" for part in NEW_PARTS.split(","))
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


def test_client_publishes_text_and_a_carousel_in_order(page: Page):
    _register(page, name="Cliente Publica")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Meu primeiro post só de texto.")
    expect(page.locator("[data-composer-count]")).to_have_text("30")
    _publish(page)
    text_id = _post_id(page)
    card = page.locator(f"#post-{text_id}")
    expect(card).to_contain_text("Meu primeiro post só de texto.")
    expect(card).to_contain_text("Cliente Publica")
    expect(card.locator(".post-carousel")).to_have_count(0)

    _open_composer(page)
    page.locator("[data-composer-files]").set_input_files(
        [
            {"name": "roxa.png", "mimeType": "image/png", "buffer": _png((107, 46, 255))},
            {"name": "verde.png", "mimeType": "image/png", "buffer": _png((40, 160, 90))},
        ]
    )
    thumbs = page.locator(".post-composer__thumb")
    expect(thumbs).to_have_count(2)
    thumbs.nth(1).locator("input").fill("Depois")
    page.get_by_role("button", name="Mover foto 2 para antes").click()
    page.locator(".post-composer__thumb").nth(1).locator("input").fill("Antes")
    _publish(page)
    carousel_id = _post_id(page)

    card = page.locator(f"#post-{carousel_id}")
    expect(card.locator("[data-carousel-count]")).to_have_text("1 de 2")
    expect(card.locator(".post-carousel__slide img").first).to_have_attribute("alt", "Depois")
    card.locator("[data-carousel-next]").click()
    expect(card.locator("[data-carousel-count]")).to_have_text("2 de 2")

    page.goto(f"/publicacoes/{carousel_id}")
    alts = page.locator(".post-carousel__slide img").evaluate_all("els => els.map((el) => el.alt)")
    assert alts == ["Depois", "Antes"]


def test_like_is_saved_and_survives_reload(page: Page):
    _register(page, name="Cliente Curte")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Post para curtir.")
    _publish(page)
    post_id = _post_id(page)

    like = page.locator(f"#post-{post_id} [data-like-button]")
    with page.expect_response(lambda r: r.url.endswith(f"/api/v1/posts/{post_id}/like")):
        like.click()
    expect(like).to_have_attribute("aria-pressed", "true")
    expect(like.locator("[data-like-count]")).to_have_text("1")

    page.reload()
    expect(page.locator(f"#post-{post_id} [data-like-button]")).to_have_attribute("aria-pressed", "true")
    payload = page.request.get(f"/api/v1/posts/{post_id}").json()
    assert payload["likesCount"] == 1 and payload["likedByMe"] is True


def test_comment_reply_report_and_removal(page: Page, browser):
    _register(page, name="Autora Conversa")
    _open_composer(page)
    page.locator("[data-composer-caption]").fill("Vamos conversar?")
    _publish(page)
    post_id = _post_id(page)
    post_url = f"/publicacoes/{post_id}"

    page.goto(post_url)
    page.get_by_label("Escreva um comentário").fill("Primeiro comentário")
    with page.expect_navigation():
        page.get_by_role("button", name="Enviar", exact=True).click()
    expect(page.locator(".post-comment")).to_contain_text("Primeiro comentário")
    page.locator(".post-comment__reply summary").first.click()
    page.locator(".post-comment__reply textarea").first.fill("Uma resposta")
    with page.expect_navigation():
        page.locator(".post-comment__reply").get_by_role("button", name="Responder").click()
    expect(page.locator(".post-comment--reply")).to_contain_text("Uma resposta")
    expect(page.get_by_role("heading", name="Comentários (2)")).to_be_visible()

    visitor = browser.new_context(base_url=page.url.split("/publicacoes")[0])
    anonymous = visitor.new_page()
    anonymous.goto(post_url)
    expect(anonymous.get_by_role("link", name="Entre para comentar")).to_be_visible()
    expect(anonymous.locator(".post-comment")).to_have_count(2)
    visitor.close()

    reporter_context = browser.new_context(base_url=page.url.split("/publicacoes")[0])
    reporter = reporter_context.new_page()
    _register(reporter, name="Quem Denuncia")
    reporter.goto(post_url)
    reporter.wait_for_load_state()
    trigger = reporter.locator("[data-post-menu-trigger]")
    trigger.focus()
    reporter.keyboard.press("Enter")
    expect(trigger).to_have_attribute("aria-expanded", "true")
    reporter.get_by_role("button", name="Denunciar publicação").click()
    dialog = reporter.locator("[data-report-dialog]")
    expect(dialog).to_be_visible()
    dialog.get_by_label("Spam ou golpe").check()
    dialog.locator("textarea").fill("Parece golpe")
    with reporter.expect_response(lambda r: r.url.endswith("/denuncias")) as response:
        dialog.get_by_role("button", name="Enviar").click()
    assert response.value.status == 204
    expect(dialog).to_be_hidden()
    # Sem protocolo nem confirmação; o post continua no ar.
    expect(reporter.locator(".flash-message")).to_have_count(0)
    reporter.reload()
    expect(reporter.locator(".post-detail__card")).to_contain_text("Vamos conversar?")
    reporter_context.close()

    page.goto("/feed")
    page.wait_for_load_state()
    card = page.locator(f"#post-{post_id}")
    card.locator("[data-post-menu-trigger]").click()
    card.get_by_role("button", name="Remover publicação").click()
    with page.expect_navigation():
        card.locator("[data-post-remove-confirm]").get_by_role("button", name="Remover").click()
    expect(page.locator(".flash-message")).to_contain_text("Publicação removida.")
    expect(page.locator(f"#post-{post_id}")).to_have_count(0)
    assert page.request.get(post_url).status == 404


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)], ids=["desktop", "mobile"])
def test_feed_composer_and_post_page_are_readable(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _register(page, name="Cliente Leitura Feed")
    _open_composer(page)
    page.locator("[data-composer-files]").set_input_files(
        [{"name": "a.png", "mimeType": "image/png", "buffer": _png((200, 120, 60))}]
    )
    expect(page.locator(".post-composer__thumb")).to_have_count(1)
    _readable(page)

    page.locator("[data-composer-caption]").fill("Post para leitura")
    _publish(page)
    post_id = _post_id(page)
    page.goto(f"/publicacoes/{post_id}")
    _readable(page)
    menu = page.locator("[data-post-menu-trigger]")
    menu.click()
    _readable(page)
