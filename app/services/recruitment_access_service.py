"""Quem pode recrutar em cada estabelecimento (V1-CONV-D05).

Regras aprovadas (Notion 08):
- A1-DEC-01 / V1-CONV-D03: o recrutamento é capacidade Business; no piloto
  sem cobrança, depende de habilitação explícita por estabelecimento, que só
  o admin do IDDUN liga e desliga, sempre com motivo e registro.
- A1-DEC-02: a dona recruta quando a empresa está habilitada; gerente só com
  concessão expressa da dona naquele estabelecimento (padrão: negado). A
  retirada vale na hora e não apaga vínculo, candidatura nem outra função.
- V1-CONV-D04 / DEC-ID-268: vagas que já existiam seguem no ar e continuam
  administráveis; só vaga NOVA (criar ou publicar pela primeira vez) exige a
  habilitação.
"""

from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    RecruitmentAuditAction,
    RecruitmentAuditEvent,
)
from app.models.user import UserRole

REASON_MIN = 5
REASON_MAX = 255


class RecruitmentAccessError(ValueError):
    def __init__(self, message, code="recruitment_access_denied"):
        super().__init__(message)
        self.code = code


NOT_ENABLED_MESSAGE = (
    "O recrutamento ainda não está habilitado para este estabelecimento. "
    "A habilitação é feita pela equipe do IDDUN."
)
NOT_GRANTED_MESSAGE = (
    "Você não tem permissão de recrutamento neste estabelecimento. "
    "Peça à dona do estabelecimento."
)


def can_manage_recruitment(access):
    """Dona sempre; gerente só com concessão. Acesso inativo: nunca."""
    if access is None or access.status != EstablishmentAccessStatus.ACTIVE:
        return False
    if access.role == EstablishmentAccessRole.OWNER:
        return True
    return access.role == EstablishmentAccessRole.MANAGER and bool(access.can_recruit)


def recruitment_capability(establishment, access):
    """O que esta pessoa pode fazer no recrutamento desta empresa."""
    manage = can_manage_recruitment(access)
    enabled = bool(establishment.recruitment_enabled)
    return {
        "pilotEnabled": enabled,
        "canManage": manage,
        "canCreate": manage and enabled,
        "isOwner": access is not None and access.role == EstablishmentAccessRole.OWNER,
    }


def require_recruitment_manager(access):
    if not can_manage_recruitment(access):
        raise RecruitmentAccessError(NOT_GRANTED_MESSAGE, "recruitment_not_granted")


def require_new_job_allowed(establishment, access):
    require_recruitment_manager(access)
    if not establishment.recruitment_enabled:
        raise RecruitmentAccessError(NOT_ENABLED_MESSAGE, "recruitment_not_enabled")


def _clean_reason(reason, *, required):
    text = " ".join(str(reason or "").split())
    if required and len(text) < REASON_MIN:
        raise RecruitmentAccessError(
            f"Informe o motivo (pelo menos {REASON_MIN} caracteres).", "reason_required"
        )
    if len(text) > REASON_MAX:
        raise RecruitmentAccessError(
            f"O motivo pode ter até {REASON_MAX} caracteres.", "reason_too_long"
        )
    return text or None


def set_recruitment_pilot(*, establishment, enabled, reason, actor):
    """Admin do IDDUN liga ou desliga o piloto, com motivo. Não mexe em vagas."""
    if actor is None or not actor.is_active or actor.role != UserRole.ADMIN:
        raise RecruitmentAccessError("Somente a equipe do IDDUN pode alterar o piloto.")
    clean = _clean_reason(reason, required=True)
    enabled = bool(enabled)
    if bool(establishment.recruitment_enabled) == enabled:
        raise RecruitmentAccessError(
            "O recrutamento já está habilitado." if enabled else "O recrutamento já está desligado.",
            "no_change",
        )
    establishment.recruitment_enabled = enabled
    db.session.add(
        RecruitmentAuditEvent(
            establishment_id=establishment.id,
            actor_user_id=actor.id,
            action=RecruitmentAuditAction.PILOT_ENABLED if enabled else RecruitmentAuditAction.PILOT_REVOKED,
            reason=clean,
        )
    )
    db.session.commit()
    return establishment


def establishment_managers(establishment):
    return db.session.scalars(
        select(EstablishmentUserAccess)
        .where(
            EstablishmentUserAccess.establishment_id == establishment.id,
            EstablishmentUserAccess.role == EstablishmentAccessRole.MANAGER,
            EstablishmentUserAccess.status == EstablishmentAccessStatus.ACTIVE,
        )
        .order_by(EstablishmentUserAccess.created_at.asc(), EstablishmentUserAccess.id.asc())
    ).all()


def set_manager_recruitment_grant(*, establishment, owner_access, target_access_id, can_recruit, reason=None):
    """A dona concede ou retira a permissão de recrutar de um gerente ativo."""
    if (
        owner_access is None
        or owner_access.establishment_id != establishment.id
        or owner_access.status != EstablishmentAccessStatus.ACTIVE
        or owner_access.role != EstablishmentAccessRole.OWNER
    ):
        raise RecruitmentAccessError("Somente a dona do estabelecimento pode alterar esta permissão.")
    target = db.session.get(EstablishmentUserAccess, target_access_id)
    if (
        target is None
        or target.establishment_id != establishment.id
        or target.role != EstablishmentAccessRole.MANAGER
        or target.status != EstablishmentAccessStatus.ACTIVE
    ):
        raise RecruitmentAccessError("Gerente não encontrado neste estabelecimento.", "manager_not_found")
    clean = _clean_reason(reason, required=False)
    can_recruit = bool(can_recruit)
    if bool(target.can_recruit) == can_recruit:
        raise RecruitmentAccessError(
            "Este gerente já tem a permissão." if can_recruit else "Este gerente já está sem a permissão.",
            "no_change",
        )
    target.can_recruit = can_recruit
    db.session.add(
        RecruitmentAuditEvent(
            establishment_id=establishment.id,
            actor_user_id=owner_access.user_id,
            subject_user_id=target.user_id,
            action=RecruitmentAuditAction.GRANT_GIVEN if can_recruit else RecruitmentAuditAction.GRANT_REVOKED,
            reason=clean,
        )
    )
    db.session.commit()
    return target


def recruitment_audit(establishment, limit=20):
    return db.session.scalars(
        select(RecruitmentAuditEvent)
        .where(RecruitmentAuditEvent.establishment_id == establishment.id)
        .order_by(RecruitmentAuditEvent.created_at.desc(), RecruitmentAuditEvent.id.desc())
        .limit(limit)
    ).all()
