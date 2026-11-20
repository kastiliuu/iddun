"""V1-CONV-D05 — piloto de recrutamento e permissão de gerentes.

Regras (Notion 08: A1-DEC-01/02/03, V1-CONV-D03/D04/D05):
- vaga nova (criar ou publicar pela primeira vez) exige o piloto ligado
  pelo admin do IDDUN, com motivo e registro;
- vagas que já existiam continuam no ar e administráveis;
- gerente só vê e altera vagas com permissão expressa da dona; o padrão é
  negado e a retirada vale na hora;
- tudo vale igual na API (app) e na Web.
"""

from datetime import datetime, timezone

import pytest
from flask import g
from sqlalchemy import func, select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    RecruitmentAuditAction,
    RecruitmentAuditEvent,
)
from app.models.job import JobApplication, JobApplicationStatus, JobPost, JobPostStatus
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.recruitment_access_service import (
    RecruitmentAccessError,
    set_manager_recruitment_grant,
    set_recruitment_pilot,
)

JOB = {"title": "Cabeleireira sênior", "description": "Atendimento de coloração e corte."}


def _user(email, role=UserRole.CLIENT):
    user = User(name=email.split("@")[0].title(), email=email, role=role)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    return user


def _access(user, establishment, role, *, can_recruit=False):
    access = EstablishmentUserAccess(
        user_id=user.id, establishment_id=establishment.id, role=role,
        status=EstablishmentAccessStatus.ACTIVE, can_recruit=can_recruit,
    )
    db.session.add(access)
    db.session.flush()
    return access


def _login(client, user_id):
    g.pop("_login_user", None)
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


@pytest.fixture
def world(app):
    owner = _user("dona-recruta@example.com")
    manager = _user("gerente-recruta@example.com")
    admin = _user("admin-recruta@example.com", UserRole.ADMIN)
    pro_user = _user("pro-recruta@example.com", UserRole.PROFESSIONAL)
    studio = Establishment(name="Studio Piloto", slug="studio-piloto", city="Curitiba", state="PR", is_active=True)
    other = Establishment(name="Outro Studio", slug="outro-studio", city="Curitiba", state="PR", is_active=True)
    db.session.add_all([studio, other])
    db.session.flush()
    owner_access = _access(owner, studio, EstablishmentAccessRole.OWNER)
    manager_access = _access(manager, studio, EstablishmentAccessRole.MANAGER)
    pro = ProfessionalProfile(
        user_id=pro_user.id, display_name="Pro Recruta", slug="pro-recruta",
        primary_specialty="Cabeleireira", city="Curitiba", state="PR", is_active=True,
    )
    db.session.add(pro)
    # V1-CONV-D04: vaga publicada antes do piloto existir.
    legacy = JobPost(
        establishment=studio, title="Vaga antiga", description="Já estava no ar.",
        status=JobPostStatus.PUBLISHED, published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    legacy_draft = JobPost(establishment=studio, title="Rascunho antigo", description="Nunca publicado.")
    db.session.add_all([legacy, legacy_draft])
    db.session.commit()
    return {
        "owner": owner.id, "manager": manager.id, "admin": admin.id, "pro": pro_user.id,
        "studio": studio.id, "other": other.id, "owner_access": owner_access.id,
        "manager_access": manager_access.id, "legacy": legacy.id, "legacy_draft": legacy_draft.id,
    }


def _enable(world, enabled=True):
    studio = db.session.get(Establishment, world["studio"])
    set_recruitment_pilot(
        establishment=studio, enabled=enabled, reason="Piloto aprovado pela equipe.",
        actor=db.session.get(User, world["admin"]),
    )


# ------------------------------------------------------------- API (app)

def test_new_job_needs_the_pilot_but_legacy_jobs_keep_working(client, world):
    _login(client, world["owner"])
    listing = client.get("/api/v1/establishments/studio-piloto/jobs").get_json()
    assert listing["recruitment"] == {"pilotEnabled": False, "canManage": True, "canCreate": False, "isOwner": True}

    created = client.post("/api/v1/establishments/studio-piloto/jobs", json=JOB)
    assert created.status_code == 403
    assert created.get_json()["error"]["code"] == "recruitment_not_enabled"

    published = client.put(f"/api/v1/establishments/studio-piloto/jobs/{world['legacy_draft']}/publish")
    assert published.status_code == 403
    assert published.get_json()["error"]["code"] == "recruitment_not_enabled"

    # A vaga antiga segue pública, editável e encerrável.
    assert client.get(f"/api/v1/jobs/{world['legacy']}").status_code == 200
    edited = client.put(f"/api/v1/establishments/studio-piloto/jobs/{world['legacy']}", json={"title": "Vaga antiga revista"})
    assert edited.status_code == 200
    closed = client.put(f"/api/v1/establishments/studio-piloto/jobs/{world['legacy']}/close")
    assert closed.status_code == 200
    assert db.session.scalar(select(func.count(JobPost.id))) == 2


def test_existing_job_remains_editable_after_pilot_revocation_but_not_when_closed(client, world):
    _login(client, world["owner"])
    job_id = world["legacy"]
    updated = client.put(
        f"/api/v1/establishments/studio-piloto/jobs/{job_id}",
        json={"title": "Vaga histórica revisada no app"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["job"]["title"] == "Vaga histórica revisada no app"
    closed = client.put(
        f"/api/v1/establishments/studio-piloto/jobs/{job_id}/close",
    )
    assert closed.status_code == 200
    blocked = client.put(
        f"/api/v1/establishments/studio-piloto/jobs/{job_id}",
        json={"title": "Tentativa não autorizada"},
    )
    assert blocked.status_code == 400


def test_closed_job_applications_remain_available_to_owner(client, world):
    _login(client, world["owner"])
    job_id = world["legacy"]
    assert client.put(
        f"/api/v1/establishments/studio-piloto/jobs/{job_id}/close",
    ).status_code == 200
    listing = client.get(
        f"/api/v1/establishments/studio-piloto/jobs/{job_id}/applications",
    )
    assert listing.status_code == 200
    assert listing.get_json()["job"]["status"] == "closed"
    # A interface Expo não deve ocultar candidatos de vagas encerradas.
    from pathlib import Path
    screen = (
        Path(__file__).resolve().parents[1]
        / "mobile/src/app/manage-jobs/[id].tsx"
    ).read_text(encoding="utf-8")
    assert 'job.status === "published" || job.status === "closed"' in screen


def test_expo_business_jobs_can_edit_existing_jobs_without_enabling_new_jobs():
    from pathlib import Path

    screen = (
        Path(__file__).resolve().parents[1]
        / "mobile/src/app/manage-jobs/[id].tsx"
    ).read_text(encoding="utf-8")
    assert 'updateJob,' in screen
    assert 'job.status !== "closed"' in screen
    assert 'recruitment?.canCreate || editingJobId !== null' in screen
    assert 'savingInFlight.current' in screen
    assert 'title="Cancelar edição"' in screen


def test_enabling_the_pilot_unlocks_new_jobs_and_revoking_does_not_take_jobs_down(client, world):
    _enable(world)
    _login(client, world["owner"])
    created = client.post("/api/v1/establishments/studio-piloto/jobs", json=JOB)
    assert created.status_code == 201
    job_id = created.get_json()["job"]["id"]
    assert client.put(f"/api/v1/establishments/studio-piloto/jobs/{job_id}/publish").status_code == 200

    _enable(world, enabled=False)
    # A vaga publicada durante o piloto continua no ar.
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 200
    # Nova vaga volta a ser bloqueada.
    again = client.post("/api/v1/establishments/studio-piloto/jobs", json=JOB)
    assert again.get_json()["error"]["code"] == "recruitment_not_enabled"


def test_manager_without_grant_is_denied_and_revocation_is_immediate(client, world):
    _enable(world)
    _login(client, world["manager"])
    denied = client.get("/api/v1/establishments/studio-piloto/jobs")
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "recruitment_not_granted"
    assert client.post("/api/v1/establishments/studio-piloto/jobs", json=JOB).status_code == 403
    assert client.get(f"/api/v1/establishments/studio-piloto/jobs/{world['legacy']}/applications").status_code == 403

    owner_access = db.session.get(EstablishmentUserAccess, world["owner_access"])
    studio = db.session.get(Establishment, world["studio"])
    set_manager_recruitment_grant(
        establishment=studio, owner_access=owner_access,
        target_access_id=world["manager_access"], can_recruit=True,
    )
    listing = client.get("/api/v1/establishments/studio-piloto/jobs")
    assert listing.status_code == 200
    assert listing.get_json()["recruitment"]["canCreate"] is True
    assert client.post("/api/v1/establishments/studio-piloto/jobs", json=JOB).status_code == 201

    set_manager_recruitment_grant(
        establishment=studio, owner_access=owner_access,
        target_access_id=world["manager_access"], can_recruit=False,
    )
    assert client.get("/api/v1/establishments/studio-piloto/jobs").status_code == 403
    # Retirar a permissão não apaga o vínculo do gerente.
    access = db.session.get(EstablishmentUserAccess, world["manager_access"])
    assert access.status == EstablishmentAccessStatus.ACTIVE and access.role == EstablishmentAccessRole.MANAGER


# ------------------------------------------------------------- regras do serviço

def test_only_admin_changes_the_pilot_with_a_reason_and_every_change_is_recorded(world):
    studio = db.session.get(Establishment, world["studio"])
    owner = db.session.get(User, world["owner"])
    admin = db.session.get(User, world["admin"])

    with pytest.raises(RecruitmentAccessError):
        set_recruitment_pilot(establishment=studio, enabled=True, reason="Quero recrutar agora.", actor=owner)
    with pytest.raises(RecruitmentAccessError) as missing:
        set_recruitment_pilot(establishment=studio, enabled=True, reason="  ", actor=admin)
    assert missing.value.code == "reason_required"
    assert studio.recruitment_enabled is False

    set_recruitment_pilot(establishment=studio, enabled=True, reason="Piloto aprovado.", actor=admin)
    with pytest.raises(RecruitmentAccessError) as twice:
        set_recruitment_pilot(establishment=studio, enabled=True, reason="De novo, sem mudança.", actor=admin)
    assert twice.value.code == "no_change"
    set_recruitment_pilot(establishment=studio, enabled=False, reason="Fim do piloto.", actor=admin)

    events = db.session.scalars(
        select(RecruitmentAuditEvent).order_by(RecruitmentAuditEvent.id)
    ).all()
    assert [(e.action, e.reason, e.actor_user_id) for e in events] == [
        (RecruitmentAuditAction.PILOT_ENABLED, "Piloto aprovado.", admin.id),
        (RecruitmentAuditAction.PILOT_REVOKED, "Fim do piloto.", admin.id),
    ]


def test_only_the_owner_grants_and_only_to_an_active_manager_of_the_same_studio(world):
    studio = db.session.get(Establishment, world["studio"])
    other = db.session.get(Establishment, world["other"])
    manager_access = db.session.get(EstablishmentUserAccess, world["manager_access"])
    owner_access = db.session.get(EstablishmentUserAccess, world["owner_access"])

    # Gerente não concede para si mesmo.
    with pytest.raises(RecruitmentAccessError):
        set_manager_recruitment_grant(
            establishment=studio, owner_access=manager_access,
            target_access_id=manager_access.id, can_recruit=True,
        )
    # A dona não alcança gerente de outra empresa nem a própria linha de dona.
    foreign_manager = _access(_user("gerente-outro@example.com"), other, EstablishmentAccessRole.MANAGER)
    for target in (foreign_manager.id, owner_access.id):
        with pytest.raises(RecruitmentAccessError) as exc:
            set_manager_recruitment_grant(
                establishment=studio, owner_access=owner_access, target_access_id=target, can_recruit=True,
            )
        assert exc.value.code == "manager_not_found"
    assert foreign_manager.can_recruit is False

    set_manager_recruitment_grant(
        establishment=studio, owner_access=owner_access, target_access_id=manager_access.id,
        can_recruit=True, reason="Gerente cuida da seleção.",
    )
    event = db.session.scalar(select(RecruitmentAuditEvent))
    assert event.action == RecruitmentAuditAction.GRANT_GIVEN
    assert event.subject_user_id == world["manager"] and event.actor_user_id == world["owner"]


# ------------------------------------------------------------- Web

def test_admin_web_page_enables_and_revokes_with_reason(client, world):
    _login(client, world["owner"])
    assert client.get(f"/admin/estabelecimentos/{world['studio']}/recrutamento").status_code == 403
    assert client.post(
        f"/admin/estabelecimentos/{world['studio']}/recrutamento",
        data={"acao": "habilitar", "motivo": "Tentativa da dona."},
    ).status_code == 403

    _login(client, world["admin"])
    page = client.get(f"/admin/estabelecimentos/{world['studio']}/recrutamento").get_data(as_text=True)
    assert "Não habilitado" in page and "Habilitar recrutamento" in page

    client.post(f"/admin/estabelecimentos/{world['studio']}/recrutamento", data={"acao": "habilitar", "motivo": ""})
    assert db.session.get(Establishment, world["studio"]).recruitment_enabled is False

    response = client.post(
        f"/admin/estabelecimentos/{world['studio']}/recrutamento",
        data={"acao": "habilitar", "motivo": "Piloto aprovado em reunião."},
        follow_redirects=True,
    )
    assert "Recrutamento habilitado para este estabelecimento." in response.get_data(as_text=True)
    db.session.expire_all()
    assert db.session.get(Establishment, world["studio"]).recruitment_enabled is True
    assert "Piloto aprovado em reunião." in response.get_data(as_text=True)


def test_business_web_page_reflects_pilot_and_grants(client, world):
    _login(client, world["owner"])
    html = client.get("/business/studio-piloto/vagas").get_data(as_text=True)
    assert "Recrutamento ainda não habilitado" in html
    assert "Nova vaga" not in html
    assert "Vaga antiga" in html
    assert "Publicar depende da habilitação do IDDUN." in html
    assert "Gerentes e recrutamento" in html and "Permitir recrutar" in html
    blocked = client.post("/business/studio-piloto/vagas", data=JOB, follow_redirects=True)
    assert "O recrutamento ainda não está habilitado" in blocked.get_data(as_text=True)
    assert db.session.scalar(select(func.count(JobPost.id))) == 2

    _enable(world)
    html = client.get("/business/studio-piloto/vagas").get_data(as_text=True)
    assert "Nova vaga" in html
    response = client.post("/business/studio-piloto/vagas", data=JOB)
    assert response.status_code == 302
    created = db.session.scalar(select(JobPost).where(JobPost.title == JOB["title"]))
    assert created.status == JobPostStatus.DRAFT
    client.post(f"/business/studio-piloto/vagas/{created.id}/publicar")
    db.session.expire_all()
    assert db.session.get(JobPost, created.id).status == JobPostStatus.PUBLISHED

    client.post(f"/business/studio-piloto/recrutamento/gerentes/{world['manager_access']}", data={"permitir": "1"})
    db.session.expire_all()
    assert db.session.get(EstablishmentUserAccess, world["manager_access"]).can_recruit is True


def test_manager_web_page_explains_denial_and_cannot_grant(client, world):
    _enable(world)
    _login(client, world["manager"])
    response = client.get("/business/studio-piloto/vagas")
    assert response.status_code == 403
    html = response.get_data(as_text=True)
    assert "Sem permissão de recrutamento" in html
    assert "Vaga antiga" not in html
    assert "Gerentes e recrutamento" not in html
    assert client.post("/business/studio-piloto/vagas", data=JOB).status_code == 403
    assert client.get(f"/business/studio-piloto/vagas/{world['legacy']}/candidaturas").status_code == 403
    assert client.post(
        f"/business/studio-piloto/recrutamento/gerentes/{world['manager_access']}", data={"permitir": "1"}
    ).status_code == 403
    db.session.expire_all()
    assert db.session.get(EstablishmentUserAccess, world["manager_access"]).can_recruit is False


def test_outsider_and_other_studio_jobs_are_out_of_reach(client, world):
    _login(client, world["pro"])
    assert client.get("/business/studio-piloto/vagas").status_code == 403
    assert client.post(f"/business/studio-piloto/vagas/{world['legacy']}/encerrar").status_code == 403
    _login(client, world["owner"])
    # Vaga de um estabelecimento não é alcançada pela URL de outro.
    other_job = JobPost(establishment_id=world["other"], title="Vaga de outro", description="x",
                        status=JobPostStatus.PUBLISHED, published_at=datetime(2026, 10, 2, tzinfo=timezone.utc))
    db.session.add(other_job)
    db.session.commit()
    assert client.get(f"/business/studio-piloto/vagas/{other_job.id}/editar").status_code == 404
    client.post(f"/business/studio-piloto/vagas/{other_job.id}/encerrar")
    db.session.expire_all()
    assert db.session.get(JobPost, other_job.id).status == JobPostStatus.PUBLISHED


def test_professional_applies_withdraws_and_reapplies_on_the_web(client, world):
    html = client.get("/vagas").get_data(as_text=True)
    assert "Vaga antiga" in html and "Rascunho antigo" not in html
    assert client.get(f"/vagas/{world['legacy_draft']}").status_code == 404

    _login(client, world["owner"])
    detail = client.get(f"/vagas/{world['legacy']}").get_data(as_text=True)
    assert "perfil profissional ativo" in detail
    assert client.post(f"/vagas/{world['legacy']}/candidatar", data={"message": "Oi"}, follow_redirects=True).status_code == 200
    assert db.session.scalar(select(func.count(JobApplication.id))) == 0

    _login(client, world["pro"])
    client.post(f"/vagas/{world['legacy']}/candidatar", data={"message": "Tenho 5 anos de coloração."})
    application = db.session.scalar(select(JobApplication))
    assert application.status == JobApplicationStatus.SUBMITTED
    again = client.post(f"/vagas/{world['legacy']}/candidatar", data={"message": "De novo"}, follow_redirects=True)
    assert "Você já se candidatou a esta vaga." in again.get_data(as_text=True)

    mine = client.get("/minhas-candidaturas").get_data(as_text=True)
    assert "Vaga antiga" in mine and "Enviada" in mine
    client.post(f"/vagas/{world['legacy']}/retirar", data={"voltar": "candidaturas"})
    db.session.expire_all()
    assert db.session.get(JobApplication, application.id).status == JobApplicationStatus.WITHDRAWN
    # A1-DEC-03: pode se candidatar de novo depois de retirar.
    client.post(f"/vagas/{world['legacy']}/candidatar", data={"message": "Voltei."})
    db.session.expire_all()
    assert db.session.get(JobApplication, application.id).status == JobApplicationStatus.SUBMITTED

    _login(client, world["owner"])
    listing = client.get(f"/business/studio-piloto/vagas/{world['legacy']}/candidaturas").get_data(as_text=True)
    assert "pro-recruta" in listing and "Voltei." in listing
    assert 'href="/@pro-recruta"' in listing
