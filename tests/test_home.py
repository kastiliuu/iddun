import re

from app.extensions import db
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


def test_home_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200

    text = response.get_data(
        as_text=True
    )

    assert "IDDUN" in text
    assert "Descubra sua" in text

    assert (
        "Profissionais em destaque"
        in text
    )

    assert (
        "Estabelecimentos em destaque"
        in text
    )

    assert "Conexões reais. Histórias que inspiram." in text
    assert "category-tattoo.svg" not in text


def test_home_search_categories_and_marketplace_sections(
    client,
):
    response = client.get("/")

    text = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # Main discovery search.
    assert 'name="q"' in text
    assert 'name="bairro"' in text

    # Date is intentionally not submitted by the Home anymore.
    # Availability is chosen after opening a real experience.
    assert 'name="data"' not in text

    assert (
        "Escolha o horário na próxima etapa"
        in text
    )

    # Marketplace categories now belong to Discover rather than the public landing.
    assert 'class="home-v4-category-grid"' not in text
    assert 'id="home-institutional-title"' in text
    assert 'href="/profissionais"' in text
    assert 'href="/estabelecimentos"' in text

    # Prototype fallback remains available until the
    # production establishment catalog is populated.
    assert "Lume Beauty Studio" in text

    # Real community counts replace the old promotional sections.
    assert (
        'class="home-v4-stats"'
        in text
    )

    assert (
        'data-count-to="0"'
        in text
    )

    assert "Pessoas cadastradas" in text
    assert "Perfis profissionais ativos" in text
    assert "Estabelecimentos ativos" in text
    assert "O IDDUN também" not in text
    assert "Em breve na" not in text

    # Favorites start inactive.
    assert (
        'aria-pressed="false"'
        in text
    )


def test_home_search_suggestions_use_searchable_values(
    client,
):
    response = client.get("/")

    text = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # Visible editorial labels can be richer than the actual
    # query sent to the marketplace.
    assert (
        "Corte e tratamento"
        in text
    )

    assert (
        "Manicure e nail art"
        in text
    )

    assert (
        "Corte e barba"
        in text
    )

    assert (
        "Gel e esmaltação"
        in text
    )

    # Search values are intentionally broad terms that exist
    # in the current catalog and can produce useful results.
    assert (
        'data-search-value="corte"'
        in text
    )

    assert (
        'data-search-value="unhas"'
        in text
    )

    assert (
        'data-search-value="barba"'
        in text
    )

    assert (
        'data-search-value="gel"'
        in text
    )

    # Do not send the old editorial phrases as literal search
    # values, because they could lead to an empty result set.
    assert (
        'data-search-value="Corte e tratamento"'
        not in text
    )

    assert (
        'data-search-value="Manicure e nail art"'
        not in text
    )

    assert (
        'data-search-value="Corte e barba"'
        not in text
    )

    assert (
        'data-search-value="Design de sobrancelhas"'
        not in text
    )


def test_home_links_to_how_it_works_and_keeps_safe_footer_links(
    client,
):
    response = client.get("/")

    text = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # The old anchor is kept for existing bookmarks to the
    # community numbers; navigation now opens the full guide.
    assert (
        'id="como-funciona"'
        in text
    )

    assert (
        'href="/como-funciona"'
        in text
    )

    # Current IDDUN positioning replaces the old temporary
    # English tagline.
    assert (
        "Mais que beleza. Conexões reais."
        in text
    )

    assert (
        "Beauty for a brighter you"
        not in text
    )

    # The footer must not fake links to pages or social profiles
    # that do not exist yet.
    assert (
        'href="#"'
        not in text
    )

    assert (
        'aria-label="Central de ajuda — em breve"'
        in text
    )

    assert (
        'aria-label="Segurança — em breve"'
        in text
    )

    assert 'href="/privacidade"' in text
    assert 'href="/termos"' in text

    assert (
        'aria-label="Instagram do IDDUN — em breve"'
        in text
    )


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


def test_home_exposes_new_brand_interactions_and_accessible_states(
    client,
):
    response = client.get("/")

    text = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert "Mais que beleza" in text

    assert (
        'role="combobox"'
        in text
    )

    assert (
        'data-search-suggestion'
        in text
    )

    assert (
        'data-favorite-id='
        in text
    )

    assert (
        'data-avatar-image'
        in text
    )

    assert (
        'data-horizontal-rail'
        in text
    )

    assert (
        'data-rail-progress'
        in text
    )

    assert (
        'data-rail-skeleton-template'
        in text
    )

    assert (
        'data-hero-item'
        in text
    )

    assert (
        'data-count-to='
        in text
    )

    assert (
        "Avaliações verificadas"
        not in text
    )


def test_home_counts_real_active_records_without_prototype_cards(app, client):
    with app.app_context():
        db.session.add_all(
            [
                User(
                    name="Cliente ativo",
                    email="active-client@example.com",
                    password_hash="test",
                    role=UserRole.CLIENT,
                    is_active_account=True,
                ),
                User(
                    name="Profissional ativo",
                    email="active-pro@example.com",
                    password_hash="test",
                    role=UserRole.PROFESSIONAL,
                    is_active_account=True,
                ),
                User(
                    name="Administrador",
                    email="admin-count@example.com",
                    password_hash="test",
                    role=UserRole.ADMIN,
                    is_active_account=True,
                ),
                User(
                    name="Cliente desativado",
                    email="inactive-client@example.com",
                    password_hash="test",
                    role=UserRole.CLIENT,
                    is_active_account=False,
                ),
                ProfessionalProfile(
                    display_name="Profissional publicado",
                    slug="active-pro-count",
                    is_active=True,
                ),
                ProfessionalProfile(
                    display_name="Profissional desativado",
                    slug="inactive-pro-count",
                    is_active=False,
                ),
                Establishment(
                    name="Estabelecimento publicado",
                    slug="active-establishment-count",
                    is_active=True,
                ),
                Establishment(
                    name="Estabelecimento desativado",
                    slug="inactive-establishment-count",
                    is_active=False,
                ),
            ]
        )
        db.session.commit()

    response = client.get("/")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    for count, label in (
        (2, "Pessoas cadastradas"),
        (1, "Perfis profissionais ativos"),
        (1, "Estabelecimentos ativos"),
    ):
        assert re.search(
            rf'data-count-to="{count}">{count}</span>\s*</strong>'
            rf'\s*<span class="home-v4-stats__label">{label}</span>',
            text,
        )


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
