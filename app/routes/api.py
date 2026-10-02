from flask import Blueprint, abort, jsonify, request, url_for
from flask_login import current_user

from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
)
from app.services.api_auth import get_user_by_access_token
from app.services.booking_service import grouped_available_slots
from app.services.entitlements import (
    SUBJECT_CLIENT,
    SUBJECT_ESTABLISHMENT,
    SUBJECT_PROFESSIONAL,
    get_entitlements,
)
from app.services.experience_service import (
    get_database_experience_by_slug,
    get_experience_by_slug,
    list_experiences,
)
from app.services.media_storage import resolve_media_url


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _natural_arg(name, default, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default

    return min(max(value, 0), maximum)


def _public_image_url(value):
    return resolve_media_url(
        value,
        external=True,
    )


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
        "webUrl": url_for(
            "public.experience_detail",
            slug=item["slug"],
            _external=True,
        ),
    }


def _capabilities_payload(snapshot):
    data = snapshot.to_dict()

    return {
        "subjectType": data["subject_type"],
        "effectivePlanCode": data["effective_plan_code"],
        "assignedPlanCode": data["assigned_plan_code"],
        "subscriptionStatus": data["subscription_status"],
        "capabilities": data["capabilities"],
        "trialEndsAt": data["trial_ends_at"],
        "currentPeriodEnd": data["current_period_end"],
        "cancelAtPeriodEnd": data["cancel_at_period_end"],
        "verificationError": data["verification_error"],
    }


def _authenticated_user():
    authorization = request.headers.get("Authorization")

    if authorization is not None:
        parts = authorization.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return get_user_by_access_token(parts[1])

    if current_user.is_authenticated and current_user.is_active:
        return current_user

    return None


@api_v1_bp.get("/me/capabilities")
def my_capabilities():
    """Retorna somente os contextos da conta autenticada."""
    user = _authenticated_user()

    if user is None:
        response = jsonify(
            {
                "error": {
                    "code": "authentication_required",
                    "message": (
                        "Entre na sua conta para consultar suas capacidades."
                    ),
                }
            }
        )
        response.status_code = 401
        response.headers["Cache-Control"] = "private, no-store"
        return response

    professional = user.professional_profile
    professional_payload = None

    if professional is not None:
        professional_payload = {
            "id": professional.id,
            "isActive": professional.is_active,
            "entitlements": _capabilities_payload(
                get_entitlements(
                    SUBJECT_PROFESSIONAL,
                    professional.id,
                )
            ),
        }

    establishments = []

    for access in user.establishment_accesses:
        if access.status != EstablishmentAccessStatus.ACTIVE:
            continue

        if access.role not in (
            EstablishmentAccessRole.OWNER,
            EstablishmentAccessRole.MANAGER,
        ):
            continue

        establishment = access.establishment

        if establishment is None:
            continue

        establishments.append(
            {
                "id": establishment.id,
                "name": establishment.name,
                "slug": establishment.slug,
                "role": access.role,
                "isActive": establishment.is_active,
                "entitlements": _capabilities_payload(
                    get_entitlements(
                        SUBJECT_ESTABLISHMENT,
                        establishment.id,
                    )
                ),
            }
        )

    response = jsonify(
        {
            "client": _capabilities_payload(
                get_entitlements(SUBJECT_CLIENT)
            ),
            "professional": professional_payload,
            "establishments": establishments,
        }
    )
    response.headers["Cache-Control"] = "private, no-store"

    return response


@api_v1_bp.get("/experiences")
def experiences():
    # Web e app consultam o mesmo catálogo. Entradas de protótipo
    # não são expostas pela API transacional.
    items = [
        item
        for item in list_experiences(
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
        "items": [
            _experience_payload(item)
            for item in page
        ],
        "total": len(items),
        "nextOffset": (
            offset + limit
            if offset + limit < len(items)
            else None
        ),
    }


@api_v1_bp.get("/experiences/<slug>")
def experience_detail(slug):
    if get_database_experience_by_slug(slug) is None:
        abort(404)

    return _experience_payload(
        get_experience_by_slug(slug)
    )


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