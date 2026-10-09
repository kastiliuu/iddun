from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.booking import Booking, BookingStatus
from app.models.profile import ClientProfile
from app.services.time_service import to_local, utcnow


CRM_BOOKING_STATUSES = {
    BookingStatus.CONFIRMED,
    BookingStatus.COMPLETED,
    BookingStatus.CANCELLED,
    BookingStatus.NO_SHOW,
}


def _whatsapp_url(phone, message):
    digits = "".join(
        char
        for char in (phone or "")
        if char.isdigit()
    )

    if not digits:
        return None

    if len(digits) in {10, 11}:
        digits = f"55{digits}"

    return (
        f"https://wa.me/{digits}"
        f"?text={quote(message)}"
    )


def _next_birthday(birth_date, today):
    if birth_date is None:
        return None

    year = today.year

    while True:
        try:
            candidate = date(
                year,
                birth_date.month,
                birth_date.day,
            )
        except ValueError:
            candidate = date(
                year,
                2,
                28,
            )

        if candidate >= today:
            return candidate

        year += 1


def _client_message(
    *,
    client_name,
    professional_name,
    experience_title=None,
    overdue_days=None,
    birthday=False,
):
    first_name = (
        client_name.split()[0]
        if client_name
        else "tudo bem"
    )

    if birthday:
        return (
            f"Oi, {first_name}! "
            f"Aqui é {professional_name}, do IDDUN. "
            "Vi que seu aniversário está chegando "
            "e passei para te desejar uma semana especial ✦"
        )

    if overdue_days is not None:
        service_text = (
            f" para {experience_title}"
            if experience_title
            else ""
        )
        return (
            f"Oi, {first_name}! Tudo bem? "
            f"Aqui é {professional_name}. "
            f"Já passou um tempinho desde seu último atendimento"
            f"{service_text}. "
            "Tenho alguns horários disponíveis. "
            "Quer que eu te envie as opções?"
        )

    return (
        f"Oi, {first_name}! Tudo bem? "
        f"Aqui é {professional_name}. "
        "Passei para saber como você está "
        "e se posso ajudar com um próximo horário."
    )


def professional_clients_context(
    profile,
    *,
    search=None,
    now=None,
):
    now_utc = now or utcnow()
    local_now = to_local(
        now_utc,
        profile.timezone,
    )
    today = local_now.date()

    bookings = db.session.scalars(
        select(Booking)
        .options(
            selectinload(Booking.slot),
            selectinload(Booking.experience),
            selectinload(Booking.client)
            .selectinload(ClientProfile.user),
        )
        .where(
            Booking.professional_id
            == profile.id,
            Booking.status.in_(
                CRM_BOOKING_STATUSES
            ),
        )
        .order_by(
            Booking.created_at.desc(),
            Booking.id.desc(),
        )
    ).all()

    by_client = defaultdict(list)

    for booking in bookings:
        by_client[
            booking.client_id
        ].append(booking)

    rows = []

    for client_bookings in by_client.values():
        client = (
            client_bookings[0].client
        )
        user = client.user

        completed = [
            booking
            for booking in client_bookings
            if booking.status
            == BookingStatus.COMPLETED
        ]

        completed.sort(
            key=lambda booking: (
                booking.completed_at
                or booking.slot.ends_at
            ),
            reverse=True,
        )

        confirmed_future = [
            booking
            for booking in client_bookings
            if (
                booking.status
                == BookingStatus.CONFIRMED
                and to_local(
                    booking.slot.starts_at,
                    profile.timezone,
                )
                > local_now
            )
        ]

        confirmed_future.sort(
            key=lambda booking:
                booking.slot.starts_at
        )

        last_booking = (
            completed[0]
            if completed
            else None
        )

        last_visit = (
            to_local(
                last_booking.slot.starts_at,
                profile.timezone,
            )
            if last_booking
            else None
        )

        last_experience = (
            last_booking.experience
            if last_booking
            else None
        )

        return_days = (
            last_experience
            .recommended_return_days
            if last_experience
            else None
        )

        recommended_return_date = None
        overdue_days = None

        if (
            last_visit is not None
            and return_days
            and not confirmed_future
        ):
            recommended_return_date = (
                last_visit.date()
                + timedelta(
                    days=return_days
                )
            )

            if today > recommended_return_date:
                overdue_days = (
                    today
                    - recommended_return_date
                ).days

        next_booking = (
            confirmed_future[0]
            if confirmed_future
            else None
        )

        next_booking_start = (
            to_local(
                next_booking.slot.starts_at,
                profile.timezone,
            )
            if next_booking
            else None
        )

        birthday_date = _next_birthday(
            client.birth_date,
            today,
        )

        birthday_in_week = bool(
            birthday_date
            and 0
            <= (
                birthday_date
                - today
            ).days
            <= 7
        )

        completed_count = len(
            completed
        )

        if completed_count >= 2:
            relationship = "recorrente"
        elif completed_count == 1:
            relationship = "nova"
        else:
            relationship = "primeiro_agendamento"

        default_message = (
            _client_message(
                client_name=user.name,
                professional_name=(
                    profile.display_name
                ),
                experience_title=(
                    last_experience.title
                    if last_experience
                    else None
                ),
                overdue_days=(
                    overdue_days
                    if overdue_days
                    is not None
                    else None
                ),
                birthday=(
                    birthday_in_week
                ),
            )
        )

        history = [
            {
                "booking": booking,
                "local_start": to_local(
                    booking.slot.starts_at,
                    profile.timezone,
                ),
            }
            for booking in client_bookings
        ]

        rows.append(
            {
                "client": client,
                "user": user,
                "bookings":
                    client_bookings,
                "history":
                    history,
                "completed_count":
                    completed_count,
                "relationship":
                    relationship,
                "last_visit":
                    last_visit,
                "last_experience":
                    last_experience,
                "recommended_return_date":
                    recommended_return_date,
                "overdue_days":
                    overdue_days,
                "needs_reactivation":
                    overdue_days
                    is not None,
                "next_booking":
                    next_booking,
                "next_booking_start":
                    next_booking_start,
                "birthday_date":
                    birthday_date,
                "birthday_in_week":
                    birthday_in_week,
                "whatsapp_url":
                    _whatsapp_url(
                        client.phone,
                        default_message,
                    ),
            }
        )

    normalized_search = (
        (search or "")
        .strip()
        .lower()
    )

    if normalized_search:
        rows = [
            row
            for row in rows
            if normalized_search
            in " ".join(
                filter(
                    None,
                    [
                        row["user"].name,
                        row["user"].email,
                        (
                            row["last_experience"].title
                            if row["last_experience"]
                            else None
                        ),
                    ],
                )
            ).lower()
        ]

    def sort_key(row):
        if row["needs_reactivation"]:
            priority = 0
        elif row["birthday_in_week"]:
            priority = 1
        elif row["next_booking_start"]:
            priority = 2
        else:
            priority = 3

        recent = (
            row["last_visit"]
            or row["next_booking_start"]
            or local_now
        )

        return (
            priority,
            -recent.timestamp(),
            row["user"].name.lower(),
        )

    rows.sort(
        key=sort_key
    )

    return {
        "clients": rows,
        "client_count": len(
            by_client
        ),
        "new_client_count": sum(
            1
            for row in rows
            if row["relationship"]
            == "nova"
        ),
        "recurring_client_count": sum(
            1
            for row in rows
            if row["relationship"]
            == "recorrente"
        ),
        "reactivation_count": sum(
            1
            for row in rows
            if row[
                "needs_reactivation"
            ]
        ),
        "birthday_week_count": sum(
            1
            for row in rows
            if row[
                "birthday_in_week"
            ]
        ),
        "reactivation_clients": [
            row
            for row in rows
            if row[
                "needs_reactivation"
            ]
        ][:4],
        "birthday_clients": [
            row
            for row in rows
            if row[
                "birthday_in_week"
            ]
        ][:4],
        "search_query":
            search or "",
        "local_today":
            today,
    }
