"""CONV-07 public identity regressions."""
from pathlib import Path

from app.extensions import db
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole

ROOT = Path(__file__).resolve().parents[1]


def test_real_professional_without_avatar_has_initials_not_stock_photo(app, client):
    with app.app_context():
        db.session.add(ProfessionalProfile(
            display_name="Maria Souza", slug="maria-sem-avatar",
            primary_specialty="nail designer", is_active=True,
        ))
        db.session.commit()
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Maria Souza" in html
    assert "Nail designer" in html
    assert 'aria-label="Avatar de Maria Souza"' in html
    assert "category-hair.jpg" not in html

    listing = client.get("/profissionais").get_data(as_text=True)
    detail = client.get("/profissionais/maria-sem-avatar").get_data(as_text=True)
    assert 'aria-label="Avatar de Maria Souza"' in listing
    assert 'aria-label="Avatar de Maria Souza"' in detail


def test_empty_business_listing_has_registration_action(client):
    html = client.get("/").get_data(as_text=True)
    assert "Cadastrar meu estabelecimento" in html
    assert 'href="/cadastro"' in html


def test_real_counts_remain_visible_for_small_communities(app, client):
    with app.app_context():
        db.session.add(User(
            name="Cliente real", email="conv07-count@example.com",
            password_hash="test", role=UserRole.CLIENT,
            is_active_account=True,
        ))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    assert "Pessoas cadastradas" in html
    assert 'aria-label="Números reais da comunidade IDDUN"' in html


def test_footer_has_only_confirmed_contact_and_app_notice(client):
    html = client.get("/").get_data(as_text=True)
    assert "Aplicativos para iOS e Android em breve" in html
    assert "Redes sociais oficiais: em breve" not in html
    assert "mailto:contato@iddun.com.br" in html
