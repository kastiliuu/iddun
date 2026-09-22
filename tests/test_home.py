def test_home_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"IDDUN" in response.data
    assert "Descubra sua" in response.get_data(as_text=True)
    assert "Profissionais em destaque" in response.get_data(as_text=True)
    assert "Salões e estúdios" in response.get_data(as_text=True)
    assert "Tatuagem" in response.get_data(as_text=True)
    assert "category-tattoo.svg" in response.get_data(as_text=True)


def test_home_search_categories_and_marketplace_sections(client):
    response = client.get("/")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Agendar agora" in text
    assert 'name="q"' in text
    assert 'name="bairro"' in text
    assert 'name="data"' in text
    assert "Sobrancelhas" in text
    assert "Lume Beauty Studio" in text
    assert "A beleza te acompanha" in text
    assert 'aria-pressed="false"' in text


def test_home_exposes_new_brand_interactions_and_accessible_states(client):
    response = client.get("/")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Mais que beleza" in text
    assert 'role="combobox"' in text
    assert 'data-search-suggestion' in text
    assert 'data-favorite-id=' in text
    assert 'data-avatar-image' in text
    assert 'data-horizontal-rail' in text
    assert "Avaliações confiáveis" in text


def test_professionals_page_returns_200(client):
    response = client.get("/profissionais")

    assert response.status_code == 200
    assert b"Camila Rocha" in response.data


def test_for_professionals_page_returns_200(client):
    response = client.get("/para-profissionais")

    assert response.status_code == 200
    assert "Seu trabalho merece um lugar próprio" in response.get_data(as_text=True)


def test_professional_detail_mock_returns_200(client):
    response = client.get("/profissionais/camila-rocha")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Camila Rocha" in text
    assert "Trabalhos recentes" in text


def test_establishments_directory_returns_200(client):
    response = client.get("/estabelecimentos")
    assert response.status_code == 200
    assert "Estabelecimentos" in response.get_data(as_text=True)
