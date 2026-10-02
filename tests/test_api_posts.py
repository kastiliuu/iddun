from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    FollowTarget,
)
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.models.work_post import (
    WorkPost,
    WorkPostStatus,
)
from app.services.api_auth import issue_session


FEED = "/api/v1/feed"
POSTS = "/api/v1/posts"


def _image_bytes():
    output = BytesIO()
    Image.new(
        "RGB",
        (48, 36),
        (90, 40, 130),
    ).save(
        output,
        format="JPEG",
    )
    return output.getvalue()


def _multipart(
    *,
    author_type="professional",
    author_id=None,
    experience_id=None,
    caption="Resultado incrível.",
    status="published",
):
    data = {
        "file": (
            BytesIO(
                _image_bytes()
            ),
            "work.jpg",
        ),
        "authorType":
            author_type,
        "caption":
            caption,
        "status":
            status,
    }

    if author_id is not None:
        data["authorId"] = str(
            author_id
        )

    if experience_id is not None:
        data[
            "experienceId"
        ] = str(
            experience_id
        )

    return data


def _user(
    app,
    *,
    email,
    with_professional=True,
):
    with app.app_context():
        user = User(
            name="Creator Test",
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            ClientProfile(
                user=user
            )
        )

        profile = None

        if with_professional:
            profile = (
                ProfessionalProfile(
                    user_id=user.id,
                    display_name=(
                        "Creator "
                        + str(
                            user.id
                        )
                    ),
                    slug=(
                        "creator-"
                        + str(
                            user.id
                        )
                    ),
                    primary_specialty=(
                        "Nail Designer"
                    ),
                    bio=(
                        "Perfil público para creator."
                    ),
                    city="Curitiba",
                    state="PR",
                    avatar_url=(
                        "uploads/avatar.jpg"
                    ),
                    is_active=True,
                )
            )
            db.session.add(
                profile
            )

        db.session.commit()

        tokens = issue_session(
            user
        )

        return (
            user.id,
            (
                profile.id
                if profile
                else None
            ),
            {
                "Authorization": (
                    "Bearer "
                    f"{tokens.access_token}"
                )
            },
        )


def _experience(
    app,
    *,
    professional_id,
    establishment_id=None,
    slug,
):
    with app.app_context():
        item = Experience(
            professional_id=(
                professional_id
            ),
            establishment_id=(
                establishment_id
            ),
            title=(
                "Experiência "
                + slug
            ),
            slug=slug,
            category="unhas",
            short_description=(
                "Serviço publicado."
            ),
            regular_price=Decimal(
                "150.00"
            ),
            price=Decimal(
                "120.00"
            ),
            duration_minutes=60,
            status=(
                ExperienceStatus.PUBLISHED
            ),
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def _upload_files(app):
    root = Path(
        app.config[
            "UPLOAD_FOLDER"
        ]
    )

    if not root.exists():
        return []

    return [
        path
        for path in root.rglob(
            "*"
        )
        if path.is_file()
    ]


def test_create_post_requires_authentication(
    client,
):
    response = client.post(
        POSTS,
        data=_multipart(),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert response.status_code == 401


def test_professional_can_publish_real_post_linked_to_own_experience(
    app,
    client,
):
    _, profile_id, headers = (
        _user(
            app,
            email=(
                "creator-post@example.com"
            ),
        )
    )
    experience_id = _experience(
        app,
        professional_id=profile_id,
        slug="creator-post-service",
    )

    created = client.post(
        POSTS,
        headers=headers,
        data=_multipart(
            author_id=profile_id,
            experience_id=(
                experience_id
            ),
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert created.status_code == 201
    post = created.get_json()[
        "post"
    ]

    assert post["author"][
        "id"
    ] == str(profile_id)
    assert post["author"][
        "kind"
    ] == "professional"
    assert post[
        "experienceId"
    ] == str(
        experience_id
    )
    assert post["service"][
        "id"
    ] == "creator-post-service"
    assert (
        post["serviceId"]
        == "creator-post-service"
    )
    assert post["image"].startswith(
        "http://"
    )
    assert post["deepLink"] == (
        "iddun://post/"
        + post["id"]
    )

    public_feed = client.get(
        FEED
    )

    assert (
        public_feed.status_code
        == 200
    )
    assert [
        item["id"]
        for item
        in public_feed.get_json()[
            "items"
        ]
    ] == [
        post["id"]
    ]

    detail = client.get(
        POSTS
        + "/"
        + post["id"]
    )

    assert detail.status_code == 200
    assert (
        detail.get_json()["id"]
        == post["id"]
    )


def test_professional_cannot_link_another_professionals_experience(
    app,
    client,
):
    _, first_profile, headers = (
        _user(
            app,
            email="first-creator@example.com",
        )
    )
    _, second_profile, _ = (
        _user(
            app,
            email="second-creator@example.com",
        )
    )

    foreign_experience = (
        _experience(
            app,
            professional_id=(
                second_profile
            ),
            slug=(
                "foreign-creator-service"
            ),
        )
    )

    response = client.post(
        POSTS,
        headers=headers,
        data=_multipart(
            author_id=(
                first_profile
            ),
            experience_id=(
                foreign_experience
            ),
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
        == "invalid_post"
    )

    with app.app_context():
        assert (
            db.session.scalar(
                select(
                    WorkPost.id
                )
            )
            is None
        )

    assert _upload_files(
        app
    ) == []


def test_establishment_access_can_publish_as_establishment(
    app,
    client,
):
    user_id, _, headers = (
        _user(
            app,
            email=(
                "establishment-creator@example.com"
            ),
            with_professional=False,
        )
    )

    with app.app_context():
        establishment = (
            Establishment(
                name="Studio Creator",
                slug="studio-creator",
                description=(
                    "Espaço público."
                ),
                category="unhas",
                city="Curitiba",
                state="PR",
                is_active=True,
            )
        )
        db.session.add(
            establishment
        )
        db.session.flush()
        db.session.add(
            EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=(
                    establishment.id
                ),
                role=(
                    EstablishmentAccessRole.OWNER
                ),
                status=(
                    EstablishmentAccessStatus.ACTIVE
                ),
            )
        )
        db.session.commit()
        establishment_id = (
            establishment.id
        )

    response = client.post(
        POSTS,
        headers=headers,
        data=_multipart(
            author_type=(
                "establishment"
            ),
            author_id=(
                establishment_id
            ),
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    assert response.status_code == 201
    payload = response.get_json()[
        "post"
    ]
    assert payload["author"][
        "kind"
    ] == "establishment"
    assert payload["author"][
        "id"
    ] == str(
        establishment_id
    )


def test_following_feed_only_contains_followed_authors(
    app,
    client,
):
    user_id, _, viewer_headers = (
        _user(
            app,
            email=(
                "feed-viewer@example.com"
            ),
            with_professional=False,
        )
    )
    _, followed_id, followed_headers = (
        _user(
            app,
            email=(
                "followed-creator@example.com"
            ),
        )
    )
    _, other_id, other_headers = (
        _user(
            app,
            email=(
                "other-creator@example.com"
            ),
        )
    )

    followed_post = client.post(
        POSTS,
        headers=followed_headers,
        data=_multipart(
            author_id=followed_id,
            caption="Seguido",
        ),
        content_type=(
            "multipart/form-data"
        ),
    ).get_json()["post"]

    client.post(
        POSTS,
        headers=other_headers,
        data=_multipart(
            author_id=other_id,
            caption="Outro",
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    with app.app_context():
        db.session.add(
            Follow(
                user_id=user_id,
                target_type=(
                    FollowTarget.PROFESSIONAL
                ),
                professional_id=(
                    followed_id
                ),
            )
        )
        db.session.commit()

    following = client.get(
        FEED
        + "?mode=following",
        headers=viewer_headers,
    )

    assert following.status_code == 200
    items = following.get_json()[
        "items"
    ]
    assert [
        item["id"]
        for item in items
    ] == [
        followed_post[
            "id"
        ]
    ]

    guest = client.get(
        FEED
        + "?mode=following"
    )

    assert guest.status_code == 401


def test_post_can_be_edited_archived_and_remains_visible_to_owner(
    app,
    client,
):
    _, profile_id, headers = (
        _user(
            app,
            email=(
                "edit-post@example.com"
            ),
        )
    )

    created = client.post(
        POSTS,
        headers=headers,
        data=_multipart(
            author_id=profile_id,
        ),
        content_type=(
            "multipart/form-data"
        ),
    ).get_json()["post"]

    edited = client.put(
        POSTS
        + "/"
        + created["id"],
        headers=headers,
        json={
            "caption":
                "Legenda editada.",
            "status":
                WorkPostStatus.ARCHIVED,
        },
    )

    assert edited.status_code == 200
    assert edited.get_json()[
        "post"
    ]["caption"] == (
        "Legenda editada."
    )
    assert edited.get_json()[
        "post"
    ]["status"] == (
        WorkPostStatus.ARCHIVED
    )

    assert client.get(
        POSTS
        + "/"
        + created["id"]
    ).status_code == 404

    owner_detail = client.get(
        POSTS
        + "/"
        + created["id"],
        headers=headers,
    )

    assert (
        owner_detail.status_code
        == 200
    )
    assert owner_detail.get_json()[
        "status"
    ] == WorkPostStatus.ARCHIVED


def test_delete_post_removes_database_row_and_media(
    app,
    client,
):
    _, profile_id, headers = (
        _user(
            app,
            email=(
                "delete-post@example.com"
            ),
        )
    )

    created = client.post(
        POSTS,
        headers=headers,
        data=_multipart(
            author_id=profile_id,
        ),
        content_type=(
            "multipart/form-data"
        ),
    ).get_json()["post"]

    assert len(
        _upload_files(app)
    ) == 1

    deleted = client.delete(
        POSTS
        + "/"
        + created["id"],
        headers=headers,
    )

    assert deleted.status_code == 200
    assert (
        deleted.get_json()[
            "success"
        ]
        is True
    )

    with app.app_context():
        assert db.session.get(
            WorkPost,
            int(
                created["id"]
            ),
        ) is None

    assert _upload_files(
        app
    ) == []


def test_feed_cursor_is_stable_and_does_not_repeat_items(
    app,
    client,
):
    _, profile_id, headers = (
        _user(
            app,
            email=(
                "cursor-post@example.com"
            ),
        )
    )

    created_ids = []

    for index in range(3):
        response = client.post(
            POSTS,
            headers=headers,
            data=_multipart(
                author_id=profile_id,
                caption=(
                    "Post "
                    + str(index)
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
        created_ids.append(
            response.get_json()[
                "post"
            ]["id"]
        )

    first = client.get(
        FEED
        + "?limit=2"
    ).get_json()

    assert len(
        first["items"]
    ) == 2
    assert first[
        "nextCursor"
    ]

    second = client.get(
        FEED
        + "?limit=2&cursor="
        + first[
            "nextCursor"
        ]
    ).get_json()

    first_ids = {
        item["id"]
        for item
        in first["items"]
    }
    second_ids = {
        item["id"]
        for item
        in second["items"]
    }

    assert (
        first_ids
        & second_ids
    ) == set()
    assert (
        first_ids
        | second_ids
    ) == set(
        created_ids
    )


def test_creator_options_only_return_authors_and_services_owned_by_account(
    app,
    client,
):
    user_id, profile_id, headers = (
        _user(
            app,
            email=(
                "creator-options@example.com"
            ),
        )
    )

    professional_experience = (
        _experience(
            app,
            professional_id=profile_id,
            slug=(
                "creator-options-pro"
            ),
        )
    )

    with app.app_context():
        establishment = Establishment(
            name="Studio Options",
            slug="studio-options",
            description=(
                "Studio público."
            ),
            category="unhas",
            city="Curitiba",
            state="PR",
            is_active=True,
        )
        db.session.add(
            establishment
        )
        db.session.flush()
        db.session.add(
            EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=(
                    establishment.id
                ),
                role=(
                    EstablishmentAccessRole.OWNER
                ),
                status=(
                    EstablishmentAccessStatus.ACTIVE
                ),
            )
        )
        db.session.commit()
        establishment_id = (
            establishment.id
        )

    establishment_experience = (
        _experience(
            app,
            professional_id=profile_id,
            establishment_id=(
                establishment_id
            ),
            slug=(
                "creator-options-est"
            ),
        )
    )

    response = client.get(
        POSTS
        + "/options",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert {
        (
            item["type"],
            item["id"],
        )
        for item
        in payload["authors"]
    } == {
        (
            "professional",
            profile_id,
        ),
        (
            "establishment",
            establishment_id,
        ),
    }

    assert {
        item["id"]
        for item
        in payload[
            "experiences"
        ]
    } == {
        professional_experience,
        establishment_experience,
    }


def test_real_work_post_can_be_saved_in_beauty_graph(
    app,
    client,
):
    _, profile_id, creator_headers = (
        _user(
            app,
            email=(
                "saved-post-creator@example.com"
            ),
        )
    )
    _, _, viewer_headers = (
        _user(
            app,
            email=(
                "saved-post-viewer@example.com"
            ),
            with_professional=False,
        )
    )

    created = client.post(
        POSTS,
        headers=creator_headers,
        data=_multipart(
            author_id=profile_id,
        ),
        content_type=(
            "multipart/form-data"
        ),
    )

    post_id = int(
        created.get_json()[
            "post"
        ]["id"]
    )

    saved = client.put(
        (
            "/api/v1/graph/saves/"
            "work_post/"
            f"{post_id}"
        ),
        headers=viewer_headers,
    )

    assert saved.status_code == 200
    assert saved.get_json()[
        "saved"
    ] is True

    state = client.get(
        "/api/v1/graph",
        headers=viewer_headers,
    ).get_json()

    assert state["saves"] == [
        {
            "targetType":
                "work_post",
            "targetId":
                post_id,
        }
    ]


def test_another_account_cannot_edit_or_delete_post(
    app,
    client,
):
    _, profile_id, owner_headers = (
        _user(
            app,
            email=(
                "post-owner@example.com"
            ),
        )
    )
    _, _, other_headers = (
        _user(
            app,
            email=(
                "post-intruder@example.com"
            ),
        )
    )

    created = client.post(
        POSTS,
        headers=owner_headers,
        data=_multipart(
            author_id=profile_id,
        ),
        content_type=(
            "multipart/form-data"
        ),
    ).get_json()["post"]

    edited = client.put(
        POSTS
        + "/"
        + created["id"],
        headers=other_headers,
        json={
            "caption":
                "Tentativa indevida",
        },
    )

    deleted = client.delete(
        POSTS
        + "/"
        + created["id"],
        headers=other_headers,
    )

    assert edited.status_code == 400
    assert deleted.status_code == 404

    detail = client.get(
        POSTS
        + "/"
        + created["id"],
    )

    assert detail.status_code == 200
    assert detail.get_json()[
        "caption"
    ] == "Resultado incrível."
