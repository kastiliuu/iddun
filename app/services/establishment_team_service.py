from datetime import datetime

from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.user import User


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


def invite_professional(
    *,
    user,
    establishment_reference,
    email,
    role_name=None,
):
    establishment, _ = (
        require_establishment_manager(
            user,
            establishment_reference,
        )
    )

    clean_email = str(
        email or ""
    ).strip().lower()

    if not clean_email:
        raise EstablishmentTeamError(
            "Informe o e-mail do profissional."
        )

    invited_user = db.session.scalar(
        select(User).where(
            User.email == clean_email
        )
    )

    if (
        invited_user is None
        or invited_user.professional_profile
        is None
    ):
        raise EstablishmentTeamError(
            "Esse e-mail ainda não possui um perfil profissional IDDUN."
        )

    professional = (
        invited_user.professional_profile
    )

    membership = db.session.scalar(
        select(
            ProfessionalEstablishmentMembership
        ).where(
            ProfessionalEstablishmentMembership
            .professional_id
            == professional.id,
            ProfessionalEstablishmentMembership
            .establishment_id
            == establishment.id,
        )
    )

    if (
        membership is not None
        and membership.status
        == MembershipStatus.ACTIVE
    ):
        raise EstablishmentTeamError(
            "Esse profissional já faz parte da equipe."
        )

    if (
        membership is not None
        and membership.status
        == MembershipStatus.PENDING
    ):
        raise EstablishmentTeamError(
            "Este profissional já possui um convite pendente."
        )

    clean_role = str(
        role_name or ""
    ).strip()
    clean_role = (
        clean_role[:120]
        if clean_role
        else professional.primary_specialty
    )

    if membership is None:
        membership = (
            ProfessionalEstablishmentMembership(
                professional=professional,
                establishment=establishment,
                role_name=clean_role,
                status=MembershipStatus.PENDING,
                is_primary=False,
            )
        )
        db.session.add(
            membership
        )
    else:
        membership.status = (
            MembershipStatus.PENDING
        )
        membership.role_name = clean_role
        membership.is_primary = False
        membership.started_at = None
        membership.ended_at = None

    db.session.commit()

    return membership


def _professional_membership(
    user,
    membership_id,
):
    _require_active_user(user)

    professional = (
        user.professional_profile
    )

    if professional is None:
        raise EstablishmentTeamError(
            "Sua conta não possui perfil profissional."
        )

    membership = db.session.get(
        ProfessionalEstablishmentMembership,
        membership_id,
    )

    if (
        membership is None
        or membership.professional_id
        != professional.id
    ):
        raise EstablishmentTeamError(
            "Convite não encontrado."
        )

    return professional, membership


def accept_invitation(
    user,
    membership_id,
):
    professional, membership = (
        _professional_membership(
            user,
            membership_id,
        )
    )

    if (
        membership.status
        != MembershipStatus.PENDING
    ):
        raise EstablishmentTeamError(
            "Este convite não está mais pendente."
        )

    has_active_membership = any(
        item.status
        == MembershipStatus.ACTIVE
        for item in professional.memberships
    )

    membership.status = MembershipStatus.ACTIVE
    membership.started_at = (
        membership.started_at
        or datetime.now().date()
    )
    membership.ended_at = None
    membership.is_primary = (
        not has_active_membership
    )

    db.session.commit()

    return membership


def reject_invitation(
    user,
    membership_id,
):
    _, membership = (
        _professional_membership(
            user,
            membership_id,
        )
    )

    if (
        membership.status
        != MembershipStatus.PENDING
    ):
        raise EstablishmentTeamError(
            "Este convite não está mais pendente."
        )

    membership.status = MembershipStatus.REJECTED
    membership.is_primary = False
    membership.ended_at = datetime.now().date()

    db.session.commit()

    return membership


def remove_team_member(
    *,
    user,
    establishment_reference,
    membership_id,
):
    establishment, _ = (
        require_establishment_manager(
            user,
            establishment_reference,
        )
    )

    membership = db.session.get(
        ProfessionalEstablishmentMembership,
        membership_id,
    )

    if (
        membership is None
        or membership.establishment_id
        != establishment.id
    ):
        raise EstablishmentTeamError(
            "Vínculo não encontrado."
        )

    if membership.status not in {
        MembershipStatus.ACTIVE,
        MembershipStatus.PENDING,
    }:
        raise EstablishmentTeamError(
            "Este vínculo não está ativo ou pendente."
        )

    membership.status = MembershipStatus.INACTIVE
    membership.is_primary = False
    membership.ended_at = datetime.now().date()

    db.session.commit()

    return membership


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
