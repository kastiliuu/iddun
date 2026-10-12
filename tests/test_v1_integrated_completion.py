"""V1 acceptance path: Client booking -> Pro completion -> Business metrics."""
from datetime import timedelta

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot
from app.models.establishment import (
    Establishment, EstablishmentAccessRole, EstablishmentUserAccess,
)
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.time_service import utcnow

from tests.test_booking import _catalog, _client_user, _login_session


def test_v1_completed_booking_flows_from_client_through_pro_to_business(
    app, client, monkeypatch,
):
    _, slot_ids = _catalog(app, slot_count=1)
    client_id, client_profile_id = _client_user(
        app, email="integrated-completion-client@example.com",
    )

    with app.app_context():
        professional = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.slug == "camila-booking"
            )
        )
        establishment = db.session.scalar(
            select(Establishment).where(Establishment.slug == "studio-booking")
        )
        professional_user = User(
            name="Camila Profissional",
            email="integrated-completion-pro@example.com",
            role=UserRole.PROFESSIONAL,
        )
        professional_user.set_password("senha-forte-123")
        manager = User(
            name="Gestora Business",
            email="integrated-completion-manager@example.com",
            role=UserRole.CLIENT,
        )
        manager.set_password("senha-forte-123")
        db.session.add_all([professional_user, manager])
        db.session.flush()
        professional.user_id = professional_user.id
        db.session.add(
            EstablishmentUserAccess(
                user_id=manager.id,
                establishment_id=establishment.id,
                role=EstablishmentAccessRole.OWNER,
            )
        )
        db.session.commit()
        professional_user_id, manager_id = professional_user.id, manager.id

    _login_session(client, client_id)
    assert client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar"
    ).status_code == 302

    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(Booking.client_id == client_profile_id)
        )
        booking_id = booking.id
        assert booking.status == BookingStatus.PENDING

    assert client.post(f"/reserva/{booking_id}/confirmar").status_code == 302

    _login_session(client, professional_user_id)
    g.pop("_login_user", None)

    # A professional cannot mark an appointment completed before its end.
    early = client.post(f"/pro/painel/reservas/{booking_id}/concluir")
    assert early.status_code == 302
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED
        after_service = booking.slot.ends_at + timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.booking_service.utcnow",
        lambda: after_service,
    )
    done = client.post(f"/pro/painel/reservas/{booking_id}/concluir")
    assert done.status_code == 302
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.COMPLETED
        assert booking.completed_at is not None

    _login_session(client, manager_id)
    g.pop("_login_user", None)
    completed = client.get("/business/studio-booking/reservas?status=completed")
    assert completed.status_code == 200
    page = completed.get_data(as_text=True)
    assert "Hair Experience Booking" in page
    assert "Cliente IDDUN" in page
    assert "Concluída" in page

    insights = client.get("/business/studio-booking/indicadores")
    assert insights.status_code == 200
    html = insights.get_data(as_text=True)
    assert "1 no total" in html
    assert "R$ 249,00" in html
    assert "Hair Experience Booking" in html

    _login_session(client, client_id)
    g.pop("_login_user", None)
    assert client.get("/business/studio-booking/indicadores").status_code == 403
    with app.app_context():
        assert db.session.get(Booking, booking_id).status == BookingStatus.COMPLETED
