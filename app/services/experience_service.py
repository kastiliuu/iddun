from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select

from app.data.mock_marketplace import EXPERIENCE_CATALOG, LOCATIONS
from app.data.mock_professionals import PROFESSIONAL_CATALOG
from app.extensions import db
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.services.booking_service import available_slots_for_experience
from app.services.time_service import to_local, utcnow


CATEGORY_LABELS = {
    "cabelo": "Cabelo",
    "unhas": "Unhas",
    "barbearia": "Barbearia",
    "tatuagem": "Tatuagem",
}

CATEGORY_IMAGES = {
    "cabelo": "img/exp-hair.jpg",
    "unhas": "img/exp-nails.jpg",
    "barbearia": "img/exp-barber.jpg",
}

CATEGORY_AVATARS = {
    "cabelo": "img/prof-camila.jpg",
    "unhas": "img/prof-juliana.jpg",
    "barbearia": "img/prof-rafael.jpg",
}


def _money_number(value):
    if value is None:
        return 0
    return int(value) if Decimal(value) == int(Decimal(value)) else float(value)


def _discount_percent(regular_price, current_price):
    """Return the rounded saving percentage without using binary floats."""
    regular = Decimal(regular_price or 0)
    current = Decimal(current_price or 0)
    if regular <= 0 or current >= regular:
        return 0
    return int(
        (((regular - current) / regular) * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _duration_label(minutes):
    minutes = max(int(minutes or 0), 0)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours and remaining_minutes:
        return f"{hours}h{remaining_minutes:02d}"
    if hours:
        return f"{hours}h"
    return f"{remaining_minutes}min"


def _time_label(value):
    return value.strftime("%Hh%M") if value.minute else value.strftime("%Hh")


def _next_available_label(slots, timezone_name):
    if not slots:
        return "Novos horários em breve"

    next_slot = min(slots, key=lambda slot: slot.starts_at)
    local_start = to_local(next_slot.starts_at, timezone_name)
    local_today = to_local(utcnow(), timezone_name).date()

    if local_start.date() == local_today:
        day_label = "Hoje"
    elif local_start.date() == local_today + timedelta(days=1):
        day_label = "Amanhã"
    else:
        day_label = local_start.strftime("%d/%m")
    return f"{day_label}, {_time_label(local_start)}"


def _db_item(experience):
    professional = experience.professional
    establishment = experience.establishment
    neighborhood = establishment.neighborhood if establishment else None
    city = (
        establishment.city
        if establishment and establishment.city
        else professional.city
    ) or "Brasil"
    location_parts = [part for part in [neighborhood, city] if part]
    available_slots = available_slots_for_experience(experience)

    return {
        "id": f"db-{experience.id}",
        "source": "database",
        "slug": experience.slug,
        "badge": experience.badge or ("Primeira experiência" if experience.is_first_experience else "Curadoria IDDUN"),
        "title": experience.title,
        "description": experience.short_description,
        "long_description": experience.description,
        "professional": professional.display_name,
        "professional_role": professional.primary_specialty or "Profissional de beleza",
        "professional_slug": professional.slug,
        "rating": 0.0,
        "reviews": 0,
        "neighborhood": neighborhood or city,
        "city": city,
        "location": " · ".join(location_parts) if location_parts else "Brasil",
        "regular_price": _money_number(experience.regular_price),
        "price": _money_number(experience.price),
        "discount_percent": _discount_percent(experience.regular_price, experience.price),
        "category": experience.category,
        "category_label": CATEGORY_LABELS.get(experience.category, experience.category.title()),
        "image": experience.image_url or CATEGORY_IMAGES.get(experience.category, "img/exp-hair.jpg"),
        "image_position": f"{50 if experience.image_focus_x is None else experience.image_focus_x}% {50 if experience.image_focus_y is None else experience.image_focus_y}%",
        "avatar": professional.avatar_url or CATEGORY_AVATARS.get(experience.category, "img/prof-camila.jpg"),
        "avatar_position": f"{50 if professional.avatar_focus_x is None else professional.avatar_focus_x}% {50 if professional.avatar_focus_y is None else professional.avatar_focus_y}%",
        "featured": experience.is_featured,
        "first_time": experience.is_first_experience,
        "duration_minutes": experience.duration_minutes,
        "duration_label": _duration_label(experience.duration_minutes),
        "establishment": establishment.name if establishment else None,
        "establishment_slug": establishment.slug if establishment else None,
        "available_slots_count": len(available_slots),
        "next_available_label": _next_available_label(
            available_slots, professional.timezone
        ),
    }


def _normalize_mock_item(item):
    item = deepcopy(item)
    defaults = {"cabelo": 120, "unhas": 90, "barbearia": 60, "tatuagem": 120}
    matching_professional = next(
        (profile for profile in PROFESSIONAL_CATALOG if profile.get("name") == item.get("professional")),
        None,
    )
    item.setdefault("long_description", item.get("description"))
    item.setdefault("duration_minutes", defaults.get(item.get("category"), 60))
    item.setdefault("duration_label", _duration_label(item["duration_minutes"]))
    item.setdefault(
        "next_available_label",
        {
            "cabelo": "Hoje, 15h",
            "unhas": "Amanhã, 10h",
            "barbearia": "Hoje, 17h",
            "tatuagem": "Sábado, 11h",
        }.get(item.get("category"), "Consulte os horários"),
    )
    item.setdefault("establishment", None)
    item.setdefault("establishment_slug", None)
    item.setdefault("professional_slug", matching_professional.get("slug") if matching_professional else None)
    item.setdefault("available_slots_count", 0)
    item.setdefault("source", "prototype")
    item.setdefault("image_position", "50% 50%")
    item.setdefault("avatar_position", "50% 50%")
    item.setdefault(
        "discount_percent",
        _discount_percent(item.get("regular_price"), item.get("price")),
    )
    return item


def _published_db_experiences():
    items = db.session.scalars(
        select(Experience)
        .join(ProfessionalProfile, Experience.professional_id == ProfessionalProfile.id)
        .where(
            Experience.status == ExperienceStatus.PUBLISHED,
            ProfessionalProfile.is_active.is_(True),
        )
        .order_by(Experience.is_featured.desc(), Experience.created_at.desc())
    ).all()
    return [
        _db_item(item)
        for item in items
        if item.establishment is None or item.establishment.is_active
    ]


def _catalog():
    database_items = _published_db_experiences()
    db_slugs = {item["slug"] for item in database_items}
    mock_items = [
        _normalize_mock_item(item)
        for item in EXPERIENCE_CATALOG
        if item["slug"] not in db_slugs
    ]
    return database_items + mock_items


def list_experiences(search="", category="", location="", sort="recommended"):
    """Return published database experiences plus remaining prototype catalog items."""
    items = _catalog()

    normalized_search = (search or "").strip().casefold()
    normalized_category = (category or "").strip().casefold()
    normalized_location = (location or "").strip().casefold()

    if normalized_search:
        items = [
            item
            for item in items
            if normalized_search in " ".join(
                [
                    item["title"],
                    item["description"],
                    item["professional"],
                    item["category_label"],
                    item["neighborhood"],
                    item.get("establishment") or "",
                ]
            ).casefold()
        ]

    if normalized_category:
        items = [item for item in items if item["category"].casefold() == normalized_category]

    if normalized_location:
        items = [item for item in items if item["neighborhood"].casefold() == normalized_location]

    if sort == "lowest_price":
        items.sort(key=lambda item: item["price"])
    elif sort == "highest_rating":
        items.sort(key=lambda item: (-item["rating"], -item["reviews"]))
    elif sort == "biggest_saving":
        items.sort(key=lambda item: (item["regular_price"] - item["price"]), reverse=True)
    elif sort == "newest":
        items.sort(
            key=lambda item: (
                item.get("source") == "database",
                str(item.get("id", "")),
            ),
            reverse=True,
        )
    else:
        items.sort(
            key=lambda item: (
                item.get("source") != "database",
                not item["featured"],
                -item["rating"],
                -item["reviews"],
            )
        )

    return items


def list_featured_experiences(limit=3):
    items = _catalog()
    featured = [item for item in items if item.get("featured")]
    remaining = [item for item in items if not item.get("featured")]
    return (featured + remaining)[:limit]


def get_experience_by_slug(slug):
    db_item = db.session.scalar(
        select(Experience).where(
            Experience.slug == slug,
            Experience.status == ExperienceStatus.PUBLISHED,
        )
    )
    if db_item:
        if not db_item.professional.is_active:
            return None
        if db_item.establishment is not None and not db_item.establishment.is_active:
            return None
        return _db_item(db_item)
    item = next((item for item in EXPERIENCE_CATALOG if item["slug"] == slug), None)
    return _normalize_mock_item(item) if item else None


def list_locations():
    locations = set(LOCATIONS)
    rows = db.session.scalars(
        select(Experience)
        .where(Experience.status == ExperienceStatus.PUBLISHED)
    ).all()
    for item in rows:
        if item.establishment and item.establishment.neighborhood:
            locations.add(item.establishment.neighborhood)
    return sorted(locations)


def get_database_experience_by_slug(slug):
    item = db.session.scalar(
        select(Experience).where(
            Experience.slug == slug,
            Experience.status == ExperienceStatus.PUBLISHED,
        )
    )
    if item is None:
        return None
    if not item.professional.is_active:
        return None
    if item.establishment is not None and not item.establishment.is_active:
        return None
    return item
