from flask import Blueprint, request
from flask_login import current_user

from app.extensions import csrf, limiter
from app.services.api_auth import (
    get_user_by_access_token,
)
from app.services.api_contract import (
    api_error,
    api_json,
)
from app.services.availability_service import (
    AvailabilityError,
    create_availability,
    creator_experiences,
    iddun_now_slots,
    slot_is_urgent,
    slot_time_label,
)
from app.services.media_storage import (
    resolve_media_url,
)
from app.services.time_service import (
    as_utc,
)


api_availability_bp = Blueprint(
    "api_availability",
    __name__,
    url_prefix="/api/v1",
)

MAX_BODY_BYTES = 32_768


def _optional_user():
    authorization = request.headers.get(
        "Authorization"
    )

    if authorization is not None:
        parts = authorization.split()

        if (
            len(parts) != 2
            or parts[0].lower()
            != "bearer"
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


def _require_user():
    user = _optional_user()

    if user is None:
        return (
            None,
            api_error(
                "authentication_required",
                "Entre na sua conta para continuar.",
                401,
            ),
        )

    return user, None


def _json_body():
    if (
        request.content_length
        is not None
        and request.content_length
        > MAX_BODY_BYTES
    ):
        return (
            None,
            api_error(
                "request_too_large",
                "A solicitação é muito grande.",
                413,
            ),
        )

    if not request.is_json:
        return (
            None,
            api_error(
                "json_required",
                "Envie os dados em formato JSON.",
                415,
            ),
        )

    payload = request.get_json(
        silent=True
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            None,
            api_error(
                "invalid_json",
                "Não foi possível ler os dados enviados.",
                400,
            ),
        )

    return payload, None


def _query_limit():
    raw = request.args.get(
        "limit",
        "20",
    )

    try:
        value = int(raw)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if value < 1 or value > 50:
        return None

    return value


def _media(value):
    if not value:
        value = "img/exp-hair.jpg"

    return resolve_media_url(
        value,
        external=True,
    )


def _location(slot):
    establishment = (
        slot.establishment
    )

    if establishment is not None:
        parts = [
            establishment.neighborhood,
            establishment.city,
            establishment.state,
        ]
    else:
        parts = [
            slot.professional.city,
            slot.professional.state,
        ]

    return (
        " · ".join(
            part
            for part in parts
            if part
        )
        or "Brasil"
    )


def _slot_payload(slot):
    experience = slot.experience
    professional = slot.professional
    establishment = (
        slot.establishment
    )

    return {
        "id": str(slot.id),
        "slotId": slot.id,
        "serviceId": experience.slug,
        "serviceEntityId": experience.id,
        "serviceName": experience.title,
        "category": experience.category,
        "image": _media(
            experience.image_url
        ),
        "price": float(
            experience.price
        ),
        "durationMinutes": (
            experience.duration_minutes
        ),
        "professionalId": str(
            professional.id
        ),
        "professionalRouteId": (
            professional.slug
        ),
        "professionalName": (
            professional.display_name
        ),
        "professionalAvatar": _media(
            professional.avatar_url
            or "img/category-hair.jpg"
        ),
        "establishmentId": (
            str(establishment.id)
            if establishment
            is not None
            else None
        ),
        "establishmentRouteId": (
            establishment.slug
            if establishment
            is not None
            else None
        ),
        "establishmentName": (
            establishment.name
            if establishment
            is not None
            else None
        ),
        "location": _location(
            slot
        ),
        "startsAt": as_utc(
            slot.starts_at
        ).isoformat(),
        "endsAt": as_utc(
            slot.ends_at
        ).isoformat(),
        "timezone": (
            professional.timezone
        ),
        "timeLabel": (
            slot_time_label(
                slot
            )
        ),
        "urgent": (
            slot_is_urgent(
                slot
            )
        ),
    }


def _option_payload(
    experience,
):
    return {
        "id": experience.slug,
        "entityId": experience.id,
        "name": experience.title,
        "category": experience.category,
        "durationMinutes": (
            experience.duration_minutes
        ),
        "price": float(
            experience.price
        ),
        "image": _media(
            experience.image_url
        ),
        "professionalId": (
            str(
                experience.professional_id
            )
        ),
        "professionalName": (
            experience.professional
            .display_name
        ),
        "establishmentId": (
            str(
                experience.establishment_id
            )
            if experience
            .establishment_id
            is not None
            else None
        ),
    }


@api_availability_bp.get(
    "/iddun-now"
)
def iddun_now():
    limit = _query_limit()

    if limit is None:
        return api_error(
            "invalid_query_parameter",
            "Limite inválido.",
            400,
        )

    mode = (
        request.args.get(
            "filter",
            "all",
        )
        or "all"
    ).strip().lower()

    try:
        slots = iddun_now_slots(
            limit=limit,
            mode=mode,
        )
    except AvailabilityError as exc:
        return api_error(
            "invalid_availability_request",
            str(exc),
            400,
        )

    return api_json(
        {
            "items": [
                _slot_payload(
                    slot
                )
                for slot in slots
            ]
        },
        cache_control=(
            "public, max-age=30"
        ),
    )


@api_availability_bp.get(
    "/availability/options"
)
def availability_options():
    user, error = _require_user()

    if error is not None:
        return error

    try:
        experiences = (
            creator_experiences(
                user
            )
        )
    except AvailabilityError as exc:
        return api_error(
            "availability_not_allowed",
            str(exc),
            403,
        )

    return api_json(
        {
            "items": [
                _option_payload(
                    experience
                )
                for experience
                in experiences
            ]
        },
        cache_control=(
            "private, no-store"
        ),
    )


@api_availability_bp.post(
    "/availability"
)
@csrf.exempt
@limiter.limit("120 per hour")
def create_slot():
    user, error = _require_user()

    if error is not None:
        return error

    payload, error = _json_body()

    if error is not None:
        return error

    try:
        slot = create_availability(
            user=user,
            experience_reference=(
                payload.get(
                    "serviceId"
                )
            ),
            slot_date=payload.get(
                "date"
            ),
            slot_time=payload.get(
                "time"
            ),
            cutoff_minutes=(
                payload.get(
                    "cutoffMinutes"
                )
            ),
        )
    except AvailabilityError as exc:
        return api_error(
            "invalid_availability",
            str(exc),
            400,
        )

    return api_json(
        {
            "slot": (
                _slot_payload(
                    slot
                )
            )
        },
        201,
        cache_control=(
            "private, no-store"
        ),
    )
