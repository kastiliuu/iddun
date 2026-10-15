"""Minimal, owner-scoped calendar and sharing payloads for bookings."""
from datetime import timedelta

from app.models.booking import BookingStatus
from app.services.time_service import as_utc, utcnow

ALLOWED = {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}


def _safe_text(value):
    """Avoid control characters and newline injection in ICS / shared summaries."""
    return " ".join(str(value or "").split())[:160]


def _ics_escape(value):
    return (_safe_text(value).replace("\\", "\\\\")
            .replace(";", "\\;").replace(",", "\\,"))


def calendar_payload(booking):
    if booking.status not in ALLOWED:
        return None
    start = as_utc(booking.slot.starts_at)
    end = as_utc(booking.slot.ends_at)
    stamp = as_utc(utcnow()).strftime("%Y%m%dT%H%M%SZ")
    fmt = lambda dt: dt.strftime("%Y%m%dT%H%M%SZ")
    title = _ics_escape("IDDUN - " + booking.experience.title)
    # UID is stable over confirmed reschedules. Event changes keep the same
    # identity and new DTSTART/DTEND when downloaded again.
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//IDDUN//Booking V0//PT-BR",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "BEGIN:VEVENT",
        f"UID:iddun-booking-{booking.id}@iddun.local",
        f"DTSTAMP:{stamp}", f"DTSTART:{fmt(start)}", f"DTEND:{fmt(end)}",
        f"SUMMARY:{title}",
        "DESCRIPTION:Reserva IDDUN. Consulte sua conta para detalhes e alteracoes.",
        "STATUS:CONFIRMED" if booking.status == BookingStatus.CONFIRMED else "STATUS:CONFIRMED",
        "END:VEVENT", "END:VCALENDAR", "",
    ]
    return "\r\n".join(lines)


def share_payload(booking):
    if booking.status not in ALLOWED:
        return None
    from app.services.time_service import to_local
    start = to_local(booking.slot.starts_at, booking.professional.timezone)
    return (
        f"Reserva IDDUN: {_safe_text(booking.experience.title)}\n"
        f"Data: {start.strftime('%d/%m/%Y')}\n"
        f"Horário: {start.strftime('%H:%M')} "
        f"({_safe_text(booking.professional.timezone)})\n"
        "Detalhes e alterações ficam disponíveis apenas na conta do titular."
    )
