from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, or_, select

from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.services.time_service import as_utc, local_naive_to_utc, to_local, utcnow
from app.services.notification_service import (
    notify_booking_cancelled,
    notify_booking_confirmed,
)


HOLD_MINUTES = 8
DEFAULT_CUTOFF_MINUTES = 60
ACTIVE_SLOT_STATUSES = {
    SlotStatus.AVAILABLE,
    SlotStatus.HELD,
    SlotStatus.BOOKED,
    SlotStatus.BLOCKED_EXTERNAL,
    SlotStatus.BLOCKED_MANUAL,
}


class SlotUnavailableError(ValueError):
    pass


class BookingStateError(ValueError):
    pass


def effective_cutoff_for_experience(experience, slot_override=None):
    if slot_override is not None:
        return slot_override
    if experience.booking_cutoff_minutes is not None:
        return experience.booking_cutoff_minutes
    professional_cutoff = getattr(experience.professional, "default_booking_cutoff_minutes", None)
    return professional_cutoff if professional_cutoff is not None else DEFAULT_CUTOFF_MINUTES


def effective_cutoff_minutes(slot):
    return effective_cutoff_for_experience(slot.experience, slot.booking_cutoff_minutes)


def booking_deadline(slot):
    return as_utc(slot.starts_at) - timedelta(minutes=effective_cutoff_minutes(slot))


def release_expired_holds(now=None, commit=True):
    now = as_utc(now or utcnow())
    held_slots = db.session.scalars(
        select(ExperienceSlot).where(
            ExperienceSlot.status == SlotStatus.HELD,
            ExperienceSlot.hold_expires_at.is_not(None),
            ExperienceSlot.hold_expires_at <= now,
        )
    ).all()
    changed = False
    for slot in held_slots:
        slot.status = SlotStatus.AVAILABLE
        slot.hold_expires_at = None
        for booking in slot.bookings:
            if booking.status == BookingStatus.PENDING:
                booking.status = BookingStatus.CANCELLED
                booking.cancelled_at = now
                booking.cancellation_reason = "Tempo de confirmação expirado"
                booking.hold_expires_at = None
        changed = True
    if changed and commit:
        db.session.commit()
    return changed


def refresh_slot(slot, now=None):
    now = as_utc(now or utcnow())

    if slot.status == SlotStatus.HELD and slot.hold_expires_at:
        if as_utc(slot.hold_expires_at) <= now:
            slot.status = SlotStatus.AVAILABLE
            slot.hold_expires_at = None
            for booking in slot.bookings:
                if booking.status == BookingStatus.PENDING:
                    booking.status = BookingStatus.CANCELLED
                    booking.cancelled_at = now
                    booking.cancellation_reason = "Tempo de confirmação expirado"
                    booking.hold_expires_at = None

    if slot.status == SlotStatus.AVAILABLE and now >= booking_deadline(slot):
        slot.status = SlotStatus.EXPIRED
        slot.hold_expires_at = None

    return slot


def refresh_experience_slots(experience, now=None, commit=True):
    changed = False
    before = [(slot.id, slot.status, slot.hold_expires_at) for slot in experience.slots]
    for slot in experience.slots:
        refresh_slot(slot, now=now)
    after = [(slot.id, slot.status, slot.hold_expires_at) for slot in experience.slots]
    changed = before != after
    if changed and commit:
        db.session.commit()
    return changed


def available_slots_for_experience(experience, now=None):
    refresh_experience_slots(experience, now=now, commit=True)
    now = as_utc(now or utcnow())
    return [
        slot
        for slot in experience.slots
        if slot.status == SlotStatus.AVAILABLE
        and as_utc(slot.starts_at) > now
        and now < booking_deadline(slot)
    ]


def grouped_available_slots(experience, now=None):
    slots = available_slots_for_experience(experience, now=now)
    timezone_name = experience.professional.timezone
    groups = defaultdict(list)
    for slot in slots:
        local_start = to_local(slot.starts_at, timezone_name)
        groups[local_start.date()].append(
            {
                "id": slot.id,
                "starts_at": local_start,
                "ends_at": to_local(slot.ends_at, timezone_name),
                "deadline": to_local(booking_deadline(slot), timezone_name),
                "cutoff_minutes": effective_cutoff_minutes(slot),
            }
        )
    weekdays = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    months = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    return [
        {
            "date": date,
            "weekday": weekdays[date.weekday()],
            "day": date.day,
            "month": months[date.month - 1],
            "label": f"{date.day} de {months[date.month - 1]}",
            "slots": groups[date],
        }
        for date in sorted(groups)
    ]


def _overlapping_slot(professional_id, starts_at, ends_at, exclude_id=None):
    query = select(ExperienceSlot).where(
        ExperienceSlot.professional_id == professional_id,
        ExperienceSlot.status.in_(ACTIVE_SLOT_STATUSES),
        ExperienceSlot.starts_at < ends_at,
        ExperienceSlot.ends_at > starts_at,
    )
    if exclude_id:
        query = query.where(ExperienceSlot.id != exclude_id)
    return db.session.scalar(query)


def parse_times(raw):
    pieces = (raw or "").replace(";", ",").replace("\n", ",").split(",")
    result = []
    seen = set()
    for piece in pieces:
        value = piece.strip()
        if not value:
            continue
        try:
            parsed = datetime.strptime(value, "%H:%M").time()
        except ValueError as exc:
            raise ValueError(f"Horário inválido: {value}. Use HH:MM, por exemplo 14:30.") from exc
        normalized = parsed.strftime("%H:%M")
        if normalized not in seen:
            seen.add(normalized)
            result.append(parsed)
    if not result:
        raise ValueError("Informe ao menos um horário.")
    return sorted(result)


def create_slots_batch(experience, slot_date, raw_times, cutoff_minutes=None):
    times = parse_times(raw_times)
    timezone_name = experience.professional.timezone
    now = utcnow()
    created = []

    for time_value in times:
        local_start = datetime.combine(slot_date, time_value)
        starts_at = local_naive_to_utc(local_start, timezone_name)
        ends_at = starts_at + timedelta(minutes=experience.duration_minutes)

        if starts_at <= now:
            raise ValueError(f"{time_value.strftime('%H:%M')}: o horário precisa estar no futuro.")

        cutoff = effective_cutoff_for_experience(experience, cutoff_minutes)
        deadline = starts_at - timedelta(minutes=cutoff)
        if now >= deadline:
            raise ValueError(
                f"{time_value.strftime('%H:%M')}: já passou da antecedência mínima para publicação."
            )
        conflict = _overlapping_slot(experience.professional_id, starts_at, ends_at)
        if conflict:
            conflict_local = to_local(conflict.starts_at, timezone_name).strftime("%d/%m %H:%M")
            raise ValueError(
                f"{time_value.strftime('%H:%M')}: conflita com outra oportunidade às {conflict_local}."
            )

        slot = ExperienceSlot(
            experience=experience,
            professional=experience.professional,
            establishment=experience.establishment,
            starts_at=starts_at,
            ends_at=ends_at,
            booking_cutoff_minutes=cutoff_minutes,
        )
        created.append(slot)
        db.session.add(slot)

    db.session.commit()
    return created


def _cancel_pending_booking(booking, now, reason):
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = now
    booking.cancellation_reason = reason
    booking.hold_expires_at = None
    if booking.slot.status == SlotStatus.HELD:
        booking.slot.status = SlotStatus.AVAILABLE
        booking.slot.hold_expires_at = None


def block_slot_manual(slot, reason="Bloqueado manualmente", now=None):
    now = as_utc(now or utcnow())
    if slot.status == SlotStatus.BOOKED:
        return False
    if slot.status == SlotStatus.HELD:
        for booking in slot.bookings:
            if booking.status == BookingStatus.PENDING:
                _cancel_pending_booking(booking, now, reason)
    slot.status = SlotStatus.BLOCKED_MANUAL
    slot.hold_expires_at = None
    db.session.commit()
    return True


def hold_slot(slot_id, client_profile, now=None):
    now = as_utc(now or utcnow())
    release_expired_holds(now=now, commit=False)

    other_pending = db.session.scalars(
        select(Booking).where(
            Booking.client_id == client_profile.id,
            Booking.status == BookingStatus.PENDING,
        )
    ).all()
    for pending in other_pending:
        _cancel_pending_booking(
            pending,
            now,
            "Nova tentativa de reserva iniciou outro hold",
        )

    slot = db.session.scalar(
        select(ExperienceSlot)
        .where(ExperienceSlot.id == slot_id)
        .with_for_update()
    )
    if slot is None:
        db.session.rollback()
        raise SlotUnavailableError("Horário não encontrado.")

    refresh_slot(slot, now=now)
    if slot.experience.status != ExperienceStatus.PUBLISHED:
        db.session.rollback()
        raise SlotUnavailableError("Esta experiência não está disponível no momento.")
    if slot.status != SlotStatus.AVAILABLE:
        db.session.rollback()
        raise SlotUnavailableError("Este horário acabou de ficar indisponível. Escolha outro.")
    if now >= booking_deadline(slot):
        slot.status = SlotStatus.EXPIRED
        db.session.commit()
        raise SlotUnavailableError("O prazo para reservar este horário terminou.")

    overlapping_client_booking = db.session.scalar(
        select(Booking)
        .join(ExperienceSlot, Booking.slot_id == ExperienceSlot.id)
        .where(
            Booking.client_id == client_profile.id,
            Booking.status == BookingStatus.CONFIRMED,
            ExperienceSlot.starts_at < slot.ends_at,
            ExperienceSlot.ends_at > slot.starts_at,
        )
    )
    if overlapping_client_booking is not None:
        db.session.rollback()
        raise SlotUnavailableError("Você já possui uma reserva confirmada nesse intervalo.")

    existing_pending = db.session.scalar(
        select(Booking).where(
            Booking.slot_id == slot.id,
            Booking.client_id == client_profile.id,
            Booking.status == BookingStatus.PENDING,
        )
    )
    if existing_pending:
        existing_pending.status = BookingStatus.CANCELLED
        existing_pending.cancelled_at = now
        existing_pending.cancellation_reason = "Nova tentativa de reserva para o mesmo horário"

    hold_until = min(
        now + timedelta(minutes=HOLD_MINUTES),
        booking_deadline(slot),
    )
    if hold_until <= now:
        slot.status = SlotStatus.EXPIRED
        db.session.commit()
        raise SlotUnavailableError("O prazo para reservar este horário terminou.")

    slot.status = SlotStatus.HELD
    slot.hold_expires_at = hold_until
    booking = Booking(
        client=client_profile,
        experience=slot.experience,
        professional=slot.professional,
        establishment=slot.establishment,
        slot=slot,
        status=BookingStatus.PENDING,
        price_at_booking=Decimal(slot.experience.price),
        hold_expires_at=hold_until,
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def confirm_booking(booking_id, client_profile, now=None):
    now = as_utc(now or utcnow())
    booking = db.session.scalar(
        select(Booking)
        .where(
            Booking.id == booking_id,
            Booking.client_id == client_profile.id,
        )
        .with_for_update()
    )
    if booking is None:
        raise BookingStateError("Reserva não encontrada.")
    if booking.status == BookingStatus.CONFIRMED:
        return booking
    if booking.status != BookingStatus.PENDING:
        raise BookingStateError("Esta reserva não pode mais ser confirmada.")

    slot = booking.slot
    refresh_slot(slot, now=now)
    if slot.status != SlotStatus.HELD or not slot.hold_expires_at or as_utc(slot.hold_expires_at) <= now:
        if booking.status == BookingStatus.PENDING:
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = now
            booking.cancellation_reason = "Tempo de confirmação expirado"
        db.session.commit()
        raise BookingStateError("O tempo para confirmar este horário expirou.")

    if now >= booking_deadline(slot):
        slot.status = SlotStatus.EXPIRED
        slot.hold_expires_at = None
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = now
        booking.cancellation_reason = "Prazo mínimo para reserva atingido"
        db.session.commit()
        raise BookingStateError("O prazo para reservar este horário terminou.")

    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = now
    booking.hold_expires_at = None
    slot.status = SlotStatus.BOOKED
    slot.hold_expires_at = None
    db.session.commit()

    notify_booking_confirmed(
        booking
    )

    return booking


def cancel_booking(booking, reason="Cancelada pelo cliente", now=None):
    now = as_utc(now or utcnow())
    was_confirmed = (
        booking.status
        == BookingStatus.CONFIRMED
    )
    if booking.status not in {BookingStatus.PENDING, BookingStatus.CONFIRMED}:
        raise BookingStateError("Esta reserva não pode ser cancelada.")
    if as_utc(booking.slot.starts_at) <= now:
        raise BookingStateError("O horário desta reserva já começou ou passou.")

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = now
    booking.cancellation_reason = reason
    booking.hold_expires_at = None

    slot = booking.slot
    if as_utc(slot.starts_at) > now and now < booking_deadline(slot):
        slot.status = SlotStatus.AVAILABLE
    else:
        slot.status = SlotStatus.EXPIRED
    slot.hold_expires_at = None
    db.session.commit()

    if was_confirmed:
        notify_booking_cancelled(
            booking
        )

    return booking


def reopen_manual_slot(slot, now=None):
    now = as_utc(now or utcnow())

    if slot.status != SlotStatus.BLOCKED_MANUAL:
        raise BookingStateError(
            "Somente horários bloqueados manualmente podem ser liberados."
        )

    slot.status = SlotStatus.AVAILABLE
    slot.hold_expires_at = None

    refresh_slot(
        slot,
        now=now,
    )

    db.session.commit()

    return slot


def complete_booking(
    booking,
    *,
    now=None,
):
    now = as_utc(now or utcnow())

    if booking.status != BookingStatus.CONFIRMED:
        raise BookingStateError(
            "Somente reservas confirmadas podem ser concluídas."
        )

    if as_utc(booking.slot.ends_at) > now:
        raise BookingStateError(
            "O atendimento ainda não terminou."
        )

    booking.status = BookingStatus.COMPLETED
    booking.completed_at = now

    db.session.commit()

    return booking


def mark_booking_no_show(
    booking,
    *,
    now=None,
):
    now = as_utc(now or utcnow())

    if booking.status != BookingStatus.CONFIRMED:
        raise BookingStateError(
            "Somente reservas confirmadas podem ser marcadas como no-show."
        )

    if as_utc(booking.slot.starts_at) > now:
        raise BookingStateError(
            "O horário do atendimento ainda não começou."
        )

    booking.status = BookingStatus.NO_SHOW
    booking.no_show_at = now

    db.session.commit()

    return booking


def mark_external_conflict(slot, provider="google", external_event_id=None, reason=None, now=None, commit=True):
    now = as_utc(now or utcnow())
    if slot.status not in {SlotStatus.AVAILABLE, SlotStatus.HELD}:
        return False

    if slot.status == SlotStatus.HELD:
        for booking in slot.bookings:
            if booking.status == BookingStatus.PENDING:
                booking.status = BookingStatus.CANCELLED
                booking.cancelled_at = now
                booking.cancellation_reason = "Horário ocupado na agenda conectada"
                booking.hold_expires_at = None

    slot.status = SlotStatus.BLOCKED_EXTERNAL
    slot.hold_expires_at = None
    slot.external_calendar_provider = provider
    slot.external_event_id = external_event_id
    slot.external_block_reason = reason or "Conflito detectado na agenda conectada"
    if commit:
        db.session.commit()
    return True


def clear_external_conflict(slot, now=None, commit=True):
    if slot.status != SlotStatus.BLOCKED_EXTERNAL:
        return False
    slot.external_calendar_provider = None
    slot.external_event_id = None
    slot.external_block_reason = None
    now = as_utc(now or utcnow())
    slot.status = SlotStatus.EXPIRED if now >= booking_deadline(slot) else SlotStatus.AVAILABLE
    if commit:
        db.session.commit()
    return True
