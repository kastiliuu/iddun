"""Regression coverage for IDDUN Pro insights and financial metrics."""

from datetime import datetime, timedelta, timezone
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
from app.services.professional_insights_service import (
    professional_insights_context,
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


def _professional(email, slug):
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
        bio="Profissional para teste de insights.",
        city="Curitiba",
        state="PR",
        timezone="America/Sao_Paulo",
        onboarding_completed=True,
        is_active=True,
    )

    db.session.add_all([user, profile])
    db.session.flush()
    return user, profile


def _client(name, email):
    user = User(
        name=name,
        email=email,
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")

    profile = ClientProfile(
        user=user,
        city="Curitiba",
        state="PR",
    )
    db.session.add_all([user, profile])
    db.session.flush()
    return profile


def _experience(profile, title, slug, price):
    item = Experience(
        professional=profile,
        title=title,
        slug=slug,
        category="unhas",
        short_description="Serviço de teste.",
        regular_price=price,
        price=price,
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _booking(
    *,
    client,
    professional,
    experience,
    local_start,
    status,
    price,
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
        price_at_booking=Decimal(str(price)),
    )

    if status == BookingStatus.COMPLETED:
        booking.completed_at = ends_at
    elif status == BookingStatus.CONFIRMED:
        booking.confirmed_at = FIXED_NOW
    elif status == BookingStatus.CANCELLED:
        booking.cancelled_at = starts_at
    elif status == BookingStatus.NO_SHOW:
        booking.no_show_at = starts_at

    db.session.add(booking)
    db.session.flush()
    return booking


def _catalog(app):
    with app.app_context():
        pro_user, pro = _professional(
            "insights-pro@example.com",
            "insights-pro",
        )
        ana = _client(
            "Ana Insights",
            "ana-insights@example.com",
        )
        bia = _client(
            "Bia Insights",
            "bia-insights@example.com",
        )

        gel = _experience(
            pro,
            "Manutenção em gel",
            "gel-insights",
            "150.00",
        )
        blindagem = _experience(
            pro,
            "Blindagem",
            "blindagem-insights",
            "100.00",
        )

        _booking(
            client=ana,
            professional=pro,
            experience=gel,
            local_start=datetime(2026, 10, 2, 14, 0),
            status=BookingStatus.COMPLETED,
            price="150.00",
        )
        _booking(
            client=bia,
            professional=pro,
            experience=gel,
            local_start=datetime(2026, 10, 5, 14, 0),
            status=BookingStatus.COMPLETED,
            price="150.00",
        )
        _booking(
            client=ana,
            professional=pro,
            experience=blindagem,
            local_start=datetime(2026, 10, 12, 10, 0),
            status=BookingStatus.CONFIRMED,
            price="100.00",
        )
        _booking(
            client=bia,
            professional=pro,
            experience=blindagem,
            local_start=datetime(2026, 10, 6, 10, 0),
            status=BookingStatus.CANCELLED,
            price="100.00",
        )
        _booking(
            client=ana,
            professional=pro,
            experience=blindagem,
            local_start=datetime(2026, 10, 7, 15, 0),
            status=BookingStatus.NO_SHOW,
            price="100.00",
        )

        _booking(
            client=ana,
            professional=pro,
            experience=blindagem,
            local_start=datetime(2026, 9, 12, 10, 0),
            status=BookingStatus.COMPLETED,
            price="100.00",
        )

        _, other_pro = _professional(
            "other-insights@example.com",
            "other-insights",
        )
        other_service = _experience(
            other_pro,
            "Outro serviço",
            "other-insights-service",
            "999.00",
        )
        outsider = _client(
            "Outro Cliente",
            "outro-insights-client@example.com",
        )
        _booking(
            client=outsider,
            professional=other_pro,
            experience=other_service,
            local_start=datetime(2026, 10, 3, 12, 0),
            status=BookingStatus.COMPLETED,
            price="999.00",
        )

        db.session.commit()
        return pro_user.id, pro.id


def test_professional_insights_calculates_real_financial_metrics(app):
    _, profile_id = _catalog(app)

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )
        context = professional_insights_context(
            profile,
            now=FIXED_NOW,
        )

        current = context["current"]

        assert current["realized_revenue"] == Decimal("300.00")
        assert current["forecast_revenue"] == Decimal("100.00")
        assert current["average_ticket"] == Decimal("150.00")
        assert current["completed_count"] == 2
        assert current["cancelled_count"] == 1
        assert current["no_show_count"] == 1
        assert current["outcome_count"] == 4
        assert current["cancellation_rate"] == 25.0
        assert current["no_show_rate"] == 25.0

        assert current["realized_variation_percent"] == 200.0
        assert context["top_service"]["experience"].title == "Manutenção em gel"
        assert context["top_service"]["completed_count"] == 2

        assert context["previous"]["realized_revenue"] == Decimal("100.00")


def test_professional_insights_does_not_leak_other_professional_data(app):
    _, profile_id = _catalog(app)

    with app.app_context():
        profile = db.session.get(
            ProfessionalProfile,
            profile_id,
        )
        context = professional_insights_context(
            profile,
            now=FIXED_NOW,
        )

        titles = [
            row["experience"].title
            for row in context["current"]["services"]
        ]

        assert "Outro serviço" not in titles
        assert context["current"]["realized_revenue"] != Decimal("1299.00")


def test_professional_insights_page_renders_real_metrics(
    app,
    client,
    monkeypatch,
):
    user_id, _ = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_insights_service.utcnow",
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        "app.services.professional_dashboard_service.utcnow",
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        "app.services.professional_crm_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    response = client.get("/pro/insights")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Entenda o que seu trabalho está gerando." in html
    assert "R$ 300,00" in html
    assert "R$ 100,00" in html
    assert "R$ 150,00" in html
    assert "25,0%" in html
    assert "Manutenção em gel" in html
    assert "Ocupação não aparece nesta sprint" in html


def test_pro_dashboard_surfaces_real_monthly_summary(
    app,
    client,
    monkeypatch,
):
    user_id, _ = _catalog(app)

    monkeypatch.setattr(
        "app.services.professional_insights_service.utcnow",
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        "app.services.professional_dashboard_service.utcnow",
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        "app.services.professional_crm_service.utcnow",
        lambda: FIXED_NOW,
    )

    _login(client, user_id)

    html = client.get(
        "/pro/painel"
    ).get_data(as_text=True)

    assert "SAÚDE DO NEGÓCIO" in html
    assert "R$ 300,00" in html
    assert "R$ 100,00" in html
    assert "R$ 150,00" in html
    assert "Manutenção em gel" in html
