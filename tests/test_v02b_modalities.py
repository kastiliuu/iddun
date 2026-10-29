"""V-02b — "Onde você atende?" com caixas de seleção (BUG-001, FE-DEC-044).

A lista múltipla nativa exigia Ctrl+clique. Agora cada modalidade é uma
caixa de seleção num grupo com título (fieldset/legend). O valor enviado e
gravado não muda: a mesma lista `attendance_modalities`, então o app e a
API não são afetados.
"""

import re

from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.forms.platform import ProfessionalEditForm, ProfessionalOnboardingForm
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

CHOICES = ("establishment", "own_space", "client_location")


def _user(app, email, modalities=None):
    with app.app_context():
        user = User(name="Pessoa Modalidade", email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        if modalities is not None:
            db.session.add(ProfessionalProfile(
                user=user,
                display_name="Pro Modalidade",
                slug=f"pro-modalidade-{user.id}",
                attendance_modalities=modalities,
            ))
        db.session.commit()
        return user.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _checkboxes(html):
    return re.findall(r'<input[^>]*name="attendance_modalities"[^>]*>', html)


def _assert_checkbox_group(html):
    assert not re.search(r'<select[^>]*name="attendance_modalities"', html)
    boxes = _checkboxes(html)
    assert len(boxes) == 3
    for box, value in zip(boxes, CHOICES):
        assert 'type="checkbox"' in box
        assert f'value="{value}"' in box
    assert re.search(r"<fieldset[^>]*>\s*<legend[^>]*>\s*Onde você atende\?", html)
    for label in ("Em estabelecimento", "Em espaço próprio", "No endereço do cliente"):
        assert label in html


def test_edit_shows_checkboxes_with_saved_choices(app, client):
    _login(client, _user(app, "mod-edit@example.com", modalities="own_space,client_location"))

    html = client.get("/pro/perfil/editar").get_data(as_text=True)

    _assert_checkbox_group(html)
    checked = [box for box in _checkboxes(html) if "checked" in box]
    assert [re.search(r'value="(\w+)"', box).group(1) for box in checked] == [
        "own_space", "client_location",
    ]


def test_onboarding_shows_checkboxes(app, client):
    _login(client, _user(app, "mod-onboarding@example.com"))

    html = client.get("/pro/onboarding").get_data(as_text=True)

    _assert_checkbox_group(html)
    assert "data-required-group" in html


def test_submitted_value_is_unchanged(app):
    data = MultiDict([("attendance_modalities", "establishment"),
                      ("attendance_modalities", "client_location")])
    with app.test_request_context(method="POST", data=data):
        for form_class in (ProfessionalOnboardingForm, ProfessionalEditForm):
            form = form_class(meta={"csrf": False})
            form.validate()
            assert form.attendance_modalities.data == ["establishment", "client_location"]
            assert "attendance_modalities" not in form.errors


def test_missing_choice_keeps_message_and_points_group_to_it(app, client):
    with app.test_request_context(method="POST", data={}):
        form = ProfessionalEditForm(meta={"csrf": False})
        form.validate()
        assert form.errors["attendance_modalities"] == [
            "Selecione pelo menos uma modalidade de atendimento."
        ]

    _login(client, _user(app, "mod-erro@example.com", modalities="own_space"))
    html = client.post(
        "/pro/perfil/editar",
        data={"display_name": "Pro Modalidade"},
        content_type="multipart/form-data",
    ).get_data(as_text=True)

    fieldset = re.search(r"<fieldset[^>]*platform-choice-group[^>]*>", html).group(0)
    assert 'aria-describedby="attendance_modalities-errors"' in fieldset
    assert 'id="attendance_modalities-errors"' in html
