from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.extensions import db
from app.models.profile import ClientProfile
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.user import User, UserRole
from app.services.api_auth import issue_session
from app.services.mobile_onboarding_service import (
    create_professional_draft,
)


BASE = "/api/v1/media/professional"


def _image_bytes(
    image_format="JPEG",
):
    output = BytesIO()

    Image.new(
        "RGB",
        (32, 24),
        (110, 70, 150),
    ).save(
        output,
        format=image_format,
    )

    return output.getvalue()


def _multipart(
    filename="image.jpg",
    *,
    content=None,
    focus_x=None,
    focus_y=None,
    caption=None,
):
    payload = {
        "file": (
            BytesIO(
                content
                if content is not None
                else _image_bytes()
            ),
            filename,
        )
    }

    if focus_x is not None:
        payload["focusX"] = str(
            focus_x
        )

    if focus_y is not None:
        payload["focusY"] = str(
            focus_y
        )

    if caption is not None:
        payload["caption"] = caption

    return payload


def _authenticated_professional(
    app,
    *,
    email="media-api@example.com",
):
    with app.app_context():
        user = User(
            name="Profissional Media",
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )

        db.session.add(user)
        db.session.flush()

        db.session.add(
            ClientProfile(user=user)
        )
        db.session.commit()

        profile = (
            create_professional_draft(
                user=user,
                display_name=(
                    "Profissional Media"
                ),
                primary_specialty=(
                    "Nail Designer"
                ),
                categories=["unhas"],
                city="Curitiba",
                state="PR",
                bio=(
                    "Perfil profissional "
                    "completo para mídia."
                ),
            )
        )

        tokens = issue_session(
            user
        )

        return (
            user.id,
            profile.id,
            {
                "Authorization": (
                    "Bearer "
                    f"{tokens.access_token}"
                )
            },
        )


def _upload_files(app):
    root = Path(
        app.config[
            "UPLOAD_FOLDER"
        ]
    )

    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
    )


def test_media_api_requires_bearer_token(
    client,
):
    response = client.post(
        f"{BASE}/avatar",
        data=_multipart(),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert response.status_code == 401
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "authentication_required"
    )


def test_avatar_upload_persists_real_media_and_focus(
    app,
    client,
):
    _, profile_id, headers = (
        _authenticated_professional(
            app
        )
    )

    response = client.post(
        f"{BASE}/avatar",
        headers=headers,
        data=_multipart(
            focus_x=37,
            focus_y=68,
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload[
        "avatar"
    ]["storedPath"].startswith(
        "uploads/professionals/"
    )
    assert payload[
        "avatar"
    ]["url"].startswith(
        "http://"
    )
    assert payload[
        "avatar"
    ]["focusX"] == 37
    assert payload[
        "avatar"
    ]["focusY"] == 68

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        assert (
            profile.avatar_url
            == payload[
                "avatar"
            ]["storedPath"]
        )
        assert (
            profile.avatar_focus_x
            == 37
        )
        assert (
            profile.avatar_focus_y
            == 68
        )

        saved_files = (
            _upload_files(app)
        )

    assert len(saved_files) == 1


def test_invalid_image_content_is_rejected_without_orphan(
    app,
    client,
):
    _, _, headers = (
        _authenticated_professional(
            app,
            email=(
                "invalid-media@example.com"
            ),
        )
    )

    response = client.post(
        f"{BASE}/avatar",
        headers=headers,
        data=_multipart(
            content=b"not-an-image",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert response.status_code == 400
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "invalid_image"
    )

    with app.app_context():
        assert (
            _upload_files(app)
            == []
        )


def test_replacing_cover_deletes_previous_file_after_commit(
    app,
    client,
):
    _, profile_id, headers = (
        _authenticated_professional(
            app,
            email=(
                "cover-media@example.com"
            ),
        )
    )

    first = client.post(
        f"{BASE}/cover",
        headers=headers,
        data=_multipart(
            filename="first.jpg",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert first.status_code == 200

    first_path = (
        first.get_json()[
            "cover"
        ]["storedPath"]
    )

    second = client.post(
        f"{BASE}/cover",
        headers=headers,
        data=_multipart(
            filename="second.jpg",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert second.status_code == 200

    second_path = (
        second.get_json()[
            "cover"
        ]["storedPath"]
    )

    assert second_path != first_path

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        assert (
            profile.cover_url
            == second_path
        )

        root = Path(
            app.config[
                "UPLOAD_FOLDER"
            ]
        )

        first_file = (
            root
            / first_path.removeprefix(
                "uploads/"
            )
        )
        second_file = (
            root
            / second_path.removeprefix(
                "uploads/"
            )
        )

        assert (
            first_file.exists()
            is False
        )
        assert (
            second_file.exists()
            is True
        )


def test_portfolio_can_upload_reorder_and_resume_from_onboarding(
    app,
    client,
):
    _, _, headers = (
        _authenticated_professional(
            app,
            email=(
                "portfolio-media@example.com"
            ),
        )
    )

    item_ids = []

    for index in range(3):
        response = client.post(
            f"{BASE}/portfolio",
            headers=headers,
            data=_multipart(
                filename=(
                    f"work-{index}.jpg"
                ),
                caption=(
                    f"Trabalho {index}"
                ),
            ),
            content_type=(
                "multipart/form-data"
            ),
        )

        assert (
            response.status_code
            == 201
        )

        item_ids.append(
            response.get_json()[
                "item"
            ]["id"]
        )

    order = list(
        reversed(item_ids)
    )

    reordered = client.put(
        f"{BASE}/portfolio/order",
        headers=headers,
        json={
            "itemIds": order,
        },
    )

    assert reordered.status_code == 200
    assert [
        item["id"]
        for item
        in reordered.get_json()[
            "portfolio"
        ]
    ] == order

    resumed = client.get(
        "/api/v1/onboarding/professional",
        headers=headers,
    )

    assert resumed.status_code == 200

    profile = resumed.get_json()[
        "profile"
    ]

    assert profile[
        "portfolioCount"
    ] == 3
    assert [
        item["id"]
        for item
        in profile["portfolio"]
    ] == order
    assert all(
        item[
            "imageUrl"
        ].startswith("http://")
        for item
        in profile["portfolio"]
    )


def test_deleting_required_portfolio_media_unpublishes_profile(
    app,
    client,
):
    _, profile_id, headers = (
        _authenticated_professional(
            app,
            email=(
                "publish-media@example.com"
            ),
        )
    )

    avatar = client.post(
        f"{BASE}/avatar",
        headers=headers,
        data=_multipart(
            filename="avatar.jpg",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert avatar.status_code == 200

    item_ids = []

    for index in range(3):
        response = client.post(
            f"{BASE}/portfolio",
            headers=headers,
            data=_multipart(
                filename=(
                    f"portfolio-{index}.jpg"
                ),
            ),
            content_type=(
                "multipart/form-data"
            ),
        )

        assert (
            response.status_code
            == 201
        )

        item_ids.append(
            response.get_json()[
                "item"
            ]["id"]
        )

    published = client.post(
        (
            "/api/v1/onboarding/"
            "professional/publish"
        ),
        headers=headers,
    )

    assert published.status_code == 200
    assert (
        published.get_json()[
            "profile"
        ]["isActive"]
        is True
    )

    removed = client.delete(
        (
            f"{BASE}/portfolio/"
            f"{item_ids[0]}"
        ),
        headers=headers,
    )

    assert removed.status_code == 200
    assert (
        removed.get_json()[
            "completion"
        ]["readyToPublish"]
        is False
    )
    assert (
        removed.get_json()[
            "completion"
        ]["isActive"]
        is False
    )

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        assert (
            profile.is_active
            is False
        )
        assert (
            profile.published_at
            is None
        )
        assert (
            profile.onboarding_completed
            is False
        )


def test_user_cannot_delete_another_professionals_portfolio_item(
    app,
    client,
):
    _, _, owner_headers = (
        _authenticated_professional(
            app,
            email="media-owner@example.com",
        )
    )

    uploaded = client.post(
        f"{BASE}/portfolio",
        headers=owner_headers,
        data=_multipart(),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert uploaded.status_code == 201

    item_id = uploaded.get_json()[
        "item"
    ]["id"]

    _, _, other_headers = (
        _authenticated_professional(
            app,
            email="media-other@example.com",
        )
    )

    response = client.delete(
        f"{BASE}/portfolio/{item_id}",
        headers=other_headers,
    )

    assert response.status_code == 404

    with app.app_context():
        item = db.session.scalar(
            select(
                ProfessionalPortfolioItem
            ).where(
                ProfessionalPortfolioItem.id
                == item_id
            )
        )

        assert item is not None


def test_cover_focus_is_persisted_and_resumed(
    app,
    client,
):
    _, profile_id, headers = (
        _authenticated_professional(
            app,
            email=(
                "cover-focus@example.com"
            ),
        )
    )

    uploaded = client.post(
        f"{BASE}/cover",
        headers=headers,
        data=_multipart(
            filename="cover-focus.jpg",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert uploaded.status_code == 200

    focused = client.put(
        f"{BASE}/cover/focus",
        headers=headers,
        json={
            "focusX": 85,
            "focusY": 15,
        },
    )

    assert focused.status_code == 200
    assert focused.get_json() == {
        "focusX": 85,
        "focusY": 15,
    }

    resumed = client.get(
        "/api/v1/onboarding/professional",
        headers=headers,
    )

    assert resumed.status_code == 200

    profile_payload = (
        resumed.get_json()[
            "profile"
        ]
    )

    assert (
        profile_payload[
            "coverFocusX"
        ]
        == 85
    )
    assert (
        profile_payload[
            "coverFocusY"
        ]
        == 15
    )

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        assert (
            profile.cover_focus_x
            == 85
        )
        assert (
            profile.cover_focus_y
            == 15
        )
