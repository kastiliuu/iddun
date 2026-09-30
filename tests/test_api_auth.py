"""Testes HTTP da autenticação do aplicativo."""

from sqlalchemy import func, select

from app import create_app
from app.extensions import db
from app.models.api_session import ApiSession
from app.models.user import User, UserRole


BASE = "/api/auth"


def _registration(email="mobile@example.com", **changes):
    payload = {
        "name": "Cliente Mobile",
        "email": email,
        "password": "senha-forte-123",
        "role": "client",
    }
    payload.update(changes)
    return payload


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_client_and_returns_mobile_contract(app, client):
    response = client.post(
        f"{BASE}/register",
        json=_registration(),
    )

    assert response.status_code == 201
    assert "no-store" in response.headers["Cache-Control"]

    data = response.get_json()
    assert data["accessToken"]
    assert data["refreshToken"]
    assert data["accessToken"] != data["refreshToken"]
    assert data["user"]["name"] == "Cliente Mobile"
    assert data["user"]["email"] == "mobile@example.com"
    assert data["user"]["role"] == "client"
    assert data["user"]["profileId"]

    user = db.session.scalar(
        select(User).where(User.email == "mobile@example.com")
    )

    assert user is not None
    assert user.role == UserRole.CLIENT
    assert user.check_password("senha-forte-123")
    assert user.client_profile is not None

    # Cadastro na API não cria uma sessão web por cookie.
    assert client.get(f"{BASE}/me").status_code == 401

    current = client.get(
        f"{BASE}/me",
        headers=_bearer(data["accessToken"]),
    )

    assert current.status_code == 200
    assert current.get_json()["email"] == user.email


def test_login_uses_existing_account_and_rejects_wrong_password(
    app,
    client,
):
    registered = client.post(
        f"{BASE}/register",
        json=_registration(),
    )
    assert registered.status_code == 201

    wrong = client.post(
        f"{BASE}/login",
        json={
            "email": "mobile@example.com",
            "password": "senha-incorreta",
        },
    )

    assert wrong.status_code == 401
    assert wrong.get_json()["error"]["code"] == "invalid_credentials"

    logged_in = client.post(
        f"{BASE}/login",
        json={
            "email": "  MOBILE@EXAMPLE.COM  ",
            "password": "senha-forte-123",
        },
    )

    assert logged_in.status_code == 200
    assert logged_in.get_json()["user"]["email"] == "mobile@example.com"
    assert logged_in.get_json()["accessToken"]

    assert db.session.scalar(
        select(func.count()).select_from(User)
    ) == 1
    assert db.session.scalar(
        select(func.count()).select_from(ApiSession)
    ) == 2


def test_refresh_rotates_tokens_and_logout_revokes_session(
    app,
    client,
):
    registered = client.post(
        f"{BASE}/register",
        json=_registration(),
    ).get_json()

    old_access = registered["accessToken"]
    old_refresh = registered["refreshToken"]

    refreshed = client.post(
        f"{BASE}/refresh",
        json={"refreshToken": old_refresh},
    )

    assert refreshed.status_code == 200
    assert "no-store" in refreshed.headers["Cache-Control"]

    new_access = refreshed.get_json()["accessToken"]
    new_refresh = refreshed.get_json()["refreshToken"]

    assert new_access != old_access
    assert new_refresh != old_refresh

    assert client.get(
        f"{BASE}/me",
        headers=_bearer(old_access),
    ).status_code == 401

    assert client.post(
        f"{BASE}/refresh",
        json={"refreshToken": old_refresh},
    ).status_code == 401

    assert client.get(
        f"{BASE}/me",
        headers=_bearer(new_access),
    ).status_code == 200

    logout = client.post(
        f"{BASE}/logout",
        headers=_bearer(new_access),
    )

    assert logout.status_code == 204
    assert "no-store" in logout.headers["Cache-Control"]

    assert client.get(
        f"{BASE}/me",
        headers=_bearer(new_access),
    ).status_code == 401

    assert client.post(
        f"{BASE}/refresh",
        json={"refreshToken": new_refresh},
    ).status_code == 401


def test_web_cookie_does_not_authorize_mobile_endpoints(app, client):
    response = client.post(
        f"{BASE}/register",
        json=_registration(),
    )
    assert response.status_code == 201

    user = db.session.scalar(
        select(User).where(User.email == "mobile@example.com")
    )

    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    assert client.get(f"{BASE}/me").status_code == 401
    assert client.post(f"{BASE}/logout").status_code == 401


def test_register_rejects_duplicate_email_and_privileged_role(
    app,
    client,
):
    first = client.post(
        f"{BASE}/register",
        json=_registration(),
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"{BASE}/register",
        json=_registration(),
    )

    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "email_in_use"

    privileged = client.post(
        f"{BASE}/register",
        json=_registration(
            email="another@example.com",
            role="admin",
        ),
    )

    assert privileged.status_code == 400
    assert privileged.get_json()["error"]["code"] == "invalid_role"

    assert db.session.scalar(
        select(func.count()).select_from(User)
    ) == 1


def test_deactivated_account_loses_mobile_access(app, client):
    registered = client.post(
        f"{BASE}/register",
        json=_registration(),
    ).get_json()

    user = db.session.scalar(
        select(User).where(User.email == "mobile@example.com")
    )
    user.is_active_account = False
    db.session.commit()

    assert client.get(
        f"{BASE}/me",
        headers=_bearer(registered["accessToken"]),
    ).status_code == 401

    assert client.post(
        f"{BASE}/refresh",
        json={"refreshToken": registered["refreshToken"]},
    ).status_code == 401

    assert client.post(
        f"{BASE}/login",
        json={
            "email": "mobile@example.com",
            "password": "senha-forte-123",
        },
    ).status_code == 401


def test_auth_requires_json_and_keeps_web_csrf_enabled(tmp_path):
    secure_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-api-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )

    with secure_app.app_context():
        db.create_all()

        try:
            secure_client = secure_app.test_client()

            form_request = secure_client.post(
                f"{BASE}/login",
                data={
                    "email": "mobile@example.com",
                    "password": "senha-forte-123",
                },
            )
            assert form_request.status_code == 415

            registered = secure_client.post(
                f"{BASE}/register",
                json=_registration(),
            )
            assert registered.status_code == 201

            # A rota web permanece protegida por CSRF.
            web_logout = secure_client.post("/logout")
            assert web_logout.status_code == 400
        finally:
            db.session.remove()
            db.drop_all()
