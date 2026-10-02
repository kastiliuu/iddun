from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.profile import ClientProfile
from app.models.professional import (
    ProfessionalProfile,
)
from app.models.user import User, UserRole
from app.services.time_service import utcnow


def _booking_graph(app):
    with app.app_context():
        user = User(
            name="Cliente Constraint",
            email="constraint@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )
        client = ClientProfile(
            user=user
        )
        professional = ProfessionalProfile(
            display_name="Profissional Constraint",
            slug="profissional-constraint",
            city="Curitiba",
        )
        experience = Experience(
            professional=professional,
            title="Experiência Constraint",
            slug="experiencia-constraint",
            category="unhas",
            short_description="Teste",
            regular_price="120.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        starts_at = utcnow()

        slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=starts_at,
            ends_at=starts_at,
            status=SlotStatus.AVAILABLE,
        )

        db.session.add_all(
            [
                user,
                client,
                professional,
                experience,
                slot,
            ]
        )
        db.session.commit()

        return (
            client.id,
            experience.id,
            professional.id,
            slot.id,
        )


def _booking(
    *,
    client_id,
    experience_id,
    professional_id,
    slot_id,
    status,
):
    return Booking(
        client_id=client_id,
        experience_id=experience_id,
        professional_id=professional_id,
        slot_id=slot_id,
        status=status,
        price_at_booking=Decimal("100.00"),
    )


def test_database_allows_only_one_active_booking_per_slot(
    app,
):
    (
        client_id,
        experience_id,
        professional_id,
        slot_id,
    ) = _booking_graph(app)

    with app.app_context():
        first = _booking(
            client_id=client_id,
            experience_id=experience_id,
            professional_id=professional_id,
            slot_id=slot_id,
            status=BookingStatus.PENDING,
        )
        db.session.add(first)
        db.session.commit()
        first_id = first.id

        competing = _booking(
            client_id=client_id,
            experience_id=experience_id,
            professional_id=professional_id,
            slot_id=slot_id,
            status=BookingStatus.CONFIRMED,
        )
        db.session.add(competing)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        first = db.session.get(
            Booking,
            first_id,
        )
        first.status = BookingStatus.CANCELLED
        db.session.commit()

        replacement = _booking(
            client_id=client_id,
            experience_id=experience_id,
            professional_id=professional_id,
            slot_id=slot_id,
            status=BookingStatus.CONFIRMED,
        )
        db.session.add(replacement)
        db.session.commit()

        assert replacement.id is not None
