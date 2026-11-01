"""PostgreSQL: dois cliques simultâneos em Publicar geram uma única publicação.

Roda só no job PostgreSQL do CI (banco descartável). Nunca usar em produção.
"""

import os
import threading
import time

import pytest
from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.user import User, UserRole
from app.services import mobile_onboarding_service


TEST_URL = os.environ.get("IDDUN_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not TEST_URL,
    reason="Requires an isolated PostgreSQL database in IDDUN_TEST_POSTGRES_URL",
)


@pytest.fixture()
def pg_app():
    flask_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "qa-postgres-onboarding-secret",
        "SQLALCHEMY_DATABASE_URI": TEST_URL,
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        user = User(name="Dona PG", email="pg-onboarding@example.com", role=UserRole.CLIENT)
        user.set_password("strong-test-password")
        business = Establishment(
            name="QA Publicação PG", slug="qa-postgres-onboarding-publish",
            category="salao", city="Curitiba", state="PR",
            description="Apresentação suficiente para publicar.",
            phone="41999990000", operation_mode="mobile",
            business_hours_mode="scheduled", is_active=False,
            published_at=None, onboarding_completed=False,
        )
        db.session.add_all([user, business])
        db.session.flush()
        db.session.add(EstablishmentUserAccess(
            user_id=user.id, establishment_id=business.id,
            role=EstablishmentAccessRole.OWNER,
            status=EstablishmentAccessStatus.ACTIVE,
        ))
        db.session.commit()
        ids = {"user_id": user.id, "establishment_id": business.id}
    yield flask_app, ids
    with flask_app.app_context():
        db.session.execute(delete(EstablishmentUserAccess).where(
            EstablishmentUserAccess.establishment_id == ids["establishment_id"]))
        db.session.execute(delete(Establishment).where(
            Establishment.id == ids["establishment_id"]))
        db.session.execute(delete(User).where(User.id == ids["user_id"]))
        db.session.commit()
        db.session.remove()


def test_postgresql_concurrent_publish_happens_once(pg_app, monkeypatch):
    flask_app, ids = pg_app
    original = mobile_onboarding_service.evaluate_establishment_readiness

    def slow_readiness(item):
        # Alarga a janela de corrida: sem o FOR UPDATE os dois publicariam.
        time.sleep(0.5)
        return original(item)

    monkeypatch.setattr(
        mobile_onboarding_service, "evaluate_establishment_readiness", slow_readiness,
    )
    start = threading.Barrier(2)
    outcomes, failures = [], []

    def click():
        with flask_app.app_context():
            try:
                user = db.session.get(User, ids["user_id"])
                start.wait(timeout=10)
                _, already = mobile_onboarding_service.publish_establishment(
                    user=user, establishment_id=ids["establishment_id"],
                )
                outcomes.append(already)
            except Exception as exc:  # pragma: no cover - reportado abaixo
                failures.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=click) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert not failures, failures
    assert sorted(outcomes) == [False, True]
    with flask_app.app_context():
        business = db.session.get(Establishment, ids["establishment_id"])
        assert business.is_active is True
        assert business.published_at is not None


def test_postgresql_concurrent_professional_publish_happens_once(monkeypatch):
    from app.models.professional import ProfessionalProfile

    flask_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "qa-postgres-onboarding-secret",
        "SQLALCHEMY_DATABASE_URI": TEST_URL,
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        user = User(name="Pro PG", email="pg-pro-onboarding@example.com", role=UserRole.CLIENT)
        user.set_password("strong-test-password")
        db.session.add(user)
        db.session.flush()
        profile = ProfessionalProfile(
            user_id=user.id, display_name="Pro PG", slug="qa-postgres-pro-publish",
            primary_specialty="Nail designer", specialties_text="Unhas",
            bio="Apresentação suficiente.", city="Curitiba", state="PR",
            attendance_modalities="own_space", is_active=False,
            published_at=None, onboarding_completed=False,
        )
        db.session.add(profile)
        db.session.commit()
        ids = {"user_id": user.id, "profile_id": profile.id}

    original = mobile_onboarding_service.professional_missing_requirements

    def slow_requirements(item):
        time.sleep(0.5)
        return original(item)

    monkeypatch.setattr(
        mobile_onboarding_service, "professional_missing_requirements", slow_requirements,
    )
    writes = []
    original_now = mobile_onboarding_service.utcnow

    def counting_now():
        writes.append(1)
        return original_now()

    monkeypatch.setattr(mobile_onboarding_service, "utcnow", counting_now)
    start = threading.Barrier(2)
    outcomes, failures = [], []

    def click():
        with flask_app.app_context():
            try:
                item = db.session.get(ProfessionalProfile, ids["profile_id"])
                was_active = bool(item.is_active)
                start.wait(timeout=10)
                published = mobile_onboarding_service.publish_professional_profile(item)
                outcomes.append((was_active, published.published_at))
            except Exception as exc:  # pragma: no cover - reportado abaixo
                failures.append(exc)
            finally:
                db.session.remove()

    try:
        threads = [threading.Thread(target=click) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        assert not failures, failures
        # Só um dos dois cliques grava a publicação.
        assert len(writes) == 1
        assert len({when for _, when in outcomes}) == 1
    finally:
        with flask_app.app_context():
            db.session.execute(delete(ProfessionalProfile).where(
                ProfessionalProfile.id == ids["profile_id"]))
            db.session.execute(delete(User).where(User.id == ids["user_id"]))
            db.session.commit()
            db.session.remove()
