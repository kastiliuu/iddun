from dataclasses import dataclass
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.plan import PlanCode, PlanSource, PlanStatus, PlanSubscription


SUBJECT_CLIENT = "client"
SUBJECT_PROFESSIONAL = "professional"
SUBJECT_ESTABLISHMENT = "establishment"

BASIC_CAPABILITIES = {
    SUBJECT_CLIENT: frozenset(
        {
            "catalog.discover",
            "bookings.create",
            "reviews.after_service",
        }
    ),
    SUBJECT_PROFESSIONAL: frozenset(
        {
            "profile.public",
            "portfolio.basic",
            "services.manage",
            "agenda.basic",
            "opportunities.manage",
            "bookings.manage",
            "reports.basic",
            "calendar.google_sync",
        }
    ),
    SUBJECT_ESTABLISHMENT: frozenset(
        {
            "profile.public",
            "experiences.manage",
            "team.membership",
            "bookings.manage",
            "reports.basic",
        }
    ),
}

# Catálogo dos extras planejados. Uma chave só deve entrar em
# LIVE_PAID_CAPABILITIES quando sua rota, proteção e interface existirem.
PAID_CAPABILITIES = {
    PlanCode.PRO: frozenset(
        {
            "reports.professional_advanced",
        }
    ),
    PlanCode.BUSINESS: frozenset(
        {
            "reports.business_advanced",
        }
    ),
}

LIVE_PAID_CAPABILITIES = frozenset()


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value):
    return value.isoformat() if value is not None else None


@dataclass(frozen=True, slots=True)
class EntitlementSnapshot:
    subject_type: str
    effective_plan_code: str
    assigned_plan_code: str
    subscription_status: str
    capabilities: frozenset[str]
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    verification_error: bool = False

    def allows(self, capability):
        return capability in self.capabilities

    def to_dict(self):
        return {
            "subject_type": self.subject_type,
            "effective_plan_code": self.effective_plan_code,
            "assigned_plan_code": self.assigned_plan_code,
            "subscription_status": self.subscription_status,
            "capabilities": sorted(self.capabilities),
            "trial_ends_at": _iso(self.trial_ends_at),
            "current_period_end": _iso(self.current_period_end),
            "cancel_at_period_end": self.cancel_at_period_end,
            "verification_error": self.verification_error,
        }


def _snapshot(
    subject_type,
    effective_plan_code=PlanCode.ESSENTIAL,
    assigned_plan_code=PlanCode.ESSENTIAL,
    subscription_status=PlanStatus.ACTIVE,
    trial_ends_at=None,
    current_period_end=None,
    cancel_at_period_end=False,
    verification_error=False,
):
    basic = BASIC_CAPABILITIES[subject_type]
    paid = PAID_CAPABILITIES.get(effective_plan_code, frozenset())
    capabilities = basic | (paid & LIVE_PAID_CAPABILITIES)

    return EntitlementSnapshot(
        subject_type=subject_type,
        effective_plan_code=effective_plan_code,
        assigned_plan_code=assigned_plan_code,
        subscription_status=subscription_status,
        capabilities=capabilities,
        trial_ends_at=trial_ends_at,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        verification_error=verification_error,
    )


def get_entitlements(subject_type, subject_id=None, *, now=None):
    """
    Consulta as capacidades de um perfil no backend.

    subject_id deve ser obtido de um perfil autorizado pelo servidor;
    uma rota não deve aceitar um ID informado pelo app sem verificar acesso.
    """
    if subject_type not in BASIC_CAPABILITIES:
        raise ValueError("Tipo de perfil inválido para consulta de capacidades.")

    # Não há plano pago para clientes nesta fase.
    if subject_type == SUBJECT_CLIENT:
        return _snapshot(subject_type)

    if subject_id is None:
        return _snapshot(subject_type)

    try:
        subject_id = int(subject_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Identificador de perfil inválido.") from exc

    if subject_id <= 0:
        raise ValueError("Identificador de perfil inválido.")

    current_time = _as_utc(now or datetime.now(timezone.utc))
    columns = PlanSubscription.__table__.c

    if subject_type == SUBJECT_PROFESSIONAL:
        condition = columns.professional_id == subject_id
        allowed_paid_plan = PlanCode.PRO
    else:
        condition = columns.establishment_id == subject_id
        allowed_paid_plan = PlanCode.BUSINESS

    query = select(
        columns.plan_code,
        columns.status,
        columns.source,
        columns.started_at,
        columns.trial_ends_at,
        columns.current_period_start,
        columns.current_period_end,
        columns.billing_cycle,
        columns.cancel_at_period_end,
    ).where(condition)

    try:
        # Uma conexão de leitura separada evita desfazer alterações pendentes
        # na sessão da rota caso a consulta ao plano falhe.
        with db.engine.connect() as connection:
            row = connection.execute(query).mappings().first()
    except SQLAlchemyError:
        current_app.logger.exception(
            "Falha ao consultar capacidades do perfil %s.",
            subject_type,
        )
        return _snapshot(
            subject_type,
            subscription_status="unavailable",
            verification_error=True,
        )

    if row is None:
        return _snapshot(subject_type)

    assigned_plan = row["plan_code"]
    status = row["status"]
    source = row["source"]
    started_at = _as_utc(row["started_at"])
    trial_ends_at = _as_utc(row["trial_ends_at"])
    period_start = _as_utc(row["current_period_start"])
    period_end = _as_utc(row["current_period_end"])
    cancel_at_period_end = bool(row["cancel_at_period_end"])

    details = {
        "assigned_plan_code": assigned_plan,
        "trial_ends_at": trial_ends_at,
        "current_period_end": period_end,
        "cancel_at_period_end": cancel_at_period_end,
    }

    if assigned_plan == PlanCode.ESSENTIAL:
        return _snapshot(subject_type, **details)

    if assigned_plan != allowed_paid_plan or status not in {
        PlanStatus.ACTIVE,
        PlanStatus.TRIALING,
        PlanStatus.EXPIRED,
        PlanStatus.CANCELED,
    }:
        return _snapshot(
            subject_type,
            subscription_status="unavailable",
            verification_error=True,
        )

    if started_at is None or current_time < started_at:
        return _snapshot(
            subject_type,
            subscription_status="scheduled",
            **details,
        )

    if status == PlanStatus.TRIALING:
        if trial_ends_at is None:
            return _snapshot(
                subject_type,
                subscription_status="unavailable",
                verification_error=True,
                **details,
            )
        if current_time < trial_ends_at:
            return _snapshot(
                subject_type,
                effective_plan_code=assigned_plan,
                subscription_status=PlanStatus.TRIALING,
                **details,
            )
        return _snapshot(
            subject_type,
            subscription_status=PlanStatus.EXPIRED,
            **details,
        )

    if status == PlanStatus.ACTIVE:
        if period_start is not None and current_time < period_start:
            return _snapshot(
                subject_type,
                subscription_status="scheduled",
                **details,
            )
        if period_end is not None and current_time >= period_end:
            return _snapshot(
                subject_type,
                subscription_status=PlanStatus.EXPIRED,
                **details,
            )

        # Uma concessão administrativa pode ser sem prazo. Assinaturas com
        # ciclo ou cancelamento marcado exigem data final verificável.
        requires_period_end = (
            source != PlanSource.ADMIN
            or row["billing_cycle"] is not None
            or cancel_at_period_end
        )
        if requires_period_end and period_end is None:
            return _snapshot(
                subject_type,
                subscription_status="unavailable",
                verification_error=True,
                **details,
            )

        return _snapshot(
            subject_type,
            effective_plan_code=assigned_plan,
            subscription_status=PlanStatus.ACTIVE,
            **details,
        )

    return _snapshot(
        subject_type,
        subscription_status=status,
        **details,
    )


def has_capability(subject_type, subject_id, capability):
    """Helper para a checagem obrigatória em rotas de recursos pagos."""
    return get_entitlements(subject_type, subject_id).allows(capability)