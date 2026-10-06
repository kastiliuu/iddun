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


def _user(email, *, professional=False):
    user = User(
        name=email.split("@")[0],
        email=email,
        role=(
            UserRole.PROFESSIONAL
            if professional
            else UserRole.CLIENT
        ),
    )
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()

    if professional:
        profile = ProfessionalProfile(
            user_id=user.id,
            display_name=(
                f"Profissional {user.name}"
            ),
            slug=(
                f"pro-{user.id}"
            ),
            primary_specialty=(
                "Nail Designer"
            ),
        )
        db.session.add(profile)
        db.session.flush()

    return user


def _establishment(slug):
    establishment = Establishment(
        name=f"Studio {slug}",
        slug=slug,
        city="Curitiba",
        state="PR",
    )
    db.session.add(establishment)
    db.session.flush()
    return establishment


def _grant_access(
    user,
    establishment,
    role=EstablishmentAccessRole.OWNER,
):
    access = EstablishmentUserAccess(
        user_id=user.id,
        establishment_id=establishment.id,
        role=role,
        status=EstablishmentAccessStatus.ACTIVE,
    )
    db.session.add(access)
    db.session.flush()
    return access


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_team_api_requires_authentication(client):
    response = client.get(
        "/api/v1/team/invitations"
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == (
        "authentication_required"
    )


def test_owner_can_invite_professional_and_list_pending_team(
    app,
    client,
):
    with app.app_context():
        owner = _user(
            "owner-team@example.com"
        )
        professional_user = _user(
            "member-team@example.com",
            professional=True,
        )
        establishment = _establishment(
            "team-studio"
        )
        _grant_access(
            owner,
            establishment,
        )
        db.session.commit()

        owner_id = owner.id
        professional_email = (
            professional_user.email
        )
        establishment_slug = (
            establishment.slug
        )

    _login(client, owner_id)

    response = client.post(
        (
            f"/api/v1/establishments/"
            f"{establishment_slug}/team"
        ),
        json={
            "email": professional_email,
            "roleName": "Nail Designer",
        },
    )

    assert response.status_code == 201
    membership = response.get_json()[
        "membership"
    ]
    assert membership["status"] == (
        MembershipStatus.PENDING
    )
    assert membership["roleName"] == (
        "Nail Designer"
    )

    listing = client.get(
        (
            f"/api/v1/establishments/"
            f"{establishment_slug}/team"
        )
    )

    assert listing.status_code == 200
    payload = listing.get_json()
    assert payload["accessRole"] == (
        EstablishmentAccessRole.OWNER
    )
    assert len(payload["items"]) == 1
    assert payload["items"][0]["status"] == (
        MembershipStatus.PENDING
    )


def test_professional_can_accept_pending_invitation(
    app,
    client,
):
    with app.app_context():
        owner = _user(
            "owner-accept@example.com"
        )
        professional_user = _user(
            "pro-accept@example.com",
            professional=True,
        )
        establishment = _establishment(
            "accept-studio"
        )
        _grant_access(
            owner,
            establishment,
        )

        membership = (
            ProfessionalEstablishmentMembership(
                professional_id=(
                    professional_user
                    .professional_profile.id
                ),
                establishment_id=(
                    establishment.id
                ),
                role_name="Cabeleireiro",
                status=MembershipStatus.PENDING,
            )
        )
        db.session.add(membership)
        db.session.commit()

        professional_user_id = (
            professional_user.id
        )
        membership_id = membership.id

    _login(
        client,
        professional_user_id,
    )

    invites = client.get(
        "/api/v1/team/invitations"
    )
    assert invites.status_code == 200
    assert len(
        invites.get_json()["items"]
    ) == 1

    response = client.put(
        (
            f"/api/v1/team/invitations/"
            f"{membership_id}/accept"
        )
    )

    assert response.status_code == 200
    payload = response.get_json()[
        "membership"
    ]
    assert payload["status"] == (
        MembershipStatus.ACTIVE
    )
    assert payload["isPrimary"] is True


def test_professional_can_reject_pending_invitation(
    app,
    client,
):
    with app.app_context():
        professional_user = _user(
            "pro-reject@example.com",
            professional=True,
        )
        establishment = _establishment(
            "reject-studio"
        )
        membership = (
            ProfessionalEstablishmentMembership(
                professional_id=(
                    professional_user
                    .professional_profile.id
                ),
                establishment_id=(
                    establishment.id
                ),
                status=MembershipStatus.PENDING,
            )
        )
        db.session.add(membership)
        db.session.commit()

        user_id = professional_user.id
        membership_id = membership.id

    _login(client, user_id)

    response = client.put(
        (
            f"/api/v1/team/invitations/"
            f"{membership_id}/reject"
        )
    )

    assert response.status_code == 200
    payload = response.get_json()[
        "membership"
    ]
    assert payload["status"] == (
        MembershipStatus.REJECTED
    )
    assert payload["isPrimary"] is False


def test_manager_can_remove_active_team_member(
    app,
    client,
):
    with app.app_context():
        manager = _user(
            "manager-remove@example.com"
        )
        professional_user = _user(
            "pro-remove@example.com",
            professional=True,
        )
        establishment = _establishment(
            "remove-studio"
        )
        _grant_access(
            manager,
            establishment,
            role=EstablishmentAccessRole.MANAGER,
        )

        membership = (
            ProfessionalEstablishmentMembership(
                professional_id=(
                    professional_user
                    .professional_profile.id
                ),
                establishment_id=(
                    establishment.id
                ),
                status=MembershipStatus.ACTIVE,
                is_primary=True,
            )
        )
        db.session.add(membership)
        db.session.commit()

        manager_id = manager.id
        establishment_slug = (
            establishment.slug
        )
        membership_id = membership.id

    _login(client, manager_id)

    response = client.delete(
        (
            f"/api/v1/establishments/"
            f"{establishment_slug}/team/"
            f"{membership_id}"
        )
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["removed"] is True
    assert payload["membership"]["status"] == (
        MembershipStatus.INACTIVE
    )


def test_user_without_business_access_cannot_manage_team(
    app,
    client,
):
    with app.app_context():
        user = _user(
            "no-access@example.com"
        )
        establishment = _establishment(
            "private-team-studio"
        )
        db.session.commit()

        user_id = user.id
        establishment_slug = (
            establishment.slug
        )

    _login(client, user_id)

    response = client.get(
        (
            f"/api/v1/establishments/"
            f"{establishment_slug}/team"
        )
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == (
        "team_access_denied"
    )
