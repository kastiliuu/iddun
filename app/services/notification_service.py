from sqlalchemy import func, select

from app.extensions import db
from app.models.notification import (
    Notification,
    NotificationKind,
    NotificationPreference,
    utcnow,
)


class NotificationError(ValueError):
    pass


def _require_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise NotificationError(
            "Entre em uma conta ativa para continuar."
        )


def notification_preferences(user):
    _require_user(user)

    preference = (
        user.notification_preference
    )

    if preference is None:
        preference = NotificationPreference(
            user=user
        )
        db.session.add(
            preference
        )
        db.session.commit()

    return preference


def preference_allows(
    preference,
    kind,
):
    if kind == NotificationKind.BOOKING:
        return preference.booking_enabled
    if kind == NotificationKind.IDDUN_NOW:
        return preference.iddun_now_enabled
    if kind == NotificationKind.FOLLOW:
        return preference.follow_enabled
    if kind == NotificationKind.SYSTEM:
        return preference.system_enabled

    return False


def create_notification(
    *,
    user,
    kind,
    title,
    body,
    action_type=None,
    action_id=None,
    commit=True,
):
    _require_user(user)

    if kind not in NotificationKind.VALUES:
        raise NotificationError(
            "Tipo de notificação inválido."
        )

    preference = notification_preferences(
        user
    )

    if not preference_allows(
        preference,
        kind,
    ):
        return None

    clean_title = str(
        title or ""
    ).strip()
    clean_body = str(
        body or ""
    ).strip()

    if not clean_title or not clean_body:
        raise NotificationError(
            "Título e mensagem são obrigatórios."
        )

    notification = Notification(
        user=user,
        kind=kind,
        title=clean_title[:180],
        body=clean_body[:600],
        action_type=(
            str(action_type).strip()[:40]
            if action_type
            else None
        ),
        action_id=(
            str(action_id).strip()[:180]
            if action_id
            else None
        ),
    )

    db.session.add(
        notification
    )

    if commit:
        db.session.commit()

    return notification


def list_notifications(
    user,
    *,
    offset=0,
    limit=30,
    unread_only=False,
):
    _require_user(user)

    filters = [
        Notification.user_id
        == user.id
    ]

    if unread_only:
        filters.append(
            Notification.read_at.is_(
                None
            )
        )

    total = (
        db.session.scalar(
            select(
                func.count(
                    Notification.id
                )
            ).where(
                *filters
            )
        )
        or 0
    )

    rows = db.session.scalars(
        select(Notification)
        .where(
            *filters
        )
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    unread_count = (
        db.session.scalar(
            select(
                func.count(
                    Notification.id
                )
            ).where(
                Notification.user_id
                == user.id,
                Notification.read_at.is_(
                    None
                ),
            )
        )
        or 0
    )

    return (
        rows,
        total,
        unread_count,
    )


def mark_notification_read(
    user,
    notification_id,
):
    _require_user(user)

    notification = db.session.scalar(
        select(Notification).where(
            Notification.id
            == notification_id,
            Notification.user_id
            == user.id,
        )
    )

    if notification is None:
        raise NotificationError(
            "Notificação não encontrada."
        )

    if notification.read_at is None:
        notification.read_at = utcnow()
        db.session.commit()

    return notification


def mark_all_notifications_read(
    user,
):
    _require_user(user)

    rows = db.session.scalars(
        select(Notification).where(
            Notification.user_id
            == user.id,
            Notification.read_at.is_(
                None
            ),
        )
    ).all()

    if not rows:
        return 0

    now = utcnow()

    for item in rows:
        item.read_at = now

    db.session.commit()

    return len(rows)


def update_notification_preferences(
    user,
    payload,
):
    preference = notification_preferences(
        user
    )

    mapping = {
        "bookingEnabled":
            "booking_enabled",
        "iddunNowEnabled":
            "iddun_now_enabled",
        "followEnabled":
            "follow_enabled",
        "systemEnabled":
            "system_enabled",
        "pushEnabled":
            "push_enabled",
    }

    for key, attribute in mapping.items():
        if key not in payload:
            continue

        value = payload[key]

        if not isinstance(
            value,
            bool,
        ):
            raise NotificationError(
                f"{key}: use true ou false."
            )

        setattr(
            preference,
            attribute,
            value,
        )

    db.session.commit()

    return preference


def serialize_preference(
    preference,
):
    return {
        "bookingEnabled":
            preference.booking_enabled,
        "iddunNowEnabled":
            preference.iddun_now_enabled,
        "followEnabled":
            preference.follow_enabled,
        "systemEnabled":
            preference.system_enabled,
        "pushEnabled":
            preference.push_enabled,
    }


def serialize_notification(
    notification,
):
    return {
        "id": str(
            notification.id
        ),
        "kind":
            notification.kind,
        "title":
            notification.title,
        "body":
            notification.body,
        "actionType":
            notification.action_type,
        "actionId":
            notification.action_id,
        "read":
            notification.is_read,
        "readAt": (
            notification.read_at
            .isoformat()
            if notification.read_at
            is not None
            else None
        ),
        "createdAt":
            notification.created_at
            .isoformat(),
    }


def notify_booking_confirmed(
    booking,
):
    user = getattr(
        booking.client,
        "user",
        None,
    )

    if user is None:
        return None

    return create_notification(
        user=user,
        kind=NotificationKind.BOOKING,
        title="Reserva confirmada",
        body=(
            f"{booking.experience.title} "
            f"com {booking.professional.display_name} "
            "está confirmada."
        ),
        action_type="booking",
        action_id=str(
            booking.id
        ),
    )


def notify_booking_cancelled(
    booking,
):
    user = getattr(
        booking.client,
        "user",
        None,
    )

    if user is None:
        return None

    return create_notification(
        user=user,
        kind=NotificationKind.BOOKING,
        title="Reserva cancelada",
        body=(
            f"{booking.experience.title} "
            "foi cancelada."
        ),
        action_type="booking",
        action_id=str(
            booking.id
        ),
    )


def notify_iddun_now_followers(
    slot,
):
    from app.models.beauty_graph import (
        Follow,
        FollowTarget,
    )

    clauses = [
        (
            Follow.target_type
            == FollowTarget.PROFESSIONAL
        ),
        (
            Follow.professional_id
            == slot.professional_id
        ),
    ]

    if (
        slot.establishment_id
        is not None
    ):
        from sqlalchemy import and_, or_

        query = select(Follow).where(
            or_(
                and_(
                    Follow.target_type
                    == FollowTarget.PROFESSIONAL,
                    Follow.professional_id
                    == slot.professional_id,
                ),
                and_(
                    Follow.target_type
                    == FollowTarget.ESTABLISHMENT,
                    Follow.establishment_id
                    == slot.establishment_id,
                ),
            )
        )
    else:
        query = select(Follow).where(
            *clauses
        )

    follows = db.session.scalars(
        query
    ).all()

    created = 0
    seen_user_ids = set()

    for follow in follows:
        if (
            follow.user_id
            in seen_user_ids
        ):
            continue

        seen_user_ids.add(
            follow.user_id
        )

        notification = (
            create_notification(
                user=follow.user,
                kind=(
                    NotificationKind
                    .IDDUN_NOW
                ),
                title=(
                    "Novo horário disponível"
                ),
                body=(
                    f"{slot.professional.display_name} "
                    f"abriu um horário para "
                    f"{slot.experience.title}."
                ),
                action_type="experience",
                action_id=(
                    slot.experience.slug
                ),
            )
        )

        if notification is not None:
            created += 1

    return created
