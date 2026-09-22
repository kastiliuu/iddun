from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.extensions import db
from app.models.booking import ExperienceSlot, SlotStatus
from app.services.booking_service import clear_external_conflict, mark_external_conflict
from app.services.time_service import as_utc, utcnow


@dataclass(frozen=True)
class BusyWindow:
    starts_at: object
    ends_at: object
    external_event_id: str | None = None
    label: str | None = None


def _coerce_datetime(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _overlaps(slot, window):
    window_start = _coerce_datetime(window.starts_at)
    window_end = _coerce_datetime(window.ends_at)
    return as_utc(slot.starts_at) < as_utc(window_end) and as_utc(slot.ends_at) > as_utc(window_start)


def reconcile_external_busy_windows(professional_id, busy_windows, provider="google", now=None):
    """Reconcile IDDUN opportunity slots against a connected calendar.

    Provider adapters (Google now, others later) only need to translate their
    calendar response into BusyWindow objects. This function owns the product
    rule: conflicting slots leave the marketplace while non-conflicting slots
    remain available.
    """
    now = as_utc(now or utcnow())
    windows = list(busy_windows)
    slots = db.session.scalars(
        select(ExperienceSlot).where(
            ExperienceSlot.professional_id == professional_id,
            ExperienceSlot.starts_at > now,
            ExperienceSlot.status.in_(
                [
                    SlotStatus.AVAILABLE,
                    SlotStatus.HELD,
                    SlotStatus.BLOCKED_EXTERNAL,
                ]
            ),
        )
    ).all()

    blocked = 0
    restored = 0
    unchanged = 0

    for slot in slots:
        conflict = next((window for window in windows if _overlaps(slot, window)), None)
        if conflict:
            if slot.status == SlotStatus.BLOCKED_EXTERNAL:
                slot.external_calendar_provider = provider
                slot.external_event_id = conflict.external_event_id
                slot.external_block_reason = conflict.label or "Conflito detectado na agenda conectada"
                unchanged += 1
                continue
            if mark_external_conflict(
                slot,
                provider=provider,
                external_event_id=conflict.external_event_id,
                reason=conflict.label,
                now=now,
                commit=False,
            ):
                blocked += 1
        elif slot.status == SlotStatus.BLOCKED_EXTERNAL and slot.external_calendar_provider == provider:
            if clear_external_conflict(slot, now=now, commit=False):
                restored += 1
        else:
            unchanged += 1

    db.session.commit()
    return {"blocked": blocked, "restored": restored, "unchanged": unchanged}
