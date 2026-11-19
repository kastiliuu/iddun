"""V1-CONV-D06 — foto do serviço e horários em lote pelo app.

Mesmas regras da Web:
- foto: só o dono, só rascunho ou pausado, JPG/PNG/WEBP até 5 MB;
- lote: até 20 horários num dia, tudo ou nada, mesmas checagens de conflito.

Também cobre o defeito encontrado nesta PR: sete rotas do app (só Bearer)
não estavam fora do CSRF da Web e respondiam 400 csrf_failed em produção.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import func, select

from app import create_app
from app.extensions import db
from app.models.booking import ExperienceSlot
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session

BASE = "/api/v1/onboarding/professional/services"


def _png(size=(32, 32)):
    output = BytesIO()
    Image.new("RGB", size, (120, 80, 140)).save(output, format="PNG")
    output.seek(0)
    return output


def _pro(email, slug):
    user = User(name=f"Pro {slug}", email=email, role=UserRole.PROFESSIONAL)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    profile = ProfessionalProfile(
        user_id=user.id, display_name=f"Pro {slug}", slug=slug, city="Curitiba",
        state="PR", timezone="America/Sao_Paulo", is_active=True, onboarding_completed=True,
    )
    db.session.add(profile)
    db.session.flush()
    return user, profile


def _service(profile, slug, status):
    item = Experience(
        professional=profile, title=f"Serviço {slug}", slug=slug, category="unhas",
        short_description="Resumo.", regular_price=Decimal("100.00"), price=Decimal("90.00"),
        duration_minutes=60, status=status,
    )
    db.session.add(item)
    db.session.flush()
    return item


@pytest.fixture
def world(app):
    owner, profile = _pro("dono-lote@example.com", "dono-lote")
    other, _ = _pro("outro-lote@example.com", "outro-lote")
    published = _service(profile, "servico-publicado-lote", ExperienceStatus.PUBLISHED)
    draft = _service(profile, "servico-rascunho-lote", ExperienceStatus.DRAFT)
    db.session.commit()
    return {
        "owner": {"Authorization": f"Bearer {issue_session(owner).access_token}"},
        "other": {"Authorization": f"Bearer {issue_session(other).access_token}"},
        "published": published.id, "draft": draft.id,
    }


def _future_date(days=10):
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


def _slots(service_id):
    return db.session.scalar(select(func.count(ExperienceSlot.id)).where(ExperienceSlot.experience_id == service_id))


# ------------------------------------------------------------- lote

def test_batch_creates_all_times_for_the_owner(client, world):
    url = f"{BASE}/{world['published']}/availability/batch"
    response = client.post(url, headers=world["owner"], json={"date": _future_date(), "times": ["09:00", "10:00", "11:00"]})
    assert response.status_code == 201
    assert response.get_json()["createdCount"] == 3
    assert _slots(world["published"]) == 3


def test_batch_is_all_or_nothing_on_conflict(client, world):
    url = f"{BASE}/{world['published']}/availability/batch"
    day = _future_date(12)
    assert client.post(url, headers=world["owner"], json={"date": day, "times": ["10:00"]}).status_code == 201
    # 09:30 sobrepõe 10:00 (60 min): nenhum horário do lote é criado.
    conflict = client.post(url, headers=world["owner"], json={"date": day, "times": ["08:00", "09:30"]})
    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "availability_invalid"
    assert _slots(world["published"]) == 1


@pytest.mark.parametrize("body", [
    {"date": "2027-01-10"},
    {"date": "2027-01-10", "times": []},
    {"date": "2027-01-10", "times": "09:00"},
    {"date": "2027-01-10", "times": [9]},
    {"date": "2027-01-10", "times": ["09:00"] * 21},
    {"date": "2027-01-10", "times": ["09:00"], "extra": 1},
])
def test_batch_rejects_malformed_bodies(client, world, body):
    url = f"{BASE}/{world['published']}/availability/batch"
    assert client.post(url, headers=world["owner"], json=body).status_code == 400
    assert _slots(world["published"]) == 0


def test_batch_refuses_strangers_drafts_and_anonymous(client, world):
    body = {"date": _future_date(), "times": ["09:00"]}
    assert client.post(f"{BASE}/{world['published']}/availability/batch", json=body).status_code == 401
    assert client.post(f"{BASE}/{world['published']}/availability/batch", headers=world["other"], json=body).status_code == 404
    draft = client.post(f"{BASE}/{world['draft']}/availability/batch", headers=world["owner"], json=body)
    assert draft.status_code == 409
    assert _slots(world["published"]) == 0 and _slots(world["draft"]) == 0


# ------------------------------------------------------------- foto

def _upload(client, service_id, headers, data=None, **kwargs):
    if data is None:
        data = {"file": (_png(), "capa.png")}
    return client.post(f"{BASE}/{service_id}/image", headers=headers, data=data,
                       content_type=kwargs.pop("content_type", "multipart/form-data"), **kwargs)


def test_owner_uploads_image_to_a_draft_and_detail_returns_it(client, world):
    response = _upload(client, world["draft"], world["owner"])
    assert response.status_code == 200
    assert response.get_json()["imageUrl"]
    stored = db.session.get(Experience, world["draft"]).image_url
    assert stored
    detail = client.get(f"{BASE}/{world['draft']}", headers=world["owner"]).get_json()["service"]
    assert detail["imageUrl"]

    # Trocar a foto mantém um único arquivo ligado ao serviço.
    assert _upload(client, world["draft"], world["owner"]).status_code == 200
    db.session.expire_all()
    assert db.session.get(Experience, world["draft"]).image_url != stored


def test_image_rules_match_the_web(client, world):
    assert _upload(client, world["draft"], {}).status_code == 401
    assert _upload(client, world["draft"], world["other"]).status_code == 404
    published = _upload(client, world["published"], world["owner"])
    assert published.status_code == 409
    assert published.get_json()["error"]["code"] == "service_not_editable"

    text = _upload(client, world["draft"], world["owner"], data={"file": (BytesIO(b"nao e imagem"), "capa.txt")})
    assert text.status_code == 400
    assert _upload(client, world["draft"], world["owner"], data={}).status_code == 400
    json_body = client.post(f"{BASE}/{world['draft']}/image", headers=world["owner"], json={"file": "x"})
    assert json_body.status_code == 415
    assert db.session.get(Experience, world["draft"]).image_url is None


def test_image_larger_than_limit_is_refused(client, world):
    big = BytesIO(b"0" * (6 * 1024 * 1024))
    response = _upload(client, world["draft"], world["owner"], data={"file": (big, "grande.png")})
    assert response.status_code in (400, 413)
    assert db.session.get(Experience, world["draft"]).image_url is None


# ------------------------------------------------------------- CSRF

APP_ROUTES = [
    ("post", BASE, {"name": "x"}),
    ("patch", BASE + "/{draft}", {"name": "x"}),
    ("post", BASE + "/{draft}/status", {"action": "publish"}),
    ("post", BASE + "/{published}/availability", {"date": "2027-01-10", "time": "10:00"}),
    ("post", BASE + "/{published}/availability/1/status", {"action": "block"}),
    ("post", BASE + "/{published}/availability/from-schedule", {"date": "2027-01-10"}),
    ("post", BASE + "/{published}/availability/batch", {"date": "2027-01-10", "times": ["10:00"]}),
    ("put", "/api/v1/onboarding/professional/weekly-schedule", {"days": []}),
]


@pytest.fixture
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


def test_app_routes_with_bearer_are_not_blocked_by_web_csrf(csrf_app):
    owner, profile = _pro("csrf-lote@example.com", "csrf-lote")
    published = _service(profile, "csrf-publicado", ExperienceStatus.PUBLISHED)
    draft = _service(profile, "csrf-rascunho", ExperienceStatus.DRAFT)
    db.session.commit()
    headers = {"Authorization": f"Bearer {issue_session(owner).access_token}"}
    client = csrf_app.test_client()
    # A foto antes do laço: o laço publica o rascunho, e publicado não troca foto.
    image = client.post(f"{BASE}/{draft.id}/image", headers=headers,
                        data={"file": (_png(), "capa.png")}, content_type="multipart/form-data")
    assert image.status_code == 200
    for method, path, body in APP_ROUTES:
        url = path.format(draft=draft.id, published=published.id)
        response = getattr(client, method)(url, headers=headers, json=body)
        code = (response.get_json() or {}).get("error", {}).get("code")
        assert code != "csrf_failed", (method, url)


def test_every_api_mutation_is_bearer_exempt_or_checks_cookie_csrf(csrf_app):
    """Guarda: nenhuma rota de API nova pode repetir o defeito."""
    from app.extensions import csrf

    exempt = csrf._exempt_views
    unprotected = []
    for rule in csrf_app.url_map.iter_rules():
        if not rule.rule.startswith("/api") or not (rule.methods & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        view = csrf_app.view_functions[rule.endpoint]
        if f"{view.__module__}.{view.__name__}" not in exempt:
            unprotected.append(rule.rule)
    assert unprotected == []
