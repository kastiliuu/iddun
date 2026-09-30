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


def test_catalog_presence_uses_public_eligibility_rules(app):
    from sqlalchemy import select

    from app.extensions import db
    from app.models.establishment import Establishment
    from app.models.experience import Experience, ExperienceStatus
    from app.models.professional import ProfessionalProfile
    from app.services.experience_service import catalog_has_experiences

    app.config["APP_ENV"] = "production"

    with app.app_context():
        assert catalog_has_experiences() is False

        professional = ProfessionalProfile(
            display_name="Profissional do Catálogo",
            slug="profissional-do-catalogo",
            is_active=True,
        )
        experience = Experience(
            professional=professional,
            title="Experiência Publicável",
            slug="experiencia-publicavel",
            category="cabelo",
            short_description="Experiência real para validar o catálogo.",
            regular_price="200.00",
            price="150.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add_all([professional, experience])
        db.session.commit()

        assert catalog_has_experiences() is True

        professional.is_active = False
        db.session.commit()

        assert catalog_has_experiences() is False

        professional.is_active = True
        establishment = Establishment(
            name="Studio Inativo do Catálogo",
            slug="studio-inativo-do-catalogo",
            is_active=False,
        )
        db.session.add(establishment)
        db.session.flush()
        experience.establishment_id = establishment.id
        db.session.commit()

        assert catalog_has_experiences() is False

        saved = db.session.scalar(
            select(Experience).where(Experience.id == experience.id)
        )
        assert saved.status == ExperienceStatus.PUBLISHED
