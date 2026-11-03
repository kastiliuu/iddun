"""PR 3 do programa IDDUN 2.0 — feed social (D-SOC-02, 08 a 11).

- Cliente publica como Cliente; texto, foto ou carrossel até 10.
- Empresa publica só pela dona; gestor não (AUD-14).
- Curtida única por pessoa; comentários com resposta em um nível.
- Denúncia vai para a fila, não apaga e não devolve protocolo.
- Moderação pela equipe da plataforma, com histórico.
- Remoção pela autora é lógica e apaga as imagens (D-SOC-09).
"""

from io import BytesIO

from flask import g
from PIL import Image
from sqlalchemy import func, select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.models.work_post import (
    CommentStatus,
    ContentReport,
    ModerationAction,
    WorkPost,
    WorkPostAuthorType,
    WorkPostComment,
    WorkPostLike,
    WorkPostStatus,
)
from tests.test_api_posts import FEED, POSTS, _image_bytes, _upload_files, _user
from tests.test_client_feed import _login


def _client_profile_id(app, user_id):
    with app.app_context():
        return db.session.scalar(select(ClientProfile.id).where(ClientProfile.user_id == user_id))


def _publish(client, headers, *, author_type="client", author_id=None, caption="Meu resultado.", images=0, alt=None):
    data = {"authorType": author_type, "caption": caption}
    if author_id is not None:
        data["authorId"] = str(author_id)
    if images:
        data["images"] = [(BytesIO(_image_bytes()), f"foto-{index}.jpg") for index in range(images)]
    if alt:
        data["altTexts"] = alt
    return client.post(POSTS, headers=headers, data=data, content_type="multipart/form-data")


def _client_post(app, client, email="cliente-post@example.com", **kwargs):
    user_id, _, headers = _user(app, email=email, with_professional=False)
    profile_id = _client_profile_id(app, user_id)
    response = _publish(client, headers, author_id=profile_id, **kwargs)
    assert response.status_code == 201, response.get_json()
    return user_id, headers, response.get_json()["post"]


def _admin(app, email="moderacao@example.com"):
    with app.app_context():
        user = User(name="Equipe IDDUN", email=email, role=UserRole.ADMIN)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.commit()
        return user.id


def _as(client, user_id):
    g.pop("_login_user", None)
    _login(client, user_id)


# ------------------------------------------------------------- autoria


def test_client_publishes_text_only_and_it_appears_in_the_feed(app, client):
    _, _, post = _client_post(app, client, caption="Primeira vez com cachos definidos!")

    assert post["authorKind"] == "client"
    assert post["image"] is None
    assert post["media"] == []

    feed = client.get(FEED).get_json()["items"]
    item = next(entry for entry in feed if entry["id"] == post["id"])
    assert item["author"]["kind"] == "client"
    assert item["author"]["name"] == "Creator Test"
    # DEC-ID-227: nenhuma cidade ou dado privado da Cliente.
    assert item["author"]["routeId"] is None
    assert "location" not in item["author"]
    assert item["likesCount"] == 0 and item["commentsCount"] == 0


def test_empty_post_is_refused_and_carousel_keeps_order_and_alt(app, client):
    user_id, _, headers = _user(app, email="carrossel@example.com", with_professional=False)
    profile_id = _client_profile_id(app, user_id)

    empty = _publish(client, headers, author_id=profile_id, caption="  ")
    assert empty.status_code == 400
    assert "texto ou adicione uma imagem" in empty.get_json()["error"]["message"]

    created = _publish(
        client,
        headers,
        author_id=profile_id,
        caption="",
        images=3,
        alt=["Antes", "Durante", "Depois"],
    )
    assert created.status_code == 201
    media = created.get_json()["post"]["media"]
    assert [item["alt"] for item in media] == ["Antes", "Durante", "Depois"]
    assert created.get_json()["post"]["image"] == media[0]["url"]
    assert len(_upload_files(app)) == 3

    too_many = _publish(client, headers, author_id=profile_id, images=11)
    assert too_many.status_code == 400
    assert too_many.get_json()["error"]["code"] == "too_many_images"


def test_client_cannot_link_a_service(app, client):
    user_id, _, headers = _user(app, email="cliente-servico@example.com", with_professional=False)
    data = {
        "authorType": "client",
        "authorId": str(_client_profile_id(app, user_id)),
        "caption": "Olha só",
        "experienceId": "1",
    }
    response = client.post(POSTS, headers=headers, data=data, content_type="multipart/form-data")
    assert response.status_code == 400


def _establishment_with(app, user_id, role):
    with app.app_context():
        establishment = Establishment(
            name=f"Studio {role}",
            slug=f"studio-{role}-{user_id}",
            category="salao",
            city="Curitiba",
            state="PR",
            is_active=True,
        )
        db.session.add(establishment)
        db.session.flush()
        db.session.add(
            EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=establishment.id,
                role=role,
                status=EstablishmentAccessStatus.ACTIVE,
            )
        )
        db.session.commit()
        return establishment.id


def test_only_the_owner_publishes_as_the_business(app, client):
    owner_id, _, owner_headers = _user(app, email="dona@example.com", with_professional=False)
    manager_id, _, manager_headers = _user(app, email="gestora@example.com", with_professional=False)
    establishment_id = _establishment_with(app, owner_id, EstablishmentAccessRole.OWNER)
    with app.app_context():
        db.session.add(
            EstablishmentUserAccess(
                user_id=manager_id,
                establishment_id=establishment_id,
                role=EstablishmentAccessRole.MANAGER,
                status=EstablishmentAccessStatus.ACTIVE,
            )
        )
        db.session.commit()

    manager = _publish(client, manager_headers, author_type="establishment", author_id=establishment_id, images=1)
    assert manager.status_code == 400

    options = client.get(POSTS + "/options", headers=manager_headers).get_json()
    assert all(item["type"] != "establishment" for item in options["authors"])

    owner = _publish(client, owner_headers, author_type="establishment", author_id=establishment_id, images=1)
    assert owner.status_code == 201
    with app.app_context():
        post = db.session.get(WorkPost, int(owner.get_json()["post"]["id"]))
        assert post.created_by_user_id == owner_id


def test_legacy_manager_post_stays_published_and_only_owner_edits(app, client):
    owner_id, _, owner_headers = _user(app, email="dona-legado@example.com", with_professional=False)
    manager_id, _, manager_headers = _user(app, email="gestora-legado@example.com", with_professional=False)
    establishment_id = _establishment_with(app, owner_id, EstablishmentAccessRole.OWNER)
    with app.app_context():
        db.session.add(
            EstablishmentUserAccess(
                user_id=manager_id,
                establishment_id=establishment_id,
                role=EstablishmentAccessRole.MANAGER,
                status=EstablishmentAccessStatus.ACTIVE,
            )
        )
        legacy = WorkPost(
            author_type=WorkPostAuthorType.ESTABLISHMENT,
            establishment_id=establishment_id,
            caption="Post de antes da PR 3",
            image_url="uploads/work-posts/antigo.jpg",
            status=WorkPostStatus.PUBLISHED,
        )
        db.session.add(legacy)
        db.session.commit()
        legacy_id = legacy.id

    assert client.get(f"{POSTS}/{legacy_id}").status_code == 200
    denied = client.put(f"{POSTS}/{legacy_id}", headers=manager_headers, json={"caption": "x"})
    assert denied.status_code == 400
    allowed = client.put(f"{POSTS}/{legacy_id}", headers=owner_headers, json={"caption": "Editado pela dona"})
    assert allowed.status_code == 200


# ------------------------------------------------------------- curtidas


def test_like_is_once_per_person_and_counts_are_real(app, client):
    _, _, post = _client_post(app, client)
    _, _, fan = _user(app, email="fa@example.com", with_professional=False)
    _, _, other = _user(app, email="outra-fa@example.com", with_professional=False)
    url = f"{POSTS}/{post['id']}/like"

    assert client.put(url).status_code == 401
    assert client.put(url, headers=fan).get_json() == {"liked": True, "likesCount": 1}
    assert client.put(url, headers=fan).get_json() == {"liked": True, "likesCount": 1}
    assert client.put(url, headers=other).get_json()["likesCount"] == 2

    detail = client.get(f"{POSTS}/{post['id']}", headers=fan).get_json()
    assert detail["likesCount"] == 2 and detail["likedByMe"] is True

    assert client.delete(url, headers=fan).get_json() == {"liked": False, "likesCount": 1}
    assert client.delete(url, headers=fan).get_json() == {"liked": False, "likesCount": 1}
    with app.app_context():
        assert db.session.scalar(select(func.count(WorkPostLike.id))) == 1


# ---------------------------------------------------------- comentários


def test_comments_with_one_level_of_replies(app, client):
    author_id, author_headers, post = _client_post(app, client)
    _, _, ana = _user(app, email="ana-comenta@example.com", with_professional=False)
    _, _, bia = _user(app, email="bia-comenta@example.com", with_professional=False)
    comments = f"{POSTS}/{post['id']}/comments"

    assert client.post(comments, json={"body": "Oi"}).status_code == 401
    assert client.post(comments, headers=ana, json={"body": "   "}).status_code == 400
    assert client.post(comments, headers=ana, json={"body": "x" * 1001}).status_code == 400

    first = client.post(comments, headers=ana, json={"body": "Ficou lindo!"})
    assert first.status_code == 201
    first_id = first.get_json()["comment"]["id"]
    reply = client.post(comments, headers=author_headers, json={"body": "Obrigada!", "parentId": first_id})
    assert reply.status_code == 201
    deeper = client.post(
        comments, headers=bia, json={"body": "Concordo", "parentId": reply.get_json()["comment"]["id"]}
    )
    assert deeper.status_code == 400
    assert deeper.get_json()["error"]["code"] == "reply_depth_exceeded"

    listing = client.get(comments).get_json()
    assert listing["total"] == 2
    assert [item["body"] for item in listing["items"]] == ["Ficou lindo!"]
    assert [item["body"] for item in listing["items"][0]["replies"]] == ["Obrigada!"]
    assert client.get(f"{POSTS}/{post['id']}").get_json()["commentsCount"] == 2


def test_comment_owner_deletes_and_post_author_hides(app, client):
    _, author_headers, post = _client_post(app, client)
    _, _, ana = _user(app, email="ana-apaga@example.com", with_professional=False)
    _, _, bia = _user(app, email="bia-oculta@example.com", with_professional=False)
    comments = f"{POSTS}/{post['id']}/comments"
    mine = client.post(comments, headers=ana, json={"body": "Meu"}).get_json()["comment"]["id"]
    rude = client.post(comments, headers=bia, json={"body": "Grosseria"}).get_json()["comment"]["id"]

    assert client.delete(f"/api/v1/comments/{mine}", headers=bia).status_code == 404
    assert client.post(f"/api/v1/comments/{rude}/hide", headers=ana).status_code == 404
    assert client.delete(f"/api/v1/comments/{mine}", headers=ana).status_code == 200
    assert client.post(f"/api/v1/comments/{rude}/hide", headers=author_headers).status_code == 200

    assert client.get(comments).get_json()["total"] == 0
    with app.app_context():
        statuses = {item.body: item.status for item in db.session.scalars(select(WorkPostComment))}
    assert statuses == {"Meu": CommentStatus.DELETED, "Grosseria": CommentStatus.HIDDEN_BY_AUTHOR}


# ----------------------------------------------------- denúncia e moderação


def test_report_goes_to_the_queue_without_protocol_or_deletion(app, client):
    _, _, post = _client_post(app, client)
    _, _, reporter = _user(app, email="denuncia@example.com", with_professional=False)
    url = f"{POSTS}/{post['id']}/report"

    assert client.post(url, headers=reporter, json={"category": "inventada"}).status_code == 400
    first = client.post(url, headers=reporter, json={"category": "spam", "description": "Link estranho"})
    again = client.post(url, headers=reporter, json={"category": "spam"})

    assert first.status_code == 204 and first.data == b""
    assert again.status_code == 204
    assert client.get(f"{POSTS}/{post['id']}").status_code == 200
    with app.app_context():
        reports = db.session.scalars(select(ContentReport)).all()
        assert len(reports) == 1
        assert reports[0].status == "open"
        assert len(reports[0].protocol) == 36


def test_moderation_hides_restores_and_keeps_history(app, client):
    _, _, post = _client_post(app, client)
    _, _, reporter = _user(app, email="denuncia-mod@example.com", with_professional=False)
    client.post(f"{POSTS}/{post['id']}/report", headers=reporter, json={"category": "sexual"})
    with app.app_context():
        report_id = db.session.scalar(select(ContentReport.id))

    regular_id, _, _ = _user(app, email="sem-acesso@example.com", with_professional=False)
    _as(client, regular_id)
    assert client.get("/admin/moderacao").status_code == 403
    assert client.post(f"/admin/moderacao/{report_id}", data={"action": "hide"}).status_code == 403

    admin_id = _admin(app)
    _as(client, admin_id)
    queue = client.get("/admin/moderacao")
    assert queue.status_code == 200
    assert "Conteúdo sexual" in queue.get_data(as_text=True)
    assert "denuncia-mod@example.com" not in queue.get_data(as_text=True)

    client.post(f"/admin/moderacao/{report_id}", data={"action": "hide", "note": "Nudez explícita"})
    with app.app_context():
        assert db.session.get(WorkPost, int(post["id"])).status == WorkPostStatus.HIDDEN
        assert db.session.get(ContentReport, report_id).status == "actioned"
    assert client.get(f"{POSTS}/{post['id']}", headers=reporter).status_code == 404
    assert all(item["id"] != post["id"] for item in client.get(FEED).get_json()["items"])
    # A equipe ainda abre a página para revisar.
    assert "ocultada pela moderação" in client.get(f"/publicacoes/{post['id']}").get_data(as_text=True)

    client.post(f"/admin/moderacao/{report_id}", data={"action": "restore", "note": "Revisado"})
    with app.app_context():
        assert db.session.get(WorkPost, int(post["id"])).status == WorkPostStatus.PUBLISHED
        actions = [item.action for item in db.session.scalars(select(ModerationAction).order_by(ModerationAction.id))]
    assert actions == ["hide", "restore"]
    assert "Revisado" in client.get("/admin/moderacao?aba=decididas").get_data(as_text=True)


def test_moderation_removes_a_comment(app, client):
    _, _, post = _client_post(app, client)
    _, _, ana = _user(app, email="ana-mod@example.com", with_professional=False)
    _, _, bia = _user(app, email="bia-mod@example.com", with_professional=False)
    comment = client.post(
        f"{POSTS}/{post['id']}/comments", headers=ana, json={"body": "Ofensa"}
    ).get_json()["comment"]["id"]
    assert client.post(f"/api/v1/comments/{comment}/report", headers=bia, json={"category": "harassment"}).status_code == 204
    with app.app_context():
        report_id = db.session.scalar(select(ContentReport.id))

    _as(client, _admin(app, "mod-comentario@example.com"))
    client.post(f"/admin/moderacao/{report_id}", data={"action": "hide"})
    with app.app_context():
        assert db.session.get(WorkPostComment, int(comment)).status == CommentStatus.REMOVED_BY_MODERATION
    assert client.get(f"{POSTS}/{post['id']}/comments").get_json()["total"] == 0


def test_hidden_post_cannot_be_republished_by_its_author(app, client):
    _, headers, post = _client_post(app, client)
    with app.app_context():
        db.session.get(WorkPost, int(post["id"])).status = WorkPostStatus.HIDDEN
        db.session.commit()
    response = client.put(f"{POSTS}/{post['id']}", headers=headers, json={"status": "published"})
    assert response.status_code == 400


def test_author_removal_is_logical_keeps_reports_and_deletes_images(app, client):
    user_id, headers, post = _client_post(app, client, images=2)
    _, _, reporter = _user(app, email="denuncia-antes@example.com", with_professional=False)
    client.post(f"{POSTS}/{post['id']}/report", headers=reporter, json={"category": "spam"})
    assert len(_upload_files(app)) == 2

    _as(client, user_id)
    response = client.post(f"/publicacoes/{post['id']}/remover")
    assert response.status_code == 302

    assert _upload_files(app) == []
    assert client.get(f"/publicacoes/{post['id']}").status_code == 404
    with app.app_context():
        removed = db.session.get(WorkPost, int(post["id"]))
        assert removed.status == WorkPostStatus.REMOVED
        assert removed.media == []
        assert db.session.scalar(select(ContentReport.post_id)) == removed.id


def test_uploaded_photo_loses_location_metadata(app, client):
    image = Image.new("RGB", (40, 30), (200, 100, 50))
    exif = Image.Exif()
    exif[0x010F] = "Camera de teste"  # Make
    exif.get_ifd(0x8825).update({1: "S", 2: (25.0, 25.0, 0.0)})  # GPSInfo
    raw = BytesIO()
    image.save(raw, format="JPEG", exif=exif.tobytes())
    with Image.open(BytesIO(raw.getvalue())) as original:
        assert original.getexif().get_ifd(0x8825)

    user_id, _, headers = _user(app, email="exif@example.com", with_professional=False)
    data = {
        "authorType": "client",
        "authorId": str(_client_profile_id(app, user_id)),
        "images": [(BytesIO(raw.getvalue()), "gps.jpg")],
    }
    assert client.post(POSTS, headers=headers, data=data, content_type="multipart/form-data").status_code == 201

    stored = _upload_files(app)[0]
    with Image.open(stored) as saved:
        assert not saved.getexif().get_ifd(0x8825)
        assert not saved.getexif().get(0x010F)


# ------------------------------------------------------------------- Web


def test_web_composer_publishes_and_the_post_page_shows_comments(app, client):
    user_id, _, _ = _user(app, email="web-composer@example.com", with_professional=False)
    profile_id = _client_profile_id(app, user_id)
    _as(client, user_id)

    feed = client.get("/feed").get_data(as_text=True)
    assert 'id="post-composer"' in feed
    assert f'value="client:{profile_id}"' in feed
    assert "Audiência: Público" in feed

    response = client.post(
        "/publicacoes/nova",
        data={
            "author": f"client:{profile_id}",
            "caption": "Post pelo navegador",
            "images": [(BytesIO(_image_bytes()), "a.jpg"), (BytesIO(_image_bytes()), "b.jpg")],
            "alt_texts": ["Primeira", "Segunda"],
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    with app.app_context():
        post = db.session.scalar(select(WorkPost).order_by(WorkPost.id.desc()))
        assert [item.alt_text for item in post.media] == ["Primeira", "Segunda"]
        post_id = post.id
    assert response.headers["Location"].endswith(f"/feed#post-{post_id}")

    json_response = client.post(
        "/publicacoes/nova",
        data={"author": f"client:{profile_id}", "caption": ""},
        headers={"Accept": "application/json"},
    )
    assert json_response.get_json() == {"redirect": "/feed#post-composer"}

    client.post(f"/publicacoes/{post_id}/comentarios", data={"body": "Comentário pela Web"})
    page = client.get(f"/publicacoes/{post_id}").get_data(as_text=True)
    assert "Comentário pela Web" in page
    assert "Comentários (1)" in page
    assert "data-report-dialog" in page
    assert "1 de 2" in page


def test_visitor_sees_the_post_page_and_is_asked_to_log_in(app, client):
    _, _, post = _client_post(app, client)
    g.pop("_login_user", None)
    page = client.get(f"/publicacoes/{post['id']}").get_data(as_text=True)
    assert "Entre para comentar" in page
    assert "data-report-dialog" not in page
    assert client.post(f"/publicacoes/{post['id']}/comentarios", data={"body": "x"}).status_code == 302


def test_carousel_images_are_not_treated_as_orphans(app, client):
    _, _, post = _client_post(app, client, email="orfas@example.com", images=3)
    from app.services.media_maintenance import orphaned_media_paths, referenced_media_paths

    with app.app_context():
        paths = {item.image_url for item in db.session.get(WorkPost, int(post["id"])).media}
        assert len(paths) == 3
        assert paths <= referenced_media_paths()
        assert not paths & set(orphaned_media_paths())
