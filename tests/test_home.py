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

    # Discovery categories.
    assert "Sobrancelhas" in text

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