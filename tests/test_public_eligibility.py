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
