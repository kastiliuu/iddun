from decimal import Decimal

from app.extensions import db
from app.models.establishment import (
    Establishment,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import (
    ProfessionalProfile,
)
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
    WorkPostStatus,
)


def _catalog(app):
    with app.app_context():
        professional = (
            ProfessionalProfile(
                display_name=(
                    "Perfil Feed"
                ),
                slug=(
                    "perfil-feed"
                ),
                primary_specialty=(
                    "Nail Designer"
                ),
                bio=(
                    "Perfil público do feed."
                ),
                city="Curitiba",
                state="PR",
                avatar_url=(
                    "uploads/avatar.jpg"
                ),
                cover_url=(
                    "uploads/cover.jpg"
                ),
                is_active=True,
            )
        )

        establishment = (
            Establishment(
                name="Studio Feed",
                slug="studio-feed",
                description=(
                    "Espaço público do feed."
                ),
                category="unhas",
                neighborhood="Batel",
                city="Curitiba",
                state="PR",
                logo_url=(
                    "uploads/logo.jpg"
                ),
                is_active=True,
            )
        )

        db.session.add_all(
            [
                professional,
                establishment,
            ]
        )
        db.session.flush()

        db.session.add(
            ProfessionalEstablishmentMembership(
                professional_id=(
                    professional.id
                ),
                establishment_id=(
                    establishment.id
                ),
                role_name=(
                    "Nail Designer"
                ),
                status=(
                    MembershipStatus.ACTIVE
                ),
                is_primary=True,
            )
        )

        experience = Experience(
            professional_id=(
                professional.id
            ),
            establishment_id=(
                establishment.id
            ),
            title=(
                "Unhas Feed"
            ),
            slug=(
                "unhas-feed"
            ),
            category="unhas",
            short_description=(
                "Serviço real."
            ),
            regular_price=Decimal(
                "150.00"
            ),
            price=Decimal(
                "120.00"
            ),
            duration_minutes=90,
            status=(
                ExperienceStatus.PUBLISHED
            ),
        )
        db.session.add(
            experience
        )
        db.session.flush()

        professional_post = WorkPost(
            author_type=(
                WorkPostAuthorType.PROFESSIONAL
            ),
            professional_id=(
                professional.id
            ),
            experience_id=(
                experience.id
            ),
            caption=(
                "Trabalho do profissional."
            ),
            image_url=(
                "uploads/work-pro.jpg"
            ),
            status=(
                WorkPostStatus.PUBLISHED
            ),
        )

        establishment_post = WorkPost(
            author_type=(
                WorkPostAuthorType.ESTABLISHMENT
            ),
            establishment_id=(
                establishment.id
            ),
            experience_id=(
                experience.id
            ),
            caption=(
                "Trabalho do studio."
            ),
            image_url=(
                "uploads/work-est.jpg"
            ),
            status=(
                WorkPostStatus.PUBLISHED
            ),
        )

        db.session.add_all(
            [
                professional_post,
                establishment_post,
            ]
        )
        db.session.commit()

        return {
            "professionalId":
                professional.id,
            "establishmentId":
                establishment.id,
            "experienceId":
                experience.id,
            "professionalPostId":
                professional_post.id,
            "establishmentPostId":
                establishment_post.id,
        }


def test_professional_public_api_returns_real_services_and_posts(
    app,
    client,
):
    ids = _catalog(app)

    response = client.get(
        "/api/v1/professionals/perfil-feed"
    )

    assert response.status_code == 200
    payload = response.get_json()

    profile = payload[
        "professional"
    ]

    assert profile["id"] == str(
        ids[
            "professionalId"
        ]
    )
    assert (
        profile["routeId"]
        == "perfil-feed"
    )
    assert (
        profile["kind"]
        == "professional"
    )

    assert len(
        payload["services"]
    ) == 1
    service = payload[
        "services"
    ][0]
    assert (
        service["id"]
        == "unhas-feed"
    )
    assert (
        service["authorId"]
        == str(
            ids[
                "professionalId"
            ]
        )
    )

    assert len(
        payload["posts"]
    ) == 1
    post = payload[
        "posts"
    ][0]
    assert post["id"] == str(
        ids[
            "professionalPostId"
        ]
    )
    assert (
        post["author"][
            "routeId"
        ]
        == "perfil-feed"
    )
    assert (
        post["service"][
            "id"
        ]
        == "unhas-feed"
    )


def test_establishment_public_api_returns_real_team_services_and_posts(
    app,
    client,
):
    ids = _catalog(app)

    response = client.get(
        "/api/v1/establishments/studio-feed"
    )

    assert response.status_code == 200
    payload = response.get_json()

    establishment = payload[
        "establishment"
    ]

    assert establishment[
        "id"
    ] == str(
        ids[
            "establishmentId"
        ]
    )
    assert (
        establishment[
            "routeId"
        ]
        == "studio-feed"
    )

    assert len(
        payload["team"]
    ) == 1
    assert (
        payload["team"][0][
            "routeId"
        ]
        == "perfil-feed"
    )

    assert len(
        payload["services"]
    ) == 1
    assert (
        payload["services"][0][
            "id"
        ]
        == "unhas-feed"
    )

    assert len(
        payload["posts"]
    ) == 1
    assert payload[
        "posts"
    ][0]["id"] == str(
        ids[
            "establishmentPostId"
        ]
    )


def test_feed_uses_numeric_social_id_and_slug_route_id(
    app,
    client,
):
    ids = _catalog(app)

    response = client.get(
        "/api/v1/feed"
    )

    assert response.status_code == 200
    items = response.get_json()[
        "items"
    ]

    professional = next(
        item
        for item in items
        if item[
            "authorKind"
        ] == "professional"
    )

    assert professional[
        "author"
    ]["id"] == str(
        ids[
            "professionalId"
        ]
    )
    assert (
        professional[
            "author"
        ]["routeId"]
        == "perfil-feed"
    )
    assert (
        professional[
            "serviceId"
        ]
        == "unhas-feed"
    )


def test_experience_contract_exposes_slug_and_numeric_entity_id(
    app,
    client,
):
    ids = _catalog(app)

    response = client.get(
        "/api/v1/experiences/unhas-feed"
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["id"] == (
        "unhas-feed"
    )
    assert payload["slug"] == (
        "unhas-feed"
    )
    assert payload[
        "entityId"
    ] == ids[
        "experienceId"
    ]
