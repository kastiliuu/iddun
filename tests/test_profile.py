from sqlalchemy import select

from app.extensions import db
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
