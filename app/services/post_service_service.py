"""Post-service eligibility: never reuse historical prices or reserve silently."""
from sqlalchemy import select

from app.extensions import db
from app.models.booking import BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import ExperienceStatus
from app.services.booking_service import booking_deadline
from app.services.time_service import as_utc, utcnow


def rebook_offer(booking, *, now=None):
    """Returns the current offer only when the original executor/location still match.

    Display is advisory; start_booking/hold_slot remains the authoritative,
    transactionally validated step for any new booking.
    """
    now = as_utc(now or utcnow())
    experience = booking.experience
    if booking.status != BookingStatus.COMPLETED:
        return None
    if (experience.status != ExperienceStatus.PUBLISHED
        or experience.professional_id != booking.professional_id
        or experience.establishment_id != booking.establishment_id):
        return None
    candidates = db.session.scalars(
        select(ExperienceSlot)
        .where(
            ExperienceSlot.experience_id == experience.id,
            ExperienceSlot.professional_id == booking.professional_id,
            ExperienceSlot.establishment_id.is_(None) if booking.establishment_id is None
            else ExperienceSlot.establishment_id == booking.establishment_id,
            ExperienceSlot.status == SlotStatus.AVAILABLE,
            ExperienceSlot.starts_at > now,
        )
        .order_by(ExperienceSlot.starts_at.asc())
    ).all()
    return experience if any(now < booking_deadline(slot) for slot in candidates) else None
