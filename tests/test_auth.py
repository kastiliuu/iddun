from sqlalchemy import select

from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User


def register(client, email="gabriel@example.com", password="senha-forte-123"):
    return client.post(
        "/cadastro",
        data={
            "name": "Gabriel Castilho",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=False,
    )


def test_register_creates_user_and_client_profile(app, client):
    response = register(client)

    assert response.status_code == 302
    assert "/minha-conta" in response.headers["Location"]

    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == "gabriel@example.com"))
        assert user is not None
        assert user.check_password("senha-forte-123")
        assert user.password_hash != "senha-forte-123"
        assert user.client_profile is not None
        assert isinstance(user.client_profile, ClientProfile)


def test_register_rejects_duplicate_email(app, client):
    register(client)
    client.post("/logout")

    response = register(client)

    assert response.status_code == 200
    assert "Já existe uma conta" in response.get_data(as_text=True)

    with app.app_context():
        users = db.session.scalars(select(User)).all()
        assert len(users) == 1


def test_login_and_logout(app, client):
    register(client)
    client.post("/logout")

    response = client.post(
        "/login",
        data={"email": "gabriel@example.com", "password": "senha-forte-123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/minha-conta" in response.headers["Location"]

    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_logout_does_not_accept_get(client):
    response = client.get("/logout")
    assert response.status_code == 405


def test_invalid_login_is_rejected(client):
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 200
    assert "E-mail ou senha incorretos" in response.get_data(as_text=True)


def test_login_page_exposes_accessible_premium_controls(client):
    response = client.get("/login")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Bem-vindo de volta" in text
    assert "Esqueci minha senha" in text
    assert "Continuar com Google" in text
    assert "Continuar com Apple" in text
    assert 'type="email"' in text
    assert 'autocomplete="current-password"' in text
    assert 'aria-pressed="false"' in text
    assert "Entrando..." in text


def test_account_requires_login(client):
    response = client.get("/minha-conta", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_external_next_redirect(app, client):
    register(client)
    client.post("/logout")

    response = client.post(
        "/login?next=https://example.com/phishing",
        data={"email": "gabriel@example.com", "password": "senha-forte-123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/minha-conta")


def test_logout_requires_csrf_when_protection_is_enabled():
    from app import create_app
    from app.extensions import db
    from app.models.user import User, UserRole

    secure_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )

    with secure_app.app_context():
        db.create_all()
        user = User(name="CSRF User", email="csrf@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    secure_client = secure_app.test_client()
    with secure_client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    response = secure_client.post("/logout")
    assert response.status_code == 400
