from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.establishment import (
    Establishment,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.reputation import (
    Review,
    ReviewTarget,
)
from app.models.user import User, UserRole
from app.services.time_service import utcnow


def _review_graph(app):
    with app.app_context():
        user = User(
            name="Cliente Constraint",
            email="review-constraint@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )
        client = ClientProfile(
            user=user
        )
        professional = ProfessionalProfile(
            display_name="Profissional Review",
            slug="profissional-review",
        )
        establishment = Establishment(
            name="Studio Review",
            slug="studio-review",
        )
        experience = Experience(
            professional=professional,
            establishment=establishment,
            title="Experiência Review",
            slug="experiencia-review",
            category="unhas",
            short_description="Teste",
            regular_price="120.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        start = (
            utcnow()
            - timedelta(days=2)
        )

        slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            establishment=establishment,
            starts_at=start,
            ends_at=(
                start
                + timedelta(hours=1)
            ),
            status=SlotStatus.BOOKED,
        )

        booking = Booking(
            client=client,
            experience=experience,
            professional=professional,
            establishment=establishment,
            slot=slot,
            status=BookingStatus.COMPLETED,
            price_at_booking="100.00",
            confirmed_at=(
                start
                - timedelta(days=1)
            ),
            completed_at=(
                start
                + timedelta(hours=1)
            ),
        )

        db.session.add_all(
            [
                user,
                client,
                professional,
                establishment,
                experience,
                slot,
                booking,
            ]
        )
        db.session.commit()

        return {
            "booking_id": booking.id,
            "client_id": client.id,
            "professional_id": professional.id,
            "establishment_id": establishment.id,
        }


def test_membership_pair_must_be_unique(
    app,
):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Membership",
            slug="profissional-membership",
        )
        establishment = Establishment(
            name="Studio Membership",
            slug="studio-membership",
        )

        db.session.add_all(
            [
                professional,
                establishment,
            ]
        )
        db.session.flush()

        db.session.add(
            ProfessionalEstablishmentMembership(
                professional=professional,
                establishment=establishment,
                status="active",
            )
        )
        db.session.commit()

        db.session.add(
            ProfessionalEstablishmentMembership(
                professional_id=professional.id,
                establishment_id=establishment.id,
                status="pending",
            )
        )

        with pytest.raises(
            IntegrityError
        ):
            db.session.commit()

        db.session.rollback()


def test_professional_review_cannot_point_to_establishment(
    app,
):
    ids = _review_graph(app)

    with app.app_context():
        review = Review(
            booking_id=ids[
                "booking_id"
            ],
            client_id=ids[
                "client_id"
            ],
            target_type=(
                ReviewTarget.PROFESSIONAL
            ),
            professional_id=ids[
                "professional_id"
            ],
            establishment_id=ids[
                "establishment_id"
            ],
            rating=5,
            recommended=True,
        )

        db.session.add(review)

        with pytest.raises(
            IntegrityError
        ):
            db.session.commit()

        db.session.rollback()


def test_establishment_review_requires_establishment_only(
    app,
):
    ids = _review_graph(app)

    with app.app_context():
        invalid = Review(
            booking_id=ids[
                "booking_id"
            ],
            client_id=ids[
                "client_id"
            ],
            target_type=(
                ReviewTarget.ESTABLISHMENT
            ),
            professional_id=ids[
                "professional_id"
            ],
            rating=5,
            recommended=True,
        )

        db.session.add(
            invalid
        )

        with pytest.raises(
            IntegrityError
        ):
            db.session.commit()

        db.session.rollback()

        valid = Review(
            booking_id=ids[
                "booking_id"
            ],
            client_id=ids[
                "client_id"
            ],
            target_type=(
                ReviewTarget.ESTABLISHMENT
            ),
            establishment_id=ids[
                "establishment_id"
            ],
            rating=5,
            recommended=True,
        )

        db.session.add(
            valid
        )
        db.session.commit()

        assert valid.id is not None
