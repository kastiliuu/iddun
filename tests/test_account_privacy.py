from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.user import User


def _register(client, email="privacy@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Conta Privacidade",
            "email": email,
            "password": "senha-forte-123",
            "role": "client",
        },
    )

    assert response.status_code == 201

    return response.get_json()


def _bearer(token):
    return {
        "Authorization": (
            f"Bearer {token}"
        )
    }


def test_delete_account_rejects_wrong_password(
    app,
    client,
):
    registered = _register(
        client
    )

    response = client.post(
        "/api/v1/account/delete",
        json={
            "password": "senha-errada",
        },
        headers=_bearer(
            registered["accessToken"]
        ),
    )

    assert response.status_code == 401
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "invalid_credentials"
    )

    with app.app_context():
        user = db.session.scalar(
            select(User).where(
                User.email
                == "privacy@example.com"
            )
        )

        assert user is not None
        assert user.is_active
        assert user.deleted_at is None


def test_delete_account_anonymizes_identity_and_revokes_session(
    app,
    client,
):
    registered = _register(
        client
    )

    with app.app_context():
        user = db.session.scalar(
            select(User).where(
                User.email
                == "privacy@example.com"
            )
        )

        profile = (
            user.client_profile
        )
        profile.phone = (
            "(41) 99999-9999"
        )
        profile.city = "Curitiba"
        profile.state = "PR"
        db.session.commit()

        user_id = user.id

    response = client.post(
        "/api/v1/account/delete",
        json={
            "password": "senha-forte-123",
        },
        headers=_bearer(
            registered["accessToken"]
        ),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "deleted": True,
        "anonymized": True,
    }

    assert client.get(
        "/api/v1/auth/me",
        headers=_bearer(
            registered["accessToken"]
        ),
    ).status_code == 401

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        assert user is not None
        assert not user.is_active
        assert user.deleted_at is not None
        assert (
            user.name
            == "Conta removida"
        )
        assert user.email.startswith(
            (
                "deleted-"
                f"{user_id}-"
            )
        )
        assert user.email.endswith(
            "@deleted.iddun.invalid"
        )
        assert (
            user.email_verified_at
            is None
        )

        profile = (
            user.client_profile
        )

        assert profile is not None
        assert profile.phone is None
        assert profile.birth_date is None
        assert profile.city is None
        assert profile.state is None
        assert profile.avatar_url is None
        assert (
            profile.onboarding_completed
            is False
        )


def test_delete_account_requires_owner_transfer(
    app,
    client,
):
    registered = _register(
        client,
        email=(
            "owner@example.com"
        ),
    )

    with app.app_context():
        user = db.session.scalar(
            select(User).where(
                User.email
                == "owner@example.com"
            )
        )

        establishment = (
            Establishment(
                name="Studio Owner",
                slug="studio-owner",
                is_active=True,
            )
        )

        db.session.add(
            establishment
        )
        db.session.flush()

        db.session.add(
            EstablishmentUserAccess(
                user_id=user.id,
                establishment_id=(
                    establishment.id
                ),
                role=(
                    EstablishmentAccessRole.OWNER
                ),
                status=(
                    EstablishmentAccessStatus.ACTIVE
                ),
            )
        )

        db.session.commit()

        user_id = user.id

    response = client.post(
        "/api/v1/account/delete",
        json={
            "password": "senha-forte-123",
        },
        headers=_bearer(
            registered["accessToken"]
        ),
    )

    assert response.status_code == 409

    payload = response.get_json()

    assert (
        payload["error"]["code"]
        == "ownership_transfer_required"
    )
    assert (
        payload["error"]["details"][
            "establishments"
        ]
        == ["Studio Owner"]
    )

    with app.app_context():
        user = db.session.get(
            User,
            user_id,
        )

        assert user is not None
        assert user.is_active
        assert user.deleted_at is None
