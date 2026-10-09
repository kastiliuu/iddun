from collections import defaultdict
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
)
from app.services.time_service import (
    local_naive_to_utc,
    to_local,
    utcnow,
)


OUTCOME_STATUSES = {
    BookingStatus.COMPLETED,
    BookingStatus.CANCELLED,
    BookingStatus.NO_SHOW,
}


def _month_shift(year, month, delta):
    absolute = (
        year * 12
        + (month - 1)
        + delta
    )
    return (
        absolute // 12,
        absolute % 12 + 1,
    )


def _period_bounds(
    profile,
    local_now,
    *,
    year,
    month,
):
    next_year, next_month = (
        _month_shift(
            year,
            month,
            1,
        )
    )

    start = local_naive_to_utc(
        datetime(
            year,
            month,
            1,
            0,
            0,
            0,
        ),
        profile.timezone,
    )
    end = local_naive_to_utc(
        datetime(
            next_year,
            next_month,
            1,
            0,
            0,
            0,
        ),
        profile.timezone,
    )

    return start, end


def _money(value):
    return Decimal(
        value or 0
    )


def _percentage(
    numerator,
    denominator,
):
    if not denominator:
        return 0.0

    return round(
        numerator
        / denominator
        * 100,
        1,
    )


def _variation(
    current,
    previous,
):
    current = float(current or 0)
    previous = float(previous or 0)

    if previous == 0:
        if current == 0:
            return 0.0
        return None

    return round(
        (
            current
            - previous
        )
        / previous
        * 100,
        1,
    )


def _service_rows(bookings):
    grouped = defaultdict(
        lambda: {
            "completed_count": 0,
            "realized_revenue": Decimal("0"),
            "booked_count": 0,
        }
    )

    experiences = {}

    for booking in bookings:
        key = booking.experience_id
        experiences[key] = booking.experience

        if booking.status in {
            BookingStatus.CONFIRMED,
            BookingStatus.COMPLETED,
        }:
            grouped[key][
                "booked_count"
            ] += 1

        if (
            booking.status
            == BookingStatus.COMPLETED
        ):
            grouped[key][
                "completed_count"
            ] += 1
            grouped[key][
                "realized_revenue"
            ] += _money(
                booking.price_at_booking
            )

    rows = []

    for experience_id, metrics in grouped.items():
        rows.append(
            {
                "experience":
                    experiences[
                        experience_id
                    ],
                **metrics,
            }
        )

    rows.sort(
        key=lambda row: (
            -row["completed_count"],
            -float(
                row[
                    "realized_revenue"
                ]
            ),
            row[
                "experience"
            ].title.lower(),
        )
    )

    return rows


def _weekday_rows(
    profile,
    bookings,
):
    weekday_names = [
        "Seg",
        "Ter",
        "Qua",
        "Qui",
        "Sex",
        "Sáb",
        "Dom",
    ]

    counts = [
        0
        for _ in range(7)
    ]

    for booking in bookings:
        if booking.status not in {
            BookingStatus.CONFIRMED,
            BookingStatus.COMPLETED,
        }:
            continue

        local_start = to_local(
            booking.slot.starts_at,
            profile.timezone,
        )
        counts[
            local_start.weekday()
        ] += 1

    maximum = max(
        counts,
        default=0,
    )

    return [
        {
            "label":
                weekday_names[index],
            "count":
                count,
            "relative_percent": (
                round(
                    count
                    / maximum
                    * 100
                )
                if maximum
                else 0
            ),
        }
        for index, count
        in enumerate(counts)
    ]


def _hour_rows(
    profile,
    bookings,
):
    counts = defaultdict(int)

    for booking in bookings:
        if booking.status not in {
            BookingStatus.CONFIRMED,
            BookingStatus.COMPLETED,
        }:
            continue

        local_start = to_local(
            booking.slot.starts_at,
            profile.timezone,
        )
        counts[
            local_start.hour
        ] += 1

    rows = [
        {
            "hour": hour,
            "label": f"{hour:02d}h",
            "count": count,
        }
        for hour, count
        in counts.items()
    ]

    rows.sort(
        key=lambda row: (
            -row["count"],
            row["hour"],
        )
    )

    return rows


def _summarize_period(
    profile,
    bookings,
    *,
    local_now,
):
    completed = [
        booking
        for booking in bookings
        if booking.status
        == BookingStatus.COMPLETED
    ]
    confirmed = [
        booking
        for booking in bookings
        if booking.status
        == BookingStatus.CONFIRMED
    ]
    cancelled = [
        booking
        for booking in bookings
        if booking.status
        == BookingStatus.CANCELLED
    ]
    no_show = [
        booking
        for booking in bookings
        if booking.status
        == BookingStatus.NO_SHOW
    ]

    realized_revenue = sum(
        (
            _money(
                booking.price_at_booking
            )
            for booking in completed
        ),
        Decimal("0"),
    )

    forecast_revenue = sum(
        (
            _money(
                booking.price_at_booking
            )
            for booking in confirmed
            if to_local(
                booking.slot.starts_at,
                profile.timezone,
            )
            >= local_now
        ),
        Decimal("0"),
    )

    average_ticket = (
        realized_revenue
        / len(completed)
        if completed
        else Decimal("0")
    )

    outcome_count = (
        len(completed)
        + len(cancelled)
        + len(no_show)
    )

    cancellation_rate = (
        _percentage(
            len(cancelled),
            outcome_count,
        )
    )
    no_show_rate = (
        _percentage(
            len(no_show),
            outcome_count,
        )
    )

    return {
        "completed_count":
            len(completed),
        "confirmed_count":
            len(confirmed),
        "cancelled_count":
            len(cancelled),
        "no_show_count":
            len(no_show),
        "outcome_count":
            outcome_count,
        "realized_revenue":
            realized_revenue,
        "forecast_revenue":
            forecast_revenue,
        "average_ticket":
            average_ticket,
        "cancellation_rate":
            cancellation_rate,
        "no_show_rate":
            no_show_rate,
        "services":
            _service_rows(
                bookings
            ),
        "weekdays":
            _weekday_rows(
                profile,
                bookings,
            ),
        "hours":
            _hour_rows(
                profile,
                bookings,
            ),
    }


def professional_insights_context(
    profile,
    *,
    now=None,
):
    now_utc = now or utcnow()
    local_now = to_local(
        now_utc,
        profile.timezone,
    )

    current_start, current_end = (
        _period_bounds(
            profile,
            local_now,
            year=local_now.year,
            month=local_now.month,
        )
    )

    previous_year, previous_month = (
        _month_shift(
            local_now.year,
            local_now.month,
            -1,
        )
    )

    previous_start, previous_end = (
        _period_bounds(
            profile,
            local_now,
            year=previous_year,
            month=previous_month,
        )
    )

    query_start = previous_start
    query_end = current_end

    bookings = list(
        db.session.scalars(
            select(Booking)
            .where(
                Booking.professional_id
                == profile.id,
                Booking.slot.has(
                    ExperienceSlot.starts_at
                    >= query_start
                ),
                Booking.slot.has(
                    ExperienceSlot.starts_at
                    < query_end
                ),
            )
            .order_by(
                Booking.created_at.desc(),
                Booking.id.desc(),
            )
        ).all()
    )

    current_bookings = []
    previous_bookings = []

    for booking in bookings:
        local_start = to_local(
            booking.slot.starts_at,
            profile.timezone,
        )

        if (
            local_start.year
            == local_now.year
            and local_start.month
            == local_now.month
        ):
            current_bookings.append(
                booking
            )
        elif (
            local_start.year
            == previous_year
            and local_start.month
            == previous_month
        ):
            previous_bookings.append(
                booking
            )

    current = _summarize_period(
        profile,
        current_bookings,
        local_now=local_now,
    )
    previous = _summarize_period(
        profile,
        previous_bookings,
        local_now=local_now,
    )

    current[
        "realized_variation_percent"
    ] = _variation(
        current[
            "realized_revenue"
        ],
        previous[
            "realized_revenue"
        ],
    )
    current[
        "ticket_variation_percent"
    ] = _variation(
        current[
            "average_ticket"
        ],
        previous[
            "average_ticket"
        ],
    )
    current[
        "completed_variation_percent"
    ] = _variation(
        current[
            "completed_count"
        ],
        previous[
            "completed_count"
        ],
    )

    top_service = (
        current["services"][0]
        if current["services"]
        else None
    )
    peak_hour = (
        current["hours"][0]
        if current["hours"]
        else None
    )
    peak_day = max(
        current["weekdays"],
        key=lambda row:
            row["count"],
        default=None,
    )

    return {
        "current": current,
        "previous": previous,
        "top_service": top_service,
        "peak_hour": peak_hour,
        "peak_day": (
            peak_day
            if (
                peak_day
                and peak_day[
                    "count"
                ]
            )
            else None
        ),
        "period_label":
            local_now.strftime(
                "%m/%Y"
            ),
        "previous_period_label":
            f"{previous_month:02d}/{previous_year}",
        "local_now": local_now,
        "definitions": {
            "realized_revenue": (
                "Soma de price_at_booking "
                "das reservas concluídas "
                "no período."
            ),
            "forecast_revenue": (
                "Soma de price_at_booking "
                "das reservas confirmadas "
                "e ainda futuras no período."
            ),
            "average_ticket": (
                "Receita realizada dividida "
                "pelos atendimentos concluídos."
            ),
            "cancellation_rate": (
                "Canceladas dividido por "
                "concluídas + canceladas + "
                "no-show."
            ),
            "no_show_rate": (
                "No-show dividido por "
                "concluídas + canceladas + "
                "no-show."
            ),
        },
    }
