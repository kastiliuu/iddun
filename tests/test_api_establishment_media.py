"""D-ONB-07 — fotos do estabelecimento pela API do app (PR 4 do onboarding).

Mesmo padrão das fotos do Profissional: só o proprietário ativo, 5 MB,
tipo verificado pelo conteúdo, metadados removidos; fotos são opcionais e
não mudam a publicação (DEC-ID-101).
"""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.extensions import db
from app.models.establishment import Establishment, EstablishmentGalleryItem
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session
from app.services.mobile_onboarding_service import create_establishment_draft

BASE = "/api/v1/media/establishments"


def _image_bytes(image_format="JPEG"):
    output = BytesIO()
    Image.new("RGB", (32, 24), (110, 70, 150)).save(output, format=image_format)
    return output.getvalue()


def _file(filename="image.jpg", content=None, **form):
    payload = {"file": (BytesIO(content if content is not None else _image_bytes()), filename)}
    payload.update({key: str(value) for key, value in form.items()})
    return payload


def _owner(app, email="dona-midia@example.com", name="Studio Mídia"):
    with app.app_context():
        user = User(name="Dona Mídia", email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        db.session.commit()
        establishment = create_establishment_draft(
            user=user, name=name, category="salao", city="Curitiba", state="PR",
        )
        token = issue_session(user).access_token
        return establishment.id, {"Authorization": f"Bearer {token}"}


def _files(app):
    root = Path(app.config["UPLOAD_FOLDER"])
    return sorted(path for path in root.rglob("*") if path.is_file()) if root.exists() else []


def test_requires_token_and_owner(app, client):
    establishment_id, _ = _owner(app)
    _, other = _owner(app, "outra@example.com", "Outro Studio")

    assert client.post(f"{BASE}/{establishment_id}/logo", data=_file(),
                       content_type="multipart/form-data").status_code == 401
    for method, path in (
        ("post", f"{BASE}/{establishment_id}/logo"),
        ("post", f"{BASE}/{establishment_id}/cover"),
        ("post", f"{BASE}/{establishment_id}/gallery"),
    ):
        response = getattr(client, method)(
            path, headers=other, data=_file(), content_type="multipart/form-data",
        )
        assert response.status_code == 404, path
        assert response.get_json()["error"]["code"] == "establishment_not_found"
    assert client.get(f"{BASE}/{establishment_id}", headers=other).status_code == 404
    assert client.get(f"{BASE}/999999", headers=other).status_code == 404
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        assert item.logo_url is None and item.cover_url is None
        assert item.gallery_items == []
    assert _files(app) == []


def test_logo_and_cover_upload_save_focus_and_keep_publication_state(app, client):
    establishment_id, headers = _owner(app)

    logo = client.post(f"{BASE}/{establishment_id}/logo", headers=headers,
                       data=_file("logo.png", _image_bytes("PNG"), focusX=30, focusY=70),
                       content_type="multipart/form-data")
    assert logo.status_code == 200
    media = logo.get_json()["media"]
    assert media["logo"]["focusX"] == 30 and media["logo"]["focusY"] == 70
    assert media["isActive"] is False

    cover = client.post(f"{BASE}/{establishment_id}/cover", headers=headers,
                        data=_file("capa.jpg"), content_type="multipart/form-data")
    assert cover.status_code == 200
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        assert item.logo_url and item.cover_url
        assert (item.logo_focus_x, item.logo_focus_y) == (30, 70)
        assert item.is_active is False and item.published_at is None
    assert len(_files(app)) == 2


def test_replacing_logo_deletes_previous_file(app, client):
    establishment_id, headers = _owner(app)
    client.post(f"{BASE}/{establishment_id}/logo", headers=headers,
                data=_file(), content_type="multipart/form-data")
    first = _files(app)
    client.post(f"{BASE}/{establishment_id}/logo", headers=headers,
                data=_file(), content_type="multipart/form-data")
    second = _files(app)
    assert len(first) == 1 and len(second) == 1
    assert first != second


def test_invalid_image_is_rejected_without_leftovers(app, client):
    establishment_id, headers = _owner(app)

    fake = client.post(f"{BASE}/{establishment_id}/logo", headers=headers,
                       data=_file("logo.jpg", b"nao-e-imagem"), content_type="multipart/form-data")
    assert fake.status_code == 400
    assert fake.get_json()["error"]["code"] == "invalid_image"

    mismatch = client.post(f"{BASE}/{establishment_id}/gallery", headers=headers,
                           data=_file("foto.jpg", _image_bytes("PNG")), content_type="multipart/form-data")
    assert mismatch.status_code == 400

    no_file = client.post(f"{BASE}/{establishment_id}/cover", headers=headers,
                          data={}, content_type="multipart/form-data")
    assert no_file.status_code == 400

    as_json = client.post(f"{BASE}/{establishment_id}/cover", headers=headers, json={})
    assert as_json.status_code == 415
    assert _files(app) == []


def test_gallery_upload_limit_and_delete(app, client):
    establishment_id, headers = _owner(app)
    for index in range(10):
        response = client.post(f"{BASE}/{establishment_id}/gallery", headers=headers,
                               data=_file(f"{index}.jpg", caption=f"Foto {index}"),
                               content_type="multipart/form-data")
        assert response.status_code == 201
    eleventh = client.post(f"{BASE}/{establishment_id}/gallery", headers=headers,
                           data=_file("11.jpg"), content_type="multipart/form-data")
    assert eleventh.status_code == 409
    assert eleventh.get_json()["error"]["code"] == "gallery_limit_reached"
    assert len(_files(app)) == 10

    with app.app_context():
        first = db.session.query(EstablishmentGalleryItem).order_by(EstablishmentGalleryItem.id).first()
        first_id = first.id
    removed = client.delete(f"{BASE}/{establishment_id}/gallery/{first_id}", headers=headers)
    assert removed.status_code == 200
    gallery = removed.get_json()["media"]["gallery"]
    assert len(gallery) == 9
    assert [item["sortOrder"] for item in gallery] == list(range(9))
    assert len(_files(app)) == 9


def test_cannot_delete_another_establishments_gallery_item(app, client):
    establishment_id, headers = _owner(app)
    other_id, other = _owner(app, "outra-galeria@example.com", "Outro Studio")
    client.post(f"{BASE}/{establishment_id}/gallery", headers=headers,
                data=_file(), content_type="multipart/form-data")
    with app.app_context():
        item_id = db.session.query(EstablishmentGalleryItem).first().id

    assert client.delete(f"{BASE}/{establishment_id}/gallery/{item_id}", headers=other).status_code == 404
    assert client.delete(f"{BASE}/{other_id}/gallery/{item_id}", headers=other).status_code == 404
    with app.app_context():
        assert db.session.get(EstablishmentGalleryItem, item_id) is not None


def test_media_on_published_establishment_keeps_it_published(app, client):
    establishment_id, headers = _owner(app)
    when = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        item.is_active = True
        item.published_at = when
        db.session.commit()

    client.post(f"{BASE}/{establishment_id}/gallery", headers=headers,
                data=_file(), content_type="multipart/form-data")
    with app.app_context():
        gallery_id = db.session.query(EstablishmentGalleryItem).first().id
    client.delete(f"{BASE}/{establishment_id}/gallery/{gallery_id}", headers=headers)

    with app.app_context():
        item = db.session.get(Establishment, establishment_id)
        assert item.is_active is True
        assert item.published_at.replace(tzinfo=None) == when.replace(tzinfo=None)
