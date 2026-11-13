"""Retomada e conclusão de ponta a ponta (PR 4 do onboarding V0).

- Rascunho Business retoma direto na etapa pendente pelo id estável.
- Só o proprietário retoma; gestor vê o rascunho sem o atalho.
- Perfil ou página desativados pela moderação (``published_at`` preenchido
  e ``is_active`` falso) não aparecem como "rascunho" nem voltam ao
  cadastro: a publicação já recusa com ``publication_locked``.
"""

from datetime import datetime, timezone

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

from onboarding_flow import complete_professional_onboarding

WHEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _user(app, email):
    with app.app_context():
        user = User(name="Conta Retomada", email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        db.session.commit()
        return user.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    g.pop("_login_user", None)


def _start(client, name="Studio Retomada"):
    response = client.post("/business/onboarding/novo", data={
        "name": name, "category": "salao", "city": "Curitiba", "state": "PR",
    })
    assert response.status_code == 302
    return int(response.headers["Location"].split("/")[-2])


def _set_state(app, establishment_id, *, active, published_at):
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        item.is_active = active
        item.published_at = published_at
        db.session.commit()
        return item.slug


def test_business_resume_goes_to_the_pending_step(app, client):
    _login(client, _user(app, "retoma@example.com"))
    establishment_id = _start(client)
    resume = f"/business/onboarding/{establishment_id}"
    assert client.get(resume).headers["Location"].endswith(f"{resume}/atendimento")

    client.post(f"{resume}/atendimento", data={"operation_mode": "mobile"})
    # Domicílio pula o endereço (F2): a próxima pendente é funcionamento.
    assert client.get(resume).headers["Location"].endswith(f"{resume}/funcionamento")


def test_business_resume_is_only_for_the_owner(app, client):
    _login(client, _user(app, "dona-retoma@example.com"))
    establishment_id = _start(client)
    _login(client, _user(app, "outra-retoma@example.com"))
    assert client.get(f"/business/onboarding/{establishment_id}").status_code == 404
    assert client.get("/business/onboarding/2147483648").status_code == 404


def test_business_resume_of_published_goes_to_the_panel(app, client):
    _login(client, _user(app, "publicada@example.com"))
    establishment_id = _start(client)
    slug = _set_state(app, establishment_id, active=True, published_at=WHEN)
    response = client.get(f"/business/onboarding/{establishment_id}")
    assert response.headers["Location"].endswith(f"/business/{slug}/painel")


def test_dashboard_and_account_link_the_draft_by_id(app, client):
    _login(client, _user(app, "atalho@example.com"))
    establishment_id = _start(client, name="Studio Atalho")
    slug = _set_state(app, establishment_id, active=False, published_at=None)

    panel = client.get(f"/business/{slug}/painel").get_data(as_text=True)
    assert f'href="/business/onboarding/{establishment_id}"' in panel
    account = client.get("/minha-conta").get_data(as_text=True)
    assert f'href="/business/onboarding/{establishment_id}"' in account
    assert "Continuar cadastro: Studio Atalho" in account


def test_manager_sees_the_draft_without_the_owner_shortcut(app, client):
    _login(client, _user(app, "dona-gestor@example.com"))
    establishment_id = _start(client, name="Studio Gestor")
    manager_id = _user(app, "gestor@example.com")
    with app.app_context():
        db.session.add(EstablishmentUserAccess(
            establishment_id=establishment_id, user_id=manager_id,
            role=EstablishmentAccessRole.MANAGER, status=EstablishmentAccessStatus.ACTIVE,
        ))
        db.session.commit()
        slug = db.session.get(Establishment, establishment_id).slug

    _login(client, manager_id)
    panel = client.get(f"/business/{slug}/painel").get_data(as_text=True)
    assert "Esta página ainda não está no ar." in panel
    assert f'href="/business/onboarding/{establishment_id}"' not in panel
    account = client.get("/minha-conta").get_data(as_text=True)
    assert "Continuar cadastro: Studio Gestor" not in account
    assert "rascunho" in account


def test_moderated_establishment_stays_out_of_the_onboarding(app, client):
    _login(client, _user(app, "moderada@example.com"))
    establishment_id = _start(client, name="Studio Moderado")
    slug = _set_state(app, establishment_id, active=False, published_at=WHEN)
    panel_url = f"/business/{slug}/painel"

    assert client.get(f"/business/onboarding/{establishment_id}").headers["Location"].endswith(panel_url)
    step = client.get(f"/business/onboarding/{establishment_id}/revisar")
    assert step.headers["Location"].endswith(panel_url)
    assert client.post(f"/business/onboarding/{establishment_id}/revisar", data={}).headers[
        "Location"
    ].endswith(panel_url)
    assert client.get("/business/onboarding").headers["Location"].endswith("/business/onboarding/novo")

    panel = client.get(panel_url).get_data(as_text=True)
    assert "Esta página foi desativada." in panel
    assert "Fale com o suporte do IDDUN." in panel
    assert "Continuar cadastro" not in panel
    account = client.get("/minha-conta").get_data(as_text=True)
    # QA-001-B1-03: só o dono vê a página moderada em Meus estabelecimentos,
    # apenas como informação, sem retomar cadastro nem acessar o painel.
    assert "Studio Moderado" in account
    assert "Fora do ar pela moderação · fale com o suporte" in account
    assert 'data-business-state="locked"' in account
    locked = account.split('data-business-state="locked"', 1)[1].split("</div>", 1)[0]
    assert "Studio Moderado" in locked
    assert "href=" not in locked
    assert "Continuar cadastro: Studio Moderado" not in account
    assert 'href="/business/onboarding/{}"'.format(establishment_id) not in account
    assert 'data-context-kind="establishment"' not in account

    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        assert item.is_active is False
        assert item.published_at.replace(tzinfo=None) == WHEN.replace(tzinfo=None)


def test_moderated_professional_stays_out_of_the_onboarding(app, client):
    user_id = _user(app, "pro-moderada@example.com")
    _login(client, user_id)
    complete_professional_onboarding(client)
    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        profile.is_active = False
        published_at = profile.published_at
        db.session.commit()

    for path in ("/pro/onboarding", "/pro/onboarding/nome", "/pro/onboarding/revisar"):
        assert client.get(path).headers["Location"].endswith("/pro/painel"), path
    assert client.post("/pro/onboarding/revisar", data={}).headers["Location"].endswith("/pro/painel")

    panel = client.get("/pro/painel").get_data(as_text=True)
    assert "FORA DO AR" in panel
    assert "Fale com o suporte do IDDUN." in panel
    assert "Seu perfil ainda não está no ar." not in panel
    account = client.get("/minha-conta").get_data(as_text=True)
    assert "Continuar cadastro profissional" not in account
    assert "fora do ar" in account

    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        assert profile.is_active is False and profile.published_at == published_at
