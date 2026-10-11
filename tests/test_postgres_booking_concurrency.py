"""PostgreSQL integration: enforce active booking uniqueness under competition.

Only run in the dedicated PostgreSQL CI job. Never connect to production.
"""

import os
import threading
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest
from app import create_app
from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


TEST_URL = os.environ.get("IDDUN_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not TEST_URL,
    reason="Requires an isolated PostgreSQL database in IDDUN_TEST_POSTGRES_URL",
)


def _pg_connection_url():
    # psycopg2 does not accept the SQLAlchemy +psycopg2 driver suffix.
    return TEST_URL.replace("postgresql+psycopg2://", "postgresql://", 1)


@pytest.fixture(scope="module")
def pg_graph():
    flask_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "qa-postgres-only-secret",
            "SQLALCHEMY_DATABASE_URI": TEST_URL,
            "WTF_CSRF_ENABLED": False,
        }
    )
    with flask_app.app_context():
        # The CI job applies the actual Alembic migrations before this test.
        user = User(
            name="Postgres Booking Tester",
            email="pg-booking-test@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password("strong-test-password")
        client = ClientProfile(user=user)
        professional = ProfessionalProfile(
            display_name="Postgres Pro",
            slug="qa-postgres-pro",
            city="Curitiba",
            state="PR",
        )
        experience = Experience(
            professional=professional,
            title="Postgres booking constraint",
            slug="qa-postgres-booking-service",
            category="unhas",
            short_description="Postgres constraint regression",
            regular_price="100.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        start = datetime.now(timezone.utc) + timedelta(days=30)
        slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            status=SlotStatus.AVAILABLE,
        )
        db.session.add_all([user, client, professional, experience, slot])
        db.session.commit()
        ids = {
            "client_id": client.id,
            "professional_id": professional.id,
            "experience_id": experience.id,
            "slot_id": slot.id,
        }
    yield ids
    with flask_app.app_context():
        db.session.remove()
        # Dedicated disposable CI database, not production or shared staging.
        db.drop_all()


def _insert_booking(conn, ids):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bookings
                (client_id, professional_id, experience_id, slot_id,
                 status, price_at_booking, created_at, updated_at)
            VALUES (%(client_id)s, %(professional_id)s, %(experience_id)s,
                    %(slot_id)s, 'confirmed', 100.00, NOW(), NOW())
            """,
            ids,
        )


def test_postgresql_concurrent_same_slot_allows_one_active_booking(pg_graph):
    ids = pg_graph
    first_inserted = threading.Event()
    second_entered = threading.Event()
    outcomes = {}
    failures = []

    def worker_one():
        conn = psycopg2.connect(_pg_connection_url())
        try:
            conn.autocommit = False
            _insert_booking(conn, ids)
            first_inserted.set()
            assert second_entered.wait(timeout=10)
            conn.commit()
            outcomes["first"] = "committed"
        except Exception as exc:
            failures.append(exc)
            conn.rollback()
        finally:
            conn.close()

    def worker_two():
        conn = psycopg2.connect(_pg_connection_url())
        try:
            assert first_inserted.wait(timeout=10)
            second_entered.set()
            # Must block behind worker one's uncommitted row or fail after commit.
            _insert_booking(conn, ids)
            conn.commit()
            outcomes["second"] = "committed"
        except psycopg2.errors.UniqueViolation:
            outcomes["second"] = "unique_violation"
            conn.rollback()
        except Exception as exc:
            failures.append(exc)
            conn.rollback()
        finally:
            conn.close()

    first = threading.Thread(target=worker_one)
    second = threading.Thread(target=worker_two)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)

    assert not first.is_alive() and not second.is_alive()
    assert not failures, failures
    assert outcomes == {
        "first": "committed",
        "second": "unique_violation",
    }


def test_postgresql_partial_index_exists_and_filters_active_bookings(pg_graph):
    # Verify the actual migration-produced index, not a temporary fake table.
    from sqlalchemy import text

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "qa-index-inspection-secret",
            "SQLALCHEMY_DATABASE_URI": TEST_URL,
        }
    )
    with app.app_context():
        definition = db.session.scalar(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'bookings' "
                "AND indexname = 'uq_bookings_active_slot'"
            )
        )
        assert definition is not None
        assert "UNIQUE INDEX" in definition
        assert "slot_id" in definition
        assert "pending" in definition
        assert "confirmed" in definition
