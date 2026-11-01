"""Cadastro de Estabelecimento por etapas (PR 3 do onboarding V0).

Substitui o assistente de POST único (PR-2 do QA e NV-07), mantendo as
mesmas garantias: português, texto digitado preservado, logo opcional
(DEC-ID-101), grade semanal válida (DEC-ID-103) e iniciais do DS sem logo.
Novas: rascunho por etapa, endereço só para físico/híbrido (F2),
apresentação 40+ (D-ONB-04), e-mail da conta só sugerido (D-ONB-05),
7 tipos (D-ONB-06) e publicação explícita (F1).
"""

import re
from datetime import datetime, timezone
from io import BytesIO

from flask import g
from PIL import Image
from sqlalchemy import func, select

from app.extensions import db
from app.forms.auth import RegisterForm
from app.forms.platform import BizStepContactForm, BUSINESS_CATEGORY_CHOICES
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.onboarding_steps import BUSINESS_CATEGORIES

from onboarding_flow import BUSINESS_DESCRIPTION, complete_business_onboarding

ENGLISH_DEFAULTS = (
    "This field is required.",
    "Field must be",
    "Invalid email address.",
    "Not a valid",
)


def _owner(app, email="dono-wizard@example.com"):
    with app.app_context():
        user = User(name="Dona Wizard", email=email, role=UserRole.CLIENT)
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
    # O fixture mantém um app context aberto; o Flask-Login guarda o usuário
    # em g. Ao trocar de conta no mesmo teste, a cache precisa ser limpa.
    g.pop("_login_user", None)


def _png(name="logo.png"):
    output = BytesIO()
    Image.new("RGB", (8, 8), (120, 80, 160)).save(output, format="PNG")
    output.seek(0)
    return output, name


def _count(app):
    with app.app_context():
        return db.session.scalar(select(func.count(Establishment.id)))


def _get(app, establishment_id):
    with app.app_context():
        return db.session.get(Establishment, establishment_id)


def _start(client, name="Studio Etapas"):
    response = client.post("/business/onboarding/novo", data={
        "name": name, "category": "salao", "city": "Curitiba", "state": "PR",
    })
    assert response.status_code == 302
    return int(response.headers["Location"].split("/")[-2])


def test_types_are_the_same_seven_in_web_and_app():
    assert BUSINESS_CATEGORY_CHOICES == list(BUSINESS_CATEGORIES.items())
    assert len(BUSINESS_CATEGORY_CHOICES) == 7


def test_start_goes_straight_to_first_step_without_drafts(app, client):
    _login(client, _owner(app))
    response = client.get("/business/onboarding")
    assert response.headers["Location"].endswith("/business/onboarding/novo")
    html = client.get("/business/onboarding/novo").get_data(as_text=True)
    assert "Etapa 1 de 7" in html
    assert len(re.findall(r'<input[^>]*name="category"[^>]*type="radio"', html)) == 7


def test_first_step_creates_a_private_draft_with_owner(app, client):
    user_id = _owner(app)
    _login(client, user_id)
    establishment_id = _start(client)

    item = _get(app, establishment_id)
    assert item.is_active is False and item.published_at is None
    assert item.email is None  # D-ONB-05
    assert client.get(f"/estabelecimentos/{item.slug}").status_code == 404
    with app.app_context():
        access = db.session.scalar(select(EstablishmentUserAccess))
        assert access.user_id == user_id
        assert access.role == EstablishmentAccessRole.OWNER
        assert access.status == EstablishmentAccessStatus.ACTIVE


def test_first_step_errors_are_portuguese_and_keep_text(app, client):
    _login(client, _owner(app))
    response = client.post("/business/onboarding/novo", data={"name": "Studio Pressa", "state": "P1"})
    html = response.get_data(as_text=True)
    assert response.status_code == 422
    assert _count(app) == 0
    for english in ENGLISH_DEFAULTS:
        assert english not in html
    assert "Escolha o tipo de estabelecimento." in html
    assert "Use as duas letras da UF." in html
    assert 'value="Studio Pressa"' in html


def test_address_is_asked_only_for_physical_or_hybrid(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client)

    mobile = client.post(f"/business/onboarding/{establishment_id}/atendimento",
                         data={"operation_mode": "mobile"})
    assert mobile.headers["Location"].endswith(f"/{establishment_id}/funcionamento")
    skipped = client.get(f"/business/onboarding/{establishment_id}/endereco")
    assert skipped.headers["Location"].endswith(f"/{establishment_id}/funcionamento")
    back = client.get(f"/business/onboarding/{establishment_id}/funcionamento").get_data(as_text=True)
    assert f'href="/business/onboarding/{establishment_id}/atendimento"' in back

    physical = client.post(f"/business/onboarding/{establishment_id}/atendimento",
                           data={"operation_mode": "physical"})
    assert physical.headers["Location"].endswith(f"/{establishment_id}/endereco")
    missing = client.post(f"/business/onboarding/{establishment_id}/endereco", data={})
    assert missing.status_code == 422
    assert "Informe o endereço comercial." in missing.get_data(as_text=True)


def test_mobile_only_business_publishes_without_address(app, client):
    _login(client, _owner(app))
    establishment_id = complete_business_onboarding(client, operation_mode="mobile")
    item = _get(app, establishment_id)
    assert item.is_active is True
    assert item.address_line1 is None


def test_fixed_hours_are_saved_and_partial_hours_rejected(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client)
    url = f"/business/onboarding/{establishment_id}/funcionamento"

    partial = client.post(url, data={"business_hours_mode": "fixed_hours", "monday_start": "09:00"})
    html = partial.get_data(as_text=True)
    assert partial.status_code == 422
    assert html.count('id="business_hours_mode-errors"') == 1
    assert "Informe abertura e fechamento válidos" in html
    assert _get(app, establishment_id).business_hours is None

    saved = client.post(url, data={
        "business_hours_mode": "fixed_hours",
        "monday_start": "09:00", "monday_end": "18:00",
        "friday_start": "10:00", "friday_end": "16:00",
    })
    assert saved.status_code == 302
    item = _get(app, establishment_id)
    assert item.business_hours_mode == "fixed_hours"
    assert item.business_hours == {
        "monday": [{"start": "09:00", "end": "18:00"}],
        "friday": [{"start": "10:00", "end": "16:00"}],
    }

    scheduled = client.post(url, data={"business_hours_mode": "scheduled"})
    assert scheduled.status_code == 302
    item = _get(app, establishment_id)
    assert item.business_hours_mode == "scheduled"
    assert item.business_hours is None


def test_weekly_hours_fields_are_portuguese_time_inputs(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client)
    html = client.get(f"/business/onboarding/{establishment_id}/funcionamento").get_data(as_text=True)

    panel = re.search(r"<fieldset[^>]*data-hours-panel[^>]*>(.*?)</fieldset>", html, re.S)
    assert panel, "bloco de horários ausente"
    block = panel.group(1)
    for day in ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"):
        assert day in block
    assert len(re.findall(r'<input[^>]*type="time"', block)) == 14
    assert 'aria-label="Abertura na segunda"' in block


def test_contact_suggests_account_email_and_needs_one_contact(app, client):
    _login(client, _owner(app, "dona-contato@example.com"))
    establishment_id = _start(client)
    url = f"/business/onboarding/{establishment_id}/contato"

    html = client.get(url).get_data(as_text=True)
    assert 'value="dona-contato@example.com"' in html
    assert _get(app, establishment_id).email is None

    short = client.post(url, data={"description": "Curta demais.", "email": ""})
    body = short.get_data(as_text=True)
    assert short.status_code == 422
    assert "Use entre 40 e 2000 caracteres." in body
    assert "Informe telefone ou e-mail comercial." in body
    assert re.search(r">\s*Curta demais\.</textarea>", body)

    saved = client.post(url, data={
        "description": BUSINESS_DESCRIPTION, "email": "Contato@Studio.Example", "phone": "",
    })
    assert saved.status_code == 302
    item = _get(app, establishment_id)
    assert item.email == "contato@studio.example"
    assert item.phone is None and item.whatsapp_enabled is False


def test_review_blocks_until_ready_and_publishes_once(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client)
    review = f"/business/onboarding/{establishment_id}/revisar"

    html = client.get(review).get_data(as_text=True)
    assert "Para publicar, falta:" in html
    assert "Diga como o estabelecimento atende." in html
    assert "retorno=revisar" in html
    forced = client.post(review, data={})
    assert forced.status_code == 422
    assert _get(app, establishment_id).is_active is False

    complete_business_onboarding_steps = {
        "atendimento": {"operation_mode": "hybrid"},
        "endereco": {"address_line1": "Rua A, 10"},
        "funcionamento": {"business_hours_mode": "scheduled"},
        "contato": {"description": BUSINESS_DESCRIPTION, "phone": "41999990000"},
    }
    for slug, data in complete_business_onboarding_steps.items():
        assert client.post(f"/business/onboarding/{establishment_id}/{slug}", data=data).status_code == 302

    published = client.post(review, data={})
    assert published.headers["Location"].endswith(f"/business/onboarding/{establishment_id}/concluido")
    item = _get(app, establishment_id)
    assert item.is_active is True and item.onboarding_completed is True
    first_published_at = item.published_at

    done = client.get(f"/business/onboarding/{establishment_id}/concluido").get_data(as_text=True)
    assert "está no ar." in done
    assert "Reservas ainda não" in done
    assert "Convidar a equipe" in done

    again = client.post(review, data={})
    assert again.headers["Location"].endswith(f"/business/{item.slug}/painel")
    assert _get(app, establishment_id).published_at == first_published_at


def test_edit_from_review_returns_to_review(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client)
    response = client.post(
        f"/business/onboarding/{establishment_id}/atendimento?retorno=revisar",
        data={"operation_mode": "mobile"},
    )
    assert response.headers["Location"].endswith(f"/{establishment_id}/revisar")


def test_other_owner_cannot_open_or_change_a_draft(app, client):
    _login(client, _owner(app, "dona-a@example.com"))
    establishment_id = _start(client)
    _login(client, _owner(app, "dona-b@example.com"))

    assert client.get(f"/business/onboarding/{establishment_id}/contato").status_code == 404
    assert client.post(f"/business/onboarding/{establishment_id}/atendimento",
                       data={"operation_mode": "mobile"}).status_code == 404
    assert client.post(f"/business/onboarding/{establishment_id}/revisar", data={}).status_code == 404
    assert _get(app, establishment_id).operation_mode is None


def test_published_or_legacy_establishment_skips_onboarding(app, client):
    user_id = _owner(app)
    _login(client, user_id)
    establishment_id = _start(client, name="Studio Legado")
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        item.is_active = True
        item.published_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        db.session.commit()
        slug = item.slug

    response = client.get(f"/business/onboarding/{establishment_id}/atendimento")
    assert response.headers["Location"].endswith(f"/business/{slug}/painel")
    assert client.get("/business/onboarding").headers["Location"].endswith("/business/onboarding/novo")


def test_owner_with_drafts_chooses_to_continue_or_start_another(app, client):
    _login(client, _owner(app))
    first = _start(client, name="Studio Um")
    html = client.get("/business/onboarding").get_data(as_text=True)
    assert "Continuar Studio Um" in html
    assert f'href="/business/onboarding/{first}/atendimento"' in html
    assert "Criar outro estabelecimento" in html

    second = _start(client, name="Studio Dois")
    assert second != first
    assert _count(app) == 2


def test_media_step_is_optional_and_logo_is_not_required(app, client):
    _login(client, _owner(app))
    establishment_id = complete_business_onboarding(
        client, name="Studio Sem Logo", logo=None,
    )
    item = _get(app, establishment_id)
    assert item.logo_url is None and item.is_active is True

    for path in (f"/estabelecimentos/{item.slug}", "/estabelecimentos", f"/business/{item.slug}/painel"):
        html = client.get(path).get_data(as_text=True)
        assert 'class="ds-avatar-initials ds-avatar-initials--fill"' in html, path
        assert ">SL</span>" in html, path


def test_media_step_saves_logo_and_gallery(app, client):
    _login(client, _owner(app))
    establishment_id = complete_business_onboarding(
        client, logo=_png(), logo_focus=(41, 52), cover_focus=(63, 48),
        gallery=(_png("1.png"), _png("2.png")), publish=False,
    )
    item = _get(app, establishment_id)
    assert item.logo_url
    assert (item.logo_focus_x, item.logo_focus_y) == (41, 52)
    assert (item.cover_focus_x, item.cover_focus_y) == (63, 48)
    with app.app_context():
        assert len(db.session.get(Establishment, establishment_id).gallery_items) == 2
    assert item.is_active is False


def test_editing_a_draft_does_not_mark_it_as_published(app, client):
    _login(client, _owner(app))
    establishment_id = complete_business_onboarding(client, publish=False)
    item = _get(app, establishment_id)
    response = client.post(f"/business/{item.slug}/editar", data={
        "name": item.name, "category": "salao", "description": BUSINESS_DESCRIPTION,
        "address_line1": "Rua Teste, 100", "city": "Curitiba", "state": "PR",
    }, content_type="multipart/form-data")
    assert response.status_code == 302
    item = _get(app, establishment_id)
    assert item.is_active is False and item.published_at is None
    published = client.post(f"/business/onboarding/{establishment_id}/revisar", data={})
    assert published.headers["Location"].endswith("/concluido")


def test_draft_dashboards_point_back_to_onboarding(app, client):
    _login(client, _owner(app))
    establishment_id = _start(client, name="Studio Rascunho")
    slug = _get(app, establishment_id).slug

    panel = client.get(f"/business/{slug}/painel").get_data(as_text=True)
    assert "Esta página ainda não está no ar." in panel
    account = client.get("/minha-conta").get_data(as_text=True)
    assert "Continuar cadastro: Studio Rascunho" in account


def test_all_web_forms_answer_in_portuguese(app):
    with app.test_request_context(method="POST", data={"email": "nao-e-email"}):
        register = RegisterForm(meta={"csrf": False})
        register.validate()
        contact = BizStepContactForm(meta={"csrf": False})
        contact.validate()

    messages = [
        message
        for form in (register, contact)
        for errors in form.errors.values()
        for message in errors
    ]
    assert messages
    for message in messages:
        for english in ENGLISH_DEFAULTS:
            assert english not in message
    assert "Informe um e-mail válido." in register.errors["email"]
    assert "Informe um e-mail válido." in contact.errors["email"]
