from flask import Blueprint, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.work_post import (
    WorkPost,
    WorkPostStatus,
)
from app.services.api_contract import (
    api_error,
    api_json,
    pagination_payload,
)
from app.services.feed_service import (
    serialize_work_post,
)
from app.services.media_storage import (
    resolve_media_url,
)
from app.services.public_eligibility import (
    public_establishments_query,
    public_professionals_query,
)
from app.services.reputation_service import reputation_summary
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


def _query_int(
    name,
    default,
    *,
    minimum,
    maximum,
):
    raw = request.args.get(name)

    if raw in (None, ""):
        return default, None

    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, api_error(
            "invalid_query_parameter",
            f"Parâmetro de consulta inválido: {name}.",
            400,
        )

    if not minimum <= value <= maximum:
        return None, api_error(
            "invalid_query_parameter",
            f"Parâmetro de consulta inválido: {name}.",
            400,
        )

    return value, None


def _query_text(
    name,
    *,
    maximum=120,
):
    value = (
        request.args.get(name)
        or ""
    ).strip()

    if len(value) > maximum:
        return None, api_error(
            "invalid_query_parameter",
            f"Parâmetro de consulta inválido: {name}.",
            400,
        )

    return value, None


def _normalized_sql(expression):
    value = func.lower(
        func.coalesce(
            expression,
            "",
        )
    )

    replacements = (
        ("á", "a"),
        ("à", "a"),
        ("ã", "a"),
        ("â", "a"),
        ("é", "e"),
        ("ê", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ô", "o"),
        ("õ", "o"),
        ("ú", "u"),
        ("ç", "c"),
    )

    for source, target in replacements:
        value = func.replace(
            value,
            source,
            target,
        )
        value = func.replace(
            value,
            source.upper(),
            target,
        )

    return value


def _profile_payload(
    item,
    *,
    kind,
):
    reputation = reputation_summary(
        item.reviews_received
    )

    if kind == "professional":
        name = item.display_name
        route_id = item.slug
        avatar = (
            item.avatar_url
            or "img/category-hair.jpg"
        )
        cover = item.cover_url
        specialty = (
            item.primary_specialty
            or "Profissional de beleza"
        )
        categories = item.specialties
        location_parts = [
            item.city,
            item.state,
        ]
    else:
        name = item.name
        route_id = item.slug
        avatar = (
            item.logo_url
            or "img/category-hair.jpg"
        )
        cover = item.cover_url
        specialty = (
            item.category
            or "Espaço de beleza"
        )
        categories = (
            [item.category]
            if item.category
            else []
        )
        location_parts = [
            item.neighborhood,
            item.city,
            item.state,
        ]

    return {
        "id": str(item.id),
        "routeId": route_id,
        "kind": kind,
        "name": name,
        "avatar": _media(avatar),
        "cover": _media(cover),
        "specialty": specialty,
        "location": (
            " · ".join(
                part
                for part
                in location_parts
                if part
            )
            or "Brasil"
        ),
        "rating": _rating(
            reputation
        ),
        "reviewsCount": (
            reputation["count"]
        ),
        "bio": item.bio
        if kind == "professional"
        else item.description,
        "categories": categories,
    }


def _list_profiles(
    *,
    kind,
    search,
    category,
    city,
    offset,
    limit,
):
    if kind == "professional":
        model = ProfessionalProfile
        query = (
            public_professionals_query()
            .options(
                selectinload(
                    ProfessionalProfile
                    .reviews_received
                )
            )
        )
        searchable = [
            model.display_name,
            model.primary_specialty,
            model.specialties_text,
            model.city,
        ]
        category_columns = [
            model.primary_specialty,
            model.specialties_text,
        ]
        city_column = model.city
        order_columns = [
            model.is_verified.desc(),
            model.created_at.desc(),
            model.id.desc(),
        ]
    else:
        model = Establishment
        query = (
            public_establishments_query()
            .options(
                selectinload(
                    Establishment
                    .reviews_received
                )
            )
        )
        searchable = [
            model.name,
            model.category,
            model.description,
            model.neighborhood,
            model.city,
        ]
        category_columns = [
            model.category,
        ]
        city_column = model.city
        order_columns = [
            model.is_verified.desc(),
            model.created_at.desc(),
            model.id.desc(),
        ]

    if search:
        needle = (
            f"%{search.lower()}%"
        )
        query = query.where(
            or_(
                *[
                    _normalized_sql(
                        column
                    ).like(needle)
                    for column
                    in searchable
                ]
            )
        )

    if category:
        needle = (
            f"%{category.lower()}%"
        )
        query = query.where(
            or_(
                *[
                    _normalized_sql(
                        column
                    ).like(needle)
                    for column
                    in category_columns
                ]
            )
        )

    if city:
        query = query.where(
            _normalized_sql(
                city_column
            ).like(
                f"%{city.lower()}%"
            )
        )

    filtered = query.order_by(
        *order_columns
    )
    items = db.session.scalars(
        filtered
        .offset(offset)
        .limit(limit)
    ).all()

    count_query = select(
        func.count()
    ).select_from(
        filtered
        .order_by(None)
        .subquery()
    )
    total = (
        db.session.scalar(
            count_query
        )
        or 0
    )

    return items, total


def _profiles_endpoint(kind):
    offset, error = _query_int(
        "offset",
        0,
        minimum=0,
        maximum=1_000_000,
    )
    if error is not None:
        return error

    limit, error = _query_int(
        "limit",
        20,
        minimum=1,
        maximum=50,
    )
    if error is not None:
        return error

    search, error = _query_text(
        "search"
    )
    if error is not None:
        return error

    category, error = _query_text(
        "category",
        maximum=80,
    )
    if error is not None:
        return error

    city, error = _query_text(
        "city",
        maximum=120,
    )
    if error is not None:
        return error

    items, total = _list_profiles(
        kind=kind,
        search=search,
        category=category,
        city=city,
        offset=offset,
        limit=limit,
    )
    pagination = pagination_payload(
        total=total,
        offset=offset,
        limit=limit,
    )

    return api_json(
        {
            "items": [
                _profile_payload(
                    item,
                    kind=kind,
                )
                for item in items
            ],
            "nextOffset": (
                pagination[
                    "nextOffset"
                ]
            ),
            "pagination": pagination,
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_profiles_bp.get(
    "/professionals"
)
def professionals():
    return _profiles_endpoint(
        "professional"
    )


@api_profiles_bp.get(
    "/establishments"
)
def establishments():
    return _profiles_endpoint(
        "establishment"
    )


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
