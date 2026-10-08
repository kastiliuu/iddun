from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.services.time_service import (
    local_naive_to_utc,
    to_local,
    timezone_or_default,
    utcnow,
)


ACTIVE_TODAY_BOOKING_STATUSES = {
    BookingStatus.CONFIRMED,
    BookingStatus.COMPLETED,
}


def _today_bounds(profile):
    timezone_name = profile.timezone

    local_now = to_local(
        utcnow(),
        timezone_name,
    )

    local_date = local_now.date()

    start_utc = local_naive_to_utc(
        datetime.combine(
            local_date,
            time.min,
        ),
        timezone_name,
    )

    end_utc = local_naive_to_utc(
        datetime.combine(
            local_date,
            time.max,
        ),
        timezone_name,
    )

    return (
        local_now,
        local_date,
        start_utc,
        end_utc,
    )


def _booking_for_slot(slot):
    for booking in slot.bookings:
        if booking.status in {
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
            BookingStatus.COMPLETED,
        }:
            return booking

    return None


def _whatsapp_url(phone):
    digits = "".join(
        character
        for character in (
            phone or ""
        )
        if character.isdigit()
    )

    if not digits:
        return None

    if len(digits) in {10, 11}:
        digits = f"55{digits}"

    return (
        "https://wa.me/"
        f"{digits}"
    )


def professional_dashboard_context(
    profile,
):
    (
        local_now,
        local_date,
        start_utc,
        end_utc,
    ) = _today_bounds(
        profile
    )

    slots = list(
        db.session.scalars(
            select(
                ExperienceSlot
            )
            .where(
                ExperienceSlot.professional_id
                == profile.id,
                ExperienceSlot.starts_at
                >= start_utc,
                ExperienceSlot.starts_at
                <= end_utc,
            )
            .order_by(
                ExperienceSlot.starts_at.asc(),
                ExperienceSlot.id.asc(),
            )
        ).all()
    )

    timeline = []

    for slot in slots:
        booking = _booking_for_slot(
            slot
        )

        client = (
            booking.client
            if booking is not None
            else None
        )

        timeline.append(
            {
                "slot": slot,
                "booking": booking,
                "client": client,
                "starts_at": to_local(
                    slot.starts_at,
                    profile.timezone,
                ),
                "ends_at": to_local(
                    slot.ends_at,
                    profile.timezone,
                ),
                "whatsapp_url": (
                    _whatsapp_url(
                        client.phone
                    )
                    if client
                    else None
                ),
            }
        )

    today_bookings = [
        item["booking"]
        for item in timeline
        if (
            item["booking"]
            is not None
            and item["booking"].status
            in ACTIVE_TODAY_BOOKING_STATUSES
        )
    ]

    forecast_revenue = sum(
        (
            Decimal(
                booking.price_at_booking
                or 0
            )
            for booking
            in today_bookings
        ),
        Decimal("0"),
    )

    free_slots = [
        item
        for item in timeline
        if (
            item["slot"].status
            == SlotStatus.AVAILABLE
            and item["starts_at"]
            > local_now
        )
    ]

    free_minutes = sum(
        int(
            (
                item["ends_at"]
                - item["starts_at"]
            ).total_seconds()
            // 60
        )
        for item in free_slots
    )

    next_appointment = next(
        (
            item
            for item in timeline
            if (
                item["booking"]
                is not None
                and item["booking"].status
                == BookingStatus.CONFIRMED
                and item["starts_at"]
                > local_now
            )
        ),
        None,
    )

    return {
        "local_now": local_now,
        "local_date": local_date,
        "timeline": timeline,
        "today_booking_count": len(
            today_bookings
        ),
        "forecast_revenue":
            forecast_revenue,
        "free_slots":
            free_slots,
        "free_minutes":
            free_minutes,
        "next_appointment":
            next_appointment,
        "slot_status":
            SlotStatus,
        "booking_status":
            BookingStatus,
    }
