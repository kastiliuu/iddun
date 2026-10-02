from flask import Blueprint
from sqlalchemy import select

from app.extensions import db
from app.models.work_post import (
    WorkPost,
    WorkPostStatus,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.feed_service import (
    serialize_work_post,
)
from app.services.media_storage import (
    resolve_media_url,
)
from app.services.professional_service import (
    get_establishment_public_view,
    get_professional_public_view,
)


api_profiles_bp = Blueprint(
    "api_profiles",
    __name__,
    url_prefix="/api/v1",
)


def _media(value):
    if not value:
        return None

    return resolve_media_url(
        value,
        external=True,
    )


def _rating(reputation):
    value = reputation.get(
        "average"
    )

    return (
        float(value)
        if value is not None
        else 0.0
    )


def _service_payload(
    item,
    *,
    author_kind,
    author_id,
):
    location_parts = []

    if item.establishment is not None:
        if item.establishment.neighborhood:
            location_parts.append(
                item.establishment.neighborhood
            )
        if item.establishment.city:
            location_parts.append(
                item.establishment.city
            )
    elif item.professional is not None:
        if item.professional.city:
            location_parts.append(
                item.professional.city
            )
        if item.professional.state:
            location_parts.append(
                item.professional.state
            )

    return {
        "id": item.slug,
        "authorId": str(
            author_id
        ),
        "authorKind": author_kind,
        "name": item.title,
        "category": item.category,
        "description": (
            item.description
            or item.short_description
        ),
        "image": _media(
            item.image_url
            or "img/exp-hair.jpg"
        ),
        "durationMinutes": (
            item.duration_minutes
        ),
        "price": float(
            item.price
        ),
        "location": (
            " · ".join(
                location_parts
            )
            or "Brasil"
        ),
        "availabilityLabel": None,
        "availableSlots": [],
    }


def _posts(
    *,
    professional_id=None,
    establishment_id=None,
):
    query = select(
        WorkPost
    ).where(
        WorkPost.status
        == WorkPostStatus.PUBLISHED,
        WorkPost.published_at.is_not(
            None
        ),
    )

    if professional_id is not None:
        query = query.where(
            WorkPost.professional_id
            == professional_id
        )

    if establishment_id is not None:
        query = query.where(
            WorkPost.establishment_id
            == establishment_id
        )

    return [
        serialize_work_post(
            item
        )
        for item in db.session.scalars(
            query.order_by(
                WorkPost.id.desc()
            )
        ).all()
    ]


@api_profiles_bp.get(
    "/professionals/<slug>"
)
def professional_profile(
    slug,
):
    view = (
        get_professional_public_view(
            slug
        )
    )

    if (
        view is None
        or view.get(
            "source"
        )
        != "database"
    ):
        return api_error(
            "professional_not_found",
            "Profissional não encontrado.",
            404,
        )

    profile = view[
        "profile"
    ]
    reputation = view[
        "reputation"
    ]

    professional = {
        "id": str(
            profile.id
        ),
        "routeId": profile.slug,
        "kind": "professional",
        "name": profile.display_name,
        "avatar": _media(
            profile.avatar_url
            or "img/category-hair.jpg"
        ),
        "cover": _media(
            profile.cover_url
        ),
        "specialty": (
            profile.primary_specialty
            or "Profissional de beleza"
        ),
        "location": (
            " · ".join(
                part
                for part in (
                    profile.city,
                    profile.state,
                )
                if part
            )
            or "Brasil"
        ),
        "rating": _rating(
            reputation
        ),
        "reviewsCount": (
            reputation[
                "count"
            ]
        ),
        "bio": profile.bio,
        "categories": (
            profile.specialties
        ),
    }

    services = [
        _service_payload(
            item,
            author_kind=(
                "professional"
            ),
            author_id=profile.id,
        )
        for item in view[
            "experiences"
        ]
    ]

    return api_json(
        {
            "professional":
                professional,
            "services":
                services,
            "posts":
                _posts(
                    professional_id=(
                        profile.id
                    )
                ),
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_profiles_bp.get(
    "/establishments/<slug>"
)
def establishment_profile(
    slug,
):
    view = (
        get_establishment_public_view(
            slug
        )
    )

    if view is None:
        return api_error(
            "establishment_not_found",
            "Estabelecimento não encontrado.",
            404,
        )

    establishment = view[
        "establishment"
    ]
    reputation = view[
        "reputation"
    ]

    location = (
        " · ".join(
            part
            for part in (
                establishment.neighborhood,
                establishment.city,
                establishment.state,
            )
            if part
        )
        or "Brasil"
    )

    profile = {
        "id": str(
            establishment.id
        ),
        "routeId":
            establishment.slug,
        "kind":
            "establishment",
        "name":
            establishment.name,
        "avatar": _media(
            establishment.logo_url
            or "img/category-hair.jpg"
        ),
        "cover": _media(
            establishment.cover_url
        ),
        "specialty": (
            establishment.category
            or "Espaço de beleza"
        ),
        "location": location,
        "rating": _rating(
            reputation
        ),
        "reviewsCount": (
            reputation[
                "count"
            ]
        ),
        "bio":
            establishment.description,
        "categories": [
            establishment.category
        ] if establishment.category
        else [],
    }

    services = [
        _service_payload(
            item,
            author_kind=(
                "establishment"
            ),
            author_id=(
                establishment.id
            ),
        )
        for item in view[
            "experiences"
        ]
    ]

    team = []

    for membership in view[
        "team"
    ]:
        professional = (
            membership.professional
        )
        professional_view = (
            get_professional_public_view(
                professional.slug
            )
        )

        if (
            professional_view is None
            or professional_view.get(
                "source"
            )
            != "database"
        ):
            continue

        professional_rep = (
            professional_view[
                "reputation"
            ]
        )

        team.append(
            {
                "id": str(
                    professional.id
                ),
                "routeId":
                    professional.slug,
                "kind":
                    "professional",
                "name":
                    professional.display_name,
                "avatar": _media(
                    professional.avatar_url
                    or "img/category-hair.jpg"
                ),
                "cover": _media(
                    professional.cover_url
                ),
                "specialty": (
                    professional.primary_specialty
                    or "Profissional de beleza"
                ),
                "location": (
                    " · ".join(
                        part
                        for part in (
                            professional.city,
                            professional.state,
                        )
                        if part
                    )
                    or "Brasil"
                ),
                "rating": _rating(
                    professional_rep
                ),
                "reviewsCount": (
                    professional_rep[
                        "count"
                    ]
                ),
                "bio":
                    professional.bio,
                "categories":
                    professional.specialties,
            }
        )

    return api_json(
        {
            "establishment":
                profile,
            "services":
                services,
            "posts":
                _posts(
                    establishment_id=(
                        establishment.id
                    )
                ),
            "team":
                team,
        },
        cache_control=(
            "public, max-age=30"
        ),
    )
