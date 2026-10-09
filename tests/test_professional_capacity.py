"""Regression coverage for professional capacity and weekly schedule."""

from datetime import datetime, time, timedelta, timezone
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
from app.models.professional_schedule import ProfessionalWorkingHour
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.professional_capacity_service import (
    professional_capacity_context,
)
from app.services.time_service import local_naive_to_utc


FIXED_NOW = datetime(
    2026,
    10,
    9,
    15,
    0,
    tzinfo=timezone.utc,
)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _catalog(app):
    with app.app_context():
        user = User(
            name="Pro Capacidade",
            email="capacity-pro@example.com",
            role=UserRole.PROFESSIONAL,
        )
        user.set_password("senha-forte-123")

        profile = ProfessionalProfile(
            user=user,
            display_name="Pro Capacidade",
            slug="pro-capacidade",
            primary_specialty="Nail Designer",
            bio="Profissional para validar capacidade real.",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )
        db.session.add_all([user, profile])
        db.session.flush()

        for weekday in range(5):
            db.session.add(
                ProfessionalWorkingHour(
                    professional=profile,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    break_start_time=time(12, 0),
                    break_end_time=time(13, 0),
                )
            )

        client_user = User(
            name="Cliente Capacidade",
            email="capacity-client@example.com",
            role=UserRole.CLIENT,
        )
        client_user.set_password("senha-forte-123")
        client_profile = ClientProfile(
            user=client_user,
            city="Curitiba",
            state="PR",
        )
        db.session.add_all(
            [client_user, client_profile]
        )

        experience = Experience(
            professional=profile,
            title="Serviço Capacidade",
            slug="servico-capacidade",
            category="unhas",
            short_description="Serviço de capacidade.",
            regular_price="100.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.flush()

        def booking(local_start, local_end, status):
            starts_at = local_naive_to_utc(
                local_start,
                profile.timezone,
            )
            ends_at = local_naive_to_utc(
                local_end,
                profile.timezone,
            )
            slot = ExperienceSlot(
                experience=experience,
                professional=profile,
                starts_at=starts_at,
                ends_at=ends_at,
                status=SlotStatus.BOOKED,
            )
            db.session.add(slot)
            db.session.flush()

            item = Booking(
                client=client_profile,
                experience=experience,
                professional=profile,
                slot=slot,
                status=status,
                price_at_booking=Decimal("100.00"),
            )
            if status == BookingStatus.COMPLETED:
                item.completed_at = ends_at
            elif status == BookingStatus.CONFIRMED:
                item.confirmed_at = FIXED_NOW
            elif status == BookingStatus.NO_SHOW:
                item.no_show_at = starts_at
            elif status == BookingStatus.CANCELLED:
                item.cancelled_at = starts_at

            db.session.add(item)

        booking(
            datetime(2026, 10, 5, 9, 0),
            datetime(2026, 10, 5, 11, 0),
            BookingStatus.COMPLETED,
        )
        booking(
            datetime(2026, 10, 6, 12, 0),
            datetime(2026, 10, 6, 13, 0),
            BookingStatus.CONFIRMED,
        )
        booking(
            datetime(2026, 10, 7, 16, 0),
            datetime(2026, 10, 7, 18, 0),
            BookingStatus.CONFIRMED,
        )
        booking(
            datetime(2026, 10, 8, 9, 0),
            datetime(2026, 10, 8, 11, 0),
            BookingStatus.CANCELLED,
        )
        booking(
            datetime(2026, 10, 9, 10, 0),
            datetime(2026, 10, 9, 11, 0),
            BookingStatus.NO_SHOW,
        )

        db.session.commit()
        return user.id, profile.id


def test_capacity_uses_schedule_breaks_clipping_and_real_booking_states(app):
    _, profile_id = _catalog(app)

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        context = professional_capacity_context(
            profile,
            now=FIXED_NOW,
        )

        week = context["week_capacity"]

        assert context["schedule_configured"] is True
        assert week["capacity_minutes"] == 35 * 60
        assert week["occupied_minutes"] == 4 * 60
        assert week["available_minutes"] == 31 * 60
        assert week["occupancy_percent"] == 11.4

        # Reserva 12-13 cai integralmente na pausa.
        tuesday = next(
            row
            for row in week["days"]
            if row["date"].isoformat() == "2026-10-06"
        )
        assert tuesday["occupied_minutes"] == 0

        # Reserva 16-18 é recortada no fim da jornada, 17h.
        wednesday = next(
            row
            for row in week["days"]
            if row["date"].isoformat() == "2026-10-07"
        )
        assert wednesday["occupied_minutes"] == 60

        # Cancelamento não ocupa capacidade.
        thursday = next(
            row
            for row in week["days"]
            if row["date"].isoformat() == "2026-10-08"
        )
        assert thursday["occupied_minutes"] == 0


def test_capacity_is_not_calculated_without_weekly_schedule(app):
    with app.app_context():
        user = User(
            name="Sem Jornada",
            email="no-schedule@example.com",
            role=UserRole.PROFESSIONAL,
        )
        user.set_password(
            "senha-forte-123"
        )
        profile = ProfessionalProfile(
            user=user,
            display_name="Sem Jornada",
            slug="sem-jornada",
            primary_specialty="Esteticista",
            bio="Perfil sem jornada configurada para teste.",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )
        db.session.add_all([user, profile])
        db.session.commit()

        context = professional_capacity_context(
            profile,
            now=FIXED_NOW,
        )

        assert context["schedule_configured"] is False
        assert context["month_capacity"]["capacity_minutes"] == 0
        assert context["month_capacity"]["occupancy_percent"] == 0.0


def test_professional_can_save_weekly_schedule(
    app,
    client,
    monkeypatch,
):
    user_id, profile_id = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_capacity_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    response = client.post(
        "/pro/jornada",
        data={
            "day_1_enabled": "1",
            "day_1_start": "10:00",
            "day_1_end": "16:00",
            "day_1_break_enabled": "1",
            "day_1_break_start": "12:30",
            "day_1_break_end": "13:00",
            "day_3_enabled": "1",
            "day_3_start": "09:00",
            "day_3_end": "15:00",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )
        rows = {
            row.weekday: row
            for row in profile.working_hours
        }

        assert set(rows) == {1, 3}
        assert rows[1].start_time == time(10, 0)
        assert rows[1].end_time == time(16, 0)
        assert rows[1].break_start_time == time(12, 30)
        assert rows[1].break_end_time == time(13, 0)
        assert rows[3].break_start_time is None


def test_professional_schedule_rejects_break_outside_working_hours(
    app,
    client,
):
    user_id, profile_id = _catalog(app)
    _login(client, user_id)

    response = client.post(
        "/pro/jornada",
        data={
            "day_0_enabled": "1",
            "day_0_start": "09:00",
            "day_0_end": "17:00",
            "day_0_break_enabled": "1",
            "day_0_break_start": "08:00",
            "day_0_break_end": "09:30",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "a pausa precisa ficar dentro da jornada" in html

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )
        monday = next(
            row
            for row in profile.working_hours
            if row.weekday == 0
        )

        assert monday.start_time == time(9, 0)
        assert monday.end_time == time(17, 0)


def test_insights_page_shows_capacity_only_when_schedule_exists(
    app,
    client,
    monkeypatch,
):
    user_id, _ = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_capacity_service.utcnow",
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        "app.services.professional_insights_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    html = client.get(
        "/pro/insights"
    ).get_data(as_text=True)

    assert "Ocupação do mês" in html
    assert "Ocupação da semana" in html
    assert "35h" in html
    assert "11,4%" in html
