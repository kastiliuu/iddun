"""DEC-ID-062/166 — aparelhos com o app conectados, também na Web.

A tela de Privacidade lista as sessões do app da própria conta (o mesmo
serviço da API) e deixa desconectar uma ou todas. Uma conta não vê nem
encerra sessões de outra. A sessão deste navegador não é tocada.
"""

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.api_session import ApiSession
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session


def _user(name, email):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()
    return user


def _login(client, user_id):
    g.pop("_login_user", None)
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _active(user_id):
    db.session.expire_all()
    return db.session.scalars(
        select(ApiSession.id).where(ApiSession.user_id == user_id, ApiSession.revoked_at.is_(None))
    ).all()


def test_lists_and_revokes_own_app_sessions(app, client):
    ana = _user("Ana Sessoes", "ana-sessoes@example.com")
    bia = _user("Bia Sessoes", "bia-sessoes@example.com")
    issue_session(ana, device_name="iPhone da Ana", platform="ios")
    issue_session(ana, device_name="Android antigo", platform="android")
    issue_session(bia, device_name="Celular da Bia", platform="android")
    ana_id, bia_id = ana.id, bia.id
    first, second = sorted(_active(ana_id))
    [bia_session] = _active(bia_id)

    _login(client, ana_id)
    page = client.get("/minha-conta/privacidade").get_data(as_text=True)
    assert "iPhone da Ana" in page and "Android antigo" in page
    assert "Celular da Bia" not in page
    assert "Desconectar todos os aparelhos" in page

    # Sessão de outra conta: não encerra.
    client.post(f"/minha-conta/sessoes/{bia_session}/encerrar")
    assert _active(bia_id) == [bia_session]

    response = client.post(f"/minha-conta/sessoes/{first}/encerrar")
    assert response.status_code == 302 and response.headers["Location"].endswith("/minha-conta/privacidade#aparelhos")
    assert _active(ana_id) == [second]

    client.post("/minha-conta/sessoes/encerrar-todas")
    assert _active(ana_id) == []
    assert _active(bia_id) == [bia_session]

    # A sessão deste navegador continua.
    after = client.get("/minha-conta/privacidade")
    assert after.status_code == 200
    assert "Nenhum aparelho com o app está conectado" in after.get_data(as_text=True)


def test_session_routes_require_login_and_post(app, client):
    assert client.post("/minha-conta/sessoes/1/encerrar").status_code == 302
    assert client.post("/minha-conta/sessoes/encerrar-todas").status_code == 302
    assert client.get("/minha-conta/sessoes/encerrar-todas").status_code == 405
