from flask import current_app
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationContext,
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
    """Reservas são essenciais e não se desligam (DEC-ID-218, D-SOC-22)."""
    if kind == NotificationKind.BOOKING:
        return True
    if kind == NotificationKind.IDDUN_NOW:
        return preference.iddun_now_enabled
    if kind == NotificationKind.FOLLOW:
        return preference.social_enabled and preference.follow_enabled
    if kind in (NotificationKind.LIKE, NotificationKind.COMMENT):
        return preference.social_enabled
    if kind in (NotificationKind.MEMBERSHIP, NotificationKind.REVIEW):
        return preference.work_enabled
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
    context_type=None,
    context_id=None,
    dedupe_key=None,
    group_key=None,
    commit=True,
):
    """Cria um aviso in-app (PR 6a; D-SOC-21, DEC-ID-219).

    - ``dedupe_key``: o mesmo evento nunca avisa duas vezes a mesma pessoa;
      a segunda chamada devolve o aviso existente.
    - ``group_key``: avisos parecidos ainda não lidos viram um só, com
      ``group_count``; ``title`` pode ser uma função do total.
    """
    _require_user(user)

    if kind not in NotificationKind.VALUES:
        raise NotificationError(
            "Tipo de notificação inválido."
        )
    if context_type is not None and context_type not in NotificationContext.VALUES:
        raise NotificationError("Contexto de notificação inválido.")

    preference = notification_preferences(
        user
    )

    if not preference_allows(
        preference,
        kind,
    ):
        return None

    if dedupe_key:
        existing = db.session.scalar(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.dedupe_key == dedupe_key,
            )
        )
        if existing is not None:
            return existing

    if group_key:
        grouped = db.session.scalar(
            select(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.group_key == group_key,
                Notification.read_at.is_(None),
            )
            .order_by(Notification.id.desc())
            .limit(1)
        )
        if grouped is not None:
            grouped.group_count += 1
            grouped.title = _clean(title(grouped.group_count) if callable(title) else title, 180)
            grouped.body = _clean(body, 600)
            grouped.created_at = utcnow()
            if commit:
                db.session.commit()
            return grouped

    clean_title = _clean(title(1) if callable(title) else title, 180)
    clean_body = _clean(body, 600)

    if not clean_title or not clean_body:
        raise NotificationError(
            "Título e mensagem são obrigatórios."
        )

    # user_id (e não user=) para não pôr o aviso na coleção do usuário antes
    # do add: o flush do savepoint avisaria "not in session" (SAWarning).
    notification = Notification(
        user_id=user.id,
        kind=kind,
        category=NotificationCategory.BY_KIND[kind],
        title=clean_title,
        body=clean_body,
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
        context_type=context_type,
        context_id=context_id,
        dedupe_key=(dedupe_key or None) and str(dedupe_key)[:160],
        group_key=(group_key or None) and str(group_key)[:160],
    )

    if not commit:
        db.session.add(notification)
        return notification

    # Corrida entre duas entregas do mesmo evento: a chave única decide.
    try:
        with db.session.begin_nested():
            db.session.add(notification)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return db.session.scalar(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.dedupe_key == dedupe_key,
            )
        )

    return notification


def _clean(value, maximum):
    return str(value or "").strip()[:maximum]


def list_notifications(
    user,
    *,
    offset=0,
    limit=30,
    unread_only=False,
    category=None,
):
    _require_user(user)

    filters = [
        Notification.user_id
        == user.id
    ]

    # Abas da central (DEC-ID-216); Todas = sem categoria.
    if category:
        if category not in NotificationCategory.VALUES:
            raise NotificationError("Categoria de notificação inválida.")
        filters.append(Notification.category == category)

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
        "socialEnabled":
            "social_enabled",
        "workEnabled":
            "work_enabled",
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
        # Essencial (DEC-ID-218): o aviso de reserva não se desliga.
        "bookingEnabled": True,
        "iddunNowEnabled":
            preference.iddun_now_enabled,
        "followEnabled":
            preference.follow_enabled,
        "systemEnabled":
            preference.system_enabled,
        "pushEnabled":
            preference.push_enabled,
        "socialEnabled":
            preference.social_enabled,
        "workEnabled":
            preference.work_enabled,
        # Reservas são essenciais (DEC-ID-218): sempre ativas.
        "bookingEssential": True,
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
        # PR 6a (D-SOC-21/22).
        "category": notification.category,
        "contextType": notification.context_type,
        "contextId": (
            str(notification.context_id)
            if notification.context_id is not None
            else None
        ),
        "groupCount": notification.group_count,
    }


def notify_iddun_now_followers(
    slot,
):
    """Seguidores avisados de um horário novo (IDDUN Now).

    PR 6a: uma falha ao avisar nunca desfaz o horário já criado.
    """
    try:
        return _notify_iddun_now_followers(slot)
    except Exception:  # noqa: BLE001 — registrar e seguir (D-SOC-21)
        db.session.rollback()
        current_app.logger.exception("Falha ao avisar seguidores do IDDUN Now")
        return 0


def _notify_iddun_now_followers(
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
                context_type="client",
                dedupe_key=f"iddun_now:slot:{slot.id}",
            )
        )

        if notification is not None:
            created += 1

    return created
