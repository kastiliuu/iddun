from calendar import monthrange
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
)
from app.services.time_service import (
    as_utc,
    local_naive_to_utc,
    to_local,
    utcnow,
)


CAPACITY_BOOKING_STATUSES = {
    BookingStatus.CONFIRMED,
    BookingStatus.COMPLETED,
    BookingStatus.NO_SHOW,
}


def _minutes(start, end):
    return max(
        0,
        int(
            (
                end - start
            ).total_seconds()
            // 60
        ),
    )


def _local_interval(
    profile,
    day,
    start_time,
    end_time,
):
    return (
        local_naive_to_utc(
            datetime.combine(
                day,
                start_time,
            ),
            profile.timezone,
        ),
        local_naive_to_utc(
            datetime.combine(
                day,
                end_time,
            ),
            profile.timezone,
        ),
    )


def _working_segments(
    profile,
    day,
    rules,
):
    rule = rules.get(
        day.weekday()
    )

    if rule is None:
        return []

    start, end = _local_interval(
        profile,
        day,
        rule.start_time,
        rule.end_time,
    )

    if not (
        rule.break_start_time
        and rule.break_end_time
    ):
        return [(start, end)]

    break_start, break_end = (
        _local_interval(
            profile,
            day,
            rule.break_start_time,
            rule.break_end_time,
        )
    )

    segments = []

    if break_start > start:
        segments.append(
            (
                start,
                min(
                    break_start,
                    end,
                ),
            )
        )

    if break_end < end:
        segments.append(
            (
                max(
                    break_end,
                    start,
                ),
                end,
            )
        )

    return [
        segment
        for segment in segments
        if segment[1] > segment[0]
    ]


def _clip(
    start,
    end,
    segment_start,
    segment_end,
):
    clipped_start = max(
        as_utc(start),
        segment_start,
    )
    clipped_end = min(
        as_utc(end),
        segment_end,
    )

    if clipped_end <= clipped_start:
        return None

    return (
        clipped_start,
        clipped_end,
    )


def _merge_intervals(
    intervals,
):
    if not intervals:
        return []

    ordered = sorted(
        intervals,
        key=lambda item:
            item[0],
    )

    merged = [
        ordered[0]
    ]

    for start, end in ordered[1:]:
        last_start, last_end = (
            merged[-1]
        )

        if start <= last_end:
            merged[-1] = (
                last_start,
                max(
                    last_end,
                    end,
                ),
            )
        else:
            merged.append(
                (
                    start,
                    end,
                )
            )

    return merged


def _period_bookings(
    profile,
    start_day,
    end_day_exclusive,
):
    start_utc = (
        local_naive_to_utc(
            datetime.combine(
                start_day,
                datetime.min.time(),
            ),
            profile.timezone,
        )
    )
    end_utc = (
        local_naive_to_utc(
            datetime.combine(
                end_day_exclusive,
                datetime.min.time(),
            ),
            profile.timezone,
        )
    )

    return list(
        db.session.scalars(
            select(Booking)
            .options(
                selectinload(Booking.slot),
            )
            .where(
                Booking.professional_id
                == profile.id,
                Booking.status.in_(
                    CAPACITY_BOOKING_STATUSES
                ),
                Booking.slot.has(
                    ExperienceSlot.starts_at
                    < end_utc
                ),
                Booking.slot.has(
                    ExperienceSlot.ends_at
                    > start_utc
                ),
            )
            .order_by(
                Booking.id.asc()
            )
        ).all()
    )


def _period_capacity(
    profile,
    *,
    start_day,
    end_day_exclusive,
):
    rules = {
        row.weekday: row
        for row in profile.working_hours
    }

    if not rules:
        return {
            "configured": False,
            "capacity_minutes": 0,
            "occupied_minutes": 0,
            "available_minutes": 0,
            "occupancy_percent": 0.0,
            "days": [],
        }

    bookings = _period_bookings(
        profile,
        start_day,
        end_day_exclusive,
    )

    bookings_by_date = {}

    for booking in bookings:
        local_start = to_local(
            booking.slot.starts_at,
            profile.timezone,
        )
        local_end = to_local(
            booking.slot.ends_at,
            profile.timezone,
        )

        cursor = local_start.date()
        last_day = local_end.date()

        while cursor <= last_day:
            bookings_by_date.setdefault(
                cursor,
                []
            ).append(
                booking
            )
            cursor += timedelta(
                days=1
            )

    capacity_minutes = 0
    occupied_minutes = 0
    days = []

    day = start_day

    while day < end_day_exclusive:
        segments = _working_segments(
            profile,
            day,
            rules,
        )

        day_capacity = sum(
            _minutes(
                start,
                end,
            )
            for start, end
            in segments
        )

        clipped = []

        for booking in bookings_by_date.get(
            day,
            [],
        ):
            for segment_start, segment_end in segments:
                overlap = _clip(
                    booking.slot.starts_at,
                    booking.slot.ends_at,
                    segment_start,
                    segment_end,
                )

                if overlap:
                    clipped.append(
                        overlap
                    )

        merged = _merge_intervals(
            clipped
        )
        day_occupied = sum(
            _minutes(
                start,
                end,
            )
            for start, end
            in merged
        )

        day_available = max(
            0,
            day_capacity
            - day_occupied,
        )

        day_percent = (
            round(
                day_occupied
                / day_capacity
                * 100,
                1,
            )
            if day_capacity
            else 0.0
        )

        if day_capacity:
            days.append(
                {
                    "date": day,
                    "weekday":
                        day.weekday(),
                    "capacity_minutes":
                        day_capacity,
                    "occupied_minutes":
                        day_occupied,
                    "available_minutes":
                        day_available,
                    "occupancy_percent":
                        day_percent,
                }
            )

        capacity_minutes += (
            day_capacity
        )
        occupied_minutes += (
            day_occupied
        )

        day += timedelta(
            days=1
        )

    available_minutes = max(
        0,
        capacity_minutes
        - occupied_minutes,
    )

    occupancy_percent = (
        round(
            occupied_minutes
            / capacity_minutes
            * 100,
            1,
        )
        if capacity_minutes
        else 0.0
    )

    return {
        "configured": True,
        "capacity_minutes":
            capacity_minutes,
        "occupied_minutes":
            occupied_minutes,
        "available_minutes":
            available_minutes,
        "occupancy_percent":
            occupancy_percent,
        "days": days,
    }


def _hours_label(minutes):
    hours = minutes // 60
    remainder = minutes % 60

    if hours and remainder:
        return (
            f"{hours}h {remainder:02d}"
        )

    if hours:
        return f"{hours}h"

    return f"{remainder}min"


def professional_capacity_context(
    profile,
    *,
    now=None,
):
    now_utc = now or utcnow()
    local_now = to_local(
        now_utc,
        profile.timezone,
    )
    today = local_now.date()

    month_start = today.replace(
        day=1
    )
    month_days = monthrange(
        today.year,
        today.month,
    )[1]
    month_end = (
        month_start
        + timedelta(
            days=month_days
        )
    )

    week_start = (
        today
        - timedelta(
            days=today.weekday()
        )
    )
    week_end = (
        week_start
        + timedelta(
            days=7
        )
    )

    month = _period_capacity(
        profile,
        start_day=month_start,
        end_day_exclusive=month_end,
    )
    week = _period_capacity(
        profile,
        start_day=week_start,
        end_day_exclusive=week_end,
    )

    for period in (
        month,
        week,
    ):
        period[
            "capacity_label"
        ] = _hours_label(
            period[
                "capacity_minutes"
            ]
        )
        period[
            "occupied_label"
        ] = _hours_label(
            period[
                "occupied_minutes"
            ]
        )
        period[
            "available_label"
        ] = _hours_label(
            period[
                "available_minutes"
            ]
        )

    fullest_day = None
    emptiest_day = None

    if month["days"]:
        fullest_day = max(
            month["days"],
            key=lambda row:
                (
                    row[
                        "occupancy_percent"
                    ],
                    row[
                        "occupied_minutes"
                    ],
                ),
        )
        emptiest_day = min(
            month["days"],
            key=lambda row:
                (
                    row[
                        "occupancy_percent"
                    ],
                    -row[
                        "capacity_minutes"
                    ],
                ),
        )

    return {
        "schedule_configured":
            bool(
                profile.working_hours
            ),
        "month_capacity":
            month,
        "week_capacity":
            week,
        "fullest_day":
            fullest_day,
        "emptiest_day":
            emptiest_day,
        "month_label":
            local_now.strftime(
                "%m/%Y"
            ),
    }
