"""D11 / D-VIS-03 / D-VIS-04 — identidade real, sem prova social fixa nem foto de estoque.

Decisões do proprietário de 27/10/2026 (Notion 08):
- D-VIS-03: o login não exibe nota nem depoimento fixos no template;
- D-VIS-04: perfil real sem foto aparece com iniciais, nunca com retrato
  ou imagem genérica de outra pessoa.
"""

from app.extensions import db
from app.models.establishment import Establishment
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.experience_service import _db_item

STOCK_PORTRAITS = (
    "prof-camila.jpg",
    "prof-juliana.jpg",
    "prof-rafael.jpg",
)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _professional_without_photo(category="cabelo"):
    professional = ProfessionalProfile(
        display_name="Bruna Teixeira",
        slug="bruna-sem-foto",
        primary_specialty="Colorista",
        city="Curitiba",
        state="PR",
        is_active=True,
        avatar_url=None,
    )
    db.session.add(professional)
    db.session.flush()
    experience = Experience(
        professional=professional,
        title="Coloração Bruna",
        slug="coloracao-bruna",
        category=category,
        short_description="Coloração com Bruna.",
        regular_price="150.00",
        price="150.00",
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(experience)
    db.session.commit()
    return professional, experience


def test_login_has_no_hardcoded_social_proof(client):
    html = client.get("/login").get_data(as_text=True)

    assert "auth-proof" not in html
    assert "4,9" not in html
    assert "Encontrei minha profissional em minutos" not in html
    # O restante da página de acesso continua intacto.
    assert 'name="email"' in html
    assert 'name="password"' in html


def test_experience_item_has_no_stock_avatar_for_real_professional(app):
    with app.app_context():
        for category in ("cabelo", "unhas", "barbearia"):
            db.session.rollback()
            Experience.query.delete()
            ProfessionalProfile.query.delete()
            db.session.commit()
            _, experience = _professional_without_photo(category)

            item = _db_item(experience)

            assert item["avatar"] is None, category


def test_experience_item_keeps_the_real_photo(app):
    with app.app_context():
        professional, experience = _professional_without_photo()
        professional.avatar_url = "uploads/avatar-bruna.jpg"
        db.session.commit()

        assert _db_item(experience)["avatar"] == "uploads/avatar-bruna.jpg"


def test_marketplace_and_detail_show_initials_instead_of_stock_portrait(app, client):
    app.config["APP_ENV"] = "production"
    with app.app_context():
        _professional_without_photo()

    listing = client.get("/experiencias").get_data(as_text=True)
    detail = client.get("/experiencias/coloracao-bruna").get_data(as_text=True)

    for html in (listing, detail):
        assert 'aria-label="Avatar de Bruna Teixeira"' in html
        assert ">BT</span>" in html
        for portrait in STOCK_PORTRAITS:
            assert portrait not in html


def test_feed_recommendations_show_initials_for_profiles_without_photo(app, client):
    with app.app_context():
        user = User(name="Cliente Feed", email="d11-feed@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add_all([
            user,
            ClientProfile(user=user, city="Curitiba", state="PR"),
            ProfessionalProfile(
                display_name="Lara Mendes",
                slug="lara-sem-foto",
                primary_specialty="Nail designer",
                city="Curitiba",
                state="PR",
                is_active=True,
            ),
            Establishment(
                name="Espaço Aurora",
                slug="espaco-aurora",
                city="Curitiba",
                state="PR",
                is_active=True,
            ),
        ])
        db.session.commit()
        user_id = user.id

    _login(client, user_id)
    html = client.get("/feed").get_data(as_text=True)

    assert 'aria-label="Avatar de Lara Mendes"' in html
    assert 'aria-label="Avatar de Espaço Aurora"' in html
    assert ">LM</span>" in html
    assert ">EA</span>" in html


def test_initials_filter(app):
    initials = app.jinja_env.filters["initials"]

    assert initials("Camila Rocha") == "CR"
    assert initials("Thaís de Oliveira Souza") == "TS"
    assert initials("  ana  ") == "A"
    assert initials("") == ""
    assert initials(None) == ""
