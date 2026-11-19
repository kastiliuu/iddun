"""V1 PR 3 — caminhos negativos que a homologação vai repetir à mão.

Complementa a matriz de autorização (recurso de outra pessoa) com:
- sessão expirada ou encerrada: 401 nas rotas do app, sem mudar o banco;
- perfil errado: conta sem perfil profissional nas rotas do Pro;
- estado inválido: ação que o estado atual não permite;
- envio repetido: a segunda tentativa não duplica nada.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from flask import g
from sqlalchemy import func, select

from app.extensions import db
from app.models.api_session import ApiSession
from app.models.booking import ExperienceSlot
from app.models.establishment import Establishment
from app.models.experience import Experience, ExperienceStatus
from app.models.job import JobApplication, JobPost, JobPostStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session

BASE = "/api/v1/onboarding/professional/services"


def _user(email, role=UserRole.CLIENT):
    user = User(name=email.split("@")[0].title(), email=email, role=role)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    return user


@pytest.fixture
def world(app):
    pro_user = _user("pro-negativo@example.com", UserRole.PROFESSIONAL)
    profile = ProfessionalProfile(
        user_id=pro_user.id, display_name="Pro Negativo", slug="pro-negativo",
        city="Curitiba", state="PR", timezone="America/Sao_Paulo", is_active=True,
    )
    db.session.add(profile)
    db.session.flush()
    service = Experience(
        professional=profile, title="Serviço negativo", slug="servico-negativo", category="unhas",
        short_description="Resumo.", regular_price=Decimal("100.00"), price=Decimal("90.00"),
        duration_minutes=60, status=ExperienceStatus.PUBLISHED,
    )
    client_user = _user("cliente-negativo@example.com")
    studio = Establishment(name="Studio Negativo", slug="studio-negativo", city="Curitiba", is_active=True)
    db.session.add_all([service, studio])
    db.session.flush()
    closed_job = JobPost(
        establishment=studio, title="Vaga encerrada", description="x", status=JobPostStatus.CLOSED,
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc), closed_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    db.session.add(closed_job)
    db.session.commit()
    return {
        "pro": pro_user.id, "client": client_user.id, "service": service.id, "closed_job": closed_job.id,
    }


def _bearer(user_id):
    return {"Authorization": f"Bearer {issue_session(db.session.get(User, user_id)).access_token}"}


def _future_date(days=9):
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


APP_CALLS = [
    ("get", BASE, None),
    ("post", BASE + "/{service}/availability/batch", {"date": "2030-01-10", "times": ["10:00"]}),
    ("post", BASE + "/{service}/status", {"action": "pause"}),
    ("get", "/api/v1/jobs/applications/mine", None),
]


def test_expired_or_revoked_session_gets_401_and_changes_nothing(client, world):
    headers = _bearer(world["pro"])
    session = db.session.scalar(select(ApiSession).where(ApiSession.user_id == world["pro"]))
    session.access_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()
    for method, path, body in APP_CALLS:
        response = getattr(client, method)(path.format(**world), headers=headers, json=body)
        assert response.status_code == 401, (method, path)
    assert db.session.get(Experience, world["service"]).status == ExperienceStatus.PUBLISHED

    headers = _bearer(world["pro"])
    session = db.session.scalars(
        select(ApiSession).where(ApiSession.user_id == world["pro"]).order_by(ApiSession.id.desc())
    ).first()
    session.revoked_at = datetime.now(timezone.utc)
    db.session.commit()
    for method, path, body in APP_CALLS:
        response = getattr(client, method)(path.format(**world), headers=headers, json=body)
        assert response.status_code == 401, (method, path)
    assert db.session.scalar(select(func.count(ExperienceSlot.id))) == 0


def test_account_without_professional_profile_cannot_use_pro_routes(client, world):
    headers = _bearer(world["client"])
    listed = client.get(BASE, headers=headers)
    assert listed.status_code == 409
    assert listed.get_json()["error"]["code"] == "professional_profile_required"
    batch = client.post(f"{BASE}/{world['service']}/availability/batch", headers=headers,
                        json={"date": _future_date(), "times": ["10:00"]})
    assert batch.status_code == 409
    image = client.post(f"{BASE}/{world['service']}/image", headers=headers)
    assert image.status_code == 409

    g.pop("_login_user", None)
    with client.session_transaction() as web:
        web["_user_id"] = str(world["client"])
        web["_fresh"] = True
    assert client.get("/pro/servicos").status_code == 302
    applied = client.post(f"/vagas/{world['closed_job']}/candidatar", data={"message": "Oi"})
    assert applied.status_code == 302
    assert db.session.scalar(select(func.count(JobApplication.id))) == 0


def test_invalid_state_is_refused_without_side_effects(client, world):
    headers = _bearer(world["pro"])
    # Vaga encerrada: não aparece, não aceita candidatura.
    assert client.get(f"/vagas/{world['closed_job']}").status_code == 404
    assert client.get(f"/api/v1/jobs/{world['closed_job']}").status_code == 404
    applied = client.post(f"/api/v1/jobs/{world['closed_job']}/apply", headers=headers, json={"message": "Oi"})
    assert applied.status_code in (400, 404, 409)
    assert db.session.scalar(select(func.count(JobApplication.id))) == 0
    # Serviço publicado não troca de foto.
    image = client.post(f"{BASE}/{world['service']}/image", headers=headers)
    assert image.status_code == 409


def test_repeated_batch_does_not_duplicate_slots(client, world):
    headers = _bearer(world["pro"])
    body = {"date": _future_date(), "times": ["09:00", "11:00"]}
    first = client.post(f"{BASE}/{world['service']}/availability/batch", headers=headers, json=body)
    assert first.status_code == 201
    again = client.post(f"{BASE}/{world['service']}/availability/batch", headers=headers, json=body)
    assert again.status_code == 409
    assert db.session.scalar(select(func.count(ExperienceSlot.id))) == 2
