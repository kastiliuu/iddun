"""Regression coverage for the IDDUN Pro CRM V1."""

from datetime import date, datetime, timedelta, timezone
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
from app.services.professional_crm_service import (
    professional_clients_context,
)
from app.services.time_service import (
    local_naive_to_utc,
)


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


def _professional(
    email,
    slug,
):
    user = User(
        name=f"Conta {slug}",
        email=email,
        role=UserRole.PROFESSIONAL,
    )
    user.set_password("senha-forte-123")

    profile = ProfessionalProfile(
        user=user,
        display_name=f"Pro {slug}",
        slug=slug,
        primary_specialty="Nail Designer",
        bio="Profissional de teste para CRM.",
        city="Curitiba",
        state="PR",
        timezone="America/Sao_Paulo",
        onboarding_completed=True,
        is_active=True,
    )

    db.session.add_all([user, profile])
    db.session.flush()

    return user, profile


def _client(
    *,
    name,
    email,
    phone,
    birth_date=None,
):
    user = User(
        name=name,
        email=email,
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")

    profile = ClientProfile(
        user=user,
        phone=phone,
        birth_date=birth_date,
        city="Curitiba",
        state="PR",
    )

    db.session.add_all([user, profile])
    db.session.flush()

    return profile


def _experience(
    professional,
    *,
    title,
    slug,
    return_days,
):
    experience = Experience(
        professional=professional,
        title=title,
        slug=slug,
        category="unhas",
        short_description="Serviço CRM.",
        regular_price="120.00",
        price="100.00",
        duration_minutes=60,
        recommended_return_days=return_days,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(experience)
    db.session.flush()
    return experience


def _booking(
    *,
    client,
    professional,
    experience,
    local_start,
    status,
):
    starts_at = local_naive_to_utc(
        local_start,
        professional.timezone,
    )
    ends_at = starts_at + timedelta(hours=1)

    slot = ExperienceSlot(
        experience=experience,
        professional=professional,
        starts_at=starts_at,
        ends_at=ends_at,
        status=SlotStatus.BOOKED,
    )
    db.session.add(slot)
    db.session.flush()

    booking = Booking(
        client=client,
        experience=experience,
        professional=professional,
        slot=slot,
        status=status,
        price_at_booking=Decimal("100.00"),
    )

    if status == BookingStatus.COMPLETED:
        booking.completed_at = ends_at

    if status == BookingStatus.CONFIRMED:
        booking.confirmed_at = FIXED_NOW

    db.session.add(booking)
    db.session.flush()
    return booking


def _catalog(app):
    with app.app_context():
        pro_user, pro = _professional(
            "crm-pro@example.com",
            "crm-pro",
        )

        maintenance = _experience(
            pro,
            title="Manutenção em gel",
            slug="manutencao-crm",
            return_days=21,
        )

        long_cycle = _experience(
            pro,
            title="Spa das mãos",
            slug="spa-maos-crm",
            return_days=60,
        )

        ana = _client(
            name="Ana Retorno",
            email="ana-retorno@example.com",
            phone="41999990001",
        )
        bia = _client(
            name="Bia Aniversário",
            email="bia-aniversario@example.com",
            phone="41999990002",
            birth_date=date(1995, 10, 12),
        )
        clara = _client(
            name="Clara Primeira",
            email="clara-primeira@example.com",
            phone="41999990003",
        )

        _booking(
            client=ana,
            professional=pro,
            experience=maintenance,
            local_start=datetime(2026, 8, 20, 10, 0),
            status=BookingStatus.COMPLETED,
        )
        _booking(
            client=ana,
            professional=pro,
            experience=maintenance,
            local_start=datetime(2026, 9, 1, 10, 0),
            status=BookingStatus.COMPLETED,
        )

        _booking(
            client=bia,
            professional=pro,
            experience=long_cycle,
            local_start=datetime(2026, 9, 25, 11, 0),
            status=BookingStatus.COMPLETED,
        )

        _booking(
            client=clara,
            professional=pro,
            experience=maintenance,
            local_start=datetime(2026, 10, 15, 14, 0),
            status=BookingStatus.CONFIRMED,
        )

        _, other_pro = _professional(
            "other-crm@example.com",
            "other-crm",
        )
        other_experience = _experience(
            other_pro,
            title="Serviço de outro profissional",
            slug="outro-servico-crm",
            return_days=20,
        )
        hidden = _client(
            name="Cliente Outro Pro",
            email="outro-cliente@example.com",
            phone="41999990004",
        )
        _booking(
            client=hidden,
            professional=other_pro,
            experience=other_experience,
            local_start=datetime(2026, 9, 1, 9, 0),
            status=BookingStatus.COMPLETED,
        )

        db.session.commit()

        return pro_user.id, pro.id


def test_professional_crm_builds_real_relationship_signals(
    app,
):
    _, profile_id = _catalog(app)

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )

        context = professional_clients_context(
            profile,
            now=FIXED_NOW,
        )

        assert context["client_count"] == 3
        assert context["recurring_client_count"] == 1
        assert context["new_client_count"] == 1
        assert context["reactivation_count"] == 1
        assert context["birthday_week_count"] == 1

        ana = next(
            row
            for row in context["clients"]
            if row["user"].name == "Ana Retorno"
        )

        assert ana["relationship"] == "recorrente"
        assert ana["needs_reactivation"] is True
        assert ana["overdue_days"] == 17
        assert ana["last_experience"].title == "Manutenção em gel"
        assert (
            "https://wa.me/5541999990001"
            in ana["whatsapp_url"]
        )

        clara = next(
            row
            for row in context["clients"]
            if row["user"].name == "Clara Primeira"
        )

        assert clara["relationship"] == "primeiro_agendamento"
        assert clara["next_booking_start"] is not None


def test_professional_clients_page_has_no_cross_professional_leak(
    app,
    client,
    monkeypatch,
):
    user_id, _ = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_crm_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    response = client.get("/pro/clientes")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Ana Retorno" in html
    assert "Bia Aniversário" in html
    assert "Clara Primeira" in html
    assert "Cliente Outro Pro" not in html
    assert "Retorno atrasado 17d" in html
    assert "Aniversário 12/10" in html


def test_professional_clients_search_filters_real_clients(
    app,
    client,
    monkeypatch,
):
    user_id, _ = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_crm_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    html = client.get(
        "/pro/clientes?q=Bia"
    ).get_data(as_text=True)

    assert "Bia Aniversário" in html
    assert "Ana Retorno" not in html
    assert "Clara Primeira" not in html


def test_return_signal_requires_service_rule(
    app,
):
    with app.app_context():
        _, pro = _professional(
            "no-rule@example.com",
            "no-rule",
        )

        experience = _experience(
            pro,
            title="Serviço sem recorrência",
            slug="sem-regra-retorno",
            return_days=None,
        )

        client_profile = _client(
            name="Cliente Sem Regra",
            email="sem-regra@example.com",
            phone="41999990005",
        )

        _booking(
            client=client_profile,
            professional=pro,
            experience=experience,
            local_start=datetime(2026, 7, 1, 10, 0),
            status=BookingStatus.COMPLETED,
        )
        db.session.commit()

        context = professional_clients_context(
            pro,
            now=FIXED_NOW,
        )

        row = context["clients"][0]

        assert row["needs_reactivation"] is False
        assert row["recommended_return_date"] is None
