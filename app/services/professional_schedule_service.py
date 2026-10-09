from datetime import datetime

from app.extensions import db
from app.models.professional_schedule import (
    ProfessionalWorkingHour,
    WEEKDAY_LABELS,
)


DEFAULT_START = "09:00"
DEFAULT_END = "18:00"


class ScheduleValidationError(ValueError):
    pass


def _parse_time(value, label):
    value = (value or "").strip()

    try:
        return datetime.strptime(
            value,
            "%H:%M",
        ).time()
    except ValueError as exc:
        raise ScheduleValidationError(
            f"{label}: use um horário válido no formato HH:MM."
        ) from exc


def schedule_rows(profile):
    by_weekday = {
        row.weekday: row
        for row in profile.working_hours
    }

    rows = []

    for weekday in range(7):
        rule = by_weekday.get(
            weekday
        )

        rows.append(
            {
                "weekday": weekday,
                "label":
                    WEEKDAY_LABELS[
                        weekday
                    ],
                "enabled":
                    rule is not None,
                "start":
                    (
                        rule.start_time.strftime(
                            "%H:%M"
                        )
                        if rule
                        else DEFAULT_START
                    ),
                "end":
                    (
                        rule.end_time.strftime(
                            "%H:%M"
                        )
                        if rule
                        else DEFAULT_END
                    ),
                "break_enabled":
                    bool(
                        rule
                        and rule.break_start_time
                        and rule.break_end_time
                    ),
                "break_start":
                    (
                        rule.break_start_time.strftime(
                            "%H:%M"
                        )
                        if (
                            rule
                            and rule.break_start_time
                        )
                        else "12:00"
                    ),
                "break_end":
                    (
                        rule.break_end_time.strftime(
                            "%H:%M"
                        )
                        if (
                            rule
                            and rule.break_end_time
                        )
                        else "13:00"
                    ),
            }
        )

    return rows


def save_weekly_schedule(
    profile,
    form_data,
):
    parsed = []

    for weekday in range(7):
        prefix = f"day_{weekday}"

        if (
            form_data.get(
                f"{prefix}_enabled"
            )
            != "1"
        ):
            continue

        start_time = _parse_time(
            form_data.get(
                f"{prefix}_start"
            ),
            WEEKDAY_LABELS[
                weekday
            ],
        )
        end_time = _parse_time(
            form_data.get(
                f"{prefix}_end"
            ),
            WEEKDAY_LABELS[
                weekday
            ],
        )

        if start_time >= end_time:
            raise ScheduleValidationError(
                f"{WEEKDAY_LABELS[weekday]}: "
                "o fim da jornada deve ser "
                "posterior ao início."
            )

        break_start = None
        break_end = None

        if (
            form_data.get(
                f"{prefix}_break_enabled"
            )
            == "1"
        ):
            break_start = _parse_time(
                form_data.get(
                    f"{prefix}_break_start"
                ),
                (
                    f"{WEEKDAY_LABELS[weekday]} "
                    "· início da pausa"
                ),
            )
            break_end = _parse_time(
                form_data.get(
                    f"{prefix}_break_end"
                ),
                (
                    f"{WEEKDAY_LABELS[weekday]} "
                    "· fim da pausa"
                ),
            )

            if break_start >= break_end:
                raise ScheduleValidationError(
                    f"{WEEKDAY_LABELS[weekday]}: "
                    "o fim da pausa deve ser "
                    "posterior ao início."
                )

            if (
                break_start < start_time
                or break_end > end_time
            ):
                raise ScheduleValidationError(
                    f"{WEEKDAY_LABELS[weekday]}: "
                    "a pausa precisa ficar "
                    "dentro da jornada."
                )

        parsed.append(
            {
                "weekday": weekday,
                "start_time":
                    start_time,
                "end_time":
                    end_time,
                "break_start_time":
                    break_start,
                "break_end_time":
                    break_end,
            }
        )

    existing = {
        row.weekday: row
        for row in profile.working_hours
    }
    desired_weekdays = {
        item["weekday"]
        for item in parsed
    }

    for weekday, row in existing.items():
        if weekday not in desired_weekdays:
            db.session.delete(
                row
            )

    for item in parsed:
        row = existing.get(
            item["weekday"]
        )

        if row is None:
            row = (
                ProfessionalWorkingHour(
                    professional=profile,
                    weekday=item[
                        "weekday"
                    ],
                )
            )
            db.session.add(
                row
            )

        row.start_time = (
            item["start_time"]
        )
        row.end_time = (
            item["end_time"]
        )
        row.break_start_time = (
            item[
                "break_start_time"
            ]
        )
        row.break_end_time = (
            item[
                "break_end_time"
            ]
        )

    db.session.commit()

    return len(parsed)
