import re


def test_experiences_page_returns_200(
    client,
):
    response = client.get(
        "/experiencias"
    )

    assert response.status_code == 200

    assert (
        b"Encontre sua pr"
        in response.data
    )

    assert (
        b"Hair Experience"
        in response.data
    )


def test_experiences_can_filter_category(
    client,
):
    response = client.get(
        "/experiencias?categoria=unhas"
    )

    assert response.status_code == 200

    assert (
        b"Nail Experience"
        in response.data
    )

    assert (
        b"Corte + Barba"
        not in response.data
    )


def test_experiences_exposes_official_categories(
    client,
):
    response = client.get(
        "/experiencias"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert (
        'data-category-filter="cabelo"'
        in html
    )

    assert (
        'data-category-filter="unhas"'
        in html
    )

    assert (
        'data-category-filter="barbearia"'
        in html
    )

    assert (
        'data-category-filter="estetica"'
        in html
    )

    assert (
        'data-category-filter="tatuagem"'
        in html
    )

    assert (
        'data-category-filter="sobrancelhas"'
        in html
    )

    assert "Cabelo" in html
    assert "Unhas" in html
    assert "Barbearia" in html
    assert "Estética" in html
    assert "Tatuagem" in html
    assert "Sobrancelhas" in html


def test_experiences_accepts_city_as_location_filter(
    client,
):
    response = client.get(
        "/experiencias?bairro=Curitiba"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # The location field promises "Cidade ou bairro".
    # Curitiba must therefore return experiences whose city
    # matches, even when they also have a neighborhood.
    assert (
        "Hair Experience"
        in html
    )

    assert (
        "Nail Experience"
        in html
    )

    assert (
        "Corte + Barba"
        in html
    )


def test_experiences_accepts_neighborhood_as_location_filter(
    client,
):
    response = client.get(
        "/experiencias?bairro=Batel"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert (
        "Hair Experience"
        in html
    )

    assert (
        "Corte &amp; Styling"
        in html
        or "Corte & Styling"
        in html
    )

    assert (
        "Executive Barber"
        in html
    )

    # Experiences from other neighborhoods must not leak into
    # the filtered result.
    assert (
        "Nail Experience"
        not in html
    )

    assert (
        "Corte + Barba"
        not in html
    )


def test_experiences_location_filter_ignores_accents(
    client,
):
    response = client.get(
        "/experiencias?bairro=Agua+Verde"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # "Agua Verde" must match the stored "Água Verde".
    assert (
        "Nail Experience"
        in html
    )

    assert (
        "Nail Art Signature"
        in html
    )

    assert (
        "Hair Experience"
        not in html
    )


def test_experiences_search_ignores_accents(
    client,
):
    response = client.get(
        "/experiencias?q=Agua+Verde"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert (
        "Nail Experience"
        in html
    )

    assert (
        "Nail Art Signature"
        in html
    )


def test_experience_detail_returns_200(
    client,
):
    response = client.get(
        "/experiencias/hair-experience-camila-rocha"
    )

    assert response.status_code == 200

    assert (
        b"Hair Experience"
        in response.data
    )


def test_experiences_uses_explicit_featured_card_above_uniform_grid(
    client,
):
    response = client.get(
        "/experiencias"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert (
        html.count(
            'class="catalog-featured"'
        )
        == 1
    )

    assert (
        html.count(
            'class="catalog-card card"'
        )
        == 8
    )

    assert (
        "Destaque IDDUN"
        in html
    )


def test_featured_experience_is_not_repeated_in_regular_grid(
    client,
):
    response = client.get(
        "/experiencias"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    featured = re.search(
        r'<article[^>]*class="catalog-featured"[^>]*data-title="([^"]+)"',
        html,
        re.DOTALL,
    )

    assert featured is not None

    featured_title = featured.group(1)

    assert (
        html.count(
            f'data-title="{featured_title}"'
        )
        == 1
    )


def test_experiences_header_search_uses_dialog_instead_of_inline_input(
    client,
):
    response = client.get(
        "/experiencias"
    )

    html = response.get_data(
        as_text=True
    )

    assert (
        "data-header-search-dialog"
        in html
    )

    assert (
        "data-header-search-open"
        in html
    )

    assert (
        'class="search-shell"'
        not in html
    )


def test_global_styles_define_screen_reader_only_utility(
    client,
):
    response = client.get(
        "/static/css/base.css"
    )

    css = response.get_data(
        as_text=True
    )

    assert response.status_code == 200
    assert ".sr-only {" in css

    required_declarations = (
        "position: absolute;",
        "width: 1px;",
        "height: 1px;",
        "overflow: hidden;",
        "clip: rect(0, 0, 0, 0);",
        "white-space: nowrap;",
    )

    for declaration in required_declarations:
        assert declaration in css

    page = client.get(
        "/experiencias"
    ).get_data(
        as_text=True
    )

    assert page.count(
        'class="sr-only"'
    ) >= 6

    filtered_page = client.get(
        "/experiencias?bairro=Batel"
    ).get_data(
        as_text=True
    )

    assert filtered_page.count(
        'class="sr-only"'
    ) >= 7


def test_experiences_filter_toolbar_has_accessible_landmarks(
    client,
):
    response = client.get(
        "/experiencias"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    assert (
        'aria-label="Filtros de descoberta"'
        in html
    )

    assert (
        'aria-label="Filtrar por categoria"'
        in html
    )

    assert (
        'aria-label="Refinar resultados"'
        in html
    )

    assert 'aria-current="page"' in html


def test_experiences_empty_state_is_available_for_no_results(
    client,
):
    response = client.get(
        "/experiencias?q=servico-inexistente"
    )

    assert response.status_code == 200

    html = response.get_data(
        as_text=True
    )

    assert (
        "Ainda não encontramos algo para essa busca."
        in html
    )

    assert (
        "Ver tudo"
        in html
    )


def test_empty_official_category_keeps_marketplace_available(
    client,
):
    response = client.get(
        "/experiencias?categoria=estetica"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # Estética is officially supported even when the current
    # prototype catalog has no item in that category yet.
    assert (
        'data-category-filter="estetica"'
        in html
    )

    assert (
        "Ainda não encontramos algo para essa busca."
        in html
    )


def test_health_check_validates_database_connection(
    client,
):
    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.get_json() == {
        "status": "ok"
    }
