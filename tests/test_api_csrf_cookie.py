"""AUD-04 / D-SOC-01 — CSRF nas APIs quando a sessão vem do cookie da Web.

As APIs ficam fora da proteção padrão porque o app usa Bearer. Seis delas
também aceitam a sessão da Web; nesse caso a mutação exige o token CSRF.
Bearer e leitura continuam como antes.
"""

import pytest
from flask import g

from app import create_app
from app.extensions import db
from app.models.establishment import Establishment
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session

# Uma mutação de cada blueprint que aceita sessão por cookie.
MUTATIONS = [
    ("put", "/api/v1/graph/follows/establishment/{est}"),
    ("put", "/api/v1/notifications/read-all"),
    ("post", "/api/v1/posts"),
    ("post", "/api/v1/jobs/999/apply"),
    ("put", "/api/v1/team/invitations/999/accept"),
    ("post", "/api/v1/availability"),
]


@pytest.fixture()
def csrf_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed(app):
    user = User(name="Cliente Cookie", email="cookie@example.com", role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    establishment = Establishment(
        name="Studio Cookie", slug="studio-cookie", category="salao",
        city="Curitiba", state="PR", description="Espaço público para testes.",
        is_active=True,
    )
    db.session.add(establishment)
    db.session.commit()
    return user, establishment.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    # O fixture mantém o app context; o Flask-Login guarda o usuário em g.
    g.pop("_login_user", None)


def _call(client, method, path, **kwargs):
    return getattr(client, method)(path, json={}, **kwargs)


def _code(response):
    body = response.get_json(silent=True) or {}
    return (body.get("error") or {}).get("code")


def test_cookie_session_without_token_is_refused_on_every_cookie_api(csrf_app):
    user, est = _seed(csrf_app)
    client = csrf_app.test_client()
    _login(client, user.id)

    for method, path in MUTATIONS:
        response = _call(client, method, path.format(est=est))
        assert response.status_code == 400, path
        assert _code(response) == "csrf_failed", path


def test_cookie_session_with_token_reaches_the_route(csrf_app):
    user, est = _seed(csrf_app)
    client = csrf_app.test_client()
    _login(client, user.id)
    token = client.get("/csrf-token").get_json()["csrfToken"]

    for method, path in MUTATIONS:
        response = _call(client, method, path.format(est=est), headers={"X-CSRFToken": token})
        assert _code(response) != "csrf_failed", path

    follow = client.put(
        f"/api/v1/graph/follows/establishment/{est}",
        json={}, headers={"X-CSRFToken": token},
    )
    assert follow.status_code in (200, 201)


def test_bearer_needs_no_csrf_token(csrf_app):
    user, est = _seed(csrf_app)
    client = csrf_app.test_client()
    bearer = {"Authorization": f"Bearer {issue_session(user).access_token}"}

    for method, path in MUTATIONS:
        response = _call(client, method, path.format(est=est), headers=bearer)
        assert _code(response) != "csrf_failed", path

    follow = client.put(f"/api/v1/graph/follows/establishment/{est}", json={}, headers=bearer)
    assert follow.status_code in (200, 201)


def test_anonymous_and_reads_are_unchanged(csrf_app):
    user, est = _seed(csrf_app)
    client = csrf_app.test_client()

    anonymous = client.put(f"/api/v1/graph/follows/establishment/{est}", json={})
    assert anonymous.status_code == 401
    assert _code(anonymous) != "csrf_failed"

    _login(client, user.id)
    assert client.get("/api/v1/graph").status_code == 200
    assert client.get("/api/v1/notifications").status_code == 200
