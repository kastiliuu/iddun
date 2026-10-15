from sqlalchemy import select

from app.extensions import db
from app.models.booking import BookingStatus
from app.models.cancellation_request import CancellationRequest
from app.services.booking_service import BookingStateError, cancel_booking
from app.services.time_service import as_utc, utcnow


def pending_cancellation(booking_id):
    return db.session.scalar(
        select(CancellationRequest).where(
            CancellationRequest.booking_id == booking_id,
            CancellationRequest.status == "pending",
        ).order_by(CancellationRequest.id.desc())
    )


def request_cancellation(booking, user, reason=None):
    if booking.client.user_id != user.id:
        raise BookingStateError("Reserva não pertence a esta conta.")
    if booking.status != BookingStatus.CONFIRMED:
        raise BookingStateError("Somente reservas confirmadas podem solicitar cancelamento.")
    if as_utc(booking.slot.starts_at) <= utcnow():
        raise BookingStateError("Não é possível solicitar cancelamento após o início.")
    existing = pending_cancellation(booking.id)
    if existing is not None:
        return existing
    item = CancellationRequest(
        booking_id=booking.id,
        client_user_id=user.id,
        reason=(reason or "").strip()[:255] or None,
        status="pending",
        requested_at=utcnow(),
    )
    db.session.add(item)
    db.session.commit()
    return item


def withdraw_cancellation(booking, user):
    if booking.client.user_id != user.id:
        raise BookingStateError("Reserva não pertence a esta conta.")
    item = pending_cancellation(booking.id)
    if item is None:
        raise BookingStateError("Não há solicitação pendente.")
    item.status = "withdrawn"
    item.resolved_at = utcnow()
    item.resolved_by_user_id = user.id
    db.session.commit()
    return item


def execute_cancellation(booking, user, reason):
    if booking.professional.user_id != user.id:
        raise BookingStateError("Apenas o executor autorizado pode cancelar a reserva.")
    reason = (reason or "").strip()
    if not reason:
        raise BookingStateError("Informe o motivo da efetivação.")
    item = pending_cancellation(booking.id)
    if item is None:
        raise BookingStateError("Não há solicitação pendente.")
    # The underlying operation validates booking state and slot timing.
    # Never acknowledge a request until its booking cancellation commits.
    cancel_booking(booking, reason=reason[:255])
    item.status = "executed"
    item.resolved_at = utcnow()
    item.resolved_by_user_id = user.id
    item.resolution_reason = reason[:255]
    db.session.commit()
    return item
