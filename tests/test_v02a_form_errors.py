"""V-02a — um único padrão de erro de formulário na Web (BUG-001/002, D-VIS-06).

- O erro do servidor usa o componente do Design System: ícone do DS e
  texto, sem o "!" cru que aparecia nas telas Pro e Business.
- O campo com erro é marcado no servidor (aria-invalid + aria-describedby
  apontando para a mensagem), em todos os formulários que herdam IddunForm.
- O formulário de experiência profissional não usa o balão nativo do
  navegador: mensagens em português ao lado de cada campo.
- O vermelho de erro vem de tokens com contraste AA (D-VIS-06).
"""

import re
from pathlib import Path

from app.extensions import db
from app.forms.platform import ProfessionalWorkExperienceForm
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

CSS = Path("app/static/css")


def _user(app, email, with_profile=False):
    with app.app_context():
        user = User(name="Pessoa Teste", email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        if with_profile:
            db.session.add(ProfessionalProfile(
                user=user, display_name="Pro Erros", slug=f"pro-erros-{user.id}",
            ))
        db.session.commit()
        return user.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _tag(html, field_id):
    match = re.search(rf'<(?:input|textarea|select)[^>]*\bid="{field_id}"[^>]*>', html)
    assert match, f"campo {field_id} não encontrado"
    return match.group(0)


def test_invalid_field_is_marked_and_points_to_its_message(app):
    with app.test_request_context(method="POST", data={"company_name": ""}):
        form = ProfessionalWorkExperienceForm(meta={"csrf": False})
        form.validate()
        invalid = str(form.company_name(class_="platform-input"))
        valid_untouched = str(form.description())

    assert 'aria-invalid="true"' in invalid
    assert 'aria-describedby="company_name-errors"' in invalid
    assert "aria-invalid" not in valid_untouched
    assert "aria-describedby" not in valid_untouched


def test_existing_describedby_is_kept(app):
    with app.test_request_context(method="POST", data={}):
        form = ProfessionalWorkExperienceForm(meta={"csrf": False})
        form.validate()
        html = str(form.company_name(**{"aria-describedby": "dica"}))

    assert 'aria-describedby="dica company_name-errors"' in html


def test_experience_errors_sit_next_to_each_field(app, client):
    _login(client, _user(app, "pro-erros@example.com", with_profile=True))

    response = client.post(
        "/pro/experiencia-profissional/adicionar",
        data={"company_name": "", "role_title": "Designer"},
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    # Sem balão nativo: o formulário é validado pelo servidor, em português.
    form = re.search(r'<form[^>]*experiencia-profissional/adicionar[^>]*>', html).group(0)
    assert "novalidate" in form
    for field_id in ("company_name", "started_at"):
        assert f'id="{field_id}-errors"' in html
        assert 'aria-invalid="true"' in _tag(html, field_id)
    assert "Preencha este campo." in html
    # O que foi digitado continua no campo.
    assert 'value="Designer"' in html
    assert "aria-invalid" not in _tag(html, "role_title")


def test_server_error_uses_design_system_component(app, client):
    _login(client, _user(app, "dono-erros@example.com"))

    html = client.post(
        "/business/onboarding",
        data={"name": "Studio Pressa", "category": "salao"},
        content_type="multipart/form-data",
    ).get_data(as_text=True)

    assert '<strong aria-hidden="true">!</strong>' not in html
    block = re.search(
        r'<div class="ds-field-errors" id="description-errors">(.*?)</div>', html, re.S
    )
    assert block, "mensagem do campo descrição fora do componente do DS"
    assert '<svg class="icon ds-field-errors__icon"' in block.group(1)
    assert "Preencha este campo." in block.group(1)
    assert 'aria-invalid="true"' in _tag(html, "description")


def test_one_error_style_with_accessible_tokens():
    tokens = (CSS / "tokens.css").read_text(encoding="utf-8")
    components = (CSS / "components.css").read_text(encoding="utf-8")

    assert "--ds-feedback-danger-on-light: #A33149;" in tokens
    assert "--ds-feedback-danger-on-dark: #FF6B6B;" in tokens
    assert ".ds-field-errors" in components
    # As três versões antigas do mesmo erro saem das folhas de página.
    for sheet in ("auth.css", "account.css", "platform.css"):
        text = (CSS / sheet).read_text(encoding="utf-8")
        assert ".auth-field-errors" not in text, sheet
        assert ".field-errors {" not in text, sheet
