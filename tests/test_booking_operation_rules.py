"""D-NV07-01/02/03 e V1-CONV-D02 — regras operacionais das reservas.

- Executor cancela direto só com motivo; a ação entra na trilha.
- No-show nunca é automático: só depois do início mais a tolerância da
  empresa (padrão 15 min, a dona ajusta de 0 a 60), com justificativa.
- Conclusão pelo executor entra na trilha; a pessoa errada não opera.
- O admin atua em exceção: motivo obrigatório e as mesmas regras de horário.
- A rota de QA "simular conflito" não existe em produção.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingActorRole,
    BookingEvent,
    BookingEventAction,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.booking_service import (
    BookingStateError,
    cancel_booking_with_reason,
    complete_booking,
    mark_booking_no_show,
    no_show_available_at,
)

START = datetime(2030, 3, 4, 15, 0, tzinfo=timezone.utc)
PASSWORD = "senha-forte-123"


def _user(name, email, role=UserRole.CLIENT):
    user = User(name=name, email=email, role=role)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()
    return user


def _login(client, user_id):
    g.pop("_login_user", None)
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


@pytest.fixture()
def world(app):
    pro_user = _user("Paula Executora", "executora@example.com")
    other_pro_user = _user("Outra Pro", "outra-pro@example.com")
    owner = _user("Dona Tolerancia", "dona-tolerancia@example.com")
    admin = _user("Admin Iddun", "admin-reservas@example.com", role=UserRole.ADMIN)
    customer = _user("Cliente Reserva", "cliente-reserva@example.com")

    pro = ProfessionalProfile(
        user_id=pro_user.id, display_name="Paula Executora", slug="paula-executora",
        city="Curitiba", state="PR", is_active=True, timezone="America/Sao_Paulo",
    )
    other = ProfessionalProfile(
        user_id=other_pro_user.id, display_name="Outra Pro", slug="outra-pro",
        city="Curitiba", state="PR", is_active=True,
    )
    business = Establishment(
        name="Studio Tolerancia", slug="studio-tolerancia", category="salao",
        city="Curitiba", state="PR", is_active=True,
    )
    db.session.add_all([pro, other, business])
    db.session.flush()
    db.session.add(EstablishmentUserAccess(
        user_id=owner.id, establishment_id=business.id,
        role=EstablishmentAccessRole.OWNER, status=EstablishmentAccessStatus.ACTIVE,
    ))
    service = Experience(
        professional=pro, establishment=business, title="Corte", slug="corte-regras",
        category="cabelo", short_description="Serviço de teste.",
        regular_price=Decimal("100.00"), price=Decimal("100.00"), duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(service)
    db.session.flush()

    bookings = {}
    for key, offset, with_business in (("future", 48, True), ("now", 0, True), ("solo", 0, False)):
        slot = ExperienceSlot(
            experience=service, professional=pro,
            establishment=business if with_business else None,
            starts_at=START + timedelta(hours=offset),
            ends_at=START + timedelta(hours=offset, minutes=60),
            status=SlotStatus.BOOKED,
        )
        db.session.add(slot)
        db.session.flush()
        booking = Booking(
            client=customer.client_profile, experience=service, professional=pro,
            establishment_id=business.id if with_business else None, slot=slot,
            status=BookingStatus.CONFIRMED, price_at_booking=Decimal("100.00"),
            confirmed_at=START - timedelta(days=1),
        )
        db.session.add(booking)
        db.session.flush()
        bookings[key] = booking.id
    db.session.commit()
    return {
        "pro": pro_user.id, "other": other_pro_user.id, "owner": owner.id,
        "admin": admin.id, "business": business.id, "slug": business.slug,
        **bookings,
    }


def _booking(booking_id):
    db.session.expire_all()
    return db.session.get(Booking, booking_id)


def _events(booking_id):
    db.session.expire_all()
    return db.session.scalars(
        select(BookingEvent).where(BookingEvent.booking_id == booking_id).order_by(BookingEvent.id)
    ).all()


def _clock(monkeypatch, moment):
    monkeypatch.setattr("app.services.booking_service.utcnow", lambda: moment)


# ------------------------------------------------------------ serviço


def test_no_show_respects_company_tolerance_and_needs_a_reason(app, world, monkeypatch):
    pro = db.session.get(User, world["pro"])
    booking = _booking(world["now"])
    assert no_show_available_at(booking) == START + timedelta(minutes=15)

    with pytest.raises(BookingStateError, match="tolerância de 15 min"):
        mark_booking_no_show(booking, reason="Não veio", actor=pro, now=START + timedelta(minutes=14))
    with pytest.raises(BookingStateError, match="justificativa"):
        mark_booking_no_show(booking, reason="   ", actor=pro, now=START + timedelta(minutes=15))
    assert _booking(world["now"]).status == BookingStatus.CONFIRMED and _events(world["now"]) == []

    mark_booking_no_show(
        _booking(world["now"]), reason="  Sem   aviso  ", actor=pro, now=START + timedelta(minutes=15),
    )
    [event] = _events(world["now"])
    assert (event.action, event.actor_role, event.actor_user_id, event.reason) == (
        BookingEventAction.NO_SHOW, BookingActorRole.EXECUTOR, world["pro"], "Sem aviso",
    )
    assert _booking(world["now"]).status == BookingStatus.NO_SHOW


def test_tolerance_comes_from_the_company_or_defaults_to_15(app, world):
    business = db.session.get(Establishment, world["business"])
    business.no_show_tolerance_minutes = 0
    db.session.commit()
    assert no_show_available_at(_booking(world["now"])) == START
    # Reserva sem empresa: padrão de 15 min.
    assert no_show_available_at(_booking(world["solo"])) == START + timedelta(minutes=15)


def test_executor_cancel_needs_a_reason_and_is_recorded(app, world):
    pro = db.session.get(User, world["pro"])
    with pytest.raises(BookingStateError, match="motivo"):
        cancel_booking_with_reason(
            _booking(world["future"]), actor=pro, actor_role=BookingActorRole.EXECUTOR,
            reason="", now=START,
        )
    assert _booking(world["future"]).status == BookingStatus.CONFIRMED

    cancel_booking_with_reason(
        _booking(world["future"]), actor=pro, actor_role=BookingActorRole.EXECUTOR,
        reason="Imprevisto", now=START,
    )
    booking = _booking(world["future"])
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancellation_reason == "Imprevisto"
    assert booking.slot.status == SlotStatus.AVAILABLE
    [event] = _events(world["future"])
    assert (event.action, event.actor_role, event.reason) == (
        BookingEventAction.CANCELLED, BookingActorRole.EXECUTOR, "Imprevisto",
    )


def test_completion_by_executor_is_recorded_and_admin_needs_a_reason(app, world):
    pro = db.session.get(User, world["pro"])
    admin = db.session.get(User, world["admin"])
    after_end = START + timedelta(minutes=61)

    with pytest.raises(BookingStateError, match="exceção"):
        complete_booking(
            _booking(world["solo"]), actor=admin, actor_role=BookingActorRole.ADMIN,
            reason=None, now=after_end,
        )
    complete_booking(_booking(world["now"]), actor=pro, now=after_end)
    [event] = _events(world["now"])
    assert (event.action, event.actor_role, event.reason) == (
        BookingEventAction.COMPLETED, BookingActorRole.EXECUTOR, None,
    )


# ---------------------------------------------------------------- Web


def test_dashboard_shows_no_show_only_after_tolerance(app, client, world, monkeypatch):
    monkeypatch.setattr(
        "app.services.professional_dashboard_service.utcnow", lambda: START + timedelta(minutes=5),
    )
    _login(client, world["pro"])
    early = client.get("/pro/painel").get_data(as_text=True)
    assert f'/pro/painel/reservas/{world["now"]}/no-show' not in early
    assert "No-show a partir das 12:15" in early

    monkeypatch.setattr(
        "app.services.professional_dashboard_service.utcnow", lambda: START + timedelta(minutes=16),
    )
    later = client.get("/pro/painel").get_data(as_text=True)
    assert f'/pro/painel/reservas/{world["now"]}/no-show' in later
    assert f'id="no-show-reason-{world["now"]}" name="motivo" maxlength="255" required' in later


def test_other_professional_cannot_operate_the_booking(app, client, world, monkeypatch):
    _clock(monkeypatch, START + timedelta(minutes=30))
    _login(client, world["other"])
    for path, data in (
        (f'/pro/painel/reservas/{world["now"]}/no-show', {"motivo": "x"}),
        (f'/pro/painel/reservas/{world["future"]}/cancelar', {"motivo": "x"}),
    ):
        response = client.post(path, data=data)
        assert response.status_code in (403, 404)
    assert _booking(world["now"]).status == BookingStatus.CONFIRMED
    assert _booking(world["future"]).status == BookingStatus.CONFIRMED
    assert _events(world["now"]) == [] and _events(world["future"]) == []


def test_owner_sets_tolerance_between_0_and_60(app, client, world):
    _login(client, world["owner"])
    page = client.get(f'/business/{world["slug"]}/editar').get_data(as_text=True)
    assert 'name="no_show_tolerance_minutes"' in page and 'value="15"' in page

    for bad in ("61", "-1", "abc", ""):
        response = client.post(
            f'/business/{world["slug"]}/editar',
            data={"section": "reservas", "no_show_tolerance_minutes": bad},
        )
        assert response.status_code == 200, bad
    assert db.session.get(Establishment, world["business"]).no_show_tolerance_minutes == 15

    saved = client.post(
        f'/business/{world["slug"]}/editar',
        data={"section": "reservas", "no_show_tolerance_minutes": "30"},
    )
    assert saved.status_code == 302 and saved.headers["Location"].endswith("#reservas")
    db.session.expire_all()
    assert db.session.get(Establishment, world["business"]).no_show_tolerance_minutes == 30


def test_admin_exception_needs_a_reason_and_follows_the_same_timing(app, client, world, monkeypatch):
    _login(client, world["admin"])
    base = "/admin/reservas/{}/{}"

    # Sem motivo: nada muda.
    client.post(base.format(world["future"], "cancelar"))
    assert _booking(world["future"]).status == BookingStatus.CONFIRMED

    # No-show pelo admin também espera a tolerância.
    _clock(monkeypatch, START + timedelta(minutes=10))
    client.post(base.format(world["now"], "no-show"), data={"motivo": "Pedido do suporte"})
    assert _booking(world["now"]).status == BookingStatus.CONFIRMED

    _clock(monkeypatch, START - timedelta(days=1))
    response = client.post(base.format(world["future"], "cancelar"), data={"motivo": "Fraude confirmada"})
    assert response.status_code == 302
    booking = _booking(world["future"])
    assert booking.status == BookingStatus.CANCELLED
    [event] = _events(world["future"])
    assert (event.actor_role, event.actor_user_id, event.reason) == (
        BookingActorRole.ADMIN, world["admin"], "Fraude confirmada",
    )

    page = client.get("/admin/reservas").get_data(as_text=True)
    assert f'id="admin-reason-{world["now"]}" name="motivo" maxlength="255" required' in page


def test_conflict_simulation_does_not_exist_in_production(app, client, world):
    _login(client, world["admin"])
    slot_id = _booking(world["future"]).slot_id
    app.config["APP_ENV"] = "production"
    try:
        assert client.post(f"/admin/oportunidades/{slot_id}/simular-conflito").status_code == 404
        assert "simular-conflito" not in client.get("/admin/oportunidades").get_data(as_text=True)
    finally:
        app.config["APP_ENV"] = "development"
