"""Rascunhos mobile seguem as mesmas regras de publicação e vínculo do web."""

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    ProfessionalEstablishmentMembership,
)
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.mobile_onboarding_service import (
    MobileOnboardingError,
    create_establishment_draft,
    create_professional_draft,
)


def _user(email="cliente@example.com"):
    user = User(
        name="Pessoa de Teste",
        email=email,
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")

    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()

    return user


def _professional_payload(user, **changes):
    values = {
        "user": user,
        "display_name": "Marina Rascunho",
        "primary_specialty": "Nail designer",
        "categories": ["unhas", "estetica"],
        "city": "Curitiba",
        "state": "PR",
        "bio": "Atendimento cuidadoso.",
        "phone": "41999999999",
    }
    values.update(changes)
    return values


def _business_payload(user, **changes):
    values = {
        "user": user,
        "name": "Ateliê Rascunho",
        "category": "unhas",
        "city": "Curitiba",
        "state": "PR",
        "description": "Um espaço para cuidar de você.",
        "neighborhood": "Batel",
    }
    values.update(changes)
    return values


def test_professional_draft_belongs_to_user_and_is_not_public(
    app,
    client,
):
    with app.app_context():
        user = _user()
        profile = create_professional_draft(
            **_professional_payload(user)
        )

        assert profile.user_id == user.id
        assert user.role == UserRole.CLIENT
        assert user.client_profile is not None
        assert profile.plan_tier == "free"
        assert profile.specialties_text == "Unhas, Estética"
        assert profile.onboarding_completed is False
        assert profile.published_at is None
        assert profile.is_active is False
        slug = profile.slug

    assert (
        client.get(f"/profissionais/{slug}").status_code
        == 404
    )


def test_professional_retry_does_not_create_another_profile(
    app,
):
    with app.app_context():
        user = _user()

        first = create_professional_draft(
            **_professional_payload(user)
        )
        second = create_professional_draft(
            **_professional_payload(user)
        )

        assert first.id == second.id
        assert db.session.scalar(
            select(func.count()).select_from(
                ProfessionalProfile
            )
        ) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"categories": []},
        {"categories": ["area-inexistente"]},
        {"state": "XXX"},
        {"display_name": "X"},
    ],
)
def test_professional_draft_rejects_invalid_data(
    app,
    changes,
):
    with app.app_context():
        user = _user()

        with pytest.raises(MobileOnboardingError):
            create_professional_draft(
                **_professional_payload(
                    user,
                    **changes,
                )
            )

        assert db.session.scalar(
            select(func.count()).select_from(
                ProfessionalProfile
            )
        ) == 0


def test_inactive_user_cannot_create_professional_draft(app):
    with app.app_context():
        user = _user()
        user.is_active_account = False
        db.session.commit()

        with pytest.raises(MobileOnboardingError):
            create_professional_draft(
                **_professional_payload(user)
            )


def test_business_draft_has_owner_but_no_professional_membership(
    app,
    client,
):
    with app.app_context():
        user = _user()
        establishment = create_establishment_draft(
            **_business_payload(user)
        )

        access = db.session.scalar(
            select(EstablishmentUserAccess).where(
                EstablishmentUserAccess.establishment_id
                == establishment.id,
                EstablishmentUserAccess.user_id
                == user.id,
            )
        )

        assert access is not None
        assert access.role == EstablishmentAccessRole.OWNER
        assert (
            access.status
            == EstablishmentAccessStatus.ACTIVE
        )
        assert user.role == UserRole.CLIENT
        assert establishment.plan_tier == "free"
        assert establishment.onboarding_completed is False
        assert establishment.published_at is None
        assert establishment.is_active is False
        assert db.session.scalar(
            select(func.count()).select_from(
                ProfessionalEstablishmentMembership
            )
        ) == 0

        slug = establishment.slug

    assert (
        client.get(f"/estabelecimentos/{slug}").status_code
        == 404
    )


def test_business_retry_keeps_the_same_owner_and_page(app):
    with app.app_context():
        user = _user()

        first = create_establishment_draft(
            **_business_payload(user)
        )
        second = create_establishment_draft(
            **_business_payload(user)
        )

        assert first.id == second.id
        assert db.session.scalar(
            select(func.count()).select_from(
                Establishment
            )
        ) == 1
        assert db.session.scalar(
            select(func.count()).select_from(
                EstablishmentUserAccess
            )
        ) == 1


def test_business_draft_rejects_unknown_category(app):
    with app.app_context():
        user = _user()

        with pytest.raises(MobileOnboardingError):
            create_establishment_draft(
                **_business_payload(
                    user,
                    category="categoria-inexistente",
                )
            )

        assert db.session.scalar(
            select(func.count()).select_from(
                Establishment
            )
        ) == 0


def test_same_client_can_own_business_and_professional_draft(
    app,
):
    with app.app_context():
        user = _user()

        profile = create_professional_draft(
            **_professional_payload(user)
        )
        establishment = create_establishment_draft(
            **_business_payload(user)
        )

        assert profile.user_id == user.id
        assert db.session.scalar(
            select(EstablishmentUserAccess).where(
                EstablishmentUserAccess.establishment_id
                == establishment.id,
                EstablishmentUserAccess.user_id
                == user.id,
            )
        ) is not None
        assert db.session.scalar(
            select(func.count()).select_from(
                ProfessionalEstablishmentMembership
            )
        ) == 0