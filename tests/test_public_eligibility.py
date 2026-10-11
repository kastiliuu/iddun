from app.extensions import db
from app.models.establishment import Establishment
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile
from app.services.experience_service import (
    get_database_experience_by_slug,
)
from app.services.professional_service import (
    get_establishment_public_view,
    get_professional_profile_by_slug,
    list_establishments,
    list_professionals,
)


def _experience(
    professional,
    slug,
    *,
    establishment=None,
):
    return Experience(
        professional=professional,
        establishment=establishment,
        title=slug.replace("-", " ").title(),
        slug=slug,
        category="unhas",
        short_description="Elegibilidade pública",
        regular_price="150.00",
        price="120.00",
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )


def test_public_policy_hides_inactive_professional_everywhere(
    app,
):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Oculta",
            slug="profissional-oculta",
            is_active=False,
        )
        experience = _experience(
            professional,
            "experiencia-profissional-oculta",
        )

        db.session.add_all(
            [
                professional,
                experience,
            ]
        )
        db.session.commit()

        database_slugs = {
            item["slug"]
            for item in list_professionals()
            if item.get("source") == "database"
        }

        assert (
            "profissional-oculta"
            not in database_slugs
        )
        assert (
            get_professional_profile_by_slug(
                "profissional-oculta"
            )
            is None
        )
        assert (
            get_database_experience_by_slug(
                "experiencia-profissional-oculta"
            )
            is None
        )


def test_public_policy_hides_experience_from_inactive_establishment(
    app,
):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Ativa",
            slug="profissional-publica",
            is_active=True,
        )
        establishment = Establishment(
            name="Studio Oculto",
            slug="studio-oculto",
            is_active=False,
        )
        experience = _experience(
            professional,
            "experiencia-studio-oculto",
            establishment=establishment,
        )

        db.session.add_all(
            [
                professional,
                establishment,
                experience,
            ]
        )
        db.session.commit()

        assert (
            get_database_experience_by_slug(
                "experiencia-studio-oculto"
            )
            is None
        )
        assert (
            get_establishment_public_view(
                "studio-oculto"
            )
            is None
        )

        establishment_slugs = {
            item.slug
            for item in list_establishments()
        }

        assert (
            "studio-oculto"
            not in establishment_slugs
        )


def test_public_policy_keeps_active_entities_visible(
    app,
):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Pública",
            slug="profissional-publica-ok",
            is_active=True,
        )
        establishment = Establishment(
            name="Studio Público",
            slug="studio-publico",
            is_active=True,
        )
        experience = _experience(
            professional,
            "experiencia-publica",
            establishment=establishment,
        )

        db.session.add_all(
            [
                professional,
                establishment,
                experience,
            ]
        )
        db.session.commit()

        assert (
            get_professional_profile_by_slug(
                "profissional-publica-ok"
            )
            is not None
        )
        assert (
            get_establishment_public_view(
                "studio-publico"
            )
            is not None
        )
        assert (
            get_database_experience_by_slug(
                "experiencia-publica"
            )
            is not None
        )


def test_professional_directory_search_stays_in_directory(
    client, monkeypatch,
):
    items = [
        {
            "name": "Ana Silva",
            "role": "Nail designer",
            "location": "Curitiba, PR",
            "specialties": ["Unhas em gel"],
            "slug": "ana-silva",
            "image": "img/category-nails.jpg",
            "rating": "0",
            "reviews": "0",
        },
        {
            "name": "Beatriz Costa",
            "role": "Cabeleireira",
            "location": "Londrina, PR",
            "specialties": ["Corte"],
            "slug": "beatriz-costa",
            "image": "img/category-hair.jpg",
            "rating": "0",
            "reviews": "0",
        },
    ]
    monkeypatch.setattr(
        "app.routes.public.list_professionals",
        lambda: items,
    )

    page = client.get("/profissionais?q=Unhas")
    assert page.status_code == 200
    assert b"Ana Silva" in page.data
    assert b"Beatriz Costa" not in page.data
    assert b'action="/profissionais"' in page.data

    by_city = client.get("/profissionais?q=londrina")
    assert by_city.status_code == 200
    assert b"Beatriz Costa" in by_city.data
    assert b"Ana Silva" not in by_city.data

    empty = client.get("/profissionais?q=sem-correspondencia")
    assert empty.status_code == 200
    assert "Nenhum profissional encontrado".encode() in empty.data
    assert b'href="/profissionais"' in empty.data


def test_establishment_directory_search_filters_public_results(
    client, monkeypatch,
):
    from types import SimpleNamespace

    establishments = [
        SimpleNamespace(
            name="Studio Aurora",
            slug="studio-aurora",
            category="salao",
            neighborhood="Batel",
            city="Curitiba",
            state="PR",
            active_memberships=[],
            cover_url=None,
            logo_url=None,
        ),
        SimpleNamespace(
            name="Barbearia Horizonte",
            slug="barbearia-horizonte",
            category="barbearia",
            neighborhood="Centro",
            city="Londrina",
            state="PR",
            active_memberships=[],
            cover_url=None,
            logo_url=None,
        ),
    ]
    monkeypatch.setattr(
        "app.routes.public.list_establishments",
        lambda: establishments,
    )

    by_neighborhood = client.get("/estabelecimentos?q=batel")
    assert by_neighborhood.status_code == 200
    assert b"Studio Aurora" in by_neighborhood.data
    assert b"Barbearia Horizonte" not in by_neighborhood.data
    assert b'action="/estabelecimentos"' in by_neighborhood.data

    by_category = client.get("/estabelecimentos?q=BARBEARIA")
    assert by_category.status_code == 200
    assert b"Barbearia Horizonte" in by_category.data
    assert b"Studio Aurora" not in by_category.data

    unmatched = client.get("/estabelecimentos?q=sem-resultado")
    assert unmatched.status_code == 200
    assert b"Nenhum estabelecimento encontrado." in unmatched.data
    assert b'href="/estabelecimentos"' in unmatched.data
    assert b"Os primeiros estabelecimentos est" not in unmatched.data


def test_establishment_directory_without_real_list_uses_launch_empty_state(
    client, monkeypatch,
):
    monkeypatch.setattr(
        "app.routes.public.list_establishments",
        lambda: [],
    )
    response = client.get("/estabelecimentos")
    assert response.status_code == 200
    assert b"Os primeiros estabelecimentos est" in response.data
