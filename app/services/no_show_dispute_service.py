from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.booking import BookingStatus
from app.models.no_show_dispute import NoShowDispute
from app.models.user import UserRole
from app.services.booking_service import BookingStateError
from app.services.time_service import utcnow


def pending_dispute(booking_id):
    return db.session.scalar(select(NoShowDispute).where(
        NoShowDispute.booking_id == booking_id,
        NoShowDispute.status == "pending",
    ))


def submit_dispute(booking, user, justification, evidence_reference=None):
    if booking.client.user_id != user.id:
        raise BookingStateError("Reserva não pertence a esta conta.")
    if booking.status != BookingStatus.NO_SHOW:
        raise BookingStateError("Somente ausências registradas podem ser contestadas.")
    justification = (justification or "").strip()
    if not 10 <= len(justification) <= 2000:
        raise BookingStateError("Justificativa deve ter entre 10 e 2000 caracteres.")
    # Optional private plain-text reference only. No URLs/uploads or external
    # content are retrieved or rendered as links in V0.
    evidence_reference = (evidence_reference or "").strip()
    if len(evidence_reference) > 500:
        raise BookingStateError("Referência da evidência excede 500 caracteres.")
    if pending_dispute(booking.id) is not None:
        raise BookingStateError("Esta reserva já possui contestação pendente.")
    dispute = NoShowDispute(
        booking_id=booking.id, client_user_id=user.id,
        justification=justification,
        evidence_reference=evidence_reference or None,
        status="pending", created_at=utcnow(),
    )
    db.session.add(dispute)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BookingStateError("Esta reserva já possui contestação pendente.")
    return dispute


def decide_dispute(dispute, moderator, decision, note):
    if moderator.role != UserRole.ADMIN or not moderator.is_active:
        raise BookingStateError("A moderação é exclusiva de administradores autorizados.")
    if dispute.status != "pending":
        raise BookingStateError("Esta contestação já foi analisada.")
    if decision not in {"accepted", "rejected"}:
        raise BookingStateError("Decisão inválida.")
    note = (note or "").strip()
    if not 10 <= len(note) <= 2000:
        raise BookingStateError("Informe uma justificativa de 10 a 2000 caracteres.")
    dispute.status = decision
    dispute.reviewer_user_id = moderator.id
    dispute.resolution_note = note
    dispute.resolved_at = utcnow()
    # No mutation of booking status, no-show timestamp or original event.
    db.session.commit()
    return dispute
