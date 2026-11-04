"""PR 4b do programa IDDUN 2.0 — edição por seção (D-SOC-15, 16).

- O editor do Pro e o da empresa têm as seções do perfil público, cada uma
  com Salvar próprio que altera só os campos dela.
- Erro numa seção não apaga o que está salvo nas outras.
- A página da empresa só é editada pelo dono; gestor recebe 403.
"""

import re

from flask import g

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

BIO = "Colorista com foco em loiros naturais e cuidado com a saúde do fio."


def _user(email, name="Pessoa Editora"):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    return user


def _login(client, user_id):
    g.pop("_login_user", None)  # troca de conta dentro do mesmo teste
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _pro(app, email="pro-secao@example.com"):
    with app.app_context():
        user = _user(email)
        profile = ProfessionalProfile(
            user=user,
            display_name="Pro Seção",
            slug=email.split("@")[0],
            primary_specialty="Colorista",
            bio=BIO,
            city="Curitiba",
            state="PR",
            phone="41999990000",
            whatsapp_enabled=True,
            instagram="@prosecao",
            attendance_modalities="establishment",
            visual_theme="beauty",
        )
        db.session.add(profile)
        db.session.commit()
        return user.id, profile.id


def _business(app, role=EstablishmentAccessRole.OWNER, email="dono-secao@example.com"):
    with app.app_context():
        user = _user(email)
        business = Establishment(
            name="Studio Seção",
            slug=email.split("@")[0],
            category="salao",
            description="Espaço de teste para a edição por seção da empresa.",
            address_line1="Rua das Flores, 120",
            city="Curitiba",
            state="PR",
            phone="41988880000",
            whatsapp_enabled=True,
            operation_mode="physical",
            business_hours_mode="scheduled",
            is_active=True,
            onboarding_completed=True,
        )
        db.session.add(business)
        db.session.flush()
        db.session.add(EstablishmentUserAccess(
            user=user,
            establishment=business,
            role=role,
            status=EstablishmentAccessStatus.ACTIVE,
        ))
        db.session.commit()
        return user.id, business.slug, business.id


def _section(html, section_id):
    match = re.search(rf'<section[^>]*id="{section_id}"[^>]*>(.*?)</section>', html, re.S)
    assert match, f"seção #{section_id} não encontrada"
    return match.group(0)


# ------------------------------------------------------------------ Pro


def test_pro_editor_has_one_form_per_section(app, client):
    user_id, _ = _pro(app)
    _login(client, user_id)
    html = client.get("/pro/perfil/editar").get_data(as_text=True)

    sections = re.findall(r'<input type="hidden" name="section" value="([a-z]+)">', html)
    assert sections == ["identidade", "sobre", "contato", "atendimento", "portfolio"]
    index = re.search(r'<nav class="profile-editor__index"[^>]*>(.*?)</nav>', html, re.S).group(1)
    for anchor in ("#identidade", "#sobre", "#contato", "#atendimento", "#portfolio", "#experiencia-profissional"):
        assert f'href="{anchor}"' in index
    assert 'href="/pro/certificacoes"' in index and 'href="/pro/servicos"' in index
    for label in ("Salvar identidade", "Salvar apresentação", "Salvar contato", "Salvar atendimento", "Salvar portfólio"):
        assert f">{label}</button>" in html
    # Cada campo aparece uma vez, no formulário da sua seção.
    assert 'name="bio"' in _section(html, "sobre")
    assert 'name="bio"' not in _section(html, "contato")
    assert html.count('id="display_name"') == 1


def test_saving_a_section_changes_only_its_fields(app, client):
    user_id, profile_id = _pro(app)
    _login(client, user_id)

    response = client.post(
        "/pro/perfil/editar",
        data={"section": "contato", "phone": "41911112222", "instagram": "@novo"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/perfil/editar#contato")

    with app.app_context():
        profile = db.session.get(ProfessionalProfile, profile_id)
        assert profile.phone == "41911112222"
        assert profile.instagram == "@novo"
        assert profile.whatsapp_enabled is False  # caixa desmarcada nesta seção
        assert profile.bio == BIO
        assert profile.display_name == "Pro Seção"
        assert profile.attendance_modalities == "establishment"

    page = client.get("/pro/perfil/editar").get_data(as_text=True)
    assert "Contato: alterações salvas." in page


def test_saving_about_keeps_whatsapp_and_modalities(app, client):
    user_id, profile_id = _pro(app)
    _login(client, user_id)
    new_bio = "Especialista em loiros e morenas iluminadas, com diagnóstico antes da química."

    response = client.post(
        "/pro/perfil/editar",
        data={"section": "sobre", "headline": "Loiros naturais", "bio": new_bio},
    )
    assert response.status_code == 302

    with app.app_context():
        profile = db.session.get(ProfessionalProfile, profile_id)
        assert profile.bio == new_bio
        assert profile.headline == "Loiros naturais"
        assert profile.whatsapp_enabled is True
        assert profile.attendance_modalities == "establishment"
        assert profile.phone == "41999990000"


def test_section_error_stays_in_the_section_and_keeps_other_values(app, client):
    user_id, profile_id = _pro(app)
    _login(client, user_id)

    response = client.post("/pro/perfil/editar", data={"section": "sobre", "bio": "curto"})
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    about = _section(html, "sobre")
    assert 'role="alert"' in about
    assert "Sobre você" in about
    assert "curto" in about
    assert 'role="alert"' not in _section(html, "contato")
    # As outras seções mostram o que está salvo.
    assert 'value="Pro Seção"' in _section(html, "identidade")
    assert re.search(r'<input[^>]*checked[^>]*id="whatsapp_enabled"|<input[^>]*id="whatsapp_enabled"[^>]*checked', _section(html, "contato"))

    with app.app_context():
        assert db.session.get(ProfessionalProfile, profile_id).bio == BIO


def test_modality_section_requires_one_choice(app, client):
    user_id, profile_id = _pro(app)
    _login(client, user_id)

    response = client.post("/pro/perfil/editar", data={"section": "atendimento"})
    assert response.status_code == 200
    assert "Selecione pelo menos uma modalidade" in _section(response.get_data(as_text=True), "atendimento")

    response = client.post(
        "/pro/perfil/editar",
        data={"section": "atendimento", "attendance_modalities": ["own_space", "client_location"]},
    )
    assert response.headers["Location"].endswith("#atendimento")
    with app.app_context():
        profile = db.session.get(ProfessionalProfile, profile_id)
        assert profile.attendance_modalities == "own_space,client_location"
        assert profile.bio == BIO


def test_unknown_section_is_rejected(app, client):
    user_id, _ = _pro(app)
    _login(client, user_id)
    assert client.post("/pro/perfil/editar", data={"section": "senha"}).status_code == 400


def test_saved_message_says_when_the_profile_left_the_air():
    from app.routes.platform import _section_saved_message

    assert _section_saved_message("Sobre", True, True) == "Sobre: alterações salvas."
    assert "saiu do ar" in _section_saved_message("Sobre", True, False)
    assert _section_saved_message("Sobre", False, False) == "Sobre: alterações salvas."


# -------------------------------------------------------------- empresa


def test_business_editor_has_the_page_sections(app, client):
    user_id, slug, _ = _business(app)
    _login(client, user_id)
    html = client.get(f"/business/{slug}/editar").get_data(as_text=True)

    sections = re.findall(r'<input type="hidden" name="section" value="([a-z]+)">', html)
    assert sections == ["identidade", "sobre", "atendimento", "funcionamento", "localizacao", "contatos", "galeria"]
    assert "Definir depois" not in html
    assert f'href="/business/{slug}/servicos"' in html


def test_business_contacts_section_changes_only_contacts(app, client):
    user_id, slug, business_id = _business(app)
    _login(client, user_id)

    response = client.post(
        f"/business/{slug}/editar",
        data={"section": "contatos", "phone": "41977776666", "whatsapp_enabled": "y", "instagram": "@studio"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/business/{slug}/editar#contatos")
    with app.app_context():
        business = db.session.get(Establishment, business_id)
        assert business.phone == "41977776666"
        assert business.whatsapp_enabled is True
        assert business.instagram == "@studio"
        assert business.description.startswith("Espaço de teste")
        assert business.address_line1 == "Rua das Flores, 120"
        assert business.is_active is True


def test_business_hours_and_mode_use_the_onboarding_rules(app, client):
    user_id, slug, business_id = _business(app)
    _login(client, user_id)

    response = client.post(
        f"/business/{slug}/editar",
        data={"section": "funcionamento", "business_hours_mode": "fixed_hours",
              "monday_start": "09:00", "monday_end": "18:00"},
    )
    assert response.headers["Location"].endswith("#funcionamento")
    with app.app_context():
        business = db.session.get(Establishment, business_id)
        assert business.business_hours_mode == "fixed_hours"
        assert business.business_hours == {"monday": [{"start": "09:00", "end": "18:00"}]}
        assert business.is_active is True

    response = client.post(
        f"/business/{slug}/editar",
        data={"section": "funcionamento", "business_hours_mode": "fixed_hours"},
    )
    assert response.status_code == 200
    assert "Informe abertura e fechamento" in _section(response.get_data(as_text=True), "funcionamento")

    response = client.post(f"/business/{slug}/editar", data={"section": "atendimento", "operation_mode": "hybrid"})
    assert response.headers["Location"].endswith("#atendimento")
    with app.app_context():
        assert db.session.get(Establishment, business_id).operation_mode == "hybrid"

    sobre = client.get(f"/estabelecimentos/{slug}/sobre").get_data(as_text=True)
    assert "09:00–18:00" in sobre


def test_business_location_error_keeps_saved_description(app, client):
    user_id, slug, _ = _business(app)
    _login(client, user_id)

    response = client.post(
        f"/business/{slug}/editar",
        data={"section": "localizacao", "address_line1": "", "city": "Curitiba", "state": "PR"},
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'role="alert"' in _section(html, "localizacao")
    assert "Espaço de teste para a edição" in _section(html, "sobre")


def test_only_the_owner_edits_the_business_page(app, client):
    owner_id, slug, business_id = _business(app)
    manager_id, _, _ = _business(app, role=EstablishmentAccessRole.MANAGER, email="gestor-secao@example.com")
    with app.app_context():
        manager_access = db.session.query(EstablishmentUserAccess).filter_by(user_id=manager_id).one()
        manager_access.establishment_id = business_id
        item = EstablishmentGalleryItem(establishment_id=business_id, image_url="https://cdn.example.com/g.jpg")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    _login(client, manager_id)
    assert client.get(f"/business/{slug}/editar").status_code == 403
    assert client.post(f"/business/{slug}/editar", data={"section": "sobre", "description": "x" * 50}).status_code == 403
    assert client.post(f"/business/{slug}/galeria/{item_id}/remover").status_code == 403
    # O painel continua aberto ao gestor, sem o atalho de edição.
    dashboard = client.get(f"/business/{slug}/painel")
    assert dashboard.status_code == 200
    assert f"/business/{slug}/editar" not in dashboard.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(EstablishmentGalleryItem, item_id) is not None

    _login(client, owner_id)
    assert client.get(f"/business/{slug}/editar").status_code == 200
    assert f"/business/{slug}/editar" in client.get(f"/business/{slug}/painel").get_data(as_text=True)


# ----------------------------------------------------------- modo dono


def test_owner_sees_edit_links_on_own_pro_profile(app, client):
    user_id, _ = _pro(app, email="pro-dono@example.com")
    with app.app_context():
        profile = db.session.query(ProfessionalProfile).filter_by(slug="pro-dono").one()
        profile.is_active = True
        db.session.commit()

    visitor = client.get("/profissionais/pro-dono").get_data(as_text=True)
    assert "profile-owner-bar" not in visitor and "profile-edit-link" not in visitor

    other_id, _ = _pro(app, email="outro-pro@example.com")
    _login(client, other_id)
    assert "profile-edit-link" not in client.get("/profissionais/pro-dono").get_data(as_text=True)

    _login(client, user_id)
    page = client.get("/profissionais/pro-dono").get_data(as_text=True)
    assert "Você está vendo seu perfil como o público vê." in page
    for href in ("/pro/perfil/editar#identidade", "/pro/perfil/editar#sobre", "/pro/perfil/editar#portfolio",
                 "/pro/servicos", "/pro/perfil/editar#experiencia-profissional", "/pro/certificacoes",
                 "/pro/perfil/editar#atendimento"):
        assert f'href="{href}"' in page, href
    # Ver e editar separados (DEC-ID-242): nenhum campo na visualização.
    assert "<input" not in page.split('<main class="public-profile-main">', 1)[1].split("</main>", 1)[0]


def test_only_the_owner_sees_business_edit_links(app, client):
    owner_id, slug, business_id = _business(app, email="dono-links@example.com")
    manager_id, _, _ = _business(app, role=EstablishmentAccessRole.MANAGER, email="gestor-links@example.com")
    with app.app_context():
        db.session.query(EstablishmentUserAccess).filter_by(user_id=manager_id).one().establishment_id = business_id
        db.session.commit()

    _login(client, manager_id)
    assert "profile-edit-link" not in client.get(f"/estabelecimentos/{slug}/sobre").get_data(as_text=True)

    _login(client, owner_id)
    sobre = client.get(f"/estabelecimentos/{slug}/sobre").get_data(as_text=True)
    assert "Você está vendo a página da sua empresa como o público vê." in sobre
    for anchor in ("sobre", "atendimento", "funcionamento", "contatos", "localizacao"):
        assert f'href="/business/{slug}/editar#{anchor}"' in sobre, anchor
    inicio = client.get(f"/estabelecimentos/{slug}").get_data(as_text=True)
    assert f'href="/business/{slug}/editar#galeria"' in inicio
    assert f'href="/business/{slug}/servicos"' in inicio
    equipe = client.get(f"/estabelecimentos/{slug}/equipe").get_data(as_text=True)
    assert f'href="/business/{slug}/painel#business-team"' in equipe


def test_client_sees_edit_link_on_own_page(app, client):
    from tests.test_api_posts import _user as api_user
    from tests.test_social_profiles import _client_profile_id, _client_text_post

    user_id, _, headers = api_user(app, email="cliente-dona@example.com", with_professional=False)
    profile_id = _client_profile_id(app, user_id)
    _client_text_post(client, headers, profile_id)

    assert "profile-owner-bar" not in client.get(f"/clientes/{profile_id}").get_data(as_text=True)
    assert client.get(f"/api/v1/clients/{profile_id}").get_json()["mine"] is False
    assert client.get(f"/api/v1/clients/{profile_id}", headers=headers).get_json()["mine"] is True
    _login(client, user_id)
    page = client.get(f"/clientes/{profile_id}").get_data(as_text=True)
    bar = page.split('class="profile-owner-bar"', 1)[1].split("</div>", 1)[0]
    assert 'href="/minha-conta/editar"' in bar
    assert "Você está vendo seu perfil como o público vê." in page
