"""Testes do contrato e do acesso à API de capacidades."""

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


ENDPOINT = "/api/v1/me/capabilities"


def _user(email):
    user = User(
        name=email.split("@")[0],
        email=email,
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    return user


def _professional(user, slug):
    profile = ProfessionalProfile(
        user_id=user.id,
        display_name=f"Profissional {slug}",
        slug=slug,
    )
    db.session.add(profile)
    db.session.flush()
    return profile


def _establishment(slug):
    establishment = Establishment(
        name=f"Studio {slug}",
        slug=slug,
    )
    db.session.add(establishment)
    db.session.flush()
    return establishment


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _assert_essential(payload, subject_type, required_capabilities):
    assert payload["subjectType"] == subject_type
    assert payload["effectivePlanCode"] == "essential"
    assert payload["assignedPlanCode"] == "essential"
    assert payload["subscriptionStatus"] == "active"
    assert payload["verificationError"] is False
    assert set(required_capabilities).issubset(payload["capabilities"])

    assert "reports.professional_advanced" not in payload["capabilities"]
    assert "reports.business_advanced" not in payload["capabilities"]


def test_capabilities_requires_an_authenticated_session(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"
    assert "no-store" in response.headers["Cache-Control"]


def test_capabilities_rejects_a_deactivated_account(app, client):
    with app.app_context():
        user = _user("inactive@example.com")
        db.session.commit()
        user_id = user.id

    _login_session(client, user_id)

    with app.app_context():
        user = db.session.get(User, user_id)
        user.is_active_account = False
        db.session.commit()

    response = client.get(ENDPOINT)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


def test_client_receives_basic_capabilities_without_extra_scopes(app, client):
    with app.app_context():
        user = _user("client@example.com")
        db.session.commit()
        user_id = user.id

    _login_session(client, user_id)
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]

    payload = response.get_json()

    _assert_essential(
        payload["client"],
        "client",
        {
            "catalog.discover",
            "bookings.create",
            "reviews.after_service",
        },
    )
    assert payload["professional"] is None
    assert payload["establishments"] == []


def test_professional_scope_belongs_only_to_the_signed_in_user(app, client):
    with app.app_context():
        own_user = _user("own-pro@example.com")
        own_profile = _professional(own_user, "own-pro")

        other_user = _user("other-pro@example.com")
        other_profile = _professional(other_user, "other-pro")

        db.session.commit()

        own_user_id = own_user.id
        own_profile_id = own_profile.id
        other_profile_id = other_profile.id

    _login_session(client, own_user_id)
    response = client.get(ENDPOINT)

    assert response.status_code == 200

    professional = response.get_json()["professional"]

    assert professional["id"] == own_profile_id
    assert professional["id"] != other_profile_id
    assert professional["isActive"] is True

    _assert_essential(
        professional["entitlements"],
        "professional",
        {
            "profile.public",
            "services.manage",
            "agenda.basic",
            "bookings.manage",
        },
    )


def test_only_active_owner_or_manager_access_exposes_business_scope(
    app,
    client,
):
    with app.app_context():
        user = _user("business@example.com")

        owner_business = _establishment("owner-business")
        manager_business = _establishment("manager-business")
        revoked_business = _establishment("revoked-business")
        unlinked_business = _establishment("unlinked-business")

        db.session.add_all(
            [
                EstablishmentUserAccess(
                    user_id=user.id,
                    establishment_id=owner_business.id,
                    role=EstablishmentAccessRole.OWNER,
                    status=EstablishmentAccessStatus.ACTIVE,
                ),
                EstablishmentUserAccess(
                    user_id=user.id,
                    establishment_id=manager_business.id,
                    role=EstablishmentAccessRole.MANAGER,
                    status=EstablishmentAccessStatus.ACTIVE,
                ),
                EstablishmentUserAccess(
                    user_id=user.id,
                    establishment_id=revoked_business.id,
                    role=EstablishmentAccessRole.MANAGER,
                    status=EstablishmentAccessStatus.INACTIVE,
                ),
            ]
        )
        db.session.commit()

        user_id = user.id
        business_ids = {
            owner_business.id: "owner",
            manager_business.id: "manager",
        }
        excluded_ids = {
            revoked_business.id,
            unlinked_business.id,
        }

    _login_session(client, user_id)
    response = client.get(ENDPOINT)

    assert response.status_code == 200

    establishments = response.get_json()["establishments"]
    returned_ids = {item["id"] for item in establishments}

    assert returned_ids == set(business_ids)
    assert returned_ids.isdisjoint(excluded_ids)

    for item in establishments:
        assert item["role"] == business_ids[item["id"]]
        assert item["isActive"] is True

        _assert_essential(
            item["entitlements"],
            "establishment",
            {
                "profile.public",
                "experiences.manage",
                "team.membership",
            },
        )


def test_pending_professional_invitation_does_not_grant_business_access(
    app,
    client,
):
    with app.app_context():
        user = _user("invited-pro@example.com")
        professional = _professional(user, "invited-pro")
        establishment = _establishment("inviting-business")

        db.session.add(
            ProfessionalEstablishmentMembership(
                professional_id=professional.id,
                establishment_id=establishment.id,
                status=MembershipStatus.PENDING,
            )
        )
        db.session.commit()
        user_id = user.id

    _login_session(client, user_id)
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.get_json()["professional"] is not None
    assert response.get_json()["establishments"] == []