def test_experiences_page_returns_200(client):
    response = client.get("/experiencias")

    assert response.status_code == 200
    assert b"Encontre sua pr" in response.data
    assert b"Hair Experience" in response.data


def test_experiences_can_filter_category(client):
    response = client.get("/experiencias?categoria=unhas")

    assert response.status_code == 200
    assert b"Nail Experience" in response.data
    assert b"Corte + Barba" not in response.data


def test_experience_detail_returns_200(client):
    response = client.get("/experiencias/hair-experience-camila-rocha")

    assert response.status_code == 200
    assert b"Hair Experience" in response.data


def test_experiences_uses_explicit_featured_card_above_uniform_grid(client):
    response = client.get("/experiencias")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert html.count('class="catalog-featured"') == 1
    assert html.count('class="catalog-card card"') == 8
    assert "Destaque da semana" in html


def test_experiences_header_search_uses_dialog_instead_of_inline_input(client):
    response = client.get("/experiencias")
    html = response.get_data(as_text=True)

    assert "data-header-search-dialog" in html
    assert "data-header-search-open" in html
    assert 'class="search-shell"' not in html


def test_experiences_empty_state_is_available_for_no_results(client):
    response = client.get("/experiencias?q=servico-inexistente")

    assert response.status_code == 200
    assert "Nenhuma experiência encontrada para esse filtro" in response.get_data(as_text=True)


def test_health_check_validates_database_connection(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
