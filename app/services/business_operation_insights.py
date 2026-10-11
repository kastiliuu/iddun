"""Read-only operational indicators for one IDDUN Business establishment.

All queries must be scoped by establishment_id before aggregation.
Values from completed bookings represent contracted booking prices,
not received payments or business revenue.
"""
from decimal import Decimal

from sqlalchemy import func, select

from app.extensions import db
from app.models.booking import Booking, BookingStatus
from app.models.experience import Experience


def business_operation_insights(establishment_id):
    statuses = dict(
        db.session.execute(
            select(Booking.status, func.count(Booking.id))
            .where(Booking.establishment_id == establishment_id)
            .group_by(Booking.status)
        ).all()
    )
    counts = {
        status: statuses.get(status, 0)
        for status, _ in BookingStatus.CHOICES
    }
    completed_value = db.session.scalar(
        select(func.sum(Booking.price_at_booking))
        .where(
            Booking.establishment_id == establishment_id,
            Booking.status == BookingStatus.COMPLETED,
        )
    ) or Decimal("0.00")

    services = db.session.execute(
        select(
            Experience.id,
            Experience.title,
            func.count(Booking.id).label("completed_count"),
        )
        .join(
            Booking,
            (Booking.experience_id == Experience.id)
            & (Booking.status == BookingStatus.COMPLETED)
            & (Booking.establishment_id == establishment_id),
            isouter=True,
        )
        .where(Experience.establishment_id == establishment_id)
        .group_by(Experience.id, Experience.title)
        .order_by(func.count(Booking.id).desc(), Experience.title.asc())
        .limit(5)
    ).all()

    return {
        "counts": counts,
        "total_bookings": sum(counts.values()),
        "completed_booking_value": completed_value,
        "top_services": [
            {"title": title, "completed_count": count}
            for _, title, count in services
            if count
        ],
    }
