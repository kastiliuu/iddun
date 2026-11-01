"""PR 2 do onboarding: cadastro Profissional por etapas no Web.

Cada etapa salva o rascunho no servidor; publicar é explícito (F1); áreas
fixas (D-ONB-01); apresentação com 40+ caracteres (D-ONB-02); tema opcional
com padrão Beleza (D-ONB-03).
"""

from io import BytesIO
import re

from PIL import Image
from sqlalchemy import select

from app.extensions import db
from app.forms.platform import PROFESSIONAL_AREA_CHOICES
from app.models.professional import ProfessionalPortfolioItem, ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session
from app.services.onboarding_steps import PROFESSIONAL_CATEGORIES

from onboarding_flow import DEFAULT_BIO, complete_professional_onboarding


def _user(app, email="etapas@example.com", name="Ana Etapas"):
    with app.app_context():
        user = User(name=name, email=email, role=UserRole.CLIENT)
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


def _profile(app, user_id):
    with app.app_context():
        return db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )


def _image(name):
    output = BytesIO()
    Image.new("RGB", (8, 8), (120, 80, 160)).save(output, format="JPEG")
    output.seek(0)
    return output, name


def _until_presentation(client):
    for slug, data in [
        ("nome", {"display_name": "Ana Etapas"}),
        ("cidade", {"city": "Curitiba", "state": "pr"}),
        ("especialidade", {"primary_specialty": "Nail designer", "categories": ["unhas", "estetica"]}),
        ("atendimento", {"attendance_modalities": ["own_space"]}),
        ("apresentacao", {"bio": DEFAULT_BIO}),
    ]:
        assert client.post(f"/pro/onboarding/{slug}", data=data).status_code == 302


def test_areas_are_the_same_fixed_list_as_the_app():
    assert PROFESSIONAL_AREA_CHOICES == list(PROFESSIONAL_CATEGORIES.items())
    assert len(PROFESSIONAL_AREA_CHOICES) == 8


def test_start_resumes_at_first_step_with_account_name(app, client):
    _login(client, _user(app))

    response = client.get("/pro/onboarding")
    assert response.headers["Location"].endswith("/pro/onboarding/nome")

    html = client.get("/pro/onboarding/nome").get_data(as_text=True)
    assert 'value="Ana Etapas"' in html
    assert "Etapa 1 de 7" in html
    assert 'aria-current="step"' in html
    assert "Sair e continuar depois" in html
    assert "LinkedIn" not in html and "Tinder" not in html


def test_later_step_without_draft_goes_back_to_first(app, client):
    _login(client, _user(app))
    response = client.get("/pro/onboarding/cidade")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/onboarding/nome")


def test_unknown_step_is_not_found(app, client):
    _login(client, _user(app))
    assert client.get("/pro/onboarding/qualquer").status_code == 404


def test_each_step_saves_a_private_draft_and_moves_on(app, client):
    user_id = _user(app)
    _login(client, user_id)

    first = client.post("/pro/onboarding/nome", data={"display_name": "Ana Etapas"})
    assert first.headers["Location"].endswith("/pro/onboarding/cidade")
    profile = _profile(app, user_id)
    assert profile.is_active is False
    assert profile.published_at is None
    assert client.get(f"/profissionais/{profile.slug}").status_code == 404

    _until_presentation(client)
    profile = _profile(app, user_id)
    assert (profile.city, profile.state) == ("Curitiba", "PR")
    assert profile.specialties_text == "Unhas, Estética"
    assert profile.attendance_modalities == "own_space"
    assert profile.is_active is False


def test_leaving_and_coming_back_resumes_the_pending_step(app, client):
    _login(client, _user(app))
    client.post("/pro/onboarding/nome", data={"display_name": "Ana Etapas"})
    client.post("/pro/onboarding/cidade", data={"city": "Curitiba", "state": "PR"})

    response = client.get("/pro/onboarding")

    assert response.headers["Location"].endswith("/pro/onboarding/especialidade")
    html = client.get("/pro/onboarding/cidade").get_data(as_text=True)
    assert 'value="Curitiba"' in html
    assert "Etapa 2 de 7" in html


def test_invalid_step_keeps_values_and_shows_field_errors(app, client):
    user_id = _user(app)
    _login(client, user_id)
    client.post("/pro/onboarding/nome", data={"display_name": "Ana Etapas"})

    city = client.post("/pro/onboarding/cidade", data={"city": "Curitiba", "state": "P1"})
    assert city.status_code == 422
    html = city.get_data(as_text=True)
    assert 'value="Curitiba"' in html
    assert 'id="state-errors"' in html
    assert "Use as duas letras da UF." in html

    areas = client.post("/pro/onboarding/especialidade", data={"primary_specialty": "Nail designer"})
    assert areas.status_code == 422
    assert "Escolha pelo menos uma área de atuação." in areas.get_data(as_text=True)

    bio = client.post("/pro/onboarding/apresentacao", data={"bio": "Curta demais."})
    assert bio.status_code == 422
    body = bio.get_data(as_text=True)
    assert "Use entre 40 e 2000 caracteres." in body
    assert "Curta demais." in body
    assert _profile(app, user_id).bio is None


def test_review_lists_what_is_missing_and_blocks_publication(app, client):
    user_id = _user(app)
    _login(client, user_id)
    client.post("/pro/onboarding/nome", data={"display_name": "Ana Etapas"})

    html = client.get("/pro/onboarding/revisar").get_data(as_text=True)
    assert "Para publicar, falta:" in html
    assert "Informe a cidade onde você atende." in html
    assert "Escreva sua apresentação com pelo menos 40 caracteres." in html
    assert 'disabled' in html
    assert "retorno=revisar" in html

    forced = client.post("/pro/onboarding/revisar", data={})
    assert forced.status_code == 422
    assert "Complete os requisitos obrigatórios antes de publicar." in forced.get_data(as_text=True)
    assert _profile(app, user_id).is_active is False


def test_edit_from_review_returns_to_review(app, client):
    _login(client, _user(app))
    _until_presentation(client)

    response = client.post(
        "/pro/onboarding/cidade?retorno=revisar",
        data={"city": "Londrina", "state": "PR"},
    )

    assert response.headers["Location"].endswith("/pro/onboarding/revisar")


def test_full_journey_publishes_only_on_explicit_action(app, client):
    user_id = _user(app)
    _login(client, user_id)

    complete_professional_onboarding(client, display_name="Ana Etapas", publish=False)
    draft = _profile(app, user_id)
    assert draft.is_active is False
    assert draft.visual_theme == "beauty"

    published = client.post("/pro/onboarding/revisar", data={})
    assert published.headers["Location"].endswith("/pro/onboarding/concluido")
    profile = _profile(app, user_id)
    assert profile.is_active is True
    assert profile.onboarding_completed is True
    published_at = profile.published_at
    assert published_at is not None

    done = client.get("/pro/onboarding/concluido").get_data(as_text=True)
    assert "Seu perfil está no ar." in done
    assert "Reservas ainda não estão abertas" in done
    assert "Criar um serviço" in done
    assert client.get(f"/profissionais/{profile.slug}").status_code == 200

    again = client.post("/pro/onboarding/revisar", data={})
    assert again.headers["Location"].endswith("/pro/painel")
    assert _profile(app, user_id).published_at == published_at


def test_published_profile_skips_onboarding(app, client):
    _login(client, _user(app))
    complete_professional_onboarding(client)

    assert client.get("/pro/onboarding").headers["Location"].endswith("/pro/painel")
    assert client.get("/pro/onboarding/nome").headers["Location"].endswith("/pro/painel")
    start = client.post("/pro/comecar", data={"mode": "professional"})
    assert start.headers["Location"].endswith("/pro/onboarding")


def test_photos_step_is_optional_and_saves_media(app, client):
    user_id = _user(app)
    _login(client, user_id)
    _until_presentation(client)

    later = client.get("/pro/onboarding/fotos").get_data(as_text=True)
    assert "Fazer depois" in later

    response = client.post(
        "/pro/onboarding/fotos",
        data={
            "avatar_file": _image("avatar.jpg"),
            "portfolio_files": [_image("1.jpg"), _image("2.jpg")],
            "avatar_focus_x": "30", "avatar_focus_y": "70",
            "cover_focus_x": "50", "cover_focus_y": "50",
            "phone": "41999990000", "whatsapp_enabled": "y",
            "instagram": "@ana", "visual_theme": "tattoo",
        },
        content_type="multipart/form-data",
    )

    assert response.headers["Location"].endswith("/pro/onboarding/revisar")
    profile = _profile(app, user_id)
    assert profile.avatar_url
    assert (profile.avatar_focus_x, profile.avatar_focus_y) == (30, 70)
    assert profile.phone == "41999990000" and profile.whatsapp_enabled is True
    assert profile.instagram == "@ana"
    assert profile.visual_theme == "tattoo"
    with app.app_context():
        assert db.session.scalar(
            select(db.func.count(ProfessionalPortfolioItem.id))
        ) == 2
    assert profile.is_active is False


def test_photos_step_respects_portfolio_limit(app, client):
    user_id = _user(app)
    _login(client, user_id)
    _until_presentation(client)

    response = client.post(
        "/pro/onboarding/fotos",
        data={
            "portfolio_files": [_image(f"{index}.jpg") for index in range(9)],
            "visual_theme": "beauty",
            "avatar_focus_x": "50", "avatar_focus_y": "50",
            "cover_focus_x": "50", "cover_focus_y": "50",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert "mais 8 foto(s)" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(db.func.count(ProfessionalPortfolioItem.id))) == 0


def test_app_draft_continues_on_the_web(app, client):
    user_id = _user(app)
    with app.app_context():
        token = issue_session(db.session.get(User, user_id)).access_token
    created = client.post(
        "/api/v1/onboarding/professional",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "displayName": "Ana do App", "primarySpecialty": "Nail designer",
            "categories": ["unhas"], "city": "Curitiba", "state": "PR",
        },
    )
    assert created.status_code in {200, 201}
    _login(client, user_id)

    assert client.get("/pro/onboarding").headers["Location"].endswith("/pro/onboarding/atendimento")
    html = client.get("/pro/onboarding/especialidade").get_data(as_text=True)
    assert re.search(r'<input checked[^>]*name="categories"[^>]*value="unhas"', html)
    assert not re.search(r'<input checked[^>]*name="categories"[^>]*value="cabelo"', html)


def test_editing_a_draft_does_not_mark_it_as_published(app, client):
    """Editar perfil não pode dar data de publicação a um rascunho, senão a
    publicação explícita o trataria como página desativada."""
    user_id = _user(app)
    _login(client, user_id)
    _until_presentation(client)

    response = client.post(
        "/pro/perfil/editar",
        data={
            "display_name": "Ana Etapas", "primary_specialty": "Nail designer",
            "bio": DEFAULT_BIO, "city": "Curitiba", "state": "PR",
            "attendance_modalities": ["own_space"], "visual_theme": "beauty",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    profile = _profile(app, user_id)
    assert profile.is_active is False
    assert profile.published_at is None

    published = client.post("/pro/onboarding/revisar", data={})
    assert published.headers["Location"].endswith("/pro/onboarding/concluido")


def test_dashboards_point_drafts_back_to_the_onboarding(app, client):
    _login(client, _user(app))
    client.post("/pro/onboarding/nome", data={"display_name": "Ana Etapas"})

    panel = client.get("/pro/painel").get_data(as_text=True)
    assert "Seu perfil ainda não está no ar." in panel
    assert 'href="/pro/onboarding"' in panel

    account = client.get("/minha-conta").get_data(as_text=True)
    assert "Continuar cadastro profissional" in account
