"""PR-2 — cadastro Business íntegro (BUG-015, BUG-017, D-QA-01).

- DEC-ID-101: logo, capa e fotos são opcionais; a empresa publica sem logo.
- Mensagens de validação em português, ao lado do campo e num resumo
  navegável; o texto digitado volta preenchido e, quando havia arquivos,
  o resumo pede para escolhê-los de novo.
- O botão "Criar página da empresa" só aparece na última etapa.
- Empresa sem logo aparece com iniciais do Design System.
"""

import re
from io import BytesIO

from PIL import Image
from sqlalchemy import func, select

from app.extensions import db
from app.forms.auth import RegisterForm
from app.forms.platform import BusinessOnboardingForm
from app.models.establishment import Establishment
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

VALID = {
    "name": "Studio Sem Logo",
    "category": "salao",
    "description": (
        "Um espaço dedicado a coloração autoral, cuidado capilar "
        "e atendimento sem pressa."
    ),
    "address_line1": "Rua Teste, 100",
    "city": "Curitiba",
    "state": "PR",
}

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


def _png():
    output = BytesIO()
    Image.new("RGB", (8, 8), (120, 80, 160)).save(output, format="PNG")
    output.seek(0)
    return output, "logo.png"


def _count(app):
    with app.app_context():
        return db.session.scalar(select(func.count(Establishment.id)))


def test_establishment_is_created_without_logo(app, client):
    _login(client, _owner(app))

    response = client.post(
        "/business/onboarding",
        data=VALID,
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "/business/" in response.headers["Location"]
    with app.app_context():
        establishment = db.session.scalar(
            select(Establishment).where(Establishment.name == "Studio Sem Logo")
        )
        assert establishment is not None
        assert establishment.logo_url is None
        assert establishment.published_at is not None


def test_server_errors_are_portuguese_listed_and_keep_typed_text(app, client):
    _login(client, _owner(app))

    response = client.post(
        "/business/onboarding",
        data={"name": "Studio Pressa", "category": "salao", "description": "Curta demais."},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert _count(app) == 0
    for english in ENGLISH_DEFAULTS:
        assert english not in html
    assert "Preencha este campo." in html
    assert "Use entre 40 e 2000 caracteres." in html
    # Resumo navegável: cada erro leva ao campo (o JS abre a etapa certa).
    assert "data-form-summary" in html
    for field_id in ("description", "address_line1", "city", "state"):
        assert f'data-summary-field="{field_id}"' in html
    # O que foi digitado volta preenchido.
    assert 'value="Studio Pressa"' in html
    assert re.search(r">\s*Curta demais\.</textarea>", html)
    # Sem arquivo enviado, não há aviso de reenvio.
    assert "Selecione de novo o logo" not in html


def test_summary_asks_to_reselect_files_after_an_error(app, client):
    _login(client, _owner(app))

    response = client.post(
        "/business/onboarding",
        data={"name": "Studio Com Logo", "category": "salao", "logo_file": _png()},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert _count(app) == 0
    assert "Selecione de novo o logo, a capa e as fotos" in html


def test_wizard_shows_final_button_only_at_last_step(app, client):
    _login(client, _owner(app))
    html = client.get("/business/onboarding").get_data(as_text=True)

    submit = re.search(r"<input[^>]*data-wizard-submit[^>]*>", html).group(0)
    assert "hidden" in submit
    assert "Opcional · até 5 MB" in html
    assert "Obrigatório · até 5 MB" not in html

    with open("app/static/css/platform.css", encoding="utf-8") as stylesheet:
        css = stylesheet.read()
    assert ".platform-wizard-actions [hidden] {\n  display: none;\n}" in css

    with open("app/static/js/platform.js", encoding="utf-8") as script:
        js = script.read()
    # Antes do envio, todas as etapas são conferidas (inclusive via Enter).
    assert "for (const step of steps)" in js
    assert "stepProblem(step)" in js
    assert "reportValidity" not in js


def test_establishment_without_logo_shows_design_system_initials(app, client):
    _login(client, _owner(app))
    client.post("/business/onboarding", data=VALID, content_type="multipart/form-data")
    with app.app_context():
        slug = db.session.scalar(
            select(Establishment.slug).where(Establishment.name == "Studio Sem Logo")
        )

    for path in (f"/estabelecimentos/{slug}", "/estabelecimentos", f"/business/{slug}/painel"):
        html = client.get(path).get_data(as_text=True)
        assert 'class="ds-avatar-initials ds-avatar-initials--fill"' in html, path
        assert ">SL</span>" in html, path


def test_all_web_forms_answer_in_portuguese(app):
    with app.test_request_context(method="POST", data={"email": "nao-e-email"}):
        register = RegisterForm(meta={"csrf": False})
        register.validate()
        onboarding = BusinessOnboardingForm(meta={"csrf": False})
        onboarding.validate()

    messages = [
        message
        for form in (register, onboarding)
        for errors in form.errors.values()
        for message in errors
    ]
    assert messages
    for message in messages:
        for english in ENGLISH_DEFAULTS:
            assert english not in message
    assert "Informe um e-mail válido." in register.errors["email"]
    assert "logo_file" not in onboarding.errors


def test_nv07_business_optional_operation_fields_persist_without_changing_publication(app, client):
    _login(client, _owner(app, "nv07-business@example.com"))

    response = client.post(
        "/business/onboarding",
        data={
            **VALID,
            "name": "Studio NV07",
            "operation_mode": "hybrid",
            "business_hours_mode": "scheduled",
            "email": "contato@nv07.example",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    with app.app_context():
        establishment = db.session.scalar(
            select(Establishment).where(Establishment.name == "Studio NV07")
        )
        assert establishment is not None
        assert establishment.operation_mode == "hybrid"
        assert establishment.business_hours_mode == "scheduled"
        assert establishment.email == "contato@nv07.example"
        # Current Web publishing behavior is intentionally unchanged.
        assert establishment.published_at is not None


def test_nv07_business_invalid_operation_mode_does_not_persist(app, client):
    _login(client, _owner(app, "nv07-invalid@example.com"))
    response = client.post(
        "/business/onboarding",
        data={**VALID, "operation_mode": "outside_contract"},
    )
    assert response.status_code == 200
    assert _count(app) == 0
    assert "operation_mode" in response.get_data(as_text=True)
