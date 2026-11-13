"""QA-001 B2-fix — cadastro "Profissional" no app cria a conta.

Antes, o app abria /signup-pro sem chamar o cadastro: nome, e-mail e senha
eram descartados e as telas Pro recebiam 401 (DEC-ID-001, 064, 092).

1. Jornada de API que o app passa a seguir: cadastro (sempre Cliente) →
   cadastro Pro com o mesmo token → uma conta, Cliente primeiro.
2. Contrato do app: o caminho Profissional cadastra antes de abrir o
   cadastro Pro, sem levar dados pessoais por parâmetro de rota.
"""

from pathlib import Path
import re

from sqlalchemy import func, select

from app.extensions import db
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

LOGIN_TSX = Path(__file__).resolve().parents[1] / "mobile" / "src" / "app" / "login.tsx"
EMAIL = "pro-pelo-app@example.com"


def _register(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bruna Pelo App",
            "email": EMAIL,
            "password": "senha-forte-123",
            "role": "client",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.get_json()['accessToken']}"}


def _pro_payload():
    return {
        "displayName": "Bruna Unhas",
        "primarySpecialty": "Nail designer",
        "categories": ["unhas"],
        "city": "Curitiba",
        "state": "PR",
    }


def test_app_pro_signup_journey_keeps_one_personal_account(app, client):
    headers = _register(client)

    # Logo depois do cadastro, o cadastro Pro abre (não 401) e ainda está vazio.
    empty = client.get("/api/v1/onboarding/professional", headers=headers)
    assert empty.status_code == 200
    assert empty.get_json()["profile"] is None

    created = client.post("/api/v1/onboarding/professional", headers=headers, json=_pro_payload())
    assert created.status_code in {200, 201}
    # Repetir o envio (toque duplo, rede instável) não cria outro perfil.
    again = client.post("/api/v1/onboarding/professional", headers=headers, json=_pro_payload())
    assert again.status_code in {200, 201}
    assert again.get_json()["profile"]["id"] == created.get_json()["profile"]["id"]

    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == EMAIL))
        assert db.session.scalar(select(func.count()).select_from(User).where(User.email == EMAIL)) == 1
        # A conta continua Cliente; o Pro é uma capacidade a mais.
        assert user.role == UserRole.CLIENT
        assert db.session.scalar(
            select(func.count()).select_from(ClientProfile).where(ClientProfile.user_id == user.id)
        ) == 1
        assert db.session.scalar(
            select(func.count()).select_from(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id)
        ) == 1

    contexts = client.get("/api/v1/auth/me", headers=headers).get_json()["contexts"]
    assert [item["kind"] for item in contexts][:2] == ["client", "professional"]


def _handle_submit(source):
    start = source.index("const handleSubmit = async")
    end = source.index("const handleVisitor", start)
    return source[start:end]


def test_app_professional_choice_registers_before_pro_onboarding():
    body = _handle_submit(LOGIN_TSX.read_text(encoding="utf-8"))

    register = body.index("await registerClient(")
    pro = body.index('router.replace("/signup-pro")')
    # Cadastra primeiro; só depois abre o cadastro Pro, já autenticado.
    assert register < pro
    # O cadastro do Cliente não é pulado por um return antes dele.
    assert not re.search(r'pathname:\s*"/signup-pro"', body)
    # Nenhum dado pessoal (e-mail, nome) vai como parâmetro de rota.
    assert "params:" not in body[:register]
