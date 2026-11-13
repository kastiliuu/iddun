from datetime import date
from io import BytesIO
import re

from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _context_list_html(html, attribute):
    """Isola um seletor renderizado para validar seus limites por viewport."""
    match = re.search(
        rf'<ul\b[^>]*\b{re.escape(attribute)}\b[^>]*>(.*?)</ul>',
        html,
        re.DOTALL,
    )
    assert match is not None, f"Seletor {attribute} ausente"
    return match.group(1)


def _create_user_without_profile(app):
    with app.app_context():
        user = User(name="Legacy User", email="legacy@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.commit()
        return user.id


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_account_lazily_creates_profile_for_legacy_user(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.get("/minha-conta")
    assert response.status_code == 200

    with app.app_context():
        profile = db.session.scalar(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        assert profile is not None


def test_account_profile_can_be_updated(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.post(
        "/minha-conta",
        data={
            "name": "Gabriel Atualizado",
            "phone": "41999999999",
            "birth_date": "1996-05-16",
            "city": "Curitiba",
            "state": "pr",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.name == "Gabriel Atualizado"
        assert user.client_profile.phone == "41999999999"
        assert user.client_profile.city == "Curitiba"
        assert user.client_profile.state == "PR"
        assert user.client_profile.onboarding_completed is True


def test_account_completion_uses_every_field_shown_on_the_page(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    client.get("/minha-conta")
    with app.app_context():
        user = db.session.get(User, user_id)
        user.client_profile.phone = "41999999999"
        user.client_profile.birth_date = date(1996, 5, 16)
        user.client_profile.city = "Curitiba"
        user.client_profile.state = "PR"
        user.client_profile.avatar_url = "uploads/clients/avatar.webp"
        db.session.commit()

    # O fixture mantém uma única sessão entre requisições; em produção cada
    # requisição abre a sua. O cabeçalho único lê o perfil do Cliente, então
    # a próxima requisição precisa reler o que foi gravado acima.
    db.session.expire_all()
    response = client.get("/minha-conta")

    assert response.status_code == 200
    assert b'data-progress="100"' in response.data
    assert "Tudo certo. Seu perfil está completo.".encode() in response.data


def test_avatar_upload_error_preserves_completion_and_business_contexts(app, client, monkeypatch):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    with app.app_context():
        establishment = Establishment(name="Studio Teste", slug="studio-teste")
        access = EstablishmentUserAccess(
            user_id=user_id,
            establishment=establishment,
            role=EstablishmentAccessRole.OWNER,
            status=EstablishmentAccessStatus.ACTIVE,
        )
        db.session.add_all([establishment, access])
        db.session.commit()

    def fail_upload(*_args, **_kwargs):
        raise ValueError("Falha controlada no upload.")

    monkeypatch.setattr("app.routes.account.save_uploaded_image", fail_upload)

    response = client.post(
        "/minha-conta",
        data={
            "name": "Legacy User",
            "phone": "",
            "birth_date": "",
            "city": "",
            "state": "",
            "avatar_file": (BytesIO(b"fake-image"), "avatar.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert b'data-progress="29"' in response.data
    assert b"Studio Teste" in response.data
    assert "Falha controlada no upload.".encode() in response.data


def test_profile_view_is_read_only_and_edit_has_form(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    view = client.get("/minha-conta")
    assert view.status_code == 200
    assert b'aria-label="Informa' in view.data
    assert b'href="/minha-conta/editar"' in view.data
    assert b'class="account-form"' not in view.data
    assert b'data-account-avatar-edit' not in view.data

    edit = client.get("/minha-conta/editar")
    assert edit.status_code == 200
    assert b'class="account-form"' in edit.data
    assert b'action="/minha-conta/editar"' in edit.data
    assert b'data-account-avatar-edit' in edit.data
    assert b'href="/minha-conta"' in edit.data


def test_dedicated_edit_route_persists_profile_and_returns_to_view(
    app, client,
):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.post(
        "/minha-conta/editar",
        data={
            "name": "Cliente Atualizado",
            "phone": "41988888888",
            "birth_date": "",
            "city": "Curitiba",
            "state": "PR",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/minha-conta")

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.name == "Cliente Atualizado"
        assert user.client_profile.phone == "41988888888"


def test_account_favorites_links_to_the_saved_tab(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    response = client.get("/minha-conta")
    assert response.status_code == 200
    # D-SOC-07: o cartão leva à aba Salvos da página Favoritos.
    assert b'href="/favoritos?aba=salvos"' in response.data
    assert b"Comece a salvar suas descobertas" in response.data
    assert b"Seus salvos chegar" not in response.data


def test_qa001_account_separates_business_management_and_moderated_owner_pages(app, client):
    from datetime import datetime, timezone

    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)
    when = datetime(2026, 11, 1, tzinfo=timezone.utc)

    with app.app_context():
        establishments = [
            ("Atelier Publicado", "atelier-publicado", True, when, "owner", "active"),
            ("Atelier Rascunho", "atelier-rascunho", False, None, "owner", "active"),
            ("Atelier Moderado", "atelier-moderado", False, when, "owner", "active"),
            ("Atelier Gestor", "atelier-gestor", True, when, "manager", "active"),
            ("Atelier Gestor Moderado", "atelier-gestor-moderado", False, when, "manager", "active"),
            ("Atelier Revogado", "atelier-revogado", True, when, "owner", "inactive"),
        ]
        for name, slug, active, published_at, role, status in establishments:
            establishment = Establishment(
                name=name,
                slug=slug,
                is_active=active,
                published_at=published_at,
            )
            db.session.add(establishment)
            db.session.flush()
            db.session.add(EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=establishment.id,
                role=role,
                status=status,
            ))
        db.session.commit()

    page = client.get("/minha-conta")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'id="account-context-title">Seus contextos' in html
    assert 'id="meus-estabelecimentos"' in html
    assert "Ativar perfil profissional" in html
    assert 'href="/business/onboarding/novo"' in html
    assert "Atelier Publicado" in html
    assert "Atelier Rascunho" in html
    assert "Continuar cadastro: Atelier Rascunho" in html
    assert "Atelier Moderado" in html
    assert "Fora do ar pela moderação · fale com o suporte" in html
    assert 'data-business-state="locked"' in html
    assert "Atelier Gestor" in html
    assert "Gestor · Publicado" in html
    assert "Atelier Gestor Moderado" not in html
    assert "Atelier Revogado" not in html

    # Locked pages appear as information, without a link to a protected panel.
    locked = html.split('data-business-state="locked"', 1)[1].split("</div>", 1)[0]
    assert "Atelier Moderado" in locked
    assert 'href=' not in locked

    # The selector still excludes moderated businesses, showing at most 3.
    for selector in ("data-account-contexts", "data-mobile-account-contexts"):
        menu_contexts = _context_list_html(html, selector)
        assert menu_contexts.count('data-context-kind="establishment"') == 3
    assert "Ver todos os estabelecimentos" not in html


def test_qa001_account_menu_limits_business_contexts_and_preserves_personal_identity(app, client):
    user_id = _create_user_without_profile(app)
    _login_session(client, user_id)

    with app.app_context():
        for n in range(4):
            item = Establishment(
                name=f"Espaço {n}",
                slug=f"espaco-{n}",
                is_active=True,
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=item.id,
                role=EstablishmentAccessRole.OWNER,
                status=EstablishmentAccessStatus.ACTIVE,
            ))
        db.session.commit()

    page = client.get("/minha-conta")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Conta pessoal · agora em Cliente" in html
    for selector in ("data-account-contexts", "data-mobile-account-contexts"):
        menu_contexts = _context_list_html(html, selector)
        assert menu_contexts.count('data-context-kind="establishment"') == 3
    assert "Ver todos os estabelecimentos" in html
    assert 'href="/minha-conta#meus-estabelecimentos"' in html
    assert "Criar e gerir estabelecimentos" in html
    assert "Ativar perfil profissional" in html
    for n in range(4):
        assert f"Espaço {n}" in html
