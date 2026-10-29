"""V-03 — remover trabalho do portfólio Pro e imagem da galeria Business.

BUG-005, FE-DEC-042/045/046:
- depois de remover, a página volta para a própria seção (id + foco);
- remover pede confirmação, como a experiência profissional;
- botão com ícone do DS e rótulo por item;
- "1 trabalho"/"N trabalhos" e estado vazio honesto;
- a ajuda não apresenta como regra o que é opcional (DEC-ID-094).
"""

import re

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
)
from app.models.professional import ProfessionalPortfolioItem, ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _user(email):
    user = User(name="Pessoa Portfólio", email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    return user


def _pro(app, works):
    with app.app_context():
        user = _user(f"pro-portfolio-{works}@example.com")
        profile = ProfessionalProfile(
            user=user, display_name="Pro Portfólio", slug=f"pro-portfolio-{works}",
        )
        db.session.add(profile)
        db.session.flush()
        for index in range(works):
            db.session.add(ProfessionalPortfolioItem(
                professional=profile,
                image_url=f"https://cdn.example.com/work-{index}.jpg",
                sort_order=index,
            ))
        db.session.commit()
        return user.id


def _business(app, images):
    with app.app_context():
        user = _user(f"dono-galeria-{images}@example.com")
        business = Establishment(
            name="Studio Galeria",
            slug=f"studio-galeria-{images}",
            category="salao",
            description="Espaço de teste para a galeria do estabelecimento.",
            city="Curitiba",
            state="PR",
            is_active=True,
            onboarding_completed=True,
        )
        db.session.add(business)
        db.session.flush()
        db.session.add(EstablishmentUserAccess(
            user=user,
            establishment=business,
            role=EstablishmentAccessRole.OWNER,
            status=EstablishmentAccessStatus.ACTIVE,
        ))
        items = []
        for index in range(images):
            item = EstablishmentGalleryItem(
                establishment=business,
                image_url=f"https://cdn.example.com/gallery-{index}.jpg",
                sort_order=index,
            )
            db.session.add(item)
            items.append(item)
        db.session.commit()
        return user.id, business.slug, [item.id for item in items]


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _section(html, section_id):
    match = re.search(rf'<section[^>]*id="{section_id}"[^>]*>(.*?)</section>', html, re.S)
    assert match, f"seção #{section_id} não encontrada"
    return match.group(0)


def test_portfolio_section_is_the_return_target_with_safe_removal(app, client):
    _login(client, _pro(app, works=2))
    html = client.get("/pro/perfil/editar").get_data(as_text=True)

    section = _section(html, "portfolio")
    opening = re.match(r"<section[^>]*>", section).group(0)
    assert 'tabindex="-1"' in opening
    assert 'data-focus-on-hash' in opening
    assert re.search(r">\s*2 trabalhos\s*<", section)

    buttons = re.findall(r"<button[^>]*form=\"remove-portfolio-\d+\"[^>]*>.*?</button>", section, re.S)
    assert len(buttons) == 2
    for number, button in enumerate(buttons, start=1):
        assert f'aria-label="Remover trabalho {number} de 2"' in button
        assert '<svg class="icon' in button
        assert "×" not in button

    forms = re.findall(r'<form[^>]*id="remove-portfolio-\d+"[^>]*>', html)
    assert len(forms) == 2
    for form in forms:
        assert 'data-confirm-submit="Remover este trabalho? A imagem será apagada."' in form

    assert "mantenha ao menos 3" not in html
    assert "3 ou mais trabalhos deixam o perfil mais completo" in html


def test_portfolio_count_is_singular(app, client):
    _login(client, _pro(app, works=1))
    html = client.get("/pro/perfil/editar").get_data(as_text=True)
    assert re.search(r">\s*1 trabalho\s*<", _section(html, "portfolio"))


def test_portfolio_empty_state_is_honest(app, client):
    _login(client, _pro(app, works=0))
    section = _section(client.get("/pro/perfil/editar").get_data(as_text=True), "portfolio")
    assert "Nenhum trabalho publicado ainda" in section
    assert "platform-manage-gallery__item" not in section


def test_business_gallery_mirrors_portfolio_and_returns_to_it(app, client):
    user_id, slug, item_ids = _business(app, images=1)
    _login(client, user_id)

    html = client.get(f"/business/{slug}/editar").get_data(as_text=True)
    section = _section(html, "galeria")
    assert 'data-focus-on-hash' in section
    assert re.search(r">\s*1 imagem\s*<", section)
    assert 'aria-label="Remover imagem 1 de 1"' in section
    assert 'data-confirm-submit="Remover esta imagem? Ela será apagada da galeria."' in html

    response = client.post(f"/business/{slug}/galeria/{item_ids[0]}/remover")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/business/{slug}/editar#galeria")
    with app.app_context():
        assert db.session.get(EstablishmentGalleryItem, item_ids[0]) is None

    empty = _section(client.get(f"/business/{slug}/editar").get_data(as_text=True), "galeria")
    assert "Nenhuma imagem na galeria ainda" in empty
