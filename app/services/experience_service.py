from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import unicodedata

from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.data.mock_marketplace import EXPERIENCE_CATALOG, LOCATIONS
from app.data.mock_professionals import PROFESSIONAL_CATALOG
from app.extensions import db
from app.models.booking import (
    ExperienceSlot,
    SlotStatus,
)
from app.models.establishment import Establishment
from app.models.experience import (
    Experience,
    ExperienceCategory,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile
from app.models.reputation import (
    Review,
    ReviewTarget,
)
from app.services.booking_service import (
    available_slots_for_experience,
    release_expired_holds,
)
from app.services.public_eligibility import (
    public_experiences_query,
)
from app.services.reputation_service import reputation_summary
from app.services.time_service import to_local, utcnow


# ============================================================
# CATEGORY PRESENTATION
# ============================================================

# The model is the source of truth for category names.
# Keeping this alias avoids duplicating the taxonomy here.
CATEGORY_LABELS = ExperienceCategory.LABELS


# These assets are only fallbacks when a database experience
# does not have its own image.
CATEGORY_IMAGES = {
    "cabelo": "img/exp-hair.jpg",
    "unhas": "img/exp-nails.jpg",
    "barbearia": "img/exp-barber.jpg",
    "estetica": "img/hero-model.png",
    "tatuagem": "img/category-tattoo.svg",
    "sobrancelhas": "img/hero-woman-v3.webp",
}


CATEGORY_AVATARS = {
    "cabelo": "img/prof-camila.jpg",
    "unhas": "img/prof-juliana.jpg",
    "barbearia": "img/prof-rafael.jpg",
}


CATEGORY_DEFAULT_DURATIONS = {
    "cabelo": 120,
    "unhas": 90,
    "barbearia": 60,
    "estetica": 60,
    "tatuagem": 120,
    "sobrancelhas": 60,
}


MOCK_NEXT_AVAILABILITY = {
    "cabelo": "Hoje, 15h",
    "unhas": "Amanhã, 10h",
    "barbearia": "Hoje, 17h",
    "tatuagem": "Sábado, 11h",
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_text(value):
    """
    Normalize text for searches and location comparisons.

    Besides ignoring uppercase/lowercase, accents are ignored,
    so "Agua Verde" can match "Água Verde".
    """
    value = str(value or "").strip()

    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return without_accents.casefold()


_SQL_ACCENT_REPLACEMENTS = (
    ("á", "a"),
    ("à", "a"),
    ("ã", "a"),
    ("â", "a"),
    ("ä", "a"),
    ("Á", "a"),
    ("À", "a"),
    ("Ã", "a"),
    ("Â", "a"),
    ("Ä", "a"),
    ("é", "e"),
    ("è", "e"),
    ("ê", "e"),
    ("ë", "e"),
    ("É", "e"),
    ("È", "e"),
    ("Ê", "e"),
    ("Ë", "e"),
    ("í", "i"),
    ("ì", "i"),
    ("î", "i"),
    ("ï", "i"),
    ("Í", "i"),
    ("Ì", "i"),
    ("Î", "i"),
    ("Ï", "i"),
    ("ó", "o"),
    ("ò", "o"),
    ("õ", "o"),
    ("ô", "o"),
    ("ö", "o"),
    ("Ó", "o"),
    ("Ò", "o"),
    ("Õ", "o"),
    ("Ô", "o"),
    ("Ö", "o"),
    ("ú", "u"),
    ("ù", "u"),
    ("û", "u"),
    ("ü", "u"),
    ("Ú", "u"),
    ("Ù", "u"),
    ("Û", "u"),
    ("Ü", "u"),
    ("ç", "c"),
    ("Ç", "c"),
)


def _sql_normalized_text(
    expression,
):
    """
    Normalização SQL portátil para os caracteres usados na busca PT-BR.

    Evita depender da extensão PostgreSQL unaccent e mantém os
    testes SQLite semanticamente equivalentes à produção.
    """
    normalized = func.coalesce(
        expression,
        "",
    )

    for source, target in (
        _SQL_ACCENT_REPLACEMENTS
    ):
        normalized = func.replace(
            normalized,
            source,
            target,
        )

    return func.lower(
        normalized
    )


# ============================================================
# PRESENTATION HELPERS
# ============================================================

_FIRST_VISIT_BADGES = {
    "primeira experiencia",
    "primeira vez",
}


def _public_badge(value, default):
    label = str(value or "").strip()
    if _normalize_text(label) in _FIRST_VISIT_BADGES:
        return default
    return label or default


def _money_number(value):
    if value is None:
        return 0

    decimal_value = Decimal(value)

    if decimal_value == int(decimal_value):
        return int(decimal_value)

    return float(decimal_value)


def _discount_percent(
    regular_price,
    current_price,
):
    """
    Return the rounded saving percentage without using
    binary floating-point arithmetic.
    """
    regular = Decimal(
        regular_price or 0
    )

    current = Decimal(
        current_price or 0
    )

    if (
        regular <= 0
        or current >= regular
    ):
        return 0

    return int(
        (
            (
                (
                    regular - current
                )
                / regular
            )
            * Decimal("100")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _duration_label(minutes):
    minutes = max(
        int(minutes or 0),
        0,
    )

    hours, remaining_minutes = divmod(
        minutes,
        60,
    )

    if (
        hours
        and remaining_minutes
    ):
        return (
            f"{hours}h"
            f"{remaining_minutes:02d}"
        )

    if hours:
        return f"{hours}h"

    return f"{remaining_minutes}min"


def _time_label(value):
    if value.minute:
        return value.strftime(
            "%Hh%M"
        )

    return value.strftime(
        "%Hh"
    )


def _next_available_label(
    slots,
    timezone_name,
):
    if not slots:
        return "Novos horários em breve"

    next_slot = min(
        slots,
        key=lambda slot: slot.starts_at,
    )

    local_start = to_local(
        next_slot.starts_at,
        timezone_name,
    )

    local_today = to_local(
        utcnow(),
        timezone_name,
    ).date()

    if (
        local_start.date()
        == local_today
    ):
        day_label = "Hoje"

    elif (
        local_start.date()
        == local_today
        + timedelta(days=1)
    ):
        day_label = "Amanhã"

    else:
        day_label = (
            local_start.strftime(
                "%d/%m"
            )
        )

    return (
        f"{day_label}, "
        f"{_time_label(local_start)}"
    )


# ============================================================
# DATABASE SERIALIZATION
# ============================================================

def _db_item(experience):
    professional = (
        experience.professional
    )

    establishment = (
        experience.establishment
    )

    professional_reputation = reputation_summary(
        professional.reviews_received
    )
    establishment_reputation = (
        reputation_summary(establishment.reviews_received)
        if establishment is not None
        else None
    )

    neighborhood = (
        establishment.neighborhood
        if establishment
        else None
    )

    city = (
        (
            establishment.city
            if (
                establishment
                and establishment.city
            )
            else professional.city
        )
        or "Brasil"
    )

    location_parts = [
        part
        for part in [
            neighborhood,
            city,
        ]
        if part
    ]

    available_slots = (
        available_slots_for_experience(
            experience
        )
    )

    category = (
        experience.category
    )

    return {
        "id": (
            f"db-{experience.id}"
        ),

        "source": "database",

        "slug": (
            experience.slug
        ),

        "badge": _public_badge(
            experience.badge,
            (
                "Oportunidade IDDUN"
                if available_slots
                else "Curadoria IDDUN"
            ),
        ),

        "title": (
            experience.title
        ),

        "description": (
            experience.short_description
        ),

        "long_description": (
            experience.description
        ),

        "professional": (
            professional.display_name
        ),

        "professional_role": (
            professional.primary_specialty
            or "Profissional de beleza"
        ),

        "professional_slug": (
            professional.slug
        ),

        "rating": professional_reputation["average"] or 0.0,
        "reviews": professional_reputation["count"],
        "establishment_rating": (
            establishment_reputation["average"]
            if establishment_reputation
            else None
        ),
        "establishment_reviews": (
            establishment_reputation["count"]
            if establishment_reputation
            else 0
        ),

        "neighborhood": (
            neighborhood
            or city
        ),

        "city": city,

        "location": (
            " · ".join(
                location_parts
            )
            if location_parts
            else "Brasil"
        ),

        "regular_price": (
            _money_number(
                experience.regular_price
            )
        ),

        "price": (
            _money_number(
                experience.price
            )
        ),

        "discount_percent": (
            _discount_percent(
                experience.regular_price,
                experience.price,
            )
        ),

        "category": category,

        "category_label": (
            CATEGORY_LABELS.get(
                category,
                category.title(),
            )
        ),

        "image": (
            experience.image_url
            or CATEGORY_IMAGES.get(
                category,
                "img/exp-hair.jpg",
            )
        ),

        "image_position": (
            f"{50 if experience.image_focus_x is None else experience.image_focus_x}% "
            f"{50 if experience.image_focus_y is None else experience.image_focus_y}%"
        ),

        "avatar": (
            professional.avatar_url
            or CATEGORY_AVATARS.get(
                category,
                "img/prof-camila.jpg",
            )
        ),

        "avatar_position": (
            f"{50 if professional.avatar_focus_x is None else professional.avatar_focus_x}% "
            f"{50 if professional.avatar_focus_y is None else professional.avatar_focus_y}%"
        ),

        "featured": (
            experience.is_featured
        ),

        # Preserve the presentation key while no longer suggesting
        # that a booking depends on being a first-time client.
        "first_time": False,

        "duration_minutes": (
            experience.duration_minutes
        ),

        "duration_label": (
            _duration_label(
                experience.duration_minutes
            )
        ),

        "establishment": (
            establishment.name
            if establishment
            else None
        ),

        "establishment_slug": (
            establishment.slug
            if establishment
            else None
        ),

        "available_slots_count": (
            len(
                available_slots
            )
        ),

        "next_available_label": (
            _next_available_label(
                available_slots,
                professional.timezone,
            )
        ),
    }


# ============================================================
# PROTOTYPE SERIALIZATION
# ============================================================

def _normalize_mock_item(item):
    item = deepcopy(
        item
    )

    category = (
        item.get(
            "category"
        )
    )

    matching_professional = next(
        (
            profile
            for profile
            in PROFESSIONAL_CATALOG
            if (
                profile.get("name")
                == item.get(
                    "professional"
                )
            )
        ),
        None,
    )

    item.setdefault(
        "long_description",
        item.get(
            "description"
        ),
    )

    item.setdefault(
        "duration_minutes",
        CATEGORY_DEFAULT_DURATIONS.get(
            category,
            60,
        ),
    )

    item.setdefault(
        "duration_label",
        _duration_label(
            item[
                "duration_minutes"
            ]
        ),
    )

    item.setdefault(
        "next_available_label",
        MOCK_NEXT_AVAILABILITY.get(
            category,
            "Consulte os horários",
        ),
    )

    item.setdefault(
        "establishment",
        None,
    )

    item.setdefault(
        "establishment_slug",
        None,
    )

    item.setdefault(
        "professional_slug",
        (
            matching_professional.get(
                "slug"
            )
            if matching_professional
            else None
        ),
    )

    item.setdefault(
        "available_slots_count",
        0,
    )

    item.setdefault(
        "source",
        "prototype",
    )

    item["badge"] = _public_badge(
        item.get("badge"),
        "Prévia IDDUN",
    )
    item["first_time"] = False

    item.setdefault(
        "image_position",
        "50% 50%",
    )

    item.setdefault(
        "avatar_position",
        "50% 50%",
    )

    item.setdefault(
        "category_label",
        CATEGORY_LABELS.get(
            category,
            (
                category.title()
                if category
                else "Beleza"
            ),
        ),
    )

    item.setdefault(
        "discount_percent",
        _discount_percent(
            item.get(
                "regular_price"
            ),
            item.get(
                "price"
            ),
        ),
    )

    return item


# ============================================================
# CATALOG
# ============================================================

def _published_db_query():
    """Compatibilidade interna para a política pública centralizada."""
    return public_experiences_query()


def _catalog_loader_options(
    now,
):
    """
    Evita carregar o histórico inteiro de slots no catálogo.

    Holds expirados são liberados antes da consulta; por isso,
    nesta carga interessam apenas slots futuros ainda disponíveis.
    """
    return (
        selectinload(
            Experience.professional
        ).selectinload(
            ProfessionalProfile.reviews_received
        ),
        selectinload(
            Experience.establishment
        ).selectinload(
            Establishment.reviews_received
        ),
        selectinload(
            Experience.slots.and_(
                ExperienceSlot.starts_at
                > now,
                ExperienceSlot.status
                == SlotStatus.AVAILABLE,
            )
        ),
    )


def _published_db_experiences():
    now = utcnow()

    release_expired_holds(
        now=now,
    )

    items = db.session.scalars(
        _published_db_query()
        .options(
            *_catalog_loader_options(
                now
            )
        )
        .order_by(
            Experience.is_featured.desc(),
            Experience.created_at.desc(),
        )
    ).unique().all()

    return [
        _db_item(item)
        for item in items
    ]


def catalog_has_experiences():
    """(c) Informa se o ambiente atual possui algum item público visível."""
    if (
        current_app.config["APP_ENV"]
        != "production"
        and EXPERIENCE_CATALOG
    ):
        return True

    query = (
        _published_db_query()
        .with_only_columns(
            Experience.id
        )
        .limit(1)
    )

    return (
        db.session.scalar(query)
        is not None
    )


def _catalog():
    database_items = (
        _published_db_experiences()
    )

    # The prototype is useful locally, but production must only
    # advertise experiences backed by actual database records.
    if current_app.config["APP_ENV"] == "production":
        return database_items

    db_slugs = {
        item["slug"]
        for item
        in database_items
    }

    mock_items = [
        _normalize_mock_item(
            item
        )
        for item
        in EXPERIENCE_CATALOG
        if (
            item["slug"]
            not in db_slugs
        )
    ]

    return (
        database_items
        + mock_items
    )


# ============================================================
# SEARCH / FILTERING
# ============================================================

def _matches_search(
    item,
    search,
):
    if not search:
        return True

    searchable_text = " ".join(
        str(value)
        for value in [
            item.get(
                "title"
            ),
            item.get(
                "description"
            ),
            item.get(
                "professional"
            ),
            item.get(
                "professional_role"
            ),
            item.get(
                "category_label"
            ),
            item.get(
                "neighborhood"
            ),
            item.get(
                "city"
            ),
            item.get(
                "establishment"
            ),
        ]
        if value
    )

    return (
        search
        in _normalize_text(
            searchable_text
        )
    )


def _matches_location(
    item,
    location,
):
    if not location:
        return True

    location_text = " ".join(
        str(value)
        for value in [
            item.get(
                "neighborhood"
            ),
            item.get(
                "city"
            ),
        ]
        if value
    )

    return (
        location
        in _normalize_text(
            location_text
        )
    )


def list_experiences(
    search="",
    category="",
    location="",
    sort="recommended",
):
    """
    Return published database experiences plus remaining
    prototype catalog items.

    `location` accepts both neighborhood and city.
    """
    items = _catalog()

    normalized_search = (
        _normalize_text(
            search
        )
    )

    normalized_category = (
        _normalize_text(
            category
        )
    )

    normalized_location = (
        _normalize_text(
            location
        )
    )

    if normalized_search:
        items = [
            item
            for item in items
            if _matches_search(
                item,
                normalized_search,
            )
        ]

    if normalized_category:
        items = [
            item
            for item in items
            if (
                _normalize_text(
                    item.get(
                        "category"
                    )
                )
                == normalized_category
            )
        ]

    if normalized_location:
        items = [
            item
            for item in items
            if _matches_location(
                item,
                normalized_location,
            )
        ]

    if (
        sort
        == "lowest_price"
    ):
        items.sort(
            key=lambda item: (
                item["price"]
            )
        )

    elif (
        sort
        == "highest_rating"
    ):
        items.sort(
            key=lambda item: (
                -item["rating"],
                -item["reviews"],
            )
        )

    elif (
        sort
        == "biggest_saving"
    ):
        items.sort(
            key=lambda item: (
                item[
                    "regular_price"
                ]
                - item["price"]
            ),
            reverse=True,
        )

    elif (
        sort
        == "newest"
    ):
        items.sort(
            key=lambda item: (
                (
                    item.get(
                        "source"
                    )
                    == "database"
                ),
                str(
                    item.get(
                        "id",
                        "",
                    )
                ),
            ),
            reverse=True,
        )

    else:
        items.sort(
            key=lambda item: (
                (
                    item.get(
                        "source"
                    )
                    != "database"
                ),
                not item[
                    "featured"
                ],
                -item[
                    "rating"
                ],
                -item[
                    "reviews"
                ],
            )
        )

    return items


def _professional_rating_expression():
    return (
        select(
            func.coalesce(
                func.avg(
                    Review.rating
                ),
                0,
            )
        )
        .where(
            Review.professional_id
            == Experience.professional_id,
            Review.target_type
            == ReviewTarget.PROFESSIONAL,
            Review.is_visible.is_(
                True
            ),
        )
        .correlate(Experience)
        .scalar_subquery()
    )


def _professional_reviews_expression():
    return (
        select(
            func.count(
                Review.id
            )
        )
        .where(
            Review.professional_id
            == Experience.professional_id,
            Review.target_type
            == ReviewTarget.PROFESSIONAL,
            Review.is_visible.is_(
                True
            ),
        )
        .correlate(Experience)
        .scalar_subquery()
    )


def _database_catalog_order(sort):
    rating = (
        _professional_rating_expression()
    )
    reviews = (
        _professional_reviews_expression()
    )

    if sort == "lowest_price":
        return (
            Experience.price.asc(),
            Experience.is_featured.desc(),
            Experience.created_at.desc(),
            Experience.id.desc(),
        )

    if sort == "highest_rating":
        return (
            rating.desc(),
            reviews.desc(),
            Experience.is_featured.desc(),
            Experience.created_at.desc(),
            Experience.id.desc(),
        )

    if sort == "biggest_saving":
        return (
            (
                Experience.regular_price
                - Experience.price
            ).desc(),
            Experience.is_featured.desc(),
            Experience.created_at.desc(),
            Experience.id.desc(),
        )

    if sort == "newest":
        return (
            Experience.created_at.desc(),
            Experience.id.desc(),
        )

    return (
        Experience.is_featured.desc(),
        rating.desc(),
        reviews.desc(),
        Experience.created_at.desc(),
        Experience.id.desc(),
    )


def list_database_experiences_page(
    *,
    search="",
    category="",
    location="",
    sort="recommended",
    offset=0,
    limit=20,
):
    """
    Página de experiências reais para API.

    Busca, filtros, ordenação, contagem e paginação acontecem
    no banco. A normalização SQL preserva a busca PT-BR sem
    acentos tanto em SQLite quanto em PostgreSQL.
    """
    normalized_search = _normalize_text(
        search
    )
    normalized_location = _normalize_text(
        location
    )
    normalized_category = _normalize_text(
        category
    )

    query = _published_db_query()

    if normalized_category:
        query = query.where(
            _sql_normalized_text(
                Experience.category
            )
            == normalized_category
        )

    if normalized_search:
        pattern = (
            f"%{normalized_search}%"
        )

        query = query.where(
            or_(
                _sql_normalized_text(
                    Experience.title
                ).like(pattern),
                _sql_normalized_text(
                    Experience.short_description
                ).like(pattern),
                _sql_normalized_text(
                    Experience.description
                ).like(pattern),
                _sql_normalized_text(
                    Experience.category
                ).like(pattern),
                _sql_normalized_text(
                    ProfessionalProfile.display_name
                ).like(pattern),
                _sql_normalized_text(
                    ProfessionalProfile.primary_specialty
                ).like(pattern),
                _sql_normalized_text(
                    ProfessionalProfile.city
                ).like(pattern),
                _sql_normalized_text(
                    Establishment.name
                ).like(pattern),
                _sql_normalized_text(
                    Establishment.neighborhood
                ).like(pattern),
                _sql_normalized_text(
                    Establishment.city
                ).like(pattern),
            )
        )

    if normalized_location:
        location_pattern = (
            f"%{normalized_location}%"
        )

        query = query.where(
            or_(
                _sql_normalized_text(
                    Establishment.neighborhood
                ).like(
                    location_pattern
                ),
                _sql_normalized_text(
                    Establishment.city
                ).like(
                    location_pattern
                ),
                _sql_normalized_text(
                    ProfessionalProfile.city
                ).like(
                    location_pattern
                ),
            )
        )

    total_query = (
        select(
            func.count()
        )
        .select_from(
            query
            .with_only_columns(
                Experience.id
            )
            .order_by(None)
            .subquery()
        )
    )

    total = (
        db.session.scalar(
            total_query
        )
        or 0
    )

    now = utcnow()

    release_expired_holds(
        now=now,
    )

    query = (
        query
        .options(
            *_catalog_loader_options(
                now
            )
        )
        .order_by(
            *_database_catalog_order(
                sort
            )
        )
        .offset(offset)
        .limit(limit)
    )

    rows = db.session.scalars(
        query
    ).unique().all()

    return (
        [
            _db_item(item)
            for item in rows
        ],
        total,
    )


# ============================================================
# FEATURED EXPERIENCES
# ============================================================

def list_featured_experiences(
    limit=3,
):
    items = _catalog()

    featured = [
        item
        for item in items
        if item.get(
            "featured"
        )
    ]

    remaining = [
        item
        for item in items
        if not item.get(
            "featured"
        )
    ]

    return (
        featured
        + remaining
    )[:limit]


# ============================================================
# EXPERIENCE DETAIL
# ============================================================

def get_experience_by_slug(
    slug,
):
    db_item = db.session.scalar(
        _published_db_query().where(
            Experience.slug
            == slug,
        )
    )

    if db_item:
        return _db_item(
            db_item
        )

    if current_app.config["APP_ENV"] == "production":
        return None

    item = next(
        (
            item
            for item
            in EXPERIENCE_CATALOG
            if (
                item["slug"]
                == slug
            )
        ),
        None,
    )

    return (
        _normalize_mock_item(
            item
        )
        if item
        else None
    )


# ============================================================
# LOCATIONS
# ============================================================

def list_locations():
    """
    Return neighborhoods available for the marketplace filter.

    Cities are intentionally not included in this dropdown
    because its interface is specifically a neighborhood
    filter. City searching is supported through `location`.
    """
    locations = (
        set()
        if current_app.config["APP_ENV"] == "production"
        else set(LOCATIONS)
    )

    rows = db.session.scalars(
        _published_db_query()
    ).all()

    for item in rows:
        if (
            item.establishment
            and item.establishment.neighborhood
        ):
            locations.add(
                item
                .establishment
                .neighborhood
            )

    return sorted(
        locations
    )


# ============================================================
# DATABASE EXPERIENCE
# ============================================================

def get_database_experience_by_slug(
    slug,
):
    item = db.session.scalar(
        _published_db_query().where(
            Experience.slug
            == slug,
        )
    )

    return item
