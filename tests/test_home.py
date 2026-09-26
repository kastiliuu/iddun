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

    assert "Tatuagem" in text

    assert (
        "category-tattoo.svg"
        in text
    )


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

    # Official discovery taxonomy exposed by the Home.
    assert "Cabelo" in text
    assert "Unhas" in text
    assert "Barbearia" in text
    assert "Estética" in text
    assert "Tatuagem" in text
    assert "Sobrancelhas" in text

    # Categories that were previously visual-only now point
    # to real marketplace filter values.
    assert (
        "categoria=estetica"
        in text
    )

    assert (
        "categoria=sobrancelhas"
        in text
    )

    # Prototype fallback remains available until the
    # production establishment catalog is populated.
    assert "Lume Beauty Studio" in text

    # App promotional section.
    assert (
        "O IDDUN também"
        in text
    )

    assert (
        "Em breve na"
        in text
    )

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


def test_home_exposes_how_it_works_anchor_and_safe_footer_links(
    client,
):
    response = client.get("/")

    text = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # Header/footer links that point to #como-funciona must
    # have a real destination on the page.
    assert (
        'id="como-funciona"'
        in text
    )

    assert (
        'href="#como-funciona"'
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

    assert (
        'aria-label="Termos de uso — em breve"'
        in text
    )

    assert (
        'aria-label="Instagram do IDDUN — em breve"'
        in text
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
        'data-app-parallax'
        in text
    )

    assert (
        "Avaliações verificadas"
        in text
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