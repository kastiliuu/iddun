"""QA-004 — "Escolher outro horário" voltava com a agenda vazia.

Causa: na confirmação, o horário escolhido fica retido para a cliente
(HELD). Ao voltar para a página do serviço, a lista só mostrava horários
AVAILABLE; o horário da própria cliente sumia e, se era o único do dia,
a agenda aparecia vazia. Escolher de novo continua seguro: hold_slot já
libera a retenção anterior da mesma cliente antes de reter o novo.

A correção só muda a leitura: o horário retido pela própria cliente volta
à lista, marcado como dela. Outras pessoas continuam sem vê-lo.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole

START = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=3)


def _user(name, email):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
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


def _setup(app):
    pro_user = _user("Pro QA004", "pro-qa004@example.com")
    pro = ProfessionalProfile(
        user_id=pro_user.id, display_name="Pro QA004", slug="pro-qa004",
        city="Curitiba", state="PR", is_active=True,
    )
    db.session.add(pro)
    db.session.flush()
    service = Experience(
        professional=pro, title="Escova QA004", slug="escova-qa004", category="cabelo",
        short_description="Serviço de teste.", regular_price=Decimal("80.00"),
        price=Decimal("80.00"), duration_minutes=60, status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(service)
    db.session.flush()
    slot = ExperienceSlot(
        experience=service, professional=pro, starts_at=START,
        ends_at=START + timedelta(hours=1), status=SlotStatus.AVAILABLE,
    )
    db.session.add(slot)
    db.session.commit()
    return {
        "slot": slot.id,
        "ana": _user("Ana QA004", "ana-qa004@example.com").id,
        "bia": _user("Bia QA004", "bia-qa004@example.com").id,
    }


def test_own_held_slot_stays_on_the_service_page_and_can_be_chosen_again(app, client):
    ids = _setup(app)
    _login(client, ids["ana"])
    start = client.post(f"/experiencias/escova-qa004/slots/{ids['slot']}/reservar")
    assert start.status_code == 302 and "/confirmar" in start.headers["Location"]
    assert db.session.get(ExperienceSlot, ids["slot"]).status == SlotStatus.HELD

    # "Escolher outro horário": a página do serviço não fica vazia.
    page = client.get("/experiencias/escova-qa004").get_data(as_text=True)
    assert f'/experiencias/escova-qa004/slots/{ids["slot"]}/reservar' in page
    assert "Seu horário em andamento" in page
    assert "Nenhum horário" not in page

    # Escolher o mesmo horário de novo funciona e não duplica a retenção.
    again = client.post(f"/experiencias/escova-qa004/slots/{ids['slot']}/reservar")
    assert again.status_code == 302 and "/confirmar" in again.headers["Location"]
    db.session.expire_all()
    pending = db.session.scalars(
        select(Booking).where(Booking.slot_id == ids["slot"], Booking.status == BookingStatus.PENDING)
    ).all()
    assert len(pending) == 1


def test_someone_elses_held_slot_stays_hidden(app, client):
    ids = _setup(app)
    _login(client, ids["ana"])
    client.post(f"/experiencias/escova-qa004/slots/{ids['slot']}/reservar")

    _login(client, ids["bia"])
    page = client.get("/experiencias/escova-qa004").get_data(as_text=True)
    assert f'/slots/{ids["slot"]}/reservar' not in page
    assert "Seu horário em andamento" not in page

    client.post("/logout")
    g.pop("_login_user", None)
    guest = client.get("/experiencias/escova-qa004").get_data(as_text=True)
    assert f'/slots/{ids["slot"]}/reservar' not in guest
