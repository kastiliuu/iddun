from sqlalchemy import select

from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import ExperienceStatus
from app.models.reschedule_request import RescheduleRequest
from app.services.booking_service import BookingStateError, booking_deadline
from app.services.time_service import as_utc, utcnow


def pending_reschedule(booking_id):
    return db.session.scalar(
        select(RescheduleRequest).where(
            RescheduleRequest.booking_id == booking_id,
            RescheduleRequest.status == "pending",
        )
    )


def eligible_reschedule_slots(booking):
    now = utcnow()
    candidates = db.session.scalars(
        select(ExperienceSlot).where(
            ExperienceSlot.experience_id == booking.experience_id,
            ExperienceSlot.professional_id == booking.professional_id,
            ExperienceSlot.establishment_id.is_(None)
            if booking.establishment_id is None
            else ExperienceSlot.establishment_id == booking.establishment_id,
            ExperienceSlot.status == SlotStatus.AVAILABLE,
            ExperienceSlot.starts_at > now,
        ).order_by(ExperienceSlot.starts_at.asc()).limit(40)
    ).all()
    return [slot for slot in candidates if now < booking_deadline(slot)]


def request_reschedule(booking, user, slot_id, reason=None):
    if booking.client.user_id != user.id:
        raise BookingStateError("Reserva não pertence a esta conta.")
    if booking.status != BookingStatus.CONFIRMED or as_utc(booking.slot.starts_at) <= utcnow():
        raise BookingStateError("Somente reservas futuras confirmadas podem ser reagendadas.")
    if pending_reschedule(booking.id):
        raise BookingStateError("Já existe uma solicitação de reagendamento pendente.")
    slot = db.session.get(ExperienceSlot, slot_id)
    if slot is None or slot.id == booking.slot_id or (
        slot.experience_id, slot.professional_id, slot.establishment_id
    ) != (booking.experience_id, booking.professional_id, booking.establishment_id):
        raise BookingStateError("Escolha um horário válido da mesma oferta e executor.")
    if booking.experience.status != ExperienceStatus.PUBLISHED:
        raise BookingStateError("Esta experiência não está disponível.")
    now = utcnow()
    if slot.status != SlotStatus.AVAILABLE or now >= booking_deadline(slot):
        raise BookingStateError("O horário solicitado não está disponível.")
    record = RescheduleRequest(
        booking_id=booking.id,
        original_slot_id=booking.slot_id,
        requested_slot_id=slot.id,
        requested_by_user_id=user.id,
        reason=(reason or "").strip()[:255] or None,
        status="pending",
        requested_at=now,
    )
    db.session.add(record)
    db.session.commit()
    return record


def withdraw_reschedule(booking, user):
    if booking.client.user_id != user.id:
        raise BookingStateError("Reserva não pertence a esta conta.")
    record = pending_reschedule(booking.id)
    if record is None:
        raise BookingStateError("Não há reagendamento pendente.")
    record.status = "withdrawn"
    record.resolved_at = utcnow()
    record.resolved_by_user_id = user.id
    db.session.commit()
    return record


def resolve_reschedule(booking_id, user, *, approve, reason=None):
    # Lock the booking first to serialize decisions about its slot.
    booking = db.session.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None or booking.professional.user_id != user.id:
        raise BookingStateError("Somente o executor autorizado pode analisar esta solicitação.")
    record = pending_reschedule(booking_id)
    if record is None:
        raise BookingStateError("Não há reagendamento pendente.")
    now = utcnow()
    if booking.status != BookingStatus.CONFIRMED or booking.slot_id != record.original_slot_id:
        raise BookingStateError("A reserva foi alterada. Solicitação exige nova análise.")
    if not approve:
        record.status = "rejected"
        record.resolved_at = now
        record.resolved_by_user_id = user.id
        record.resolution_reason = (reason or "").strip()[:255] or None
        db.session.commit()
        return record

    target = db.session.scalar(
        select(ExperienceSlot).where(ExperienceSlot.id == record.requested_slot_id).with_for_update()
    )
    source = db.session.scalar(
        select(ExperienceSlot).where(ExperienceSlot.id == booking.slot_id).with_for_update()
    )
    if (target is None or target.status != SlotStatus.AVAILABLE
        or target.experience_id != booking.experience_id
        or target.professional_id != booking.professional_id
        or target.establishment_id != booking.establishment_id
        or booking.experience.status != ExperienceStatus.PUBLISHED
        or now >= booking_deadline(target)
        or as_utc(target.starts_at) <= now
        or as_utc(source.starts_at) <= now):
        raise BookingStateError("Novo horário indisponível. A reserva original foi preservada.")

    # No other active booking may hold the target. The partial active-slot unique
    # index also protects the reassignment at commit.
    collision = db.session.scalar(
        select(Booking.id).where(
            Booking.slot_id == target.id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
        ).limit(1)
    )
    overlapping = db.session.scalar(
        select(Booking.id).join(ExperienceSlot, Booking.slot_id == ExperienceSlot.id).where(
            Booking.client_id == booking.client_id,
            Booking.id != booking.id,
            Booking.status == BookingStatus.CONFIRMED,
            ExperienceSlot.starts_at < target.ends_at,
            ExperienceSlot.ends_at > target.starts_at,
        ).limit(1)
    )
    if collision is not None or overlapping is not None:
        raise BookingStateError("Conflito de agenda. A reserva original foi preservada.")

    # One commit atomically switches both slot states, booking pointer and audit.
    booking.slot_id = target.id
    source.status = SlotStatus.AVAILABLE if now < booking_deadline(source) else SlotStatus.EXPIRED
    source.hold_expires_at = None
    target.status = SlotStatus.BOOKED
    target.hold_expires_at = None
    record.status = "executed"
    record.resolved_at = now
    record.resolved_by_user_id = user.id
    record.resolution_reason = (reason or "").strip()[:255] or None
    db.session.commit()
    return record
