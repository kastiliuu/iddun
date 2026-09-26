def test_production_does_not_publish_prototype_catalog(app, client):
    app.config["APP_ENV"] = "production"

    assert client.get("/experiencias").status_code == 200
    assert "Hair Experience" not in client.get("/experiencias").get_data(as_text=True)
    assert client.get("/experiencias/hair-experience-camila-rocha").status_code == 404

    assert client.get("/profissionais").status_code == 200
    assert "Camila Rocha" not in client.get("/profissionais").get_data(as_text=True)
    assert client.get("/profissionais/camila-rocha").status_code == 404

    home = client.get("/").get_data(as_text=True)
    assert "Lume Beauty Studio" not in home

    from app.services.experience_service import list_locations

    with app.app_context():
        assert list_locations() == []


def test_development_keeps_prototype_catalog(app, client):
    app.config["APP_ENV"] = "development"

    assert client.get("/experiencias/hair-experience-camila-rocha").status_code == 200
    assert client.get("/profissionais/camila-rocha").status_code == 200
