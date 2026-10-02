from datetime import date, datetime, timedelta

from sqlalchemy import or_, select

from app.extensions import db
from app.models.booking import (
    ExperienceSlot,
    SlotStatus,
)
from app.models.establishment import (
    Establishment,
    EstablishmentAccessStatus,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import (
    ProfessionalProfile,
)
from app.services.booking_service import (
    booking_deadline,
    create_slots_batch,
)
from app.services.time_service import (
    as_utc,
    to_local,
    utcnow,
)


class AvailabilityError(ValueError):
    pass


def _require_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise AvailabilityError(
            "Entre em uma conta ativa para continuar."
        )


def owned_experience(
    *,
    user,
    reference,
):
    _require_user(user)

    value = str(
        reference or ""
    ).strip()

    if not value:
        raise AvailabilityError(
            "Serviço não informado."
        )

    if value.isdigit():
        experience = db.session.get(
            Experience,
            int(value),
        )
    else:
        experience = db.session.scalar(
            select(Experience).where(
                Experience.slug == value
            )
        )

    if experience is None:
        raise AvailabilityError(
            "Serviço não encontrado."
        )

    professional = (
        user.professional_profile
    )

    if (
        professional is not None
        and experience.professional_id
        == professional.id
    ):
        return experience

    if experience.establishment_id is not None:
        for access in user.establishment_accesses:
            if (
                access.status
                == EstablishmentAccessStatus.ACTIVE
                and access.establishment_id
                == experience.establishment_id
            ):
                return experience

    raise AvailabilityError(
        "Este serviço não pertence à sua conta."
    )


def creator_experiences(user):
    _require_user(user)

    professional_id = (
        user.professional_profile.id
        if user.professional_profile
        is not None
        else None
    )

    establishment_ids = [
        access.establishment_id
        for access
        in user.establishment_accesses
        if (
            access.status
            == EstablishmentAccessStatus.ACTIVE
        )
    ]

    clauses = []

    if professional_id is not None:
        clauses.append(
            Experience.professional_id
            == professional_id
        )

    if establishment_ids:
        clauses.append(
            Experience.establishment_id.in_(
                establishment_ids
            )
        )

    if not clauses:
        return []

    return db.session.scalars(
        select(Experience)
        .where(
            Experience.status
            == ExperienceStatus.PUBLISHED,
            or_(*clauses),
        )
        .order_by(
            Experience.title.asc(),
            Experience.id.asc(),
        )
    ).all()


def create_availability(
    *,
    user,
    experience_reference,
    slot_date,
    slot_time,
    cutoff_minutes=None,
):
    experience = owned_experience(
        user=user,
        reference=experience_reference,
    )

    if (
        experience.status
        != ExperienceStatus.PUBLISHED
    ):
        raise AvailabilityError(
            "Publique o serviço antes de abrir horários."
        )

    try:
        parsed_date = date.fromisoformat(
            str(slot_date or "").strip()
        )
    except ValueError as exc:
        raise AvailabilityError(
            "Data inválida. Use AAAA-MM-DD."
        ) from exc

    time_value = str(
        slot_time or ""
    ).strip()

    if not time_value:
        raise AvailabilityError(
            "Horário não informado."
        )

    parsed_cutoff = None

    if cutoff_minutes not in (
        None,
        "",
    ):
        try:
            parsed_cutoff = int(
                cutoff_minutes
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise AvailabilityError(
                "Antecedência mínima inválida."
            ) from exc

        if (
            parsed_cutoff < 0
            or parsed_cutoff
            > 10_080
        ):
            raise AvailabilityError(
                "Antecedência mínima inválida."
            )

    try:
        slots = create_slots_batch(
            experience,
            parsed_date,
            time_value,
            cutoff_minutes=(
                parsed_cutoff
            ),
        )
    except ValueError as exc:
        raise AvailabilityError(
            str(exc)
        ) from exc

    return slots[0]


def iddun_now_slots(
    *,
    limit=20,
    mode="all",
    now=None,
):
    if mode not in (
        "all",
        "today",
        "soon",
    ):
        raise AvailabilityError(
            "Filtro inválido."
        )

    now = as_utc(
        now or utcnow()
    )

    candidates = db.session.scalars(
        select(ExperienceSlot)
        .join(
            Experience,
            ExperienceSlot.experience_id
            == Experience.id,
        )
        .join(
            ProfessionalProfile,
            ExperienceSlot.professional_id
            == ProfessionalProfile.id,
        )
        .outerjoin(
            Establishment,
            ExperienceSlot.establishment_id
            == Establishment.id,
        )
        .where(
            ExperienceSlot.status
            == SlotStatus.AVAILABLE,
            ExperienceSlot.starts_at
            > now,
            Experience.status
            == ExperienceStatus.PUBLISHED,
            ProfessionalProfile.is_active.is_(
                True
            ),
            or_(
                ExperienceSlot.establishment_id
                .is_(None),
                Establishment.is_active.is_(
                    True
                ),
            ),
        )
        .order_by(
            ExperienceSlot.starts_at.asc(),
            ExperienceSlot.id.asc(),
        )
        .limit(
            max(limit * 4, 40)
        )
    ).all()

    result = []

    for slot in candidates:
        if now >= booking_deadline(
            slot
        ):
            continue

        local_start = to_local(
            slot.starts_at,
            slot.professional.timezone,
        )
        local_now = to_local(
            now,
            slot.professional.timezone,
        )

        if (
            mode == "today"
            and local_start.date()
            != local_now.date()
        ):
            continue

        if (
            mode == "soon"
            and local_start.date()
            == local_now.date()
        ):
            continue

        result.append(slot)

        if len(result) >= limit:
            break

    return result


def slot_time_label(
    slot,
    *,
    now=None,
):
    now = as_utc(
        now or utcnow()
    )
    local_start = to_local(
        slot.starts_at,
        slot.professional.timezone,
    )
    local_now = to_local(
        now,
        slot.professional.timezone,
    )
    delta_days = (
        local_start.date()
        - local_now.date()
    ).days

    clock = local_start.strftime(
        "%H:%M"
    )

    if delta_days == 0:
        return f"Hoje {clock}"

    if delta_days == 1:
        return f"Amanhã {clock}"

    return local_start.strftime(
        "%d/%m %H:%M"
    )


def slot_is_urgent(
    slot,
    *,
    now=None,
):
    now = as_utc(
        now or utcnow()
    )

    return (
        as_utc(slot.starts_at)
        <= now
        + timedelta(hours=24)
    )
