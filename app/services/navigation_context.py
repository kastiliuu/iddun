"""Contextos de navegação de uma conta (D-SOC-01, DEC-ID-077, FE-DEC-022).

Uma conta é sempre Cliente e pode, além disso, ter perfil profissional e
acesso ativo a um ou mais estabelecimentos. A lista serve só para montar
menus: cada rota continua conferindo a permissão no servidor.
"""

from sqlalchemy import func, select

from app.extensions import db
from app.models.beauty_graph import Save
from app.models.establishment import EstablishmentAccessStatus
from app.models.notification import Notification


def _publication_state(item):
    """Publicado, rascunho ou fora do ar pela moderação."""
    if item.is_active:
        return "published"
    if item.published_at is not None:
        return "locked"
    return "draft"


def account_contexts(user):
    """Contextos autorizados, na ordem do menu: Cliente, Pro, empresas."""
    contexts = [{"kind": "client", "name": user.name}]

    profile = user.professional_profile
    if profile is not None:
        contexts.append({
            "kind": "professional",
            "id": profile.id,
            "name": profile.display_name or user.name,
            "slug": profile.slug,
            "state": _publication_state(profile),
        })

    accesses = [
        access for access in user.establishment_accesses
        if access.status == EstablishmentAccessStatus.ACTIVE
        and access.establishment is not None
    ]
    accesses.sort(key=lambda access: (access.establishment.name or "").lower())
    for access in accesses:
        establishment = access.establishment
        state = _publication_state(establishment)
        if state == "locked":
            # Como em Minha conta desde a PR 3 do onboarding: página
            # desativada pela moderação não aparece entre os contextos.
            continue
        contexts.append({
            "kind": "establishment",
            "id": establishment.id,
            "name": establishment.name,
            "slug": establishment.slug,
            "role": access.role,
            "state": state,
        })

    return contexts


def unread_notification_count(user):
    return db.session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    ) or 0


def saved_item_count(user):
    return db.session.scalar(
        select(func.count(Save.id)).where(Save.user_id == user.id)
    ) or 0


def contexts_payload(contexts):
    """Mesmos contextos em camelCase para a API do app."""
    payload = []
    for item in contexts:
        entry = {"kind": item["kind"], "name": item["name"]}
        if "id" in item:
            entry["id"] = str(item["id"])
            entry["slug"] = item["slug"]
            entry["state"] = item["state"]
        if "role" in item:
            entry["role"] = item["role"]
        payload.append(entry)
    return payload
