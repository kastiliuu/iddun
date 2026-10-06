import unicodedata
from flask import Blueprint, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.experience import Experience
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
from app.services.experience_service import (
    list_database_experiences_page,
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


def _normalize_query_text(
    value,
):
    normalized = unicodedata.normalize(
        "NFKD",
        str(value or "").strip(),
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    ).casefold()


def _discovery_post_query(
    search,
    location="",
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

    if search or location:
        query = (
            query
            .outerjoin(
                ProfessionalProfile,
                WorkPost.professional_id
                == ProfessionalProfile.id,
            )
            .outerjoin(
                Establishment,
                WorkPost.establishment_id
                == Establishment.id,
            )
            .outerjoin(
                Experience,
                WorkPost.experience_id
                == Experience.id,
            )
        )

    if search:
        needle = (
            f"%{_normalize_query_text(search)}%"
        )
        query = query.where(
            or_(
                _normalized_sql(
                    WorkPost.caption
                ).like(needle),
                _normalized_sql(
                    ProfessionalProfile
                    .display_name
                ).like(needle),
                _normalized_sql(
                    Establishment.name
                ).like(needle),
                _normalized_sql(
                    Experience.title
                ).like(needle),
            )
        )

    if location:
        needle = (
            f"%{_normalize_query_text(location)}%"
        )
        query = query.where(
            or_(
                _normalized_sql(
                    ProfessionalProfile.city
                ).like(needle),
                _normalized_sql(
                    Establishment.city
                ).like(needle),
                _normalized_sql(
                    Establishment.neighborhood
                ).like(needle),
            )
        )

    return query.order_by(
        WorkPost.published_at.desc(),
        WorkPost.id.desc(),
    )


def _global_experience_payload(
    item,
):
    return {
        "id": str(
            item.get(
                "database_id"
            )
            or item["slug"]
        ),
        "routeId": item[
            "slug"
        ],
        "kind": "experience",
        "title": item[
            "title"
        ],
        "subtitle": (
            item.get(
                "professional"
            )
            or item.get(
                "category_label"
            )
        ),
        "image": _media(
            item.get(
                "image"
            )
            or "img/exp-hair.jpg"
        ),
        "location": (
            item.get(
                "location"
            )
            or "Brasil"
        ),
        "rating": float(
            item.get(
                "rating"
            )
            or 0
        ),
        "reviewsCount": int(
            item.get(
                "reviews"
            )
            or 0
        ),
        "category": item.get(
            "category"
        ),
        "price": float(
            item.get(
                "price"
            )
            or 0
        ),
        "availableSlotsCount": int(
            item.get(
                "available_slots_count"
            )
            or 0
        ),
    }


def _global_profile_payload(
    item,
    *,
    kind,
):
    payload = _profile_payload(
        item,
        kind=kind,
    )

    return {
        "id": payload["id"],
        "routeId": payload[
            "routeId"
        ],
        "kind": kind,
        "title": payload[
            "name"
        ],
        "subtitle": payload[
            "specialty"
        ],
        "image": (
            payload[
                "cover"
            ]
            or payload[
                "avatar"
            ]
        ),
        "location": payload[
            "location"
        ],
        "rating": payload[
            "rating"
        ],
        "reviewsCount": payload[
            "reviewsCount"
        ],
        "category": (
            payload[
                "categories"
            ][0]
            if payload[
                "categories"
            ]
            else None
        ),
    }


def _global_post_payload(
    item,
):
    payload = (
        serialize_work_post(
            item
        )
    )
    author = (
        payload.get(
            "author"
        )
        or {}
    )

    return {
        "id": str(
            payload[
                "id"
            ]
        ),
        "routeId": str(
            payload[
                "id"
            ]
        ),
        "kind": "post",
        "title": (
            author.get(
                "name"
            )
            or "Trabalho IDDUN"
        ),
        "subtitle": (
            payload.get(
                "caption"
            )
            or ""
        ),
        "image": payload.get(
            "image"
        ),
        "location": None,
        "rating": (
            author.get(
                "rating"
            )
            or 0
        ),
        "reviewsCount": 0,
        "category": None,
    }


@api_profiles_bp.get(
    "/search"
)
def global_search():
    query, error = _query_text(
        "q"
    )
    if error is not None:
        return error

    category, error = _query_text(
        "category",
        maximum=80,
    )
    if error is not None:
        return error

    location, error = _query_text(
        "location",
        maximum=120,
    )
    if error is not None:
        return error

    limit, error = _query_int(
        "limit",
        8,
        minimum=1,
        maximum=20,
    )
    if error is not None:
        return error

    professionals, _ = (
        _list_profiles(
            kind="professional",
            search=query,
            category=category,
            city=location,
            offset=0,
            limit=limit,
        )
    )

    establishments, _ = (
        _list_profiles(
            kind="establishment",
            search=query,
            category=category,
            city=location,
            offset=0,
            limit=limit,
        )
    )

    experiences, _ = (
        list_database_experiences_page(
            search=query,
            category=category,
            location=location,
            offset=0,
            limit=limit,
        )
    )

    posts = db.session.scalars(
        _discovery_post_query(
            query,
            location,
        ).limit(limit)
    ).all()

    professional_items = [
        _global_profile_payload(
            item,
            kind="professional",
        )
        for item
        in professionals
    ]

    establishment_items = [
        _global_profile_payload(
            item,
            kind="establishment",
        )
        for item
        in establishments
    ]

    experience_items = [
        _global_experience_payload(
            item
        )
        for item
        in experiences
    ]

    post_items = [
        _global_post_payload(
            item
        )
        for item
        in posts
    ]

    sections = {
        "professionals":
            professional_items,
        "establishments":
            establishment_items,
        "experiences":
            experience_items,
        "posts":
            post_items,
    }

    ordered = []

    longest = max(
        (
            len(items)
            for items
            in sections.values()
        ),
        default=0,
    )

    for index in range(
        longest
    ):
        for key in (
            "experiences",
            "professionals",
            "establishments",
            "posts",
        ):
            items = sections[
                key
            ]

            if index < len(
                items
            ):
                ordered.append(
                    items[index]
                )

    return api_json(
        {
            "query": query,
            "location":
                location,
            "category":
                category,
            "items":
                ordered[
                    : limit * 4
                ],
            "sections":
                sections,
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_profiles_bp.get(
    "/discovery"
)
def discovery():
    limit, error = _query_int(
        "limit",
        8,
        minimum=1,
        maximum=20,
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

    professionals, _ = _list_profiles(
        kind="professional",
        search=search,
        category=category,
        city=city,
        offset=0,
        limit=limit,
    )
    establishments, _ = _list_profiles(
        kind="establishment",
        search=search,
        category=category,
        city=city,
        offset=0,
        limit=limit,
    )
    posts = db.session.scalars(
        _discovery_post_query(
            search
        ).limit(limit)
    ).all()

    return api_json(
        {
            "professionals": [
                _profile_payload(
                    item,
                    kind="professional",
                )
                for item in professionals
            ],
            "establishments": [
                _profile_payload(
                    item,
                    kind="establishment",
                )
                for item in establishments
            ],
            "posts": [
                serialize_work_post(
                    item
                )
                for item in posts
            ],
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


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
            f"%{_normalize_query_text(search)}%"
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
            f"%{_normalize_query_text(category)}%"
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
        needle = (
            f"%{_normalize_query_text(city)}%"
        )

        if kind == "establishment":
            query = query.where(
                or_(
                    _normalized_sql(
                        model.city
                    ).like(needle),
                    _normalized_sql(
                        model.neighborhood
                    ).like(needle),
                )
            )
        else:
            query = query.where(
                _normalized_sql(
                    city_column
                ).like(needle)
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
