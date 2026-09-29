from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.establishment import Establishment
from app.models.plan import BillingCycle, PlanCode, PlanSource, PlanStatus, PlanSubscription
from app.models.professional import ProfessionalProfile
from app.services.entitlements import (
    SUBJECT_CLIENT,
    SUBJECT_ESTABLISHMENT,
    SUBJECT_PROFESSIONAL,
    get_entitlements,
    has_capability,
)


START = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _create_profiles():
    professional = ProfessionalProfile(
        display_name="Profissional de Teste",
        slug="profissional-planos-teste",
    )
    establishment = Establishment(
        name="Estabelecimento de Teste",
        slug="estabelecimento-planos-teste",
    )
    db.session.add_all([professional, establishment])
    db.session.commit()
    return professional.id, establishment.id


def test_essential_keeps_basic_capabilities_without_subscription(app):
    with app.app_context():
        professional_id, establishment_id = _create_profiles()

        client = get_entitlements(SUBJECT_CLIENT)
        professional = get_entitlements(SUBJECT_PROFESSIONAL, professional_id)
        establishment = get_entitlements(SUBJECT_ESTABLISHMENT, establishment_id)

        assert client.effective_plan_code == PlanCode.ESSENTIAL
        assert client.allows("catalog.discover")
        assert client.allows("bookings.create")
        assert client.allows("reviews.after_service")

        assert professional.effective_plan_code == PlanCode.ESSENTIAL
        assert professional.allows("services.manage")
        assert professional.allows("agenda.basic")
        assert professional.allows("opportunities.manage")
        assert professional.allows("bookings.manage")
        assert professional.allows("calendar.google_sync")

        assert establishment.effective_plan_code == PlanCode.ESSENTIAL
        assert establishment.allows("profile.public")
        assert establishment.allows("team.membership")
        assert establishment.allows("reports.basic")

        assert not professional.verification_error
        assert not establishment.verification_error
        assert not professional.allows("reports.professional_advanced")
        assert not establishment.allows("reports.business_advanced")


def test_admin_plans_belong_to_the_correct_profile(app):
    with app.app_context():
        professional_id, establishment_id = _create_profiles()

        db.session.add_all(
            [
                PlanSubscription(
                    professional_id=professional_id,
                    plan_code=PlanCode.PRO,
                    status=PlanStatus.ACTIVE,
                    source=PlanSource.ADMIN,
                    started_at=START,
                ),
                PlanSubscription(
                    establishment_id=establishment_id,
                    plan_code=PlanCode.BUSINESS,
                    status=PlanStatus.ACTIVE,
                    source=PlanSource.ADMIN,
                    started_at=START,
                ),
            ]
        )
        db.session.commit()

        professional = get_entitlements(
            SUBJECT_PROFESSIONAL,
            professional_id,
            now=START + timedelta(days=1),
        )
        establishment = get_entitlements(
            SUBJECT_ESTABLISHMENT,
            establishment_id,
            now=START + timedelta(days=1),
        )
        client = get_entitlements(SUBJECT_CLIENT)

        assert professional.effective_plan_code == PlanCode.PRO
        assert professional.assigned_plan_code == PlanCode.PRO
        assert professional.allows("bookings.manage")
        assert not professional.allows("reports.professional_advanced")

        assert establishment.effective_plan_code == PlanCode.BUSINESS
        assert establishment.assigned_plan_code == PlanCode.BUSINESS
        assert establishment.allows("team.membership")
        assert not establishment.allows("reports.business_advanced")

        assert client.effective_plan_code == PlanCode.ESSENTIAL
        assert not client.allows("reports.professional_advanced")

        # Os relatórios pagos ainda não existem: atribuir o plano não
        # anuncia uma capacidade que não foi lançada.
        assert not has_capability(
            SUBJECT_PROFESSIONAL,
            professional_id,
            "reports.professional_advanced",
        )


def test_trial_expires_without_deleting_subscription(app):
    with app.app_context():
        professional_id, _ = _create_profiles()
        trial_end = START + timedelta(days=14)

        subscription = PlanSubscription(
            professional_id=professional_id,
            plan_code=PlanCode.PRO,
            status=PlanStatus.TRIALING,
            source=PlanSource.ADMIN,
            started_at=START,
            trial_ends_at=trial_end,
        )
        db.session.add(subscription)
        db.session.commit()
        subscription_id = subscription.id

        during_trial = get_entitlements(
            SUBJECT_PROFESSIONAL,
            professional_id,
            now=trial_end - timedelta(seconds=1),
        )
        after_trial = get_entitlements(
            SUBJECT_PROFESSIONAL,
            professional_id,
            now=trial_end,
        )

        assert during_trial.effective_plan_code == PlanCode.PRO
        assert during_trial.subscription_status == PlanStatus.TRIALING
        assert during_trial.trial_ends_at == trial_end

        assert after_trial.effective_plan_code == PlanCode.ESSENTIAL
        assert after_trial.assigned_plan_code == PlanCode.PRO
        assert after_trial.subscription_status == PlanStatus.EXPIRED
        assert after_trial.allows("agenda.basic")
        assert after_trial.allows("opportunities.manage")

        saved = db.session.get(PlanSubscription, subscription_id)
        assert saved is not None
        assert saved.status == PlanStatus.TRIALING


def test_cancel_at_period_end_preserves_access_until_end(app):
    with app.app_context():
        _, establishment_id = _create_profiles()
        period_end = START + timedelta(days=30)

        subscription = PlanSubscription(
            establishment_id=establishment_id,
            plan_code=PlanCode.BUSINESS,
            status=PlanStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            source=PlanSource.GATEWAY,
            started_at=START,
            current_period_start=START,
            current_period_end=period_end,
            cancel_at_period_end=True,
            canceled_at=START + timedelta(days=5),
        )
        db.session.add(subscription)
        db.session.commit()
        subscription_id = subscription.id

        before_end = get_entitlements(
            SUBJECT_ESTABLISHMENT,
            establishment_id,
            now=period_end - timedelta(seconds=1),
        )
        at_end = get_entitlements(
            SUBJECT_ESTABLISHMENT,
            establishment_id,
            now=period_end,
        )

        assert before_end.effective_plan_code == PlanCode.BUSINESS
        assert before_end.subscription_status == PlanStatus.ACTIVE
        assert before_end.cancel_at_period_end

        assert at_end.effective_plan_code == PlanCode.ESSENTIAL
        assert at_end.assigned_plan_code == PlanCode.BUSINESS
        assert at_end.subscription_status == PlanStatus.EXPIRED
        assert at_end.allows("team.membership")
        assert db.session.get(PlanSubscription, subscription_id) is not None


def test_paid_period_without_end_fails_safely(app):
    with app.app_context():
        professional_id, _ = _create_profiles()

        db.session.add(
            PlanSubscription(
                professional_id=professional_id,
                plan_code=PlanCode.PRO,
                status=PlanStatus.ACTIVE,
                billing_cycle=BillingCycle.MONTHLY,
                source=PlanSource.GATEWAY,
                started_at=START,
            )
        )
        db.session.commit()

        result = get_entitlements(
            SUBJECT_PROFESSIONAL,
            professional_id,
            now=START + timedelta(days=1),
        )

        assert result.effective_plan_code == PlanCode.ESSENTIAL
        assert result.verification_error
        assert result.allows("bookings.manage")
        assert result.allows("opportunities.manage")
        assert not result.allows("reports.professional_advanced")


def test_database_failure_keeps_basic_capabilities(app, monkeypatch):
    with app.app_context():
        professional_id, _ = _create_profiles()

        def unavailable_connection(*args, **kwargs):
            raise SQLAlchemyError("Falha simulada na consulta do plano")

        monkeypatch.setattr(db.engine, "connect", unavailable_connection)

        result = get_entitlements(SUBJECT_PROFESSIONAL, professional_id)

        assert result.effective_plan_code == PlanCode.ESSENTIAL
        assert result.subscription_status == "unavailable"
        assert result.verification_error
        assert result.allows("agenda.basic")
        assert result.allows("bookings.manage")
        assert not result.allows("reports.professional_advanced")


def test_unknown_subject_is_rejected(app):
    with app.app_context():
        with pytest.raises(ValueError, match="Tipo de perfil inválido"):
            get_entitlements("admin", 1)