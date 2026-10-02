from flask import Blueprint, current_app, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import csrf, db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
)
from app.services.api_auth import get_user_by_access_token
from app.services.api_contract import (
    api_error,
    api_json,
    pagination_payload,
)
from app.services.booking_service import (
    BookingStateError,
    SlotUnavailableError,
    cancel_booking,
    confirm_booking,
    hold_slot,
    release_expired_holds,
)
from app.services.google_calendar_service import (
    create_booking_event,
    delete_booking_event,
)
from app.services.profile_service import ensure_client_profile
from app.services.time_service import as_utc, to_local, utcnow


api_bookings_bp = Blueprint(
    "api_bookings",
    __name__,
    url_prefix="/api/v1",
)

BOOKING_STATUSES = {
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.COMPLETED,
    BookingStatus.CANCELLED,
    BookingStatus.NO_SHOW,
}


def _bearer_user():
    authorization = request.headers.get(
        "Authorization",
        "",
    )
    parts = authorization.split()

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
    ):
        return None

    return get_user_by_access_token(
        parts[1]
    )


def _require_client():
    user = _bearer_user()

    if user is None:
        return None, api_error(
            "authentication_required",
            "Entre na sua conta para continuar.",
            401,
        )

    return (
        ensure_client_profile(user),
        None,
    )


def _booking_query(client_id):
    return (
        select(Booking)
        .where(
            Booking.client_id == client_id
        )
        .options(
            selectinload(
                Booking.experience
            ),
            selectinload(
                Booking.professional
            ),
            selectinload(
                Booking.establishment
            ),
            selectinload(
                Booking.slot
            ),
        )
    )


def _booking_payload(booking):
    timezone_name = (
        booking.professional.timezone
    )
    local_start = to_local(
        booking.slot.starts_at,
        timezone_name,
    )
    local_end = to_local(
        booking.slot.ends_at,
        timezone_name,
    )

    return {
        "id": str(booking.id),
        "status": booking.status,
        "price": float(
            booking.price_at_booking
        ),
        "experience": {
            "id": (
                booking.experience.slug
            ),
            "slug": (
                booking.experience.slug
            ),
            "title": (
                booking.experience.title
            ),
            "durationMinutes": (
                booking.experience.duration_minutes
            ),
        },
        "professional": {
            "id": str(
                booking.professional.id
            ),
            "slug": (
                booking.professional.slug
            ),
            "name": (
                booking.professional.display_name
            ),
        },
        "establishment": (
            {
                "id": str(
                    booking.establishment.id
                ),
                "slug": (
                    booking.establishment.slug
                ),
                "name": (
                    booking.establishment.name
                ),
            }
            if booking.establishment is not None
            else None
        ),
        "slot": {
            "id": booking.slot.id,
            "startsAt": (
                as_utc(
                    booking.slot.starts_at
                ).isoformat()
            ),
            "endsAt": (
                as_utc(
                    booking.slot.ends_at
                ).isoformat()
            ),
            "localDate": (
                local_start.date().isoformat()
            ),
            "localTime": (
                local_start.strftime(
                    "%H:%M"
                )
            ),
            "localEndsAt": (
                local_end.isoformat()
            ),
            "timezone": timezone_name,
        },
        "holdExpiresAt": (
            as_utc(
                booking.hold_expires_at
            ).isoformat()
            if booking.hold_expires_at
            else None
        ),
        "confirmedAt": (
            as_utc(
                booking.confirmed_at
            ).isoformat()
            if booking.confirmed_at
            else None
        ),
        "cancelledAt": (
            as_utc(
                booking.cancelled_at
            ).isoformat()
            if booking.cancelled_at
            else None
        ),
        "completedAt": (
            as_utc(
                booking.completed_at
            ).isoformat()
            if booking.completed_at
            else None
        ),
        "cancellationReason": (
            booking.cancellation_reason
        ),
        "createdAt": (
            as_utc(
                booking.created_at
            ).isoformat()
        ),
        "canConfirm": (
            booking.status
            == BookingStatus.PENDING
        ),
        "canCancel": (
            booking.status
            in {
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            }
        ),
    }


def _booking_for_client(
    booking_id,
    client_id,
):
    return db.session.scalar(
        _booking_query(
            client_id
        ).where(
            Booking.id == booking_id
        )
    )


def _query_page():
    raw_offset = request.args.get(
        "offset",
        "0",
    )
    raw_limit = request.args.get(
        "limit",
        "20",
    )

    try:
        offset = int(raw_offset)
        limit = int(raw_limit)
    except ValueError:
        return None, api_error(
            "invalid_query_parameter",
            "Paginação inválida.",
            400,
            details={
                "offset": raw_offset,
                "limit": raw_limit,
            },
        )

    if (
        offset < 0
        or limit < 1
        or limit > 50
    ):
        return None, api_error(
            "invalid_query_parameter",
            "Paginação inválida.",
            400,
            details={
                "offset": raw_offset,
                "limit": raw_limit,
            },
        )

    return (offset, limit), None


@api_bookings_bp.get("/bookings")
def bookings():
    client, error = _require_client()

    if error is not None:
        return error

    page, error = _query_page()

    if error is not None:
        return error

    offset, limit = page
    status = (
        request.args.get(
            "status",
            "",
        )
        .strip()
        .lower()
    )

    if (
        status
        and status not in BOOKING_STATUSES
    ):
        return api_error(
            "invalid_query_parameter",
            "Status de reserva inválido.",
            400,
            details={
                "parameter": "status",
                "value": status,
            },
        )

    release_expired_holds()

    filters = [
        Booking.client_id
        == client.id
    ]

    if status:
        filters.append(
            Booking.status == status
        )

    total = (
        db.session.scalar(
            select(
                func.count(
                    Booking.id
                )
            ).where(
                *filters
            )
        )
        or 0
    )

    rows = db.session.scalars(
        select(Booking)
        .where(
            *filters
        )
        .options(
            selectinload(
                Booking.experience
            ),
            selectinload(
                Booking.professional
            ),
            selectinload(
                Booking.establishment
            ),
            selectinload(
                Booking.slot
            ),
        )
        .order_by(
            Booking.created_at.desc(),
            Booking.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    pagination = pagination_payload(
        total=total,
        offset=offset,
        limit=limit,
    )

    return api_json(
        {
            "items": [
                _booking_payload(item)
                for item in rows
            ],
            "pagination": pagination,
        },
        cache_control="private, no-store",
    )


@api_bookings_bp.get(
    "/bookings/<int:booking_id>"
)
def booking_detail(booking_id):
    client, error = _require_client()

    if error is not None:
        return error

    release_expired_holds()

    booking = _booking_for_client(
        booking_id,
        client.id,
    )

    if booking is None:
        return api_error(
            "booking_not_found",
            "Reserva não encontrada.",
            404,
        )

    return api_json(
        {
            "booking": (
                _booking_payload(
                    booking
                )
            )
        },
        cache_control="private, no-store",
    )


@api_bookings_bp.post(
    "/experiences/<slug>/slots/<int:slot_id>/hold"
)
@csrf.exempt
def hold_experience_slot(
    slug,
    slot_id,
):
    client, error = _require_client()

    if error is not None:
        return error

    release_expired_holds()

    slot = db.session.scalar(
        select(
            ExperienceSlot
        )
        .where(
            ExperienceSlot.id == slot_id
        )
        .options(
            selectinload(
                ExperienceSlot.experience
            ),
        )
    )

    if (
        slot is None
        or slot.experience.slug != slug
    ):
        return api_error(
            "slot_not_found",
            "Horário não encontrado para esta experiência.",
            404,
        )

    existing = db.session.scalar(
        _booking_query(
            client.id
        ).where(
            Booking.slot_id == slot.id,
            Booking.status
            == BookingStatus.PENDING,
        )
    )

    now = utcnow()

    if (
        existing is not None
        and existing.hold_expires_at
        and as_utc(
            existing.hold_expires_at
        ) > now
    ):
        return api_json(
            {
                "booking": (
                    _booking_payload(
                        existing
                    )
                )
            },
            cache_control="private, no-store",
        )

    try:
        booking = hold_slot(
            slot.id,
            client,
            now=now,
        )
    except SlotUnavailableError as exc:
        return api_error(
            "slot_unavailable",
            str(exc),
            409,
        )
    except IntegrityError:
        db.session.rollback()

        return api_error(
            "slot_unavailable",
            (
                "Este horário acabou de ficar "
                "indisponível. Escolha outro."
            ),
            409,
        )

    return api_json(
        {
            "booking": (
                _booking_payload(
                    booking
                )
            )
        },
        201,
        cache_control="private, no-store",
    )


@api_bookings_bp.post(
    "/bookings/<int:booking_id>/confirm"
)
@csrf.exempt
def confirm_client_booking(
    booking_id,
):
    client, error = _require_client()

    if error is not None:
        return error

    booking = _booking_for_client(
        booking_id,
        client.id,
    )

    if booking is None:
        return api_error(
            "booking_not_found",
            "Reserva não encontrada.",
            404,
        )

    try:
        booking = confirm_booking(
            booking.id,
            client,
        )
    except BookingStateError as exc:
        return api_error(
            "booking_state_conflict",
            str(exc),
            409,
        )

    calendar_synced = True

    try:
        create_booking_event(
            booking
        )
    except Exception:
        calendar_synced = False
        current_app.logger.warning(
            (
                "Falha ao criar evento da reserva "
                "booking_id=%s"
            ),
            booking.id,
            exc_info=True,
        )

    return api_json(
        {
            "booking": (
                _booking_payload(
                    booking
                )
            ),
            "calendarSynced": (
                calendar_synced
            ),
        },
        cache_control="private, no-store",
    )


@api_bookings_bp.post(
    "/bookings/<int:booking_id>/cancel"
)
@csrf.exempt
def cancel_client_booking(
    booking_id,
):
    client, error = _require_client()

    if error is not None:
        return error

    booking = _booking_for_client(
        booking_id,
        client.id,
    )

    if booking is None:
        return api_error(
            "booking_not_found",
            "Reserva não encontrada.",
            404,
        )

    if (
        booking.status
        == BookingStatus.CANCELLED
    ):
        return api_json(
            {
                "booking": (
                    _booking_payload(
                        booking
                    )
                )
            },
            cache_control="private, no-store",
        )

    try:
        try:
            delete_booking_event(
                booking
            )
        except Exception:
            current_app.logger.warning(
                (
                    "Falha ao remover evento da reserva "
                    "booking_id=%s"
                ),
                booking.id,
                exc_info=True,
            )

        booking = cancel_booking(
            booking
        )
    except BookingStateError as exc:
        return api_error(
            "booking_state_conflict",
            str(exc),
            409,
        )

    return api_json(
        {
            "booking": (
                _booking_payload(
                    booking
                )
            )
        },
        cache_control="private, no-store",
    )
