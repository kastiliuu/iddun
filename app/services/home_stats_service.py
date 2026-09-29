"""Contagens reais para a home pública do IDDUN.

Os critérios de profissionais e estabelecimentos acompanham as
listagens públicas atuais. Perfis fictícios usados na apresentação
não são armazenados nessas tabelas e não entram nos totais.
"""

from sqlalchemy import func, select

from app.extensions import db
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


def get_home_stats():
    """Retorna os três totais em uma consulta ao banco."""
    members_count = (
        select(func.count(User.id))
        .where(
            User.is_active_account.is_(True),
            User.role != UserRole.ADMIN,
        )
        .scalar_subquery()
    )

    professionals_count = (
        select(func.count(ProfessionalProfile.id))
        .where(
            ProfessionalProfile.is_active.is_(True)
        )
        .scalar_subquery()
    )

    establishments_count = (
        select(func.count(Establishment.id))
        .where(
            Establishment.is_active.is_(True)
        )
        .scalar_subquery()
    )

    members, professionals, establishments = db.session.execute(
        select(
            members_count,
            professionals_count,
            establishments_count,
        )
    ).one()

    return {
        "members": members,
        "professionals": professionals,
        "establishments": establishments,
    }