from sqlalchemy import or_, select

from app.models.establishment import Establishment
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile


def professional_is_public(
    professional,
):
    return bool(
        professional is not None
        and professional.is_active
    )


def establishment_is_public(
    establishment,
):
    return bool(
        establishment is not None
        and establishment.is_active
    )


def public_professionals_query():
    return select(
        ProfessionalProfile
    ).where(
        ProfessionalProfile.is_active.is_(
            True
        )
    )


def public_establishments_query():
    return select(
        Establishment
    ).where(
        Establishment.is_active.is_(
            True
        )
    )


def public_experiences_query():
    """
    Fonte única das regras mínimas para uma experiência aparecer
    em superfícies públicas e na API.

    A política preserva o comportamento atual:
    - experiência publicada;
    - profissional ativo;
    - estabelecimento ausente ou ativo.
    """
    return (
        select(Experience)
        .join(
            ProfessionalProfile,
            (
                Experience.professional_id
                == ProfessionalProfile.id
            ),
        )
        .outerjoin(
            Establishment,
            (
                Experience.establishment_id
                == Establishment.id
            ),
        )
        .where(
            Experience.status
            == ExperienceStatus.PUBLISHED,
            ProfessionalProfile.is_active.is_(
                True
            ),
            or_(
                Experience.establishment_id.is_(
                    None
                ),
                Establishment.is_active.is_(
                    True
                ),
            ),
        )
    )
