from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class PlanCode:
    ESSENTIAL = "essential"
    PRO = "pro"
    BUSINESS = "business"


class PlanStatus:
    ACTIVE = "active"
    TRIALING = "trialing"
    EXPIRED = "expired"
    CANCELED = "canceled"


class BillingCycle:
    MONTHLY = "monthly"
    ANNUAL = "annual"


class PlanSource:
    SYSTEM = "system"
    ADMIN = "admin"
    GATEWAY = "gateway"


class PlanSubscription(db.Model):
    """
    Estado do plano de um perfil profissional ou estabelecimento.

    As datas e o status serão avaliados pelo serviço de capacidades.
    A presença de uma linha com plan_code='pro' ou 'business', por si só,
    não concede acesso a recursos pagos.
    """

    __tablename__ = "plan_subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("professional_profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=True,
    )

    plan_code = db.Column(
        db.String(24),
        nullable=False,
        default=PlanCode.ESSENTIAL,
    )
    status = db.Column(
        db.String(24),
        nullable=False,
        default=PlanStatus.ACTIVE,
    )
    billing_cycle = db.Column(db.String(16), nullable=True)
    source = db.Column(
        db.String(24),
        nullable=False,
        default=PlanSource.SYSTEM,
    )

    started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    trial_ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    current_period_start = db.Column(db.DateTime(timezone=True), nullable=True)
    current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
    cancel_at_period_end = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )
    canceled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Reservados para uma integração futura. Nenhuma cobrança é feita aqui.
    billing_provider = db.Column(db.String(32), nullable=True)
    provider_subscription_id = db.Column(db.String(190), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship("ProfessionalProfile")
    establishment = db.relationship("Establishment")
    changes = db.relationship(
        "PlanChangeEvent",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="PlanChangeEvent.created_at.desc()",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "professional_id",
            name="uq_plan_subscriptions_professional",
        ),
        db.UniqueConstraint(
            "establishment_id",
            name="uq_plan_subscriptions_establishment",
        ),
        db.CheckConstraint(
            "("
            "professional_id IS NOT NULL "
            "AND establishment_id IS NULL "
            "AND plan_code IN ('essential', 'pro')"
            ") OR ("
            "professional_id IS NULL "
            "AND establishment_id IS NOT NULL "
            "AND plan_code IN ('essential', 'business')"
            ")",
            name="ck_plan_subscriptions_subject_and_plan",
        ),
        db.CheckConstraint(
            "status IN ('active', 'trialing', 'expired', 'canceled')",
            name="ck_plan_subscriptions_status",
        ),
        db.CheckConstraint(
            "billing_cycle IS NULL OR billing_cycle IN ('monthly', 'annual')",
            name="ck_plan_subscriptions_billing_cycle",
        ),
        db.Index(
            "ix_plan_subscriptions_status_period_end",
            "status",
            "current_period_end",
        ),
    )


class PlanChangeEvent(db.Model):
    """Registra quem alterou o plano e qual era o estado anterior."""

    __tablename__ = "plan_change_events"

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(
        db.Integer,
        db.ForeignKey("plan_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    previous_plan_code = db.Column(db.String(24), nullable=True)
    new_plan_code = db.Column(db.String(24), nullable=False)
    previous_status = db.Column(db.String(24), nullable=True)
    new_status = db.Column(db.String(24), nullable=False)
    source = db.Column(db.String(24), nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    subscription = db.relationship(
        "PlanSubscription",
        back_populates="changes",
    )
    actor = db.relationship("User")