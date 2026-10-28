"""Pure Business profile readiness evaluation (DEC-ID-100–108, NV-07A1-D).

No persistence, publication transitions, authorization, or route integration.
A published legacy establishment can be incomplete by current rules without
losing its persisted publication state. Consumers opt in in a later PR.
"""

from dataclasses import dataclass
import re

OPERATION_MODES = frozenset({"physical", "mobile", "hybrid"})
HOURS_MODES = frozenset({"scheduled", "fixed_hours"})
WEEKDAYS = frozenset({
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
})
_CLOCK = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class EstablishmentReadiness:
    percentage: int
    ready_to_publish: bool
    missing_requirements: tuple[str, ...]


def _filled(value):
    return isinstance(value, str) and bool(value.strip())


def _has_contact(establishment):
    phone = getattr(establishment, "phone", None)
    email = getattr(establishment, "email", None)
    digits = re.sub(r"\D", "", phone) if isinstance(phone, str) else ""
    return (8 <= len(digits) <= 15) or (
        isinstance(email, str) and bool(_EMAIL.fullmatch(email.strip()))
    )


def _minute(value):
    if not isinstance(value, str) or _CLOCK.fullmatch(value) is None:
        return None
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def valid_business_hours(value):
    """Validate a weekly JSON map of weekdays to non-overlapping time ranges.

    Shape: {"monday": [{"start": "09:00", "end": "17:00"}]}.
    Missing weekdays are closed. Empty schedules are not fixed hours.
    Overnight ranges and ambiguous/unknown keys are rejected.
    """
    if not isinstance(value, dict) or not value:
        return False
    if any(day not in WEEKDAYS for day in value):
        return False
    has_interval = False
    for intervals in value.values():
        if not isinstance(intervals, list):
            return False
        previous_end = -1
        for item in intervals:
            if not isinstance(item, dict) or set(item) != {"start", "end"}:
                return False
            start, end = _minute(item["start"]), _minute(item["end"])
            if start is None or end is None or start >= end:
                return False
            if start < previous_end:
                return False
            has_interval = True
            previous_end = end
    return has_interval


def evaluate_establishment_readiness(establishment):
    """Check current requirements without changing the establishment.

    `ready_to_publish` means eligible under *current* rules, not that an
    existing establishment is published or has bookable services.
    """
    operation = getattr(establishment, "operation_mode", None)
    hours_mode = getattr(establishment, "business_hours_mode", None)
    hours = getattr(establishment, "business_hours", None)

    checks = [
        ("name", _filled(getattr(establishment, "name", None))),
        ("category", _filled(getattr(establishment, "category", None))),
        ("description", _filled(getattr(establishment, "description", None))),
        ("location", (
            _filled(getattr(establishment, "city", None))
            and _filled(getattr(establishment, "state", None))
            and len(establishment.state.strip()) == 2
        )),
        ("commercial_contact", _has_contact(establishment)),
        ("operation_mode", operation in OPERATION_MODES),
        ("business_hours_mode", hours_mode in HOURS_MODES),
    ]
    if operation in {"physical", "hybrid"}:
        checks.append((
            "business_address",
            _filled(getattr(establishment, "address_line1", None)),
        ))
    if hours_mode == "fixed_hours":
        checks.append(("business_hours", valid_business_hours(hours)))
    elif hours is not None and not valid_business_hours(hours):
        checks.append(("business_hours", False))

    missing = tuple(name for name, valid in checks if not valid)
    percentage = round(100 * (len(checks) - len(missing)) / len(checks))
    return EstablishmentReadiness(
        percentage=percentage,
        ready_to_publish=not missing,
        missing_requirements=missing,
    )
