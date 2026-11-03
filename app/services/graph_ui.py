"""
Estado de Seguir e Salvar de quem está vendo a página (PR 2, D-SOC-05).

Uma leitura por requisição: os botões de uma lista inteira consultam
conjuntos em memória em vez de uma consulta por cartão.
"""

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.beauty_graph import FollowTarget
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.services.beauty_graph_service import follower_count, graph_state


def _viewer(user):
    viewer_id = user.id if user is not None and user.is_authenticated else None
    cached = g.get("_iddun_graph_viewer")
    if cached is not None and cached["viewer_id"] == viewer_id:
        return cached

    state = {
        "viewer_id": viewer_id,
        "follows": set(),
        "saves": set(),
        "own_professional": None,
        "own_client": None,
        "owned_establishments": set(),
    }

    if user is not None and user.is_authenticated:
        graph = graph_state(user)
        state["follows"] = {
            (item["targetType"], item["targetId"]) for item in graph["follows"]
        }
        state["saves"] = {
            (item["targetType"], item["targetId"]) for item in graph["saves"]
        }
        profile = user.professional_profile
        state["own_professional"] = profile.id if profile is not None else None
        client = user.client_profile
        state["own_client"] = client.id if client is not None else None
        state["owned_establishments"] = set(
            db.session.scalars(
                select(EstablishmentUserAccess.establishment_id).where(
                    EstablishmentUserAccess.user_id == user.id,
                    EstablishmentUserAccess.role == EstablishmentAccessRole.OWNER,
                    EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
                )
            )
        )

    g._iddun_graph_viewer = state
    return state


def template_helpers(user):
    def follows(target_type, target_id):
        return (target_type, int(target_id)) in _viewer(user)["follows"]

    def saved(target_type, target_id):
        return (target_type, int(target_id)) in _viewer(user)["saves"]

    def owns(target_type, target_id):
        """D-SOC-06: o próprio perfil e a própria empresa não têm Seguir."""
        state = _viewer(user)
        if target_type == FollowTarget.PROFESSIONAL:
            return state["own_professional"] == int(target_id)
        if target_type == FollowTarget.ESTABLISHMENT:
            return int(target_id) in state["owned_establishments"]
        if target_type == "client":
            # Publicação da própria Cliente (PR 3): menu com Remover.
            return state["own_client"] == int(target_id)
        return False

    return {
        "graph_follows": follows,
        "graph_saved": saved,
        "graph_owns": owns,
        "graph_follower_count": follower_count,
    }
