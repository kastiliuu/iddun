"""Quem é avisado de quê (PR 6a; DEC-ID-025, 215–223; D-SOC-21, 23).

Cada função é chamada depois do commit da ação de domínio. Uma falha ao
avisar fica no log e nunca desfaz a ação nem vira erro para quem a fez.
O mesmo evento não avisa duas vezes a mesma pessoa (``dedupe_key``).
E-mail só para os avisos essenciais de reserva (D-SOC-23).
"""

from sqlalchemy import select

from flask import current_app

from app.extensions import db
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.notification import Notification, NotificationContext, NotificationKind
from app.services.email_delivery import send_transactional_email
from app.services.notification_service import create_notification
from app.services.time_service import to_local

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def _safe(event):
    """Decorador: aviso nunca quebra a ação que já foi gravada."""

    def wrapper(*args, **kwargs):
        try:
            return event(*args, **kwargs)
        except Exception:  # noqa: BLE001 — registrar e seguir (D-SOC-21)
            db.session.rollback()
            current_app.logger.exception("Falha ao gerar notificação %s", event.__name__)
            return None

    wrapper.__name__ = event.__name__
    wrapper.__doc__ = event.__doc__
    return wrapper


def _active(user):
    return user is not None and user.id is not None and user.is_active


def _notify(user, *, email=None, **fields):
    """Cria o aviso e, se for novo e houver e-mail, envia uma vez só."""
    if not _active(user):
        return None
    key = fields.get("dedupe_key")
    if key and db.session.scalar(
        select(Notification.id).where(
            Notification.user_id == user.id,
            Notification.dedupe_key == key,
        )
    ):
        return None
    notification = create_notification(user=user, **fields)
    if notification is not None and email and user.email:
        subject, text = email
        try:
            send_transactional_email(to_email=user.email, subject=subject, text_body=text)
        except Exception:  # noqa: BLE001 — o aviso in-app já está gravado
            current_app.logger.exception("Falha ao enviar e-mail de reserva")
    return notification


def _owners(establishment_id):
    if establishment_id is None:
        return []
    accesses = db.session.scalars(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.establishment_id == establishment_id,
            EstablishmentUserAccess.role == EstablishmentAccessRole.OWNER,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    ).all()
    return [access.user for access in accesses if access.user is not None]


def _when(booking):
    local = to_local(booking.slot.starts_at)
    return f"{WEEKDAYS[local.weekday()]} {local:%d/%m} às {local:%H:%M}"


def _client_user(booking):
    return getattr(booking.client, "user", None)


def _pro_user(booking):
    return getattr(booking.professional, "user", None)


def _client_name(booking):
    user = _client_user(booking)
    name = (getattr(user, "name", "") or "").strip()
    return name.split()[0] if name else "Cliente"


# ---------------------------------------------------------------- reservas


@_safe
def booking_confirmed(booking):
    """Cliente e Pro executor; e-mail essencial para a Cliente."""
    title = booking.experience.title
    pro = booking.professional.display_name
    when = _when(booking)
    _notify(
        _client_user(booking),
        kind=NotificationKind.BOOKING,
        title="Reserva confirmada",
        body=f"{title} com {pro} · {when}.",
        action_type="booking",
        action_id=booking.id,
        context_type=NotificationContext.CLIENT,
        dedupe_key=f"booking:{booking.id}:confirmed:client",
        email=(
            "Sua reserva no IDDUN está confirmada",
            f"{title} com {pro}, {when}.\n\nVeja os detalhes em Minhas reservas no IDDUN.",
        ),
    )
    _notify(
        _pro_user(booking),
        kind=NotificationKind.BOOKING,
        title="Nova reserva",
        body=f"{_client_name(booking)} reservou {title} · {when}.",
        action_type="pro_booking",
        action_id=booking.id,
        context_type=NotificationContext.PROFESSIONAL,
        context_id=booking.professional_id,
        dedupe_key=f"booking:{booking.id}:confirmed:pro",
    )


@_safe
def booking_cancelled(booking):
    """Cancelada pelo Pro, pela administração ou por pedido aceito."""
    title = booking.experience.title
    when = _when(booking)
    _notify(
        _client_user(booking),
        kind=NotificationKind.BOOKING,
        title="Reserva cancelada",
        body=f"{title} · {when} foi cancelada.",
        action_type="booking",
        action_id=booking.id,
        context_type=NotificationContext.CLIENT,
        dedupe_key=f"booking:{booking.id}:cancelled:client",
        email=(
            "Sua reserva no IDDUN foi cancelada",
            f"{title}, {when}, foi cancelada.\n\nVeja os detalhes em Minhas reservas no IDDUN.",
        ),
    )
    _notify(
        _pro_user(booking),
        kind=NotificationKind.BOOKING,
        title="Reserva cancelada",
        body=f"{title} de {_client_name(booking)} · {when} foi cancelada.",
        action_type="pro_booking",
        action_id=booking.id,
        context_type=NotificationContext.PROFESSIONAL,
        context_id=booking.professional_id,
        dedupe_key=f"booking:{booking.id}:cancelled:pro",
    )


@_safe
def booking_completed(booking):
    """DEC-ID-026: só o executor conclui; aí a Cliente pode avaliar."""
    _notify(
        _client_user(booking),
        kind=NotificationKind.BOOKING,
        title="Como foi o atendimento?",
        body=f"{booking.experience.title} com {booking.professional.display_name} foi concluído. Avalie quando quiser.",
        action_type="review_booking",
        action_id=booking.id,
        context_type=NotificationContext.CLIENT,
        dedupe_key=f"booking:{booking.id}:completed:client",
    )


@_safe
def cancellation_requested(request):
    booking = request.booking
    _notify(
        _pro_user(booking),
        kind=NotificationKind.BOOKING,
        title="Pedido de cancelamento",
        body=f"{_client_name(booking)} pediu para cancelar {booking.experience.title} · {_when(booking)}.",
        action_type="pro_booking",
        action_id=booking.id,
        context_type=NotificationContext.PROFESSIONAL,
        context_id=booking.professional_id,
        dedupe_key=f"cancellation:{request.id}:requested",
    )


@_safe
def reschedule_requested(record):
    booking = record.booking
    _notify(
        _pro_user(booking),
        kind=NotificationKind.BOOKING,
        title="Pedido de reagendamento",
        body=f"{_client_name(booking)} pediu outro horário para {booking.experience.title}.",
        action_type="pro_booking",
        action_id=booking.id,
        context_type=NotificationContext.PROFESSIONAL,
        context_id=booking.professional_id,
        dedupe_key=f"reschedule:{record.id}:requested",
    )


@_safe
def reschedule_resolved(record):
    booking = record.booking
    approved = record.status == "executed"  # aceito e já remarcado
    title = booking.experience.title
    body = (
        f"{title} foi remarcado para {_when(booking)}."
        if approved
        else f"O novo horário para {title} não foi aceito. A reserva original continua valendo."
    )
    _notify(
        _client_user(booking),
        kind=NotificationKind.BOOKING,
        title="Reagendamento aceito" if approved else "Reagendamento recusado",
        body=body,
        action_type="booking",
        action_id=booking.id,
        context_type=NotificationContext.CLIENT,
        dedupe_key=f"reschedule:{record.id}:{record.status}",
        email=(
            "Seu pedido de reagendamento no IDDUN foi analisado",
            body + "\n\nVeja os detalhes em Minhas reservas no IDDUN.",
        ),
    )


# ------------------------------------------------------------------ social


def _target_recipients(target_type, target_id):
    """Pro: a conta dele. Empresa: os donos (D-SOC-16)."""
    from app.models.beauty_graph import FollowTarget
    from app.models.professional import ProfessionalProfile

    if target_type == FollowTarget.PROFESSIONAL:
        profile = db.session.get(ProfessionalProfile, target_id)
        user = getattr(profile, "user", None)
        return [(user, NotificationContext.PROFESSIONAL, target_id)] if user else []
    if target_type == FollowTarget.ESTABLISHMENT:
        return [(user, NotificationContext.ESTABLISHMENT, target_id) for user in _owners(target_id)]
    return []


@_safe
def new_follower(follow):
    follower = follow.user
    name = (follower.name or "Alguém").split()[0]
    target_id = follow.professional_id or follow.establishment_id
    for user, context_type, context_id in _target_recipients(follow.target_type, target_id):
        if user.id == follower.id:
            continue
        _notify(
            user,
            kind=NotificationKind.FOLLOW,
            title="Novo seguidor",
            body=f"{name} começou a seguir {'você' if context_type == NotificationContext.PROFESSIONAL else 'sua empresa'}.",
            action_type="followers",
            action_id=context_id,
            context_type=context_type,
            context_id=context_id,
            dedupe_key=f"follow:{follow.target_type}:{context_id}:{follower.id}",
        )


def _post_recipients(post):
    from app.models.work_post import WorkPostAuthorType

    if post.author_type == WorkPostAuthorType.PROFESSIONAL:
        user = getattr(post.professional, "user", None)
        return [(user, NotificationContext.PROFESSIONAL, post.professional_id)] if user else []
    if post.author_type == WorkPostAuthorType.ESTABLISHMENT:
        return [(user, NotificationContext.ESTABLISHMENT, post.establishment_id) for user in _owners(post.establishment_id)]
    if post.author_type == WorkPostAuthorType.CLIENT:
        user = getattr(post.client_profile, "user", None)
        return [(user, NotificationContext.CLIENT, None)] if user else []
    return []


def _excerpt(text, size=60):
    text = " ".join((text or "").split())
    return f"“{text[:size]}{'…' if len(text) > size else ''}”" if text else "sua publicação"


@_safe
def post_liked(post, liker, likes_count):
    """DEC-ID-219: curtidas do mesmo post viram um aviso só.

    O total é real e não conta a curtida de quem recebe o aviso.
    """
    from app.models.work_post import WorkPostLike

    name = (liker.name or "Alguém").split()[0]
    for user, context_type, context_id in _post_recipients(post):
        if user.id == liker.id:
            continue
        own_like = db.session.scalar(
            select(WorkPostLike.id).where(
                WorkPostLike.post_id == post.id,
                WorkPostLike.user_id == user.id,
            )
        )
        others = max(likes_count - 1 - (1 if own_like else 0), 0)
        title = f"{name} curtiu sua publicação" if not others else (
            f"{name} e mais {others} {'pessoa' if others == 1 else 'pessoas'} curtiram sua publicação"
        )
        _notify(
            user,
            kind=NotificationKind.LIKE,
            title=title,
            body=_excerpt(post.caption),
            action_type="post",
            action_id=post.id,
            context_type=context_type,
            context_id=context_id,
            group_key=f"like:post:{post.id}",
        )


@_safe
def comment_added(comment, post):
    from app.models.work_post import WorkPostComment

    author = comment.user
    name = (author.name or "Alguém").split()[0]
    notified = {author.id}
    parent = db.session.get(WorkPostComment, comment.parent_id) if comment.parent_id else None
    if parent is not None and parent.user is not None and parent.user.id not in notified:
        notified.add(parent.user.id)
        _notify(
            parent.user,
            kind=NotificationKind.COMMENT,
            title=f"{name} respondeu ao seu comentário",
            body=_excerpt(comment.body),
            action_type="post",
            action_id=post.id,
            dedupe_key=f"comment:{comment.id}:reply",
        )
    for user, context_type, context_id in _post_recipients(post):
        if user.id in notified:
            continue
        notified.add(user.id)
        _notify(
            user,
            kind=NotificationKind.COMMENT,
            title=f"{name} comentou sua publicação",
            body=_excerpt(comment.body),
            action_type="post",
            action_id=post.id,
            context_type=context_type,
            context_id=context_id,
            dedupe_key=f"comment:{comment.id}:post",
        )


# --------------------------------------------------- profissional e empresa


@_safe
def membership_invited(membership):
    user = getattr(membership.professional, "user", None)
    _notify(
        user,
        kind=NotificationKind.MEMBERSHIP,
        title="Convite de vínculo",
        body=f"{membership.establishment.name} convidou você para a equipe.",
        action_type="membership",
        action_id=membership.id,
        context_type=NotificationContext.PROFESSIONAL,
        context_id=membership.professional_id,
        dedupe_key=f"membership:{membership.id}:invited:{membership.updated_at or ''}",
    )


@_safe
def membership_answered(membership):
    accepted = membership.status == "active"
    pro = membership.professional.display_name
    for user in _owners(membership.establishment_id):
        _notify(
            user,
            kind=NotificationKind.MEMBERSHIP,
            title="Convite aceito" if accepted else "Convite recusado",
            body=f"{pro} {'agora faz parte' if accepted else 'não aceitou fazer parte'} da equipe de {membership.establishment.name}.",
            action_type="business_team",
            action_id=membership.establishment.slug,
            context_type=NotificationContext.ESTABLISHMENT,
            context_id=membership.establishment_id,
            dedupe_key=f"membership:{membership.id}:{membership.status}:{membership.updated_at or ''}",
        )


@_safe
def reviews_saved(booking):
    """Avaliação recebida: o Pro e os donos da empresa avaliada."""
    from app.models.reputation import Review, ReviewTarget

    reviews = db.session.scalars(select(Review).where(Review.booking_id == booking.id)).all()
    for review in reviews:
        stars = "★" * int(review.rating)
        if review.target_type == ReviewTarget.PROFESSIONAL:
            recipients = [(_pro_user(booking), NotificationContext.PROFESSIONAL, booking.professional_id, booking.professional.slug, "professional_reviews")]
        elif booking.establishment is not None:
            recipients = [
                (user, NotificationContext.ESTABLISHMENT, booking.establishment_id, booking.establishment.slug, "business_reviews")
                for user in _owners(booking.establishment_id)
            ]
        else:
            recipients = []
        for user, context_type, context_id, slug, action in recipients:
            _notify(
                user,
                kind=NotificationKind.REVIEW,
                title="Nova avaliação",
                body=f"{_client_name(booking)} avaliou {booking.experience.title}: {stars}",
                action_type=action,
                action_id=slug,
                context_type=context_type,
                context_id=context_id,
                dedupe_key=f"review:{review.id}",
            )
