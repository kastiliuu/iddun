from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import unicodedata

from flask import current_app
from sqlalchemy import select

from app.data.mock_marketplace import EXPERIENCE_CATALOG, LOCATIONS
from app.data.mock_professionals import PROFESSIONAL_CATALOG
from app.extensions import db
from app.models.experience import (
    Experience,
    ExperienceCategory,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile
from app.services.booking_service import available_slots_for_experience
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


# ============================================================
# PRESENTATION HELPERS
# ============================================================

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

        "badge": (
            experience.badge
            or (
                "Primeira experiência"
                if experience.is_first_experience
                else "Curadoria IDDUN"
            )
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

        "first_time": (
            experience.is_first_experience
        ),

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

def _published_db_experiences():
    items = db.session.scalars(
        select(
            Experience
        )
        .join(
            ProfessionalProfile,
            (
                Experience.professional_id
                == ProfessionalProfile.id
            ),
        )
        .where(
            Experience.status
            == ExperienceStatus.PUBLISHED,

            ProfessionalProfile.is_active.is_(
                True
            ),
        )
        .order_by(
            Experience.is_featured.desc(),
            Experience.created_at.desc(),
        )
    ).all()

    return [
        _db_item(item)
        for item in items
        if (
            item.establishment is None
            or item.establishment.is_active
        )
    ]


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
        select(
            Experience
        ).where(
            Experience.slug
            == slug,

            Experience.status
            == ExperienceStatus.PUBLISHED,
        )
    )

    if db_item:
        if not (
            db_item
            .professional
            .is_active
        ):
            return None

        if (
            db_item.establishment
            is not None
            and not (
                db_item
                .establishment
                .is_active
            )
        ):
            return None

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
        select(
            Experience
        ).where(
            Experience.status
            == ExperienceStatus.PUBLISHED
        )
    ).all()

    for item in rows:
        if not item.professional.is_active or (
            item.establishment is not None
            and not item.establishment.is_active
        ):
            continue
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
        select(
            Experience
        ).where(
            Experience.slug
            == slug,

            Experience.status
            == ExperienceStatus.PUBLISHED,
        )
    )

    if item is None:
        return None

    if not (
        item.professional.is_active
    ):
        return None

    if (
        item.establishment
        is not None
        and not (
            item.establishment.is_active
        )
    ):
        return None

    return item
