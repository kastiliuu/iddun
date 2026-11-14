"""ID-SOC-R1-02 (Notion 08, 14/11/2026) — @username único, alterável, sem quebrar links.

Regras: 3 a 30 caracteres a-z 0-9 . _, sem ponto no início, no fim ou
repetido; reservados recusados; um @ usado nunca passa a outra pessoa;
troca 1 vez a cada 14 dias; o @ antigo continua chegando à pessoa.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.beauty_graph import Follow
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole, UsernameHistory
from app.services import username_service
from app.services.account_privacy import anonymize_account
from app.services.username_service import UsernameError

PASSWORD = "senha-forte-123"


def _user(name, email, username=None):
    user = User(name=name, email=email, role=UserRole.CLIENT, username=username)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()
    return user


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Bruna", "bruna"),
        ("@ana.costa", "ana.costa"),
        ("joao_2", "joao_2"),
        ("abc", "abc"),
        ("a" * 30, "a" * 30),
    ],
)
def test_valid_usernames_are_normalized(app, raw, expected):
    assert username_service.validate_format(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["ab", "a" * 31, ".ana", "ana.", "an..a", "ana costa", "anã", "ana-costa", "iddun", "ad.min", "suporte2", "iddun_oficial", "pro"],
)
def test_invalid_or_reserved_usernames_are_refused(app, raw):
    with pytest.raises(UsernameError):
        username_service.validate_format(raw)


def test_new_accounts_get_a_username_from_the_name_even_in_the_same_flush(app):
    first = User(name="Ana Côsta", email="a1@example.com", role=UserRole.CLIENT)
    second = User(name="Ana Costa", email="a2@example.com", role=UserRole.CLIENT)
    third = User(name="Jo", email="a3@example.com", role=UserRole.CLIENT)
    for user in (first, second, third):
        user.set_password(PASSWORD)
    db.session.add_all([first, second, third])
    db.session.commit()

    assert first.username == "ana.costa"
    assert second.username == "ana.costa2"
    # Nome curto demais: base neutra.
    assert third.username == "pessoa"


def test_web_signup_accepts_optional_username_and_validates_it(client, app):
    def signup(email, username=""):
        return client.post(
            "/cadastro",
            data={
                "account_type": "client",
                "name": "Bruna Lima",
                "username": username,
                "email": email,
                "password": PASSWORD,
                "confirm_password": PASSWORD,
            },
        )

    assert signup("b1@example.com").status_code == 302
    client.post("/logout")
    assert signup("b2@example.com", "@Bruna.Unhas").status_code == 302
    client.post("/logout")
    taken = signup("b3@example.com", "bruna.unhas")
    assert taken.status_code == 200
    assert "Este @ já está em uso" in taken.get_data(as_text=True)
    reserved = signup("b4@example.com", "admin")
    assert "Este @ é reservado" in reserved.get_data(as_text=True)

    with app.app_context():
        names = dict(db.session.execute(select(User.email, User.username)).all())
    assert names == {"b1@example.com": "bruna.lima", "b2@example.com": "bruna.unhas"}


def test_api_signup_accepts_optional_username_and_reports_conflicts(client, app):
    def register(email, **extra):
        return client.post(
            "/api/v1/auth/register",
            json={"name": "Carla Dias", "email": email, "password": PASSWORD, "role": "client", **extra},
        )

    created = register("c1@example.com")
    assert created.status_code == 201
    assert created.get_json()["user"]["username"] == "carla.dias"
    assert register("c2@example.com", username="carla.unhas").get_json()["user"]["username"] == "carla.unhas"
    conflict = register("c3@example.com", username="Carla.Unhas")
    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "invalid_username"
    invalid = register("c4@example.com", username="ca")
    assert invalid.status_code == 400
    assert register("c5@example.com", username=12).status_code == 400

    with app.app_context():
        assert db.session.scalar(select(User).where(User.email == "c3@example.com")) is None


def test_change_keeps_old_handle_for_the_same_person_and_limits_frequency(app):
    owner = _user("Dani Reis", "d1@example.com")
    other = _user("Outra Pessoa", "d2@example.com")

    assert username_service.change_username(owner, "dani.unhas") is True
    db.session.commit()
    assert owner.username == "dani.unhas"
    assert db.session.scalar(select(UsernameHistory.username).where(UsernameHistory.user_id == owner.id)) == "dani.reis"

    # O @ antigo nunca passa a outra pessoa.
    assert username_service.is_available("dani.reis") is False
    with pytest.raises(UsernameError, match="em uso"):
        username_service.change_username(other, "dani.reis")

    # Segunda troca antes de 14 dias: recusada.
    with pytest.raises(UsernameError, match="poderá trocar"):
        username_service.change_username(owner, "dani.nails")

    # Depois de 14 dias, pode voltar ao @ que já foi dela.
    history = db.session.scalar(select(UsernameHistory).where(UsernameHistory.user_id == owner.id))
    history.created_at = datetime.now(timezone.utc) - timedelta(days=15)
    db.session.commit()
    username_service.change_username(owner, "dani.reis")
    db.session.commit()
    assert owner.username == "dani.reis"
    assert sorted(db.session.scalars(
        select(UsernameHistory.username).where(UsernameHistory.user_id == owner.id)
    ).all()) == ["dani.unhas"]


def test_account_edit_changes_username_and_shows_errors(client, app):
    with app.app_context():
        _user("Eva Melo", "e1@example.com")
        _user("Eva Outra", "e2@example.com", username="eva.taken")
    client.post("/login", data={"email": "e1@example.com", "password": PASSWORD})

    page = client.get("/minha-conta/editar").get_data(as_text=True)
    assert 'value="eva.melo"' in page
    assert "Pode trocar 1 vez a cada 14 dias" in page

    taken = client.post("/minha-conta/editar", data={"name": "Eva Melo", "username": "eva.taken"})
    assert taken.status_code == 200
    assert "Este @ já está em uso" in taken.get_data(as_text=True)

    changed = client.post("/minha-conta/editar", data={"name": "Eva Melo", "username": "@Eva.Nails"})
    assert changed.status_code == 302
    with app.app_context():
        assert db.session.scalar(select(User.username).where(User.email == "e1@example.com")) == "eva.nails"
    again = client.get("/minha-conta/editar").get_data(as_text=True)
    assert "Você poderá trocar de novo em" in again


def test_at_route_redirects_current_old_and_unknown_handles(client, app):
    with app.app_context():
        client_only = _user("Fabi Souza", "f1@example.com", username="fabi")
        pro_user = _user("Gabi Pro", "f2@example.com", username="gabi")
        profile = ProfessionalProfile(
            user_id=pro_user.id, display_name="Gabi Unhas", slug="gabi-unhas",
            city="Curitiba", state="PR", is_active=True, published_at=datetime.now(timezone.utc),
        )
        db.session.add(profile)
        db.session.commit()
        username_service.change_username(client_only, "fabi.souza")
        db.session.commit()
        client_page = f"/clientes/{client_only.client_profile.id}"

    current = client.get("/@fabi.souza")
    assert current.status_code == 302 and current.headers["Location"].endswith(client_page)
    old = client.get("/@fabi")
    assert old.status_code == 301 and old.headers["Location"].endswith("/@fabi.souza")
    upper = client.get("/@Fabi.Souza")
    assert upper.status_code == 301 and upper.headers["Location"].endswith("/@fabi.souza")
    pro = client.get("/@gabi")
    assert pro.status_code == 302 and pro.headers["Location"].endswith("/profissionais/gabi-unhas")
    assert client.get("/@ninguem").status_code == 404


def test_deleted_account_frees_personal_handle_data_and_followers(app, client):
    leaving = _user("Helo Lima", "h1@example.com", username="helo")
    fan = _user("Fã Helo", "h2@example.com")
    username_service.change_username(leaving, "helo.lima")
    db.session.add(Follow(user_id=fan.id, target_type="person", followed_user_id=leaving.id))
    db.session.commit()

    anonymize_account(leaving)

    assert leaving.username == f"conta.removida.{leaving.id}"
    assert db.session.scalar(select(UsernameHistory).where(UsernameHistory.user_id == leaving.id)) is None
    assert db.session.scalar(select(Follow).where(Follow.followed_user_id == leaving.id)) is None
    assert client.get("/@helo").status_code == 404
    assert client.get(f"/@conta.removida.{leaving.id}").status_code == 404


def test_me_payload_includes_username(client, app):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Iris Nunes", "email": "i1@example.com", "password": PASSWORD, "role": "client"},
    )
    token = response.get_json()["accessToken"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).get_json()
    # /auth/me devolve o usuário na raiz.
    assert me["username"] == "iris.nunes"
