"""P-004 / F16 e ID-SOC-R1-06 — painel Business em feed, com cartão Equipe.

O centro do painel é o feed da empresa: compositor só para quem publica
como ela (dona, página no ar) e as publicações reais dela. O envio feito no
painel volta ao painel por rota validada. A equipe vira um cartão compacto
com dados reais; os formulários de antes abrem sob demanda, sem rota nova,
e as validações, o aceite e as permissões não mudam.
"""

import re
from datetime import datetime, timezone
from io import BytesIO

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from tests.test_api_posts import _image_bytes

WHEN = datetime(2026, 11, 1, tzinfo=timezone.utc)
PASSWORD = "senha-forte-123"


def _user(name, email, *, pro=False):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    if pro:
        db.session.add(ProfessionalProfile(
            user_id=user.id, display_name=name, slug=email.split("@")[0],
            primary_specialty="Colorista", city="Curitiba", state="PR", is_active=True,
        ))
    db.session.commit()
    return user


def _business(slug, *, active=True):
    item = Establishment(
        name=f"Studio {slug.title()}", slug=slug, category="salao",
        city="Curitiba", state="PR", is_active=active,
        published_at=WHEN if active else None,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _access(user, business, role=EstablishmentAccessRole.OWNER):
    db.session.add(EstablishmentUserAccess(
        user_id=user.id, establishment_id=business.id, role=role,
        status=EstablishmentAccessStatus.ACTIVE,
    ))
    db.session.commit()


def _member(business, pro_user, status=MembershipStatus.ACTIVE):
    db.session.add(ProfessionalEstablishmentMembership(
        professional=pro_user.professional_profile, establishment=business,
        role_name="Colorista", status=status, is_primary=False,
    ))
    db.session.commit()


def _post(caption, **author):
    item = WorkPost(
        caption=caption, status=WorkPostStatus.PUBLISHED, published_at=WHEN,
        image_focus_x=50, image_focus_y=50, **author,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


@pytest.fixture()
def world(app):
    owner = _user("Dona Painel", "dona-painel@example.com")
    manager = _user("Gestora Painel", "gestora-painel@example.com")
    rival = _user("Dona Rival", "dona-rival@example.com")
    business = _business("painel")
    other = _business("rival")
    _access(owner, business)
    _access(manager, business, EstablishmentAccessRole.MANAGER)
    _access(rival, other)
    _post("Novidade da empresa", author_type=WorkPostAuthorType.ESTABLISHMENT, establishment_id=business.id)
    _post("Post pessoal da dona", author_type=WorkPostAuthorType.CLIENT, client_profile_id=owner.client_profile.id)
    _post("Post da rival", author_type=WorkPostAuthorType.ESTABLISHMENT, establishment_id=other.id)
    return {
        "owner": owner.id, "manager": manager.id, "rival": rival.id,
        "business": business.id, "slug": business.slug, "other": other.id,
        "panel": f"/business/{business.slug}/painel",
    }


def _panel(client, world, query=""):
    response = client.get(world["panel"] + query)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _dialog(html, dialog_id):
    return re.search(rf'<dialog[^>]*id="{dialog_id}"[^>]*>', html).group(0)


# ---------------------------------------------------------------- feed


def test_owner_panel_is_the_company_feed_with_its_composer(client, world):
    _login(client, world["owner"])
    html = _panel(client, world)

    # Compositor como a empresa, voltando ao painel; sem trocar para a pessoa.
    assert f'name="author" value="establishment:{world["business"]}"' in html
    assert 'name="origem" value="painel"' in html
    assert "Publicar como você" not in html
    # Só as publicações reais desta empresa.
    assert "Novidade da empresa" in html
    assert "Post pessoal da dona" not in html and "Post da rival" not in html
    # Identidade e números reais; nada de receita ou métrica inventada.
    assert "<strong>1</strong><span>Publicação</span>" in html
    assert "<strong>0</strong><span>Seguidores</span>" in html
    assert "Receita" not in html


def test_manager_sees_the_feed_but_does_not_publish_as_the_company(client, world):
    _login(client, world["manager"])
    html = _panel(client, world)
    assert "Novidade da empresa" in html
    assert 'name="author"' not in html
    assert "Só quem é proprietário publica em nome da empresa." in html

    refused = client.post(
        "/publicacoes/nova",
        data={"author": f'establishment:{world["business"]}', "caption": "Tentativa", "origem": "painel"},
        headers={"Accept": "application/json"},
    )
    # Recusado pelo servidor e sem voltar ao painel por causa do campo.
    assert refused.get_json()["redirect"].endswith("/feed#post-composer")
    assert db.session.scalar(select(WorkPost).where(WorkPost.caption == "Tentativa")) is None


def test_draft_page_has_no_composer(client, app, world):
    owner = db.session.get(User, world["owner"])
    draft = _business("rascunho", active=False)
    _access(owner, draft)
    _login(client, world["owner"])
    html = client.get(f"/business/{draft.slug}/painel").get_data(as_text=True)
    assert 'name="author"' not in html
    assert "A empresa publica novidades quando a página estiver no ar." in html
    assert "Esta página ainda não está no ar." in html


def test_posting_from_the_panel_returns_to_the_panel(client, world):
    _login(client, world["owner"])
    response = client.post(
        "/publicacoes/nova",
        data={
            "author": f'establishment:{world["business"]}',
            "caption": "Publicado pelo painel",
            "origem": "painel",
            "images": (BytesIO(_image_bytes()), "foto.jpg"),
        },
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    post = db.session.scalar(select(WorkPost).where(WorkPost.caption == "Publicado pelo painel"))
    assert post is not None
    assert (post.author_type, post.establishment_id, post.created_by_user_id) == (
        WorkPostAuthorType.ESTABLISHMENT, world["business"], world["owner"],
    )
    assert response.get_json()["redirect"] == f'{world["panel"]}#post-{post.id}'

    # Publicação vazia: o erro também volta ao painel.
    empty = client.post(
        "/publicacoes/nova",
        data={"author": f'establishment:{world["business"]}', "caption": "", "origem": "painel"},
        headers={"Accept": "application/json"},
    )
    assert empty.get_json()["redirect"] == f'{world["panel"]}#post-composer'


@pytest.mark.parametrize("author", ["establishment:{other}", "client:1", "establishment:999999", "x", ""])
def test_origin_field_never_redirects_outside_the_owned_panel(client, world, author):
    _login(client, world["owner"])
    response = client.post(
        "/publicacoes/nova",
        data={"author": author.format(other=world["other"]), "caption": "", "origem": "painel"},
        headers={"Accept": "application/json"},
    )
    assert response.get_json()["redirect"].endswith("/feed#post-composer")


def test_feed_composer_still_returns_to_the_feed(client, world):
    _login(client, world["owner"])
    response = client.post(
        "/publicacoes/nova",
        data={"author": f'establishment:{world["business"]}', "caption": "Pelo feed"},
        headers={"Accept": "application/json"},
    )
    assert re.search(r"/feed#post-\d+$", response.get_json()["redirect"])


# -------------------------------------------------------------- equipe


def test_team_card_is_compact_and_forms_are_closed_until_asked(client, world):
    business = db.session.get(Establishment, world["business"])
    for index in range(4):
        _member(business, _user(f"Pro Equipe {index}", f"pro-equipe-{index}@example.com", pro=True))
    _member(business, _user("Pro Pendente", "pro-pendente@example.com", pro=True), MembershipStatus.PENDING)
    _login(client, world["owner"])
    html = _panel(client, world)

    card = html.split('id="business-team"')[1].split("</section>")[0]
    assert "4 profissionais na equipe" in card
    assert card.count("<li>") == 3 and "e mais 1" in card
    assert "1 convite aguardando resposta" in card
    assert "Gerenciar equipe" in card and "Convidar profissional" in card
    assert "<form" not in card and "<input" not in card

    # As duas janelas existem e vêm fechadas.
    for dialog_id in ("business-team-invite", "business-team-manage"):
        assert " open" not in _dialog(html, dialog_id)
    # A lista completa e o Remover continuam, dentro da janela.
    manage = html.split('id="business-team-manage"')[1].split("</dialog>")[0]
    assert manage.count("/remover") == 4 and "Pro Pendente" in manage


@pytest.mark.parametrize(
    "query, opened",
    [("?equipe=convidar", "business-team-invite"), ("?equipe=gerenciar", "business-team-manage")],
)
def test_team_dialogs_open_on_demand_without_javascript(client, world, query, opened):
    _login(client, world["owner"])
    html = _panel(client, world, query)
    for dialog_id in ("business-team-invite", "business-team-manage"):
        assert (" open" in _dialog(html, dialog_id)) is (dialog_id == opened)


def test_unknown_dialog_value_is_ignored(client, world):
    _login(client, world["owner"])
    html = _panel(client, world, "?equipe=apagar-tudo")
    for dialog_id in ("business-team-invite", "business-team-manage"):
        assert " open" not in _dialog(html, dialog_id)


def test_invite_keeps_its_rules_and_reopens_the_dialog_on_error(client, world):
    _user("Pro Convidada", "pro-convidada@example.com", pro=True)
    _login(client, world["owner"])

    wrong = client.post(world["panel"], data={"email": "ninguem@example.com", "role_name": ""})
    assert wrong.status_code == 200
    html = wrong.get_data(as_text=True)
    assert "ainda não possui um perfil profissional IDDUN" in html
    assert " open" in _dialog(html, "business-team-invite")
    assert db.session.scalar(select(ProfessionalEstablishmentMembership)) is None

    sent = client.post(world["panel"], data={"email": "pro-convidada@example.com", "role_name": "Colorista"})
    assert sent.status_code == 302 and sent.headers["Location"].endswith(world["panel"])
    membership = db.session.scalar(select(ProfessionalEstablishmentMembership))
    # O vínculo continua dependendo do aceite da pessoa.
    assert membership.status == MembershipStatus.PENDING
    assert "1 convite aguardando resposta" in _panel(client, world)

    again = client.post(world["panel"], data={"email": "pro-convidada@example.com", "role_name": ""})
    assert "já possui um convite pendente" in again.get_data(as_text=True)


def test_other_company_cannot_open_the_panel_or_its_dialogs(client, world):
    _login(client, world["rival"])
    assert client.get(world["panel"]).status_code == 403
    assert client.get(world["panel"] + "?equipe=gerenciar").status_code == 403
    assert client.post(world["panel"], data={"email": "x@example.com"}).status_code == 403
