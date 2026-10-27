"""D-VIS-05 — trabalhos reais primeiro (decisão do proprietário, 27/10/2026, Notion 08).

- O card do Explorar leva ao perfil da profissional aberto no portfólio, com
  o serviço escolhido numa barra fixa.
- Imagem do serviço: foto do próprio serviço; senão trabalhos reais do
  portfólio; senão o bloco tipográfico (D-VIS-04). Nunca foto de estoque.
- Vários serviços da mesma profissional começam por trabalhos diferentes.
- A API do app continua recebendo uma imagem até a PR do mobile.
"""

import re
from datetime import timedelta
from types import SimpleNamespace

from app.extensions import db
from app.models.booking import ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalPortfolioItem, ProfessionalProfile
from app.services.client_feed_service import _real_work_image
from app.services.experience_service import _real_works
from app.services.time_service import utcnow

STOCK_SERVICE_IMAGES = ("exp-hair.jpg", "exp-nails.jpg", "exp-barber.jpg", "category-hair.jpg")


# Works use absolute URLs: a local upload missing from disk is replaced by
# ``resolve_image_url`` with a stock picture, which is a separate finding.
def _professional(slug, name, works=0):
    professional = ProfessionalProfile(
        display_name=name,
        slug=slug,
        primary_specialty="Colorista",
        city="Curitiba",
        state="PR",
        is_active=True,
        published_at=utcnow(),
    )
    db.session.add(professional)
    db.session.flush()
    for index in range(works):
        db.session.add(
            ProfessionalPortfolioItem(
                professional=professional,
                image_url=f"https://cdn.example.com/{slug}-work-{index + 1}.jpg",
                caption=f"Trabalho {index + 1} de {name}",
                sort_order=index,
            )
        )
    return professional


def _service(professional, slug, image_url=None, with_slot=True, created_offset=0):
    experience = Experience(
        professional=professional,
        title=f"Serviço {slug}",
        slug=slug,
        category="cabelo",
        short_description="Serviço real.",
        regular_price="150.00",
        price="150.00",
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
        image_url=image_url,
        created_at=utcnow() - timedelta(minutes=created_offset),
    )
    db.session.add(experience)
    db.session.flush()
    if with_slot:
        starts_at = utcnow() + timedelta(days=1)
        db.session.add(
            ExperienceSlot(
                experience=experience,
                professional=professional,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=60),
                status=SlotStatus.AVAILABLE,
            )
        )
    return experience


def _card(html, slug):
    """HTML of the Explorar card whose links point at ``slug``."""
    for chunk in re.split(r"<article", html):
        if f"servico={slug}#portfolio" in chunk:
            return chunk
    raise AssertionError(f"card {slug} not found")


def test_real_works_rotate_and_are_limited_to_three():
    items = [SimpleNamespace(image_url=f"w{i}.jpg", caption=None) for i in range(5)]

    assert [w["image"] for w in _real_works(items)] == ["w0.jpg", "w1.jpg", "w2.jpg"]
    assert [w["image"] for w in _real_works(items, 1)] == ["w1.jpg", "w2.jpg", "w3.jpg"]
    assert [w["image"] for w in _real_works(items, 6)] == ["w1.jpg", "w2.jpg", "w3.jpg"]
    assert _real_works([], 3) == []


def test_explorar_card_opens_profile_and_shows_real_work_never_stock(app, client):
    app.config["APP_ENV"] = "production"
    with app.app_context():
        marina = _professional("marina-qa", "Marina Costa", works=4)
        _service(marina, "marina-a", created_offset=1)
        _service(marina, "marina-b", created_offset=2)
        bruna = _professional("bruna-qa", "Bruna Teixeira")
        _service(bruna, "bruna-a")
        camila = _professional("camila-qa", "Camila Rocha", works=2)
        _service(camila, "camila-a", image_url="https://cdn.example.com/camila-servico.jpg")
        db.session.commit()

    html = client.get("/experiencias").get_data(as_text=True)

    for stock in STOCK_SERVICE_IMAGES:
        assert stock not in html

    marina_a, marina_b = _card(html, "marina-a"), _card(html, "marina-b")
    for card in (marina_a, marina_b):
        assert "ds-work-mosaic--3" in card
        assert ">4 trabalhos</span>" in card
        assert 'href="/profissionais/marina-qa?servico=marina-' in card
        assert "Ver trabalhos" in card
        assert "/experiencias/marina-" not in card
    first_work = re.compile(r'ds-work-mosaic--3">\s*<img\s+src="[^"]*?(marina-qa-work-\d)')
    assert {first_work.search(marina_a).group(1), first_work.search(marina_b).group(1)} == {
        "marina-qa-work-1",
        "marina-qa-work-2",
    }

    bruna_card = _card(html, "bruna-a")
    assert "ds-media-type" in bruna_card
    assert "Ainda sem trabalhos publicados" in bruna_card
    assert "ds-work-mosaic" not in bruna_card
    assert "Ver perfil" in bruna_card
    assert "Ver trabalhos" not in bruna_card

    camila_card = _card(html, "camila-a")
    assert "camila-servico.jpg" in camila_card
    assert "ds-work-mosaic" not in camila_card


def test_profile_highlights_the_chosen_service_only_for_its_own_services(app, client):
    with app.app_context():
        marina = _professional("marina-bar", "Marina Costa", works=1)
        _service(marina, "marina-com-horario")
        _service(marina, "marina-sem-horario", with_slot=False)
        outra = _professional("outra-bar", "Outra Pessoa")
        _service(outra, "servico-de-outra")
        db.session.commit()

    with_slot = client.get("/profissionais/marina-bar?servico=marina-com-horario").get_data(as_text=True)
    assert 'class="profile-service-bar"' in with_slot
    assert "Serviço marina-com-horario" in with_slot
    assert 'href="/experiencias/marina-com-horario#horarios"' in with_slot
    assert "Ver horários" in with_slot

    without_slot = client.get("/profissionais/marina-bar?servico=marina-sem-horario").get_data(as_text=True)
    assert 'class="profile-service-bar"' in without_slot
    assert "Ver serviço" in without_slot
    assert "#horarios" not in without_slot.split('class="profile-service-bar"')[1]

    for query in ("servico=servico-de-outra", "servico=nao-existe", ""):
        html = client.get(f"/profissionais/marina-bar?{query}").get_data(as_text=True)
        assert 'class="profile-service-bar"' not in html, query


def test_detail_hero_uses_real_work_then_typographic_block(app, client):
    app.config["APP_ENV"] = "production"
    with app.app_context():
        marina = _professional("marina-hero", "Marina Costa", works=3)
        _service(marina, "marina-hero-servico")
        bruna = _professional("bruna-hero", "Bruna Teixeira")
        _service(bruna, "bruna-hero-servico")
        db.session.commit()

    with_works = client.get("/experiencias/marina-hero-servico").get_data(as_text=True)
    assert "ds-work-mosaic--3" in with_works
    assert 'href="/profissionais/marina-hero#portfolio">Ver 3 trabalhos de Marina Costa</a>' in with_works

    without = client.get("/experiencias/bruna-hero-servico").get_data(as_text=True)
    assert "ds-media-type ds-media-type--hero" in without
    assert "Ainda sem trabalhos publicados" in without
    assert "experience-detail-media__overlay" not in without

    for html in (with_works, without):
        for stock in STOCK_SERVICE_IMAGES:
            assert stock not in html


def test_app_api_keeps_an_image_until_the_mobile_pr(app, client):
    with app.app_context():
        bruna = _professional("bruna-api", "Bruna Teixeira")
        _service(bruna, "bruna-api-servico")
        db.session.commit()

    payload = client.get("/api/v1/experiences/bruna-api-servico").get_json()
    body = payload.get("data", payload)
    image = body.get("imageUrl") or body.get("experience", {}).get("imageUrl")
    assert image and image.endswith("img/exp-hair.jpg")


def test_iddun_now_image_is_service_photo_then_real_work_never_portrait(app):
    with app.test_request_context():
        work = SimpleNamespace(image_url="https://cdn.example.com/work.jpg")

        def slot(service_image, works, avatar="https://cdn.example.com/portrait.jpg"):
            return SimpleNamespace(
                experience=SimpleNamespace(image_url=service_image),
                professional=SimpleNamespace(portfolio_items=works, avatar_url=avatar),
            )

        assert _real_work_image(slot("https://cdn.example.com/service.jpg", [work])).endswith("/service.jpg")
        assert _real_work_image(slot(None, [work])).endswith("/work.jpg")
        assert _real_work_image(slot(None, [])) is None
