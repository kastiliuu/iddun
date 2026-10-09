"""Regression coverage for the IDDUN Pro daily dashboard V1 and Sprint 02 operations."""

from datetime import datetime, timezone
from decimal import Decimal

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
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.time_service import (
    local_naive_to_utc,
)


FIXED_NOW = datetime(
    2026,
    10,
    8,
    15,
    0,
    tzinfo=timezone.utc,
)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(
            user_id
        )
        session["_fresh"] = True


def _catalog(app):
    with app.app_context():
        professional_user = User(
            name="Profissional Painel",
            email="pro-painel@example.com",
            role=UserRole.PROFESSIONAL,
        )
        professional_user.set_password(
            "senha-forte-123"
        )

        professional = ProfessionalProfile(
            user=professional_user,
            display_name="Marina Painel",
            slug="marina-painel",
            primary_specialty="Nail Designer",
            bio="Especialista em unhas.",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )

        client_user = User(
            name="Ana Cliente",
            email="ana-painel@example.com",
            role=UserRole.CLIENT,
        )
        client_user.set_password(
            "senha-forte-123"
        )

        client_profile = ClientProfile(
            user=client_user,
            phone="41999998888",
            city="Curitiba",
            state="PR",
        )

        db.session.add_all(
            [
                professional_user,
                professional,
                client_user,
                client_profile,
            ]
        )
        db.session.flush()

        experience = Experience(
            professional=professional,
            title="Manutenção em gel",
            slug="manutencao-painel",
            category="unhas",
            short_description=(
                "Manutenção profissional."
            ),
            regular_price="120.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add(experience)
        db.session.flush()

        booked_start = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                13,
                0,
            ),
            professional.timezone,
        )

        booked_slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=booked_start,
            ends_at=booked_start.replace(
                hour=booked_start.hour + 1
            ),
            status=SlotStatus.BOOKED,
        )

        free_start = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                15,
                0,
            ),
            professional.timezone,
        )

        free_slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=free_start,
            ends_at=free_start.replace(
                hour=free_start.hour + 1
            ),
            status=SlotStatus.AVAILABLE,
        )

        db.session.add_all(
            [
                booked_slot,
                free_slot,
            ]
        )
        db.session.flush()

        booking = Booking(
            client=client_profile,
            experience=experience,
            professional=professional,
            slot=booked_slot,
            status=BookingStatus.CONFIRMED,
            price_at_booking=Decimal(
                "100.00"
            ),
            confirmed_at=FIXED_NOW,
        )

        db.session.add(booking)
        db.session.commit()

        return professional_user.id


def test_pro_dashboard_requires_professional_profile(
    app,
    client,
):
    with app.app_context():
        user = User(
            name="Cliente sem Pro",
            email="sem-pro@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    _login(
        client,
        user_id,
    )

    response = client.get(
        "/pro/painel",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/pro/comecar" in response.headers[
        "Location"
    ]


def test_pro_dashboard_renders_real_day_context(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    _login(
        client,
        user_id,
    )

    response = client.get(
        "/pro/painel"
    )

    assert response.status_code == 200

    html = response.get_data(
        as_text=True
    )

    assert (
        "Tudo o que importa para hoje."
        in html
    )
    assert "Ana Cliente" in html
    assert "Manutenção em gel" in html
    assert "R$ 100,00" in html
    assert "1h" in html
    assert (
        "https://wa.me/5541999998888"
        in html
    )
    assert (
        "Oportunidades de hoje"
        in html
    )


def test_pro_dashboard_does_not_invent_occupancy(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    _login(
        client,
        user_id,
    )

    html = client.get(
        "/pro/painel"
    ).get_data(
        as_text=True
    )

    assert "ocupação semanal" not in html.lower()
    assert "ocupação mensal" not in html.lower()



def test_pro_can_block_and_reopen_own_available_slot(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    with app.app_context():
        slot = db.session.scalar(
            db.select(
                ExperienceSlot
            ).where(
                ExperienceSlot.status
                == SlotStatus.AVAILABLE
            )
        )
        slot_id = slot.id

    _login(
        client,
        user_id,
    )

    blocked = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/bloquear"
        ),
        follow_redirects=False,
    )

    assert blocked.status_code == 302

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.BLOCKED_MANUAL
        )

    reopened = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/liberar"
        ),
        follow_redirects=False,
    )

    assert reopened.status_code == 302

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_pro_can_cancel_own_future_booking(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "booking_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    with app.app_context():
        booking = db.session.scalar(
            db.select(
                Booking
            ).where(
                Booking.status
                == BookingStatus.CONFIRMED
            )
        )
        booking_id = booking.id
        slot_id = booking.slot_id

    _login(
        client,
        user_id,
    )

    response = client.post(
        (
            "/pro/painel/reservas/"
            f"{booking_id}/cancelar"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        booking = db.session.get(
            Booking,
            booking_id,
        )
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )

        assert (
            booking.status
            == BookingStatus.CANCELLED
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_pro_cannot_operate_another_professional_slot(
    app,
    client,
):
    user_id = _catalog(app)

    with app.app_context():
        other_user = User(
            name="Outro Pro",
            email="outro-pro@example.com",
            role=UserRole.PROFESSIONAL,
        )
        other_user.set_password(
            "senha-forte-123"
        )

        other_profile = ProfessionalProfile(
            user=other_user,
            display_name="Outro Profissional",
            slug="outro-profissional",
            primary_specialty="Barbeiro",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )

        db.session.add_all(
            [
                other_user,
                other_profile,
            ]
        )
        db.session.flush()

        experience = Experience(
            professional=other_profile,
            title="Corte de teste",
            slug="corte-outro-pro",
            category="cabelo",
            short_description="Teste",
            regular_price="80.00",
            price="70.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add(experience)
        db.session.flush()

        starts_at = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                17,
                0,
            ),
            other_profile.timezone,
        )

        slot = ExperienceSlot(
            experience=experience,
            professional=other_profile,
            starts_at=starts_at,
            ends_at=starts_at.replace(
                hour=starts_at.hour + 1
            ),
            status=SlotStatus.AVAILABLE,
        )

        db.session.add(slot)
        db.session.commit()
        slot_id = slot.id

    _login(
        client,
        user_id,
    )

    response = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/bloquear"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 404

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )
