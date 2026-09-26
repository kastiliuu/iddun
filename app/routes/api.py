from flask import Blueprint, abort, request, url_for

from app.services.booking_service import grouped_available_slots
from app.services.experience_service import (
    get_database_experience_by_slug,
    get_experience_by_slug,
    list_experiences,
)

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _natural_arg(name, default, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(max(value, 0), maximum)


def _public_image_url(value):
    if value.startswith(("https://", "http://", "data:", "/")):
        return value if not value.startswith("/") else request.host_url.rstrip("/") + value
    return url_for("static", filename=value, _external=True)


def _experience_payload(item):
    return {
        "id": item["slug"],
        "slug": item["slug"],
        "title": item["title"],
        "description": item["description"],
        "category": item["category"],
        "categoryLabel": item["category_label"],
        "professional": item["professional"],
        "professionalSlug": item["professional_slug"],
        "establishment": item["establishment"],
        "establishmentSlug": item["establishment_slug"],
        "location": item["location"],
        "price": item["price"],
        "regularPrice": item["regular_price"],
        "durationMinutes": item["duration_minutes"],
        "rating": item["rating"],
        "reviews": item["reviews"],
        "establishmentRating": item["establishment_rating"],
        "establishmentReviews": item["establishment_reviews"],
        "availableSlotsCount": item["available_slots_count"],
        "imageUrl": _public_image_url(item["image"]),
        "webUrl": url_for("public.experience_detail", slug=item["slug"], _external=True),
    }


@api_v1_bp.get("/experiences")
def experiences():
    # The web search and app API share the same catalog service.
    # Prototype entries are never exposed through a transactional API.
    items = [
        item for item in list_experiences(
            search=request.args.get("search", ""),
            category=request.args.get("category", ""),
            location=request.args.get("location", ""),
            sort=request.args.get("sort", "recommended"),
        )
        if item["source"] == "database"
    ]
    offset = _natural_arg("offset", 0, 1_000_000)
    limit = _natural_arg("limit", 20, 50) or 20
    page = items[offset:offset + limit]
    return {
        "items": [_experience_payload(item) for item in page],
        "total": len(items),
        "nextOffset": offset + limit if offset + limit < len(items) else None,
    }


@api_v1_bp.get("/experiences/<slug>")
def experience_detail(slug):
    if get_database_experience_by_slug(slug) is None:
        abort(404)
    return _experience_payload(get_experience_by_slug(slug))


@api_v1_bp.get("/experiences/<slug>/availability")
def experience_availability(slug):
    experience = get_database_experience_by_slug(slug)
    if experience is None:
        abort(404)
    return {
        "experienceId": slug,
        "timezone": experience.professional.timezone,
        "days": [
            {
                "date": group["date"].isoformat(),
                "slots": [
                    {
                        "id": slot["id"],
                        "startsAt": slot["starts_at"].isoformat(),
                        "endsAt": slot["ends_at"].isoformat(),
                        "deadline": slot["deadline"].isoformat(),
                    }
                    for slot in group["slots"]
                ],
            }
            for group in grouped_available_slots(experience)
        ],
    }

