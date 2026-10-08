from sqlalchemy import select

from app.extensions import db
from app.models.beauty_graph import Follow
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
    WorkPostStatus,
)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(
            user_id
        )
        session["_fresh"] = True


def _catalog(app):
    with app.app_context():
        user = User(
            name="Cliente Feed",
            email="feed-client@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )

        profile = ClientProfile(
            user=user,
            city="Curitiba",
            state="PR",
        )

        professional = ProfessionalProfile(
            display_name="Marina Feed",
            slug="marina-feed",
            primary_specialty="Hair Colorist",
            city="Curitiba",
            state="PR",
            is_active=True,
            is_verified=True,
        )

        db.session.add_all(
            [
                user,
                profile,
                professional,
            ]
        )
        db.session.flush()

        post = WorkPost(
            author_type=(
                WorkPostAuthorType
                .PROFESSIONAL
            ),
            professional_id=(
                professional.id
            ),
            caption=(
                "Coloração natural "
                "com acabamento editorial."
            ),
            image_url=(
                "img/category-hair.jpg"
            ),
            status=(
                WorkPostStatus.PUBLISHED
            ),
        )

        db.session.add(post)
        db.session.commit()

        return {
            "user_id": user.id,
            "professional_id":
                professional.id,
            "post_id": post.id,
        }


def test_feed_requires_login(
    client,
):
    response = client.get(
        "/feed",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers[
        "Location"
    ]


def test_authenticated_feed_uses_real_work_posts(
    app,
    client,
):
    catalog = _catalog(app)

    _login(
        client,
        catalog["user_id"],
    )

    response = client.get(
        "/feed"
    )

    assert response.status_code == 200

    html = response.get_data(
        as_text=True
    )

    assert (
        "Descubra o que vale viver."
        in html
    )
    assert "Para você" in html
    assert "Seguindo" in html
    assert "Cliente Feed" in html
    assert "Marina Feed" in html
    assert (
        "Coloração natural "
        "com acabamento editorial."
        in html
    )

    assert (
        'data-target-type="work_post"'
        in html
    )
    assert (
        'data-target-type="professional"'
        in html
    )


def test_following_feed_only_shows_followed_profiles(
    app,
    client,
):
    catalog = _catalog(app)

    _login(
        client,
        catalog["user_id"],
    )

    empty = client.get(
        "/feed?mode=following"
    )

    assert empty.status_code == 200
    assert (
        "Você ainda não tem novidades "
        "de quem segue."
        in empty.get_data(
            as_text=True
        )
    )

    with app.app_context():
        db.session.add(
            Follow(
                user_id=catalog[
                    "user_id"
                ],
                target_type="professional",
                professional_id=catalog[
                    "professional_id"
                ],
            )
        )
        db.session.commit()

    populated = client.get(
        "/feed?mode=following"
    )

    assert populated.status_code == 200
    assert (
        "Marina Feed"
        in populated.get_data(
            as_text=True
        )
    )


def test_feed_more_returns_private_html_page(
    app,
    client,
):
    catalog = _catalog(app)

    _login(
        client,
        catalog["user_id"],
    )

    response = client.get(
        "/feed/mais?mode=for-you"
    )

    assert response.status_code == 200
    assert (
        response.headers[
            "Cache-Control"
        ]
        == "private, no-store"
    )

    payload = response.get_json()

    assert "html" in payload
    assert "nextCursor" in payload
    assert "Marina Feed" in payload[
        "html"
    ]


def test_feed_profile_completion_is_contextual(
    app,
    client,
):
    catalog = _catalog(app)

    _login(
        client,
        catalog["user_id"],
    )

    incomplete = client.get(
        "/feed"
    ).get_data(
        as_text=True
    )

    assert (
        "Seu perfil está quase lá."
        in incomplete
    )

    with app.app_context():
        user = db.session.get(
            User,
            catalog["user_id"],
        )
        profile = user.client_profile

        user.email = (
            "feed-client@example.com"
        )
        profile.avatar_url = (
            "img/category-hair.jpg"
        )
        profile.phone = (
            "(41) 99999-9999"
        )

        from datetime import date

        profile.birth_date = date(
            1996,
            5,
            16,
        )
        profile.city = "Curitiba"
        profile.state = "PR"

        db.session.commit()

    complete = client.get(
        "/feed"
    ).get_data(
        as_text=True
    )

    assert (
        "Seu perfil está quase lá."
        not in complete
    )


def test_feed_graph_actions_accept_web_session(
    app,
    client,
):
    catalog = _catalog(app)

    _login(
        client,
        catalog["user_id"],
    )

    follow = client.put(
        (
            "/api/v1/graph/follows/"
            "professional/"
            f"{catalog['professional_id']}"
        )
    )

    saved = client.put(
        (
            "/api/v1/graph/saves/"
            "work_post/"
            f"{catalog['post_id']}"
        )
    )

    assert follow.status_code == 200
    assert saved.status_code == 200

    with app.app_context():
        user = db.session.get(
            User,
            catalog["user_id"],
        )

        assert len(user.follows) == 1
        assert len(user.saves) == 1
