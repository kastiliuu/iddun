from datetime import date

from app.extensions import db
from app.models.establishment import (
    Establishment,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile


def test_professional_can_exist_without_login_user(app):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Camila Rocha",
            slug="camila-rocha",
            primary_specialty="Cabelo",
            city="Curitiba",
            state="PR",
        )
        db.session.add(professional)
        db.session.commit()

        assert professional.id is not None
        assert professional.user_id is None


def test_professional_membership_preserves_identity_across_establishments(app):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Camila Rocha",
            slug="camila-rocha",
        )
        establishment_a = Establishment(name="Studio A", slug="studio-a")
        establishment_b = Establishment(name="Studio B", slug="studio-b")
        db.session.add_all([professional, establishment_a, establishment_b])
        db.session.flush()

        first = ProfessionalEstablishmentMembership(
            professional=professional,
            establishment=establishment_a,
            role_name="Cabeleireira",
            started_at=date(2025, 1, 1),
            ended_at=date(2026, 1, 1),
            status="inactive",
        )
        second = ProfessionalEstablishmentMembership(
            professional=professional,
            establishment=establishment_b,
            role_name="Cabeleireira",
            started_at=date(2026, 1, 2),
            status="active",
            is_primary=True,
        )
        db.session.add_all([first, second])
        db.session.commit()

        assert professional.id == first.professional_id == second.professional_id
        assert len(professional.memberships) == 2
