"""Security regression tests for tenant isolation in the Business web dashboard.

These tests intentionally use real Flask requests and SQLite-backed test records.
PostgreSQL concurrency checks remain a separate QA-01 deliverable.
"""

import pytest

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


def _user(email, *, is_pro=False):
    user = User(
        name=email.split("@")[0],
        email=email,
        role=UserRole.PROFESSIONAL if is_pro else UserRole.CLIENT,
    )
    user.set_password("qa-strong-password")
    db.session.add(user)
    db.session.flush()
    if is_pro:
        db.session.add(
            ProfessionalProfile(
                user_id=user.id,
                display_name="Profissional QA",
                slug=f"qa-pro-{user.id}",
                primary_specialty="Nail Designer",
                is_active=True,
                onboarding_completed=True,
            )
        )
        db.session.flush()
    return user


def _establishment(slug):
    item = Establishment(
        name=f"Studio {slug}",
        slug=slug,
        category="unhas",
        city="Curitiba",
        state="PR",
        is_active=True,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _grant(user, establishment, *, status=EstablishmentAccessStatus.ACTIVE):
    db.session.add(
        EstablishmentUserAccess(
            user_id=user.id,
            establishment_id=establishment.id,
            role=EstablishmentAccessRole.OWNER,
            status=status,
        )
    )
    db.session.flush()


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


@pytest.fixture()
def two_businesses(app):
    with app.app_context():
        owner_a = _user("tenant-a-qa@example.com")
        owner_b = _user("tenant-b-qa@example.com")
        outsider = _user("tenant-outsider-qa@example.com")
        professional = _user("tenant-pro-qa@example.com", is_pro=True)
        a = _establishment("tenant-a-qa")
        b = _establishment("tenant-b-qa")
        _grant(owner_a, a)
        _grant(owner_b, b)
        for place, slug, title in [
            (a, "qa-service-a", "Serviço exclusivo empresa Alfa"),
            (b, "qa-service-b", "Serviço exclusivo empresa Beta"),
        ]:
            db.session.add(
                Experience(
                    professional_id=professional.professional_profile.id,
                    establishment_id=place.id,
                    title=title,
                    slug=slug,
                    category="unhas",
                    short_description="Serviço específico deste estabelecimento.",
                    regular_price="90.00",
                    price="80.00",
                    duration_minutes=60,
                    status=ExperienceStatus.PUBLISHED,
                )
            )
        db.session.commit()
        return {
            "a": a.slug,
            "b": b.slug,
            "owner_a": owner_a.id,
            "owner_b": owner_b.id,
            "outsider": outsider.id,
        }


def test_business_dashboard_isolates_catalog_between_establishments(
    client, two_businesses
):
    data = two_businesses
    _login(client, data["owner_a"])
    response = client.get(f'/business/{data["a"]}/painel')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Serviço exclusivo empresa Alfa" in html
    assert "Serviço exclusivo empresa Beta" not in html
    assert "qa-service-b" not in html


@pytest.mark.parametrize("actor", ["owner_b", "outsider"])
def test_non_member_cannot_read_other_business_dashboard(
    client, two_businesses, actor
):
    data = two_businesses
    _login(client, data[actor])
    response = client.get(f'/business/{data["a"]}/painel')
    assert response.status_code == 403
    assert "Serviço exclusivo empresa Alfa" not in response.get_data(
        as_text=True
    )


def test_non_member_cannot_edit_other_business(
    client, two_businesses
):
    data = two_businesses
    _login(client, data["owner_b"])
    response = client.get(f'/business/{data["a"]}/editar')
    assert response.status_code == 403


def test_revoked_access_is_denied_even_for_former_owner(
    app, client, two_businesses
):
    data = two_businesses
    with app.app_context():
        access = db.session.query(EstablishmentUserAccess).join(
            Establishment,
            EstablishmentUserAccess.establishment_id == Establishment.id,
        ).filter(
            Establishment.slug == data["a"],
            EstablishmentUserAccess.user_id == data["owner_a"],
        ).one()
        access.status = EstablishmentAccessStatus.INACTIVE
        db.session.commit()

    _login(client, data["owner_a"])
    assert client.get(f'/business/{data["a"]}/painel').status_code == 403
    assert client.get(f'/business/{data["a"]}/editar').status_code == 403
