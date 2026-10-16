from flask import Blueprint, current_app, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import csrf, db
from app.models.no_show_dispute import NoShowDispute
from app.services.booking_share_service import calendar_payload, share_payload
from app.models.reputation import ReviewTarget
from app.services.reputation_service import get_review, save_review, ReviewError
from app.services.no_show_dispute_service import submit_dispute, pending_dispute
from app.models.cancellation_request import CancellationRequest
from app.models.reschedule_request import RescheduleRequest
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
from app.services.cancellation_request_service import (
    request_cancellation, withdraw_cancellation, pending_cancellation,
)
from app.services.reschedule_service import request_reschedule, withdraw_reschedule, pending_reschedule, eligible_reschedule_slots
from app.services.post_service_service import rebook_offer
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
        "canCancel": booking.status == BookingStatus.PENDING,
        "canRequestCancellation": booking.status == BookingStatus.CONFIRMED,
        "cancellationRequestStatus": (
            pending_cancellation(booking.id).status if pending_cancellation(booking.id) else None
        ),
        "rescheduleRequestStatus": (
            pending_reschedule(booking.id).status if pending_reschedule(booking.id) else None
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


@api_bookings_bp.post("/bookings/<int:booking_id>/cancel")
@csrf.exempt
def cancel_client_booking(booking_id):
    """Backwards-compatible endpoint: now submits a request, never cancels."""
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    # An unconfirmed hold is not yet a confirmed booking: allow release.
    if booking.status == BookingStatus.PENDING:
        try:
            cancel_booking(booking, reason="Retenção temporária liberada pelo cliente")
        except BookingStateError as exc:
            return api_error("booking_state_conflict", str(exc), 409)
        return api_json(
            {"booking": _booking_payload(booking)},
            cache_control="private, no-store",
        )
    if booking.status == BookingStatus.CANCELLED:
        return api_json(
            {"booking": _booking_payload(booking)},
            cache_control="private, no-store",
        )
    user = _bearer_user()
    payload = request.get_json(silent=True) or {}
    try:
        item = request_cancellation(booking, user, payload.get("reason"))
    except BookingStateError as exc:
        return api_error("booking_state_conflict", str(exc), 409)
    return api_json(
        {"booking": _booking_payload(booking),
         "cancellationRequest": {"id": item.id, "status": item.status, "reason": item.reason}},
        cache_control="private, no-store",
    )


@api_bookings_bp.post("/bookings/<int:booking_id>/cancel-request/withdraw")
@csrf.exempt
def withdraw_client_booking_cancellation(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    try:
        item = withdraw_cancellation(booking, _bearer_user())
    except BookingStateError as exc:
        return api_error("booking_state_conflict", str(exc), 409)
    return api_json(
        {"booking": _booking_payload(booking), "cancellationRequest": {"id": item.id, "status": item.status}},
        cache_control="private, no-store",
    )


@api_bookings_bp.get("/bookings/<int:booking_id>/actions")
def booking_actions(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    pending = pending_reschedule(booking.id)
    alternatives = (
        eligible_reschedule_slots(booking)
        if booking.status == BookingStatus.CONFIRMED and pending is None
        else []
    )
    rebook_eligible = rebook_offer(booking) is not None
    return api_json({
        "rescheduleRequestStatus": pending.status if pending else None,
        "rescheduleSlots": [
            {"id": slot.id, "startsAt": as_utc(slot.starts_at).isoformat(),
             "localDate": to_local(slot.starts_at, booking.professional.timezone).strftime("%Y-%m-%d"),
             "localTime": to_local(slot.starts_at, booking.professional.timezone).strftime("%H:%M"),
             "timezone": booking.professional.timezone}
            for slot in alternatives
        ],
        "canRebook": rebook_eligible,
        "rebookExperienceSlug": booking.experience.slug if rebook_eligible else None,
    }, cache_control="private, no-store")


@api_bookings_bp.post("/bookings/<int:booking_id>/reschedule-request")
@csrf.exempt
def request_client_booking_reschedule(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    payload = request.get_json(silent=True) or {}
    try:
        slot_id = int(payload.get("slotId") or 0)
        item = request_reschedule(booking, _bearer_user(), slot_id, payload.get("reason"))
    except (BookingStateError, ValueError) as exc:
        return api_error("booking_state_conflict", str(exc), 409)
    return api_json({"booking": _booking_payload(booking),
                     "rescheduleRequest": {"id": item.id, "status": item.status}},
                    cache_control="private, no-store")


@api_bookings_bp.post("/bookings/<int:booking_id>/reschedule-request/withdraw")
@csrf.exempt
def withdraw_client_booking_reschedule(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    try:
        item = withdraw_reschedule(booking, _bearer_user())
    except BookingStateError as exc:
        return api_error("booking_state_conflict", str(exc), 409)
    return api_json({"booking": _booking_payload(booking),
                     "rescheduleRequest": {"id": item.id, "status": item.status}},
                    cache_control="private, no-store")


@api_bookings_bp.get("/bookings/<int:booking_id>/timeline")
def booking_timeline(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    events = [{"at": booking.created_at, "label": "Reserva iniciada"}]
    for date, label in (
        (booking.confirmed_at, "Reserva confirmada"),
        (booking.cancelled_at, "Reserva cancelada"),
        (booking.completed_at, "Atendimento concluído"),
        (booking.no_show_at, "Ausência registrada"),
    ):
        if date is not None:
            events.append({"at": date, "label": label})
    cancellations = db.session.scalars(
        select(CancellationRequest).where(CancellationRequest.booking_id == booking.id)
    ).all()
    for item in cancellations:
        events.append({"at": item.requested_at, "label": "Cancelamento solicitado"})
        if item.resolved_at:
            events.append({"at": item.resolved_at, "label": {
                "withdrawn": "Cancelamento retirado",
                "executed": "Cancelamento efetivado",
            }.get(item.status, "Solicitação de cancelamento encerrada")})
    reschedules = db.session.scalars(
        select(RescheduleRequest).where(RescheduleRequest.booking_id == booking.id)
    ).all()
    for item in reschedules:
        events.append({"at": item.requested_at, "label": "Reagendamento solicitado"})
        if item.resolved_at:
            events.append({"at": item.resolved_at, "label": {
                "withdrawn": "Reagendamento retirado",
                "executed": "Reagendamento confirmado",
                "rejected": "Reagendamento recusado",
            }.get(item.status, "Solicitação de reagendamento encerrada")})
    events.sort(key=lambda event: as_utc(event["at"]))
    return api_json({
        "items": [{"at": as_utc(event["at"]).isoformat(), "label": event["label"]}
                  for event in events],
    }, cache_control="private, no-store")


def _dispute_payload(dispute):
    return {
        "id": dispute.id,
        "status": dispute.status,
        "justification": dispute.justification,
        "evidenceReference": dispute.evidence_reference,
        "resolutionNote": dispute.resolution_note,
        "createdAt": as_utc(dispute.created_at).isoformat(),
        "resolvedAt": as_utc(dispute.resolved_at).isoformat() if dispute.resolved_at else None,
    }


@api_bookings_bp.get("/bookings/<int:booking_id>/no-show-disputes")
def list_client_no_show_disputes(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    disputes = db.session.scalars(
        select(NoShowDispute).where(NoShowDispute.booking_id == booking.id)
        .order_by(NoShowDispute.created_at.asc(), NoShowDispute.id.asc())
    ).all()
    return api_json({
        "canDispute": booking.status == BookingStatus.NO_SHOW and pending_dispute(booking.id) is None,
        "items": [_dispute_payload(item) for item in disputes],
    }, cache_control="private, no-store")


@api_bookings_bp.post("/bookings/<int:booking_id>/no-show-disputes")
@csrf.exempt
def create_client_no_show_dispute(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("invalid_payload", "Informe os dados da contestação.", 400)
    if not isinstance(payload.get("justification"), str) or not isinstance(payload.get("evidenceReference", ""), str):
        return api_error("invalid_payload", "Justificativa ou referência inválida.", 400)
    try:
        dispute = submit_dispute(booking, _bearer_user(), payload["justification"], payload.get("evidenceReference"))
    except BookingStateError as exc:
        return api_error("booking_state_conflict", str(exc), 409)
    return api_json({"dispute": _dispute_payload(dispute)}, 201, cache_control="private, no-store")


@api_bookings_bp.get("/bookings/<int:booking_id>/review")
def get_client_booking_review(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    review = get_review(booking.id, ReviewTarget.PROFESSIONAL)
    return api_json({
        "eligible": booking.status == BookingStatus.COMPLETED,
        "review": ({
            "rating": review.rating, "recommended": review.recommended,
            "comment": review.comment,
        } if review else None),
    }, cache_control="private, no-store")


@api_bookings_bp.post("/bookings/<int:booking_id>/review")
@csrf.exempt
def save_client_booking_review(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("invalid_payload", "Informe os dados da avaliação.", 400)
    rating = payload.get("rating")
    recommended = payload.get("recommended")
    comment = payload.get("comment")
    if isinstance(rating, bool) or not isinstance(rating, int) or not isinstance(recommended, bool) or (comment is not None and not isinstance(comment, str)):
        return api_error("invalid_payload", "Avaliação inválida.", 400)
    if comment is not None and len(comment) > 2000:
        return api_error("invalid_payload", "Comentário muito longo.", 400)
    try:
        save_review(
            booking=booking, client_profile=client,
            target_type=ReviewTarget.PROFESSIONAL,
            rating=rating, recommended=recommended, comment=comment,
        )
        db.session.commit()
    except ReviewError as exc:
        db.session.rollback()
        return api_error("review_not_allowed", str(exc), 409)
    return api_json({"saved": True}, cache_control="private, no-store")


@api_bookings_bp.get("/bookings/<int:booking_id>/calendar")
def client_booking_calendar(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    ics = calendar_payload(booking)
    if ics is None:
        return api_error("booking_not_exportable", "Reserva indisponível para calendário.", 409)
    return api_json({
        "ics": ics,
        "startsAt": as_utc(booking.slot.starts_at).isoformat(),
        "endsAt": as_utc(booking.slot.ends_at).isoformat(),
        "title": "IDDUN - " + booking.experience.title,
        "uid": f"iddun-booking-{booking.id}@iddun.local",
    }, cache_control="private, no-store")


@api_bookings_bp.get("/bookings/<int:booking_id>/share")
def client_booking_share(booking_id):
    client, error = _require_client()
    if error is not None:
        return error
    booking = _booking_for_client(booking_id, client.id)
    if booking is None:
        return api_error("booking_not_found", "Reserva não encontrada.", 404)
    message = share_payload(booking)
    if message is None:
        return api_error("booking_not_shareable", "Reserva indisponível para compartilhamento.", 409)
    return api_json({"message": message}, cache_control="private, no-store")
