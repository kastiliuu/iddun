"""PR 1 do onboarding: rascunhos seguros, salvamento parcial e publicação explícita.

Os dois primeiros testes reproduzem defeitos achados na auditoria de 01/11/2026
antes da correção: (1) renomear um rascunho criava outro estabelecimento e
(2) salvar sem um campo opcional apagava o valor já salvo.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

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
from app.services.api_auth import issue_session


BASE = "/api/v1/onboarding"

DRAFT = {
    "name": "Studio Rascunho",
    "category": "salao",
    "city": "Curitiba",
    "state": "PR",
    "description": "Cuidado de cabelo com hora marcada e atendimento atento.",
    "phone": "41999990000",
    "neighborhood": "Batel",
}

READY = {
    **DRAFT,
    "operationMode": "physical",
    "businessHoursMode": "scheduled",
    "addressLine1": "Rua Comercial, 100",
}


def _client(app, email):
    with app.app_context():
        user = User(name="Dona do Studio", email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        db.session.commit()
        tokens = issue_session(user)
        return user.id, {"Authorization": f"Bearer {tokens.access_token}"}


def _count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def _create(client, headers, data=None):
    response = client.post(f"{BASE}/establishment", headers=headers, json=data or DRAFT)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["establishment"]


def _publish_directly(app, establishment_id, *, when=None):
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        item.is_active = True
        item.onboarding_completed = True
        item.published_at = when or datetime(2026, 10, 1, tzinfo=timezone.utc)
        db.session.commit()


# --- Defeitos reproduzidos -------------------------------------------------


def test_renaming_a_draft_by_id_updates_it_instead_of_creating_another(app, client):
    _, headers = _client(app, "renomear@example.com")
    first = _create(client, headers)

    renamed = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={**DRAFT, "establishmentId": first["id"], "name": "Studio Novo Nome"},
    )

    assert renamed.status_code in {200, 201}
    body = renamed.get_json()["establishment"]
    assert body["id"] == first["id"]
    assert body["name"] == "Studio Novo Nome"
    with app.app_context():
        assert _count(Establishment) == 1
        assert _count(EstablishmentUserAccess) == 1


def test_saving_without_optional_fields_keeps_saved_values(app, client):
    _, headers = _client(app, "parcial@example.com")
    first = _create(client, headers)
    minimal = {key: DRAFT[key] for key in ("name", "category", "city", "state")}

    again = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={**minimal, "establishmentId": first["id"]},
    )

    assert again.status_code in {200, 201}
    body = again.get_json()["establishment"]
    assert body["description"] == DRAFT["description"]
    assert body["phone"] == DRAFT["phone"]
    assert body["neighborhood"] == DRAFT["neighborhood"]


def test_legacy_post_without_optional_fields_keeps_saved_values(app, client):
    """Clientes antigos reenviam sem id; ausência continua preservando."""
    _, headers = _client(app, "parcial-antigo@example.com")
    _create(client, headers)
    minimal = {key: DRAFT[key] for key in ("name", "category", "city", "state")}

    again = client.post(f"{BASE}/establishment", headers=headers, json=minimal)

    assert again.status_code in {200, 201}
    body = again.get_json()["establishment"]
    assert body["description"] == DRAFT["description"]
    assert body["phone"] == DRAFT["phone"]
    with app.app_context():
        assert _count(Establishment) == 1


def test_professional_post_without_optional_fields_keeps_bio_and_phone(app, client):
    _, headers = _client(app, "pro-parcial@example.com")
    full = {
        "displayName": "Marina Parcial",
        "primarySpecialty": "Nail designer",
        "categories": ["unhas"],
        "city": "Curitiba",
        "state": "PR",
        "bio": "Atendimento cuidadoso para unhas naturais e alongamento.",
        "phone": "41988887777",
    }
    assert client.post(f"{BASE}/professional", headers=headers, json=full).status_code in {200, 201}
    without_optional = {key: value for key, value in full.items() if key not in {"bio", "phone"}}

    again = client.post(f"{BASE}/professional", headers=headers, json=without_optional)

    assert again.status_code == 200
    profile = again.get_json()["profile"]
    assert profile["bio"] == full["bio"]
    assert profile["phone"] == full["phone"]


# --- Id estável e autorização por proprietário ------------------------------


def test_other_account_cannot_read_update_or_publish_by_id(app, client):
    _, owner = _client(app, "dona@example.com")
    _, intruder = _client(app, "intrusa@example.com")
    item = _create(client, owner, READY)
    path = f"{BASE}/establishments/{item['id']}"

    assert client.get(path, headers=intruder).status_code == 404
    assert client.patch(path, headers=intruder, json={"name": "Tomado"}).status_code == 404
    assert client.post(f"{path}/publish", headers=intruder).status_code == 404
    via_post = client.post(
        f"{BASE}/establishment",
        headers=intruder,
        json={**DRAFT, "establishmentId": item["id"], "name": "Tomado"},
    )
    assert via_post.status_code == 404
    assert via_post.get_json()["error"]["code"] == "establishment_not_found"

    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        assert stored.name == DRAFT["name"]
        assert stored.is_active is False
        assert _count(Establishment) == 1


def test_unknown_id_and_missing_token_are_rejected(app, client):
    _, headers = _client(app, "sem-id@example.com")
    assert client.patch(f"{BASE}/establishments/999", headers=headers, json={"name": "X Y"}).status_code == 404
    assert client.post(f"{BASE}/establishments/999/publish", headers=headers).status_code == 404
    assert client.patch(f"{BASE}/establishments/1", json={"name": "X Y"}).status_code == 401
    assert client.post(f"{BASE}/establishments/1/publish").status_code == 401
    assert client.get(f"{BASE}/establishments").status_code == 401
    bad = client.post(f"{BASE}/establishment", headers=headers, json={**DRAFT, "establishmentId": "abc"})
    assert bad.status_code == 400
    huge = "9" * 30
    assert client.patch(f"{BASE}/establishments/{huge}", headers=headers, json={"name": "X Y"}).status_code == 404
    assert client.post(f"{BASE}/establishment", headers=headers,
                       json={**DRAFT, "establishmentId": huge}).status_code == 404


def test_name_compatibility_never_touches_another_owner(app, client):
    _, first = _client(app, "primeira@example.com")
    _, second = _client(app, "segunda@example.com")
    mine = _create(client, first)

    theirs = client.post(f"{BASE}/establishment", headers=second, json={**DRAFT, "description": None})

    assert theirs.status_code == 201
    assert theirs.get_json()["establishment"]["id"] != mine["id"]
    with app.app_context():
        assert db.session.get(Establishment, int(mine["id"])).description == DRAFT["description"]
        assert _count(Establishment) == 2


def test_list_returns_only_owned_establishments_with_journey(app, client):
    _, owner = _client(app, "lista@example.com")
    _, other = _client(app, "lista-outra@example.com")
    _create(client, owner)
    _create(client, other, {**DRAFT, "name": "Outro Studio"})

    listed = client.get(f"{BASE}/establishments", headers=owner)

    assert listed.status_code == 200
    items = listed.get_json()["establishments"]
    assert [item["name"] for item in items] == [DRAFT["name"]]
    assert items[0]["journey"]["currentStep"] == "operation"
    assert listed.headers["Cache-Control"] == "no-store"


# --- Salvamento parcial -------------------------------------------------------


def test_patch_changes_only_sent_fields_and_clears_explicitly(app, client):
    _, headers = _client(app, "patch@example.com")
    item = _create(client, headers, READY)
    path = f"{BASE}/establishments/{item['id']}"

    renamed = client.patch(path, headers=headers, json={"name": "Studio Renomeado"})
    assert renamed.status_code == 200
    body = renamed.get_json()["establishment"]
    assert body["name"] == "Studio Renomeado"
    assert body["slug"] == item["slug"]
    assert body["description"] == DRAFT["description"]
    assert body["addressLine1"] == READY["addressLine1"]

    cleared = client.patch(path, headers=headers, json={"neighborhood": None, "phone": ""})
    assert cleared.status_code == 200
    body = cleared.get_json()["establishment"]
    assert body["neighborhood"] == ""
    assert body["phone"] == ""
    assert body["description"] == DRAFT["description"]
    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        assert stored.neighborhood is None
        assert stored.phone is None
        assert stored.whatsapp_enabled is False
        assert _count(Establishment) == 1


def test_patch_saves_address_complement_and_postal_code(app, client):
    _, headers = _client(app, "endereco@example.com")
    item = _create(client, headers)
    response = client.patch(
        f"{BASE}/establishments/{item['id']}",
        headers=headers,
        json={"addressLine1": "Rua A, 10", "addressLine2": "Sala 2", "postalCode": "80000-000"},
    )
    assert response.status_code == 200
    body = response.get_json()["establishment"]
    assert (body["addressLine1"], body["addressLine2"], body["postalCode"]) == (
        "Rua A, 10", "Sala 2", "80000-000",
    )


@pytest.mark.parametrize("changes", [
    {"name": ""},
    {"name": None},
    {"category": ""},
    {"category": "padaria"},
    {"city": None},
    {"state": "P"},
    {"state": ""},
    {"description": 42},
    {"phone": ["41"]},
    {"postalCode": "1" * 17},
    {"isActive": True},
    {"publishedAt": "2026-01-01"},
    {"slug": "outro"},
])
def test_patch_rejects_invalid_required_or_unknown_fields(app, client, changes):
    _, headers = _client(app, "invalido@example.com")
    item = _create(client, headers)
    response = client.patch(f"{BASE}/establishments/{item['id']}", headers=headers, json=changes)
    assert response.status_code == 400
    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        assert stored.name == DRAFT["name"]
        assert stored.category == DRAFT["category"]
        assert stored.city == DRAFT["city"]
        assert stored.is_active is False
        assert stored.description == DRAFT["description"]


def test_published_establishment_cannot_lose_a_met_requirement(app, client):
    _, headers = _client(app, "publicado@example.com")
    item = _create(client, headers, READY)
    assert client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers).status_code == 200
    path = f"{BASE}/establishments/{item['id']}"

    blocked = client.patch(path, headers=headers, json={"description": None})
    assert blocked.status_code == 409
    error = blocked.get_json()["error"]
    assert error["code"] == "publication_requirement_removed"
    assert error["details"]["missingRequirements"] == [
        {"key": "description", "message": "Escreva a apresentação do estabelecimento."}
    ]

    to_mobile = client.patch(path, headers=headers, json={"operationMode": "mobile", "addressLine1": None})
    assert to_mobile.status_code == 200
    allowed = client.patch(path, headers=headers, json={"neighborhood": "Centro"})
    assert allowed.status_code == 200
    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        assert stored.description == DRAFT["description"]
        assert stored.neighborhood == "Centro"
        assert stored.is_active is True


def test_legacy_incomplete_published_stays_published_and_editable(app, client):
    user_id, headers = _client(app, "legado@example.com")
    item = _create(client, headers)  # sem modalidade e funcionamento
    _publish_directly(app, int(item["id"]))

    edited = client.patch(
        f"{BASE}/establishments/{item['id']}", headers=headers, json={"neighborhood": "Centro"},
    )

    assert edited.status_code == 200
    body = edited.get_json()["establishment"]
    assert body["isActive"] is True
    assert body["journey"]["published"] is True
    assert body["journey"]["readyToPublish"] is False
    assert body["profileCompletion"] < 100


# --- Publicação explícita ---------------------------------------------------


def test_publish_is_blocked_with_specific_messages_until_ready(app, client):
    _, headers = _client(app, "incompleto@example.com")
    item = _create(client, headers)

    response = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)

    assert response.status_code == 409
    error = response.get_json()["error"]
    assert error["code"] == "establishment_incomplete"
    assert [entry["key"] for entry in error["details"]["missingRequirements"]] == [
        "operation_mode", "business_hours_mode",
    ]
    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        assert stored.is_active is False
        assert stored.published_at is None
        assert stored.onboarding_completed is False


def test_publish_is_explicit_and_idempotent(app, client):
    _, headers = _client(app, "publicar@example.com")
    item = _create(client, headers, READY)
    assert item["isActive"] is False
    assert item["journey"]["registrationComplete"] is True
    assert item["journey"]["published"] is False

    first = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)
    assert first.status_code == 200
    first_body = first.get_json()
    assert first_body["alreadyPublished"] is False
    assert first_body["establishment"]["isActive"] is True
    assert first_body["establishment"]["journey"]["published"] is True
    published_at = first_body["establishment"]["publishedAt"]
    assert published_at

    second = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)
    assert second.status_code == 200
    assert second.get_json()["alreadyPublished"] is True
    assert second.get_json()["establishment"]["publishedAt"] == published_at
    with app.app_context():
        assert _count(Establishment) == 1


def test_mobile_only_business_publishes_without_address(app, client):
    _, headers = _client(app, "domicilio@example.com")
    data = {**DRAFT, "operationMode": "mobile", "businessHoursMode": "scheduled"}
    item = _create(client, headers, data)
    assert item["journey"]["steps"][2] == {
        "key": "address", "label": "Endereço comercial", "required": True,
        "applicable": False, "complete": True,
    }

    response = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["establishment"]["addressLine1"] is None


def test_moderated_establishment_is_not_republished_by_owner(app, client):
    _, headers = _client(app, "moderado@example.com")
    item = _create(client, headers, READY)
    with app.app_context():
        stored = db.session.get(Establishment, int(item["id"]))
        stored.published_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        stored.is_active = False
        db.session.commit()

    response = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "publication_locked"
    with app.app_context():
        assert db.session.get(Establishment, int(item["id"])).is_active is False


def test_publishing_does_not_make_anything_bookable(app, client):
    """Publicado ≠ reservável (DEC-ID-108): nenhum serviço ou horário surge."""
    from app.models.booking import ExperienceSlot
    from app.models.experience import Experience

    _, headers = _client(app, "sem-reserva@example.com")
    item = _create(client, headers, READY)
    response = client.post(f"{BASE}/establishments/{item['id']}/publish", headers=headers)
    assert response.status_code == 200
    journey = response.get_json()["establishment"]["journey"]
    assert "bookable" not in journey
    with app.app_context():
        assert _count(Experience) == 0
        assert _count(ExperienceSlot) == 0


# --- Regra única de prontidão e etapas --------------------------------------


def test_business_completion_uses_the_single_approved_rule(app):
    with app.app_context():
        item = Establishment(
            name="Sem logo", slug="sem-logo", category="salao",
            description="Apresentação.", city="Curitiba", state="PR",
            phone="41999990000", operation_mode="mobile",
            business_hours_mode="scheduled",
        )
        assert item.logo_url is None
        assert item.profile_completion == 100
        assert item.ready_to_publish is True

        item.business_hours_mode = None
        assert item.profile_completion < 100
        assert item.ready_to_publish is False


def test_business_journey_moves_step_by_step(app, client):
    _, headers = _client(app, "etapas@example.com")
    item = _create(client, headers, {key: DRAFT[key] for key in ("name", "category", "city", "state")})
    path = f"{BASE}/establishments/{item['id']}"
    assert item["journey"]["currentStep"] == "operation"

    sequence = [
        ({"operationMode": "hybrid"}, "address"),
        ({"addressLine1": "Rua A, 10"}, "hours"),
        ({"businessHoursMode": "fixed_hours"}, "hours"),
        ({"businessHours": {"monday": [{"start": "09:00", "end": "18:00"}]}}, "contact"),
        # O e-mail da conta já vem como e-mail comercial do rascunho.
        ({"description": "Apresentação."}, "review"),
        ({"commercialEmail": ""}, "contact"),
        ({"phone": "41999990000"}, "review"),
    ]
    for changes, expected in sequence:
        response = client.patch(path, headers=headers, json=changes)
        assert response.status_code == 200, response.get_json()
        journey = response.get_json()["establishment"]["journey"]
        assert journey["currentStep"] == expected, changes

    assert journey["registrationComplete"] is True
    assert journey["profileComplete"] is True
    assert journey["published"] is False
    assert journey["missingRequirements"] == []


# --- Profissional ----------------------------------------------------------


def test_professional_patch_creates_private_draft_from_name_only(app, client):
    user_id, headers = _client(app, "pro-etapa@example.com")

    created = client.patch(f"{BASE}/professional", headers=headers, json={"displayName": "Marina Etapas"})

    assert created.status_code == 200
    profile = created.get_json()["profile"]
    assert profile["isActive"] is False
    assert profile["journey"]["currentStep"] == "location"
    assert profile["journey"]["registrationComplete"] is False

    for changes, expected in [
        ({"city": "Curitiba", "state": "pr"}, "specialty"),
        ({"primarySpecialty": "Nail designer", "categories": ["unhas"]}, "modality"),
        ({"attendanceModalities": ["own_space"]}, "presentation"),
        ({"bio": "Atendimento cuidadoso."}, "review"),
    ]:
        response = client.patch(f"{BASE}/professional", headers=headers, json=changes)
        assert response.status_code == 200, response.get_json()
        assert response.get_json()["profile"]["journey"]["currentStep"] == expected

    body = response.get_json()["profile"]
    assert body["state"] == "PR"
    assert body["journey"]["registrationComplete"] is True
    assert body["journey"]["published"] is False
    # Perfil 100% continua sendo outro conceito (foto e portfólio contam).
    assert body["journey"]["profileComplete"] is False
    with app.app_context():
        assert _count(ProfessionalProfile) == 1


@pytest.mark.parametrize("changes", [
    {"categories": ["inexistente"]},
    {"state": "XYZ"},
    {"displayName": ""},
    {"attendanceModalities": ["online"]},
    {"whatsappEnabled": "sim"},
    {"isActive": True},
])
def test_professional_patch_rejects_invalid_or_unknown(app, client, changes):
    _, headers = _client(app, "pro-invalido@example.com")
    assert client.patch(f"{BASE}/professional", headers=headers, json={"displayName": "Marina"}).status_code == 200
    response = client.patch(f"{BASE}/professional", headers=headers, json=changes)
    assert response.status_code == 400
    with app.app_context():
        profile = db.session.scalar(select(ProfessionalProfile))
        assert profile.display_name == "Marina"
        assert profile.is_active is False


def test_professional_patch_without_profile_requires_name(app, client):
    _, headers = _client(app, "pro-sem-nome@example.com")
    response = client.patch(f"{BASE}/professional", headers=headers, json={"city": "Curitiba"})
    assert response.status_code == 400
    with app.app_context():
        assert _count(ProfessionalProfile) == 0


def _ready_professional(client, headers):
    response = client.patch(f"{BASE}/professional", headers=headers, json={
        "displayName": "Marina Pronta", "city": "Curitiba", "state": "PR",
        "primarySpecialty": "Nail designer", "categories": ["unhas"],
        "attendanceModalities": ["own_space"], "bio": "Atendimento cuidadoso.",
    })
    assert response.status_code == 200
    return response.get_json()["profile"]


def test_professional_publish_is_idempotent_and_guards_requirements(app, client):
    _, headers = _client(app, "pro-publica@example.com")
    _ready_professional(client, headers)

    first = client.post(f"{BASE}/professional/publish", headers=headers)
    assert first.status_code == 200
    assert first.get_json()["alreadyPublished"] is False
    published_at = first.get_json()["profile"]["publishedAt"]

    second = client.post(f"{BASE}/professional/publish", headers=headers)
    assert second.status_code == 200
    assert second.get_json()["alreadyPublished"] is True
    assert second.get_json()["profile"]["publishedAt"] == published_at

    blocked = client.patch(f"{BASE}/professional", headers=headers, json={"bio": None})
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "publication_requirement_removed"
    blocked_post = client.post(f"{BASE}/professional", headers=headers, json={
        "displayName": "Marina Pronta", "primarySpecialty": "Nail designer",
        "categories": ["unhas"], "city": "Curitiba", "state": "PR", "bio": "",
    })
    assert blocked_post.status_code == 409
    with app.app_context():
        profile = db.session.scalar(select(ProfessionalProfile))
        assert profile.bio == "Atendimento cuidadoso."
        assert profile.is_active is True


def test_professional_publish_incomplete_lists_messages(app, client):
    _, headers = _client(app, "pro-incompleto@example.com")
    client.patch(f"{BASE}/professional", headers=headers, json={"displayName": "Marina"})

    response = client.post(f"{BASE}/professional/publish", headers=headers)

    assert response.status_code == 409
    error = response.get_json()["error"]
    assert error["code"] == "profile_incomplete"
    assert "completion" in error["details"]
    keys = [entry["key"] for entry in error["details"]["missingRequirements"]]
    assert keys == ["city", "state", "specialty", "categories", "attendance_modalities", "bio"]


def test_moderated_professional_is_not_republished_by_owner(app, client):
    _, headers = _client(app, "pro-moderado@example.com")
    _ready_professional(client, headers)
    with app.app_context():
        profile = db.session.scalar(select(ProfessionalProfile))
        profile.published_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        profile.is_active = False
        db.session.commit()

    response = client.post(f"{BASE}/professional/publish", headers=headers)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "publication_locked"
    with app.app_context():
        assert db.session.scalar(select(ProfessionalProfile)).is_active is False
