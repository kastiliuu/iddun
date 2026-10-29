"""V-04 — card de /estabelecimentos.

Com capa, o card mostra a capa da empresa (como antes). Sem capa (a capa é
opcional, DEC-ID-101), mostra o bloco tipográfico do DS (D-VIS-04) no lugar
da faixa dourada antiga. Plural correto na contagem.
"""

from app.extensions import db
from app.models.establishment import Establishment


def _establishment(app, slug, cover_url=None):
    with app.app_context():
        db.session.add(Establishment(
            name=f"Studio {slug.title()}",
            slug=slug,
            category="salao",
            description="Espaço de teste para o diretório de estabelecimentos.",
            city="Curitiba",
            state="PR",
            cover_url=cover_url,
            is_active=True,
            onboarding_completed=True,
        ))
        db.session.commit()


def _card(html, slug):
    start = html.index(f'href="/estabelecimentos/{slug}"')
    return html[start:html.index("</a>", start)]


def test_card_keeps_cover_and_uses_type_block_without_it(app, client):
    _establishment(app, "com-capa", cover_url="https://cdn.example.com/capa.jpg")
    _establishment(app, "sem-capa")

    html = client.get("/estabelecimentos").get_data(as_text=True)

    with_cover = _card(html, "com-capa")
    assert '<img src="https://cdn.example.com/capa.jpg"' in with_cover
    assert "ds-media-type" not in with_cover

    without_cover = _card(html, "sem-capa")
    assert "<img" not in without_cover
    assert 'class="ds-media-type establishment-directory-card__type" aria-hidden="true"' in without_cover
    assert "Ainda sem fotos publicadas" in without_cover
    assert "establishment-directory-card__fallback" not in html
    assert "0 profissionais" in without_cover


def test_published_count_is_singular(app, client):
    _establishment(app, "unica")

    html = client.get("/estabelecimentos").get_data(as_text=True)

    assert "1 página publicada" in html
    assert "1 páginas publicadas" not in html
