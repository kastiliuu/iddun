"""Central de notificações (PR 6a; DEC-ID-215–223; D-SOC-22).

Abas por categoria, contagens, rótulo de contexto e o destino de cada aviso.
O destino é decidido no servidor a cada abertura: se o acesso não vale
mais (vínculo, empresa, post removido), nada é aberto nem exposto.
"""

from flask import url_for
from sqlalchemy import func, select

from app.extensions import db
from app.models.booking import Booking
from app.models.establishment import (
    Establishment,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.notification import Notification, NotificationCategory, NotificationContext
from app.models.professional import ProfessionalProfile

TABS = {
    "todas": (None, "Todas"),
    "reservas": (NotificationCategory.BOOKINGS, "Reservas"),
    "social": (NotificationCategory.SOCIAL, "Social"),
    "profissional": (NotificationCategory.WORK, "Profissional e Empresa"),
}


def category_counts(user, *, unread_only=False):
    """Total por aba, com o mesmo filtro de lidas da lista."""
    filters = [Notification.user_id == user.id]
    if unread_only:
        filters.append(Notification.read_at.is_(None))
    rows = db.session.execute(
        select(Notification.category, func.count(Notification.id))
        .where(*filters)
        .group_by(Notification.category)
    ).all()
    by_category = {category: count for category, count in rows}
    counts = {key: by_category.get(category, 0) for key, (category, _) in TABS.items() if category}
    counts["todas"] = sum(by_category.values())
    return counts


def _active_access(user, establishment_id):
    return db.session.scalar(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.user_id == user.id,
            EstablishmentUserAccess.establishment_id == establishment_id,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
    )


def context_label(user, notification):
    """DEC-ID-221: de que contexto é o aviso, sem expor empresa sem acesso."""
    if notification.context_type == NotificationContext.PROFESSIONAL:
        return "Profissional"
    if notification.context_type == NotificationContext.ESTABLISHMENT:
        if notification.context_id and _active_access(user, notification.context_id):
            business = db.session.get(Establishment, notification.context_id)
            return business.name if business else "Empresa"
        return "Empresa"
    if notification.context_type == NotificationContext.CLIENT:
        return "Cliente"
    return None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_target(user, notification):
    """Destino autorizado do aviso, ou None quando não há (mais) acesso.

    Devolve {"type", "id", "endpoint", "values"}: a Web monta a URL com
    endpoint/values e o app abre a tela pelo type/id (PR 6b). A checagem de
    acesso é a mesma para os dois (DEC-ID-220, 221).
    """
    kind = notification.action_type
    action = notification.action_id

    def target(type_, id_, endpoint, **values):
        return {"type": type_, "id": str(id_) if id_ is not None else None, "endpoint": endpoint, "values": values}

    # Contexto de Pro ou empresa precisa valer agora (DEC-ID-221).
    if notification.context_type == NotificationContext.PROFESSIONAL:
        profile = user.professional_profile
        if profile is None or (notification.context_id and profile.id != notification.context_id):
            return None
    if notification.context_type == NotificationContext.ESTABLISHMENT:
        if not notification.context_id or _active_access(user, notification.context_id) is None:
            return None

    if kind in ("booking", "review_booking"):
        booking = db.session.get(Booking, _int(action))
        if booking is None or getattr(booking.client, "user_id", None) != user.id:
            return None
        if kind == "review_booking":
            return target("review_booking", booking.id, "bookings.review", booking_id=booking.id)
        return target("booking", booking.id, "bookings.mine", _anchor=f"booking-title-{booking.id}")

    if kind == "pro_booking":
        booking = db.session.get(Booking, _int(action))
        if booking is None or getattr(booking.professional, "user_id", None) != user.id:
            return None
        return target("pro_booking", booking.id, "professional.dashboard")

    if kind == "experience" and action:
        return target("experience", action, "public.experience_detail", slug=action)

    if kind == "post":
        from app.services.feed_service import public_post_record

        if public_post_record(_int(action)) is None:
            return None
        return target("post", _int(action), "posts.detail", post_id=_int(action))

    if kind == "followers":
        if notification.context_type == NotificationContext.PROFESSIONAL:
            profile = db.session.get(ProfessionalProfile, notification.context_id)
            if profile is None:
                return None
            return target("professional", profile.slug, "public.professional_detail", slug=profile.slug)
        business = db.session.get(Establishment, notification.context_id)
        if business is None:
            return None
        return target("establishment", business.slug, "public.establishment_detail", slug=business.slug)

    if kind == "membership":
        return target("membership", action, "professional.dashboard")

    if kind == "business_team" and action:
        return target("business_team", action, "business.dashboard", slug=action, _anchor="business-team")

    if kind == "professional_reviews" and action:
        return target("professional", action, "public.professional_detail", slug=action)

    if kind == "business_reviews" and action:
        return target("establishment", action, "public.establishment_tab", slug=action, tab="sobre")

    return None


def destination(user, notification):
    """URL autorizada para o aviso na Web, ou None quando não há (mais) acesso."""
    resolved = resolve_target(user, notification)
    if resolved is None:
        return None
    return url_for(resolved["endpoint"], **resolved["values"])


def api_target(user, notification):
    """Destino para o app: tipo, id e o caminho equivalente na Web."""
    resolved = resolve_target(user, notification)
    if resolved is None:
        return None
    return {
        "type": resolved["type"],
        "id": resolved["id"],
        "webPath": url_for(resolved["endpoint"], **resolved["values"]),
    }
