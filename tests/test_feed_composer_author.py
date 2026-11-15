"""ID-SOC-R1-01/05 (Notion 08, 14/11/2026) — autor pessoal e compositor.

Post pessoal novo sai sempre pelo perfil pessoal (author_type client +
created_by_user_id), inclusive quando o app instalado manda o formato
antigo "professional". O perfil Pro não é outro autor: posts Pro antigos
aparecem como a mesma pessoa, com selo Pro. O post pessoal pode vincular
só serviço publicado do próprio perfil Pro público. Empresa publica como
empresa quando a conta é dona.
"""

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
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from app.services.feed_service import author_posts_page, serialize_work_post
from app.services.work_post_service import WorkPostError, create_work_post
from tests.test_api_posts import POSTS, _experience, _image_bytes, _multipart, _user
from tests.test_client_feed import _login

WHEN = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _client_id(app, user_id):
    with app.app_context():
        return db.session.scalar(select(ClientProfile.id).where(ClientProfile.user_id == user_id))


def _owned_establishment(app, user_id, slug="studio-compositor"):
    with app.app_context():
        business = Establishment(
            name="Studio Compositor", slug=slug, category="unhas",
            city="Curitiba", state="PR", is_active=True, published_at=WHEN,
        )
        db.session.add(business)
        db.session.flush()
        db.session.add(EstablishmentUserAccess(
            user_id=user_id, establishment_id=business.id,
            role=EstablishmentAccessRole.OWNER, status=EstablishmentAccessStatus.ACTIVE,
        ))
        db.session.commit()
        return business.id


def _web_post(client, author, **extra):
    data = {
        "author": author,
        "caption": extra.pop("caption", "Resultado de hoje"),
        "images": (BytesIO(_image_bytes()), "foto.jpg"),
        **extra,
    }
    return client.post(
        "/publicacoes/nova", data=data, content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )


def _posts(app):
    with app.app_context():
        return db.session.scalars(select(WorkPost).order_by(WorkPost.id)).all()


# ------------------------------------------------------------ compositor


def test_web_composer_has_one_personal_identity_and_compact_actions(app, client):
    user_id, pro_id, _ = _user(app, email="compositor-pro@example.com")
    own = _experience(app, professional_id=pro_id, slug="servico-proprio")
    _, other_pro, _ = _user(app, email="compositor-outra@example.com")
    _experience(app, professional_id=other_pro, slug="servico-alheio")
    client_id = _client_id(app, user_id)
    with app.app_context():
        username = db.session.get(User, user_id).username

    _login(client, user_id)
    html = client.get("/feed").get_data(as_text=True)

    # Sem seletor "Publicar como": uma identidade, com o @ da pessoa.
    assert 'id="composer-author"' not in html
    assert "Publicar como" not in html
    assert f'<input type="hidden" name="author" value="client:{client_id}">' in html
    assert f"@{username}" in html
    # Linha de ações: Foto, Vídeo inativo (sem envio) e Serviço.
    assert 'for="composer-images"' in html
    assert 'aria-disabled="true"' in html and "Em breve" in html
    assert "data-composer-service-toggle" in html
    # Só o serviço do próprio perfil Pro público aparece.
    assert f'<option value="{own}">' in html
    assert "servico-alheio" not in html


def test_client_without_pro_has_no_service_action(app, client):
    user_id, _, _ = _user(app, email="compositor-cliente@example.com", with_professional=False)
    _login(client, user_id)
    html = client.get("/feed").get_data(as_text=True)
    assert f'value="client:{_client_id(app, user_id)}"' in html
    assert "data-composer-service-toggle" not in html
    assert 'name="experience_id"' not in html


def test_composer_opens_as_the_company_only_for_its_owner(app, client):
    user_id, _, _ = _user(app, email="compositor-dona@example.com", with_professional=False)
    owned = _owned_establishment(app, user_id)
    other_owner, _, _ = _user(app, email="compositor-alheia@example.com", with_professional=False)
    foreign = _owned_establishment(app, other_owner, slug="studio-alheio")
    client_id = _client_id(app, user_id)
    _login(client, user_id)

    as_company = client.get(f"/feed?publicar_como=establishment:{owned}").get_data(as_text=True)
    assert f'name="author" value="establishment:{owned}"' in as_company
    assert "Publicar como você" in as_company
    assert 'id="post-composer" data-composer open' in as_company

    # Empresa de outra conta, valor forjado ou vazio: fica a pessoa.
    for value in (f"establishment:{foreign}", "professional:1", "x"):
        html = client.get(f"/feed?publicar_como={value}").get_data(as_text=True)
        assert f'name="author" value="client:{client_id}"' in html
        assert f"establishment:{foreign}" not in html.split('name="author"')[1][:40]

    # A página da empresa abre o compositor como a empresa.
    with app.app_context():
        slug = db.session.get(Establishment, owned).slug
    page = client.get(f"/estabelecimentos/{slug}").get_data(as_text=True)
    assert f"publicar_como=establishment:{owned}" in page


# --------------------------------------------------------- autor gravado


def test_pro_publishing_from_the_web_is_stored_as_personal_post(app, client):
    user_id, pro_id, _ = _user(app, email="web-pro@example.com")
    own = _experience(app, professional_id=pro_id, slug="web-servico")
    client_id = _client_id(app, user_id)
    _login(client, user_id)

    response = _web_post(client, f"client:{client_id}", experience_id=str(own))
    assert response.status_code == 200 and "#post-" in response.get_json()["redirect"]

    [post] = _posts(app)
    assert (post.author_type, post.client_profile_id, post.professional_id) == (
        WorkPostAuthorType.CLIENT, client_id, None,
    )
    assert post.created_by_user_id == user_id
    assert post.experience_id == own


def test_old_professional_author_is_recorded_as_the_person(app, client):
    user_id, pro_id, headers = _user(app, email="legado-pro@example.com")
    client_id = _client_id(app, user_id)
    _login(client, user_id)

    assert _web_post(client, f"professional:{pro_id}").status_code == 200
    api = client.post(POSTS, headers=headers, data=_multipart(author_id=pro_id),
                      content_type="multipart/form-data")
    assert api.status_code == 201

    posts = _posts(app)
    assert len(posts) == 2
    assert {(item.author_type, item.client_profile_id, item.professional_id) for item in posts} == {
        (WorkPostAuthorType.CLIENT, client_id, None),
    }


def test_forged_authors_are_refused_without_creating_posts(app, client):
    user_id, _, headers = _user(app, email="forja@example.com")
    victim_id, victim_pro, _ = _user(app, email="vitima@example.com")
    victim_owner, _, _ = _user(app, email="dona-vitima@example.com", with_professional=False)
    victim_business = _owned_establishment(app, victim_owner, slug="studio-vitima")
    _login(client, user_id)

    for author in (
        f"client:{_client_id(app, victim_id)}",
        f"professional:{victim_pro}",
        f"establishment:{victim_business}",
        "admin:1",
        "",
    ):
        response = _web_post(client, author)
        assert response.get_json()["redirect"].endswith("#post-composer"), author

    api = client.post(POSTS, headers=headers, data=_multipart(author_id=victim_pro),
                      content_type="multipart/form-data")
    assert api.status_code == 400
    assert _posts(app) == []


@pytest.mark.parametrize("case", ["alheio", "rascunho", "pausado", "pro_inativo", "sem_pro"])
def test_personal_post_links_only_own_published_service(app, case):
    owner_id, pro_id, _ = _user(app, email="servico-dona@example.com")
    _, other_pro, _ = _user(app, email="servico-outra@example.com")
    client_only, _, _ = _user(app, email="servico-cliente@example.com", with_professional=False)
    own = _experience(app, professional_id=pro_id, slug="servico-da-dona")
    other = _experience(app, professional_id=other_pro, slug="servico-da-outra")

    with app.app_context():
        user = db.session.get(User, owner_id)
        experience_id = own
        if case == "alheio":
            experience_id = other
        elif case in ("rascunho", "pausado"):
            db.session.get(Experience, own).status = (
                ExperienceStatus.DRAFT if case == "rascunho" else ExperienceStatus.PAUSED
            )
        elif case == "pro_inativo":
            db.session.get(ProfessionalProfile, pro_id).is_active = False
        elif case == "sem_pro":
            user = db.session.get(User, client_only)
        db.session.commit()

        with pytest.raises(WorkPostError):
            create_work_post(
                user=user, author_type=WorkPostAuthorType.CLIENT,
                caption="Com serviço", experience_id=experience_id,
            )
        db.session.rollback()
        assert db.session.scalar(select(WorkPost)) is None


def test_personal_post_with_own_service_is_accepted(app):
    owner_id, pro_id, _ = _user(app, email="servico-ok@example.com")
    own = _experience(app, professional_id=pro_id, slug="servico-ok")
    with app.test_request_context():
        post = create_work_post(
            user=db.session.get(User, owner_id), author_type=WorkPostAuthorType.CLIENT,
            caption="Com serviço meu", experience_id=own,
        )
        db.session.commit()
        payload = serialize_work_post(post)
        assert payload["service"]["id"] == "servico-ok"
        assert payload["author"]["professional"]["id"] == str(pro_id)


# ------------------------------------------------------------- exibição


def _legacy_post(app, professional_id, caption="Post Pro antigo"):
    with app.app_context():
        item = WorkPost(
            author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=professional_id,
            caption=caption, status=WorkPostStatus.PUBLISHED, published_at=WHEN,
            image_focus_x=50, image_focus_y=50,
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def test_old_pro_post_shows_the_person_and_keeps_old_fields(app):
    user_id, pro_id, _ = _user(app, email="legado-exibe@example.com")
    post_id = _legacy_post(app, pro_id)
    with app.test_request_context():
        user = db.session.get(User, user_id)
        payload = serialize_work_post(db.session.get(WorkPost, post_id))

    author = payload["author"]
    # Campos antigos intactos para o app instalado.
    assert payload["authorKind"] == "professional"
    assert (author["kind"], author["id"]) == ("professional", str(pro_id))
    # A mesma pessoa: nome da conta, @ e selo Pro.
    assert author["identity"] == "person"
    assert author["name"] == user.name
    assert author["username"] == user.username
    assert author["profileUrl"] == f"/@{user.username}"
    assert author["professional"]["id"] == str(pro_id)
    assert payload["followTarget"] == {"type": "person", "id": user_id}


def test_catalogue_profile_without_account_keeps_its_own_identity(app):
    with app.app_context():
        catalogue = ProfessionalProfile(
            display_name="Catálogo Sem Conta", slug="catalogo-compositor",
            city="Curitiba", state="PR", is_active=True, published_at=WHEN,
        )
        db.session.add(catalogue)
        db.session.commit()
        catalogue_id = catalogue.id
    post_id = _legacy_post(app, catalogue_id)
    with app.test_request_context():
        payload = serialize_work_post(db.session.get(WorkPost, post_id))
    assert payload["author"]["identity"] == "professional"
    assert payload["author"]["name"] == "Catálogo Sem Conta"
    assert payload["followTarget"] == {"type": "professional", "id": catalogue_id}


def test_company_post_follow_target_is_the_company(app):
    owner, _, _ = _user(app, email="empresa-alvo@example.com", with_professional=False)
    business = _owned_establishment(app, owner, slug="studio-alvo")
    with app.test_request_context():
        post = create_work_post(
            user=db.session.get(User, owner), author_type=WorkPostAuthorType.ESTABLISHMENT,
            author_id=business, caption="Novidade da empresa",
        )
        db.session.commit()
        payload = serialize_work_post(post)
    assert payload["author"]["identity"] == "establishment"
    assert payload["followTarget"] == {"type": "establishment", "id": business}


def test_person_page_merges_personal_and_old_pro_posts(app, client):
    user_id, pro_id, _ = _user(app, email="mescla@example.com")
    client_id = _client_id(app, user_id)
    old = _legacy_post(app, pro_id, caption="Antigo")
    with app.test_request_context():
        new = create_work_post(
            user=db.session.get(User, user_id), author_type=WorkPostAuthorType.CLIENT,
            caption="Novo",
        ).id
        db.session.commit()

        by_client = author_posts_page(WorkPostAuthorType.CLIENT, client_id)
        by_pro = author_posts_page(WorkPostAuthorType.PROFESSIONAL, pro_id)
    for page in (by_client, by_pro):
        assert [int(item["id"]) for item in page["items"]] == [new, old]
        assert page["total"] == 2

    # O perfil público do app (por perfil Pro) também traz os dois.
    with app.app_context():
        slug = db.session.get(ProfessionalProfile, pro_id).slug
    profile = client.get(f"/api/v1/professionals/{slug}").get_json()
    assert [int(item["id"]) for item in profile["posts"]][:2] == [new, old]


def test_feed_card_links_person_and_follows_the_person(app, client):
    author_id, pro_id, _ = _user(app, email="cartao-autora@example.com")
    viewer_id, _, _ = _user(app, email="cartao-leitora@example.com", with_professional=False)
    _legacy_post(app, pro_id, caption="Cartão")
    with app.app_context():
        username = db.session.get(User, author_id).username

    _login(client, viewer_id)
    html = client.get("/feed").get_data(as_text=True)
    assert f'href="/@{username}"' in html
    assert f'data-target-type="person"\n        data-target-id="{author_id}"' in html
    assert "· Nail Designer" in html
