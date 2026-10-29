import re

from app.extensions import db
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


def test_home_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "IDDUN" in html
    assert "Beleza abre portas." in html
    assert "Conexões criam histórias." in html
    assert "Profissionais no IDDUN" in html
    assert "Estabelecimentos no IDDUN" in html


def test_home_is_public_landing_with_account_entry_and_legal_links(client):
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'href="/login"' in html
    assert 'href="/cadastro"' in html
    assert 'href="/privacidade"' in html
    assert 'href="/termos"' in html
    assert 'href="/como-funciona"' in html
    assert "mailto:contato@iddun.com.br" in html
    assert 'href="#"' not in html
    assert "Aplicativos para iOS e Android em breve" in html
    assert "Redes sociais oficiais: em breve" not in html
    assert "Beauty for a brighter you" not in html


def test_home_search_opens_discovery_with_existing_filters(client):
    # D-HOME-04 (29/10/2026) revoga a D-HOME-01: a busca da Home abre o
    # Explorar com os filtros que ele já aceita (q e bairro).
    landing = client.get("/").get_data(as_text=True)
    form = re.search(r'<form class="landing-search"[^>]*>(.*?)</form>', landing, re.S)
    assert form, "busca da Home ausente"
    opening = re.search(r'<form class="landing-search"[^>]*>', landing).group(0)
    assert 'action="/experiencias"' in opening
    assert 'method="get"' in opening
    assert 'name="q"' in form.group(1)
    assert 'name="bairro"' in form.group(1)
    assert 'href="/cadastro"' in landing

    discovery = client.get("/experiencias?q=Corte&bairro=Batel")
    assert discovery.status_code == 200


def test_how_it_works_page_explains_current_and_planned_features(
    client,
):
    response = client.get("/como-funciona")

    assert response.status_code == 200
    text = response.get_data(as_text=True)

    assert "Um lugar para a beleza se encontrar." in text
    assert "Disponível agora" in text
    assert "Em desenvolvimento" in text
    assert "qualquer cliente pode reservar" in text
    assert "Vagas na área da beleza" in text
    assert "Visitas ao perfil" in text
    assert 'href="/static/css/how-it-works.css"' in text
    assert re.search(
        r'class="nav-link is-active"\s+aria-current="page"\s*>\s*Como funciona',
        text,
    )


def test_home_exposes_accessible_landing_sections(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="inicio"' in html
    assert 'id="comunidade"' in html
    assert 'id="profissionais"' in html
    assert 'id="estabelecimentos"' in html
    assert 'aria-label="Números reais da comunidade IDDUN"' in html
    assert 'href="#comunidade"' in html
    assert 'data-search-suggestion' not in html
    assert "Avaliações verificadas" not in html


def test_home_counts_real_active_records_without_prototype_cards(app, client):
    with app.app_context():
        db.session.add_all([
            User(name="Cliente ativo", email="active-client@example.com",
                 password_hash="test", role=UserRole.CLIENT, is_active_account=True),
            User(name="Profissional ativo", email="active-pro@example.com",
                 password_hash="test", role=UserRole.PROFESSIONAL, is_active_account=True),
            User(name="Administrador", email="admin-count@example.com",
                 password_hash="test", role=UserRole.ADMIN, is_active_account=True),
            User(name="Cliente desativado", email="inactive-client@example.com",
                 password_hash="test", role=UserRole.CLIENT, is_active_account=False),
            ProfessionalProfile(display_name="Profissional publicado",
                                slug="active-pro-count", is_active=True),
            ProfessionalProfile(display_name="Profissional desativado",
                                slug="inactive-pro-count", is_active=False),
            Establishment(name="Estabelecimento publicado",
                          slug="active-establishment-count", is_active=True),
            Establishment(name="Estabelecimento desativado",
                          slug="inactive-establishment-count", is_active=False),
        ])
        db.session.commit()

    html = client.get("/").get_data(as_text=True)
    assert 'class="landing-stats"' in html
    for value, label in (
        (2, "Pessoas cadastradas"),
        (1, "Profissionais ativos"),
        (1, "Estabelecimentos ativos"),
    ):
        assert re.search(
            rf"<strong>\s*{value}\s*</strong>\s*<span>{label}</span>",
            html,
        )
    assert "Profissional publicado" in html
    assert "Estabelecimento publicado" in html
    assert "Profissional desativado" not in html
    assert "Estabelecimento desativado" not in html
    assert "Camila Rocha" not in html
    assert "Lume Beauty Studio" not in html


def test_professionals_page_returns_200(
    client,
):
    response = client.get(
        "/profissionais"
    )

    assert response.status_code == 200

    assert (
        b"Camila Rocha"
        in response.data
    )


def test_for_professionals_page_returns_200(
    client,
):
    response = client.get(
        "/para-profissionais"
    )

    assert response.status_code == 200

    assert (
        "Seu trabalho merece um lugar próprio"
        in response.get_data(
            as_text=True
        )
    )


def test_professional_detail_mock_returns_200(
    client,
):
    response = client.get(
        "/profissionais/camila-rocha"
    )

    assert response.status_code == 200

    text = response.get_data(
        as_text=True
    )

    assert "Camila Rocha" in text

    assert (
        "Trabalhos recentes"
        in text
    )


def test_establishments_directory_returns_200(
    client,
):
    response = client.get(
        "/estabelecimentos"
    )

    assert response.status_code == 200

    assert (
        "Estabelecimentos"
        in response.get_data(
            as_text=True
        )
    )


def test_public_legal_pages_are_available(
    client,
):
    privacy = client.get(
        "/privacidade"
    )
    terms = client.get(
        "/termos"
    )

    assert privacy.status_code == 200
    assert terms.status_code == 200

    privacy_text = (
        privacy.get_data(
            as_text=True
        )
    )
    terms_text = (
        terms.get_data(
            as_text=True
        )
    )

    assert (
        "Política de Privacidade"
        in privacy_text
    )
    assert (
        "Versão pré-lançamento"
        in privacy_text
    )
    assert (
        "Termos de Uso"
        in terms_text
    )
    assert (
        "Versão pré-lançamento"
        in terms_text
    )
