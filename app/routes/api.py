from flask import Blueprint, request, url_for
from flask_login import current_user

from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
)
from app.services.api_auth import get_user_by_access_token
from app.services.api_contract import (
    api_error,
    api_json,
    pagination_payload,
)
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
    list_database_experiences_page,
)
from app.services.media_storage import resolve_media_url


api_v1_bp = Blueprint(
    "api_v1",
    __name__,
    url_prefix="/api/v1",
)

EXPERIENCE_SORTS = {
    "recommended",
    "lowest_price",
    "highest_rating",
    "biggest_saving",
    "newest",
}


def _invalid_query_parameter(
    name,
    value,
    expected,
):
    return api_error(
        "invalid_query_parameter",
        f"Parâmetro de consulta inválido: {name}.",
        400,
        details={
            "parameter": name,
            "value": value,
            "expected": expected,
        },
    )


def _query_int(
    name,
    default,
    *,
    minimum,
    maximum,
):
    raw = request.args.get(name)

    if raw is None or raw == "":
        return default, None

    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, _invalid_query_parameter(
            name,
            raw,
            (
                f"integer between "
                f"{minimum} and {maximum}"
            ),
        )

    if not minimum <= value <= maximum:
        return None, _invalid_query_parameter(
            name,
            raw,
            (
                f"integer between "
                f"{minimum} and {maximum}"
            ),
        )

    return value, None


def _query_text(
    name,
    *,
    default="",
    maximum,
):
    raw = request.args.get(name)

    if raw is None:
        return default, None

    value = raw.strip()

    if len(value) > maximum:
        return None, _invalid_query_parameter(
            name,
            raw,
            f"text up to {maximum} characters",
        )

    return value, None


def _query_sort():
    raw = request.args.get(
        "sort",
        "recommended",
    )
    value = raw.strip()

    if value not in EXPERIENCE_SORTS:
        return None, _invalid_query_parameter(
            "sort",
            raw,
            (
                "one of: "
                + ", ".join(
                    sorted(EXPERIENCE_SORTS)
                )
            ),
        )

    return value, None


def _public_image_url(value):
    return resolve_media_url(
        value,
        external=True,
    )


def _experience_payload(item):
    return {
        "id": item["slug"],
        "entityId": item.get(
            "database_id"
        ),
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
    authorization = request.headers.get(
        "Authorization"
    )

    if authorization is not None:
        parts = authorization.split()

        if (
            len(parts) != 2
            or parts[0].lower() != "bearer"
        ):
            return None

        return get_user_by_access_token(
            parts[1]
        )

    if (
        current_user.is_authenticated
        and current_user.is_active
    ):
        return current_user

    return None


@api_v1_bp.get("/me/capabilities")
def my_capabilities():
    """Retorna somente os contextos da conta autenticada."""
    user = _authenticated_user()

    if user is None:
        return api_error(
            "authentication_required",
            (
                "Entre na sua conta para consultar "
                "suas capacidades."
            ),
            401,
        )

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
        if (
            access.status
            != EstablishmentAccessStatus.ACTIVE
        ):
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
                "entitlements": (
                    _capabilities_payload(
                        get_entitlements(
                            SUBJECT_ESTABLISHMENT,
                            establishment.id,
                        )
                    )
                ),
            }
        )

    return api_json(
        {
            "client": _capabilities_payload(
                get_entitlements(
                    SUBJECT_CLIENT
                )
            ),
            "professional": professional_payload,
            "establishments": establishments,
        },
        cache_control="private, no-store",
    )


@api_v1_bp.get("/experiences")
def experiences():
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
        "search",
        maximum=120,
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

    sort, error = _query_sort()

    if error is not None:
        return error

    # A API expõe apenas experiências reais. O service pagina no
    # banco sempre que isso não altera a semântica da busca textual.
    page, total = (
        list_database_experiences_page(
            search=search,
            category=category,
            location=location,
            sort=sort,
            offset=offset,
            limit=limit,
        )
    )
    pagination = pagination_payload(
        total=total,
        offset=offset,
        limit=limit,
    )

    return api_json(
        {
            "items": [
                _experience_payload(item)
                for item in page
            ],
            # Compatibilidade com o contrato mobile atual.
            "total": pagination["total"],
            "nextOffset": pagination["nextOffset"],
            "pagination": pagination,
        }
    )


@api_v1_bp.get("/experiences/<slug>")
def experience_detail(slug):
    if (
        get_database_experience_by_slug(
            slug
        )
        is None
    ):
        return api_error(
            "experience_not_found",
            "Experiência não encontrada.",
            404,
        )

    return api_json(
        _experience_payload(
            get_experience_by_slug(
                slug
            )
        )
    )


@api_v1_bp.get(
    "/experiences/<slug>/availability"
)
def experience_availability(slug):
    experience = (
        get_database_experience_by_slug(
            slug
        )
    )

    if experience is None:
        return api_error(
            "experience_not_found",
            "Experiência não encontrada.",
            404,
        )

    return api_json(
        {
            "experienceId": slug,
            "timezone": (
                experience.professional.timezone
            ),
            "days": [
                {
                    "date": (
                        group["date"].isoformat()
                    ),
                    "slots": [
                        {
                            "id": slot["id"],
                            "startsAt": (
                                slot[
                                    "starts_at"
                                ].isoformat()
                            ),
                            "endsAt": (
                                slot[
                                    "ends_at"
                                ].isoformat()
                            ),
                            "deadline": (
                                slot[
                                    "deadline"
                                ].isoformat()
                            ),
                        }
                        for slot in group["slots"]
                    ],
                }
                for group in (
                    grouped_available_slots(
                        experience
                    )
                )
            ],
        }
    )
