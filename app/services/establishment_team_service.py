from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)


class EstablishmentTeamError(ValueError):
    pass


def _require_active_user(user):
    if (
        user is None
        or user.id is None
        or not user.is_active
    ):
        raise EstablishmentTeamError(
            "Entre em uma conta ativa para continuar."
        )


def _active_access(
    user,
    establishment,
):
    return next(
        (
            access
            for access
            in user.establishment_accesses
            if (
                access.establishment_id
                == establishment.id
                and access.status
                == EstablishmentAccessStatus.ACTIVE
            )
        ),
        None,
    )


def require_establishment_manager(
    user,
    establishment_reference,
):
    _require_active_user(user)

    value = str(
        establishment_reference
        or ""
    ).strip()

    if not value:
        raise EstablishmentTeamError(
            "Estabelecimento não informado."
        )

    if value.isdigit():
        establishment = db.session.get(
            Establishment,
            int(value),
        )
    else:
        establishment = db.session.scalar(
            select(Establishment).where(
                Establishment.slug == value
            )
        )

    if establishment is None:
        raise EstablishmentTeamError(
            "Estabelecimento não encontrado."
        )

    access = _active_access(
        user,
        establishment,
    )

    if access is None:
        raise EstablishmentTeamError(
            "Você não possui acesso a este estabelecimento."
        )

    if access.role not in {
        EstablishmentAccessRole.OWNER,
        EstablishmentAccessRole.MANAGER,
    }:
        raise EstablishmentTeamError(
            "Você não possui permissão para gerenciar a equipe."
        )

    return establishment, access


def professional_membership_invites(
    user,
):
    _require_active_user(user)

    professional = (
        user.professional_profile
    )

    if professional is None:
        return []

    return db.session.scalars(
        select(
            ProfessionalEstablishmentMembership
        )
        .where(
            ProfessionalEstablishmentMembership
            .professional_id
            == professional.id,
            ProfessionalEstablishmentMembership
            .status
            == MembershipStatus.PENDING,
        )
        .order_by(
            ProfessionalEstablishmentMembership
            .created_at.desc(),
            ProfessionalEstablishmentMembership
            .id.desc(),
        )
    ).all()


def establishment_team(
    establishment,
):
    return db.session.scalars(
        select(
            ProfessionalEstablishmentMembership
        )
        .where(
            ProfessionalEstablishmentMembership
            .establishment_id
            == establishment.id,
            ProfessionalEstablishmentMembership
            .status.in_(
                [
                    MembershipStatus.PENDING,
                    MembershipStatus.ACTIVE,
                ]
            ),
        )
        .order_by(
            ProfessionalEstablishmentMembership
            .status.asc(),
            ProfessionalEstablishmentMembership
            .created_at.desc(),
        )
    ).all()


def serialize_membership(
    membership,
):
    professional = (
        membership.professional
    )
    establishment = (
        membership.establishment
    )

    return {
        "id": str(
            membership.id
        ),
        "status":
            membership.status,
        "roleName":
            membership.role_name,
        "isPrimary":
            membership.is_primary,
        "startedAt": (
            membership.started_at.isoformat()
            if membership.started_at
            else None
        ),
        "endedAt": (
            membership.ended_at.isoformat()
            if membership.ended_at
            else None
        ),
        "professional": {
            "id": str(
                professional.id
            ),
            "routeId":
                professional.slug,
            "name":
                professional.display_name,
            "specialty":
                professional.primary_specialty,
            "avatar":
                professional.avatar_url,
        },
        "establishment": {
            "id": str(
                establishment.id
            ),
            "routeId":
                establishment.slug,
            "name":
                establishment.name,
            "city":
                establishment.city,
            "state":
                establishment.state,
            "logo":
                establishment.logo_url,
        },
    }
