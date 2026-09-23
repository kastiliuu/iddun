from datetime import date
from io import BytesIO

from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _create_user_without_profile(app):
    with app.app_context():
        user = User(name="Legacy User", email="legacy@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.commit()
        return user.id


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_account_lazily_creates_profile_for_legacy_user(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.get("/minha-conta")
    assert response.status_code == 200

    with app.app_context():
        profile = db.session.scalar(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        assert profile is not None


def test_account_profile_can_be_updated(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.post(
        "/minha-conta",
        data={
            "name": "Gabriel Atualizado",
            "phone": "41999999999",
            "birth_date": "1996-05-16",
            "city": "Curitiba",
            "state": "pr",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.name == "Gabriel Atualizado"
        assert user.client_profile.phone == "41999999999"
        assert user.client_profile.city == "Curitiba"
        assert user.client_profile.state == "PR"
        assert user.client_profile.onboarding_completed is True


def test_account_completion_uses_every_field_shown_on_the_page(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    client.get("/minha-conta")
    with app.app_context():
        user = db.session.get(User, user_id)
        user.client_profile.phone = "41999999999"
        user.client_profile.birth_date = date(1996, 5, 16)
        user.client_profile.city = "Curitiba"
        user.client_profile.state = "PR"
        user.client_profile.avatar_url = "uploads/clients/avatar.webp"
        db.session.commit()

    response = client.get("/minha-conta")

    assert response.status_code == 200
    assert b'data-progress="100"' in response.data
    assert "Tudo certo. Seu perfil está completo.".encode() in response.data


def test_avatar_upload_error_preserves_completion_and_business_contexts(app, client, monkeypatch):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    with app.app_context():
        establishment = Establishment(name="Studio Teste", slug="studio-teste")
        access = EstablishmentUserAccess(
            user_id=user_id,
            establishment=establishment,
            role=EstablishmentAccessRole.OWNER,
            status=EstablishmentAccessStatus.ACTIVE,
        )
        db.session.add_all([establishment, access])
        db.session.commit()

    def fail_upload(*_args, **_kwargs):
        raise ValueError("Falha controlada no upload.")

    monkeypatch.setattr("app.routes.account.save_uploaded_image", fail_upload)

    response = client.post(
        "/minha-conta",
        data={
            "name": "Legacy User",
            "phone": "",
            "birth_date": "",
            "city": "",
            "state": "",
            "avatar_file": (BytesIO(b"fake-image"), "avatar.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert b'data-progress="29"' in response.data
    assert b"Studio Teste" in response.data
    assert "Falha controlada no upload.".encode() in response.data
