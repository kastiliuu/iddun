from datetime import timedelta

from sqlalchemy import select

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.establishment import Establishment
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.booking_service import (
    SlotUnavailableError,
    booking_deadline,
    clear_external_conflict,
    confirm_booking,
    hold_slot,
    mark_external_conflict,
    refresh_slot,
)
from app.services.time_service import utcnow


def _catalog(
    app,
    slot_count=2,
    cutoff=60,
):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Camila Rocha",
            slug="camila-booking",
            primary_specialty="Cabeleireira",
            city="Curitiba",
            state="PR",
            default_booking_cutoff_minutes=cutoff,
        )

        establishment = Establishment(
            name="Studio Booking",
            slug="studio-booking",
            city="Curitiba",
            state="PR",
        )

        db.session.add_all(
            [
                professional,
                establishment,
            ]
        )

        db.session.flush()

        experience = Experience(
            professional=professional,
            establishment=establishment,
            title="Hair Experience Booking",
            slug="hair-experience-booking",
            category="cabelo",
            short_description=(
                "Experiência para teste de reserva"
            ),
            regular_price="350.00",
            price="249.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add(
            experience
        )

        db.session.flush()

        start = (
            utcnow()
            + timedelta(days=2)
        )

        slots = []

        for index in range(
            slot_count
        ):
            slot = ExperienceSlot(
                experience=experience,
                professional=professional,
                establishment=establishment,
                starts_at=(
                    start
                    + timedelta(
                        hours=index * 2
                    )
                ),
                ends_at=(
                    start
                    + timedelta(
                        hours=index * 2 + 1
                    )
                ),
                status=SlotStatus.AVAILABLE,
            )

            db.session.add(
                slot
            )

            slots.append(
                slot
            )

        db.session.commit()

        return (
            experience.id,
            [
                slot.id
                for slot in slots
            ],
        )


def _client_user(
    app,
    email="cliente@example.com",
):
    with app.app_context():
        user = User(
            name="Cliente IDDUN",
            email=email,
            role=UserRole.CLIENT,
        )

        user.set_password(
            "senha-forte-123"
        )

        profile = ClientProfile(
            user=user
        )

        db.session.add_all(
            [
                user,
                profile,
            ]
        )

        db.session.commit()

        return (
            user.id,
            profile.id,
        )


def _login_session(
    client,
    user_id,
):
    with client.session_transaction() as session:
        session["_user_id"] = str(
            user_id
        )

        session["_fresh"] = True


def test_external_conflict_blocks_only_one_slot(
    app,
):
    experience_id, slot_ids = (
        _catalog(
            app,
            slot_count=2,
        )
    )

    with app.app_context():
        first = db.session.get(
            ExperienceSlot,
            slot_ids[0],
        )

        second = db.session.get(
            ExperienceSlot,
            slot_ids[1],
        )

        assert (
            mark_external_conflict(
                first,
                provider="google",
                external_event_id="event-123",
            )
            is True
        )

        assert (
            first.status
            == SlotStatus.BLOCKED_EXTERNAL
        )

        assert (
            second.status
            == SlotStatus.AVAILABLE
        )

        assert (
            clear_external_conflict(
                first
            )
            is True
        )

        assert (
            first.status
            == SlotStatus.AVAILABLE
        )


def test_cutoff_expires_slot_on_backend(
    app,
):
    experience_id, slot_ids = (
        _catalog(
            app,
            slot_count=1,
            cutoff=10,
        )
    )

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_ids[0],
        )

        deadline = (
            booking_deadline(
                slot
            )
        )

        refresh_slot(
            slot,
            now=deadline,
        )

        assert (
            slot.status
            == SlotStatus.EXPIRED
        )


def test_hold_prevents_second_client_from_taking_same_slot(
    app,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )

    _, profile_one_id = (
        _client_user(
            app,
            "one@example.com",
        )
    )

    _, profile_two_id = (
        _client_user(
            app,
            "two@example.com",
        )
    )

    with app.app_context():
        first_profile = (
            db.session.get(
                ClientProfile,
                profile_one_id,
            )
        )

        second_profile = (
            db.session.get(
                ClientProfile,
                profile_two_id,
            )
        )

        booking = hold_slot(
            slot_ids[0],
            first_profile,
        )

        assert (
            booking.status
            == BookingStatus.PENDING
        )

        assert (
            booking.slot.status
            == SlotStatus.HELD
        )

        try:
            hold_slot(
                slot_ids[0],
                second_profile,
            )

        except SlotUnavailableError:
            pass

        else:
            raise AssertionError(
                "Second client should not be able "
                "to hold the same slot"
            )


def test_confirm_booking_marks_slot_booked(
    app,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )

    _, profile_id = (
        _client_user(
            app
        )
    )

    with app.app_context():
        profile = db.session.get(
            ClientProfile,
            profile_id,
        )

        booking = hold_slot(
            slot_ids[0],
            profile,
        )

        booking_id = (
            booking.id
        )

        confirmed = confirm_booking(
            booking_id,
            profile,
        )

        assert (
            confirmed.status
            == BookingStatus.CONFIRMED
        )

        assert (
            confirmed.slot.status
            == SlotStatus.BOOKED
        )

        assert (
            confirmed.confirmed_at
            is not None
        )


def test_booking_detail_shows_only_real_available_slot_count(app, client):
    _catalog(app, slot_count=2)
    html = client.get(
        "/experiencias/hair-experience-booking"
    ).get_data(as_text=True)
    assert "2" in html
    assert "horários" in html
    assert "disponíveis" in html
    assert "Selecione o dia e o horário para continuar sua reserva." in html


def test_unavailable_slot_returns_client_to_availability_section(app, client):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, _ = _client_user(app)
    _login_session(client, user_id)

    with app.app_context():
        slot = db.session.get(ExperienceSlot, slot_ids[0])
        slot.status = SlotStatus.BOOKED
        db.session.commit()

    response = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/experiencias/hair-experience-booking#horarios"
    )


def test_real_experience_detail_shows_available_slot(
    app,
    client,
):
    experience_id, slot_ids = _catalog(
        app,
        slot_count=1,
    )

    with app.app_context():
        experience = db.session.get(Experience, experience_id)
        experience.is_first_experience = True
        experience.badge = "Primeira experiência"
        db.session.commit()

    response = client.get(
        "/experiencias/"
        "hair-experience-booking"
    )

    assert (
        response.status_code
        == 200
    )

    html = response.get_data(
        as_text=True
    )

    assert (
        "Escolha o melhor momento para você."
        in html
    )

    assert (
        "Disponibilidade verificada"
        in html
    )

    assert (
        "Hair Experience Booking"
        in html
    )

    assert (
        "Camila Rocha"
        in html
    )

    assert (
        "Studio Booking"
        in html
    )

    assert "Para qualquer cliente" in html
    assert "Qualquer cliente pode reservar um horário disponível." in html
    assert "Oportunidade IDDUN" in html
    assert "Primeira experiência" not in html

    assert (
        'data-slot-tab="0"'
        in html
    )

    assert (
        'data-slot-panel="0"'
        in html
    )

    assert (
        'role="tabpanel"'
        in html
    )

    assert (
        'name="csrf_token"'
        in html
    )

    assert (
        "Reservar"
        in html
    )


def test_my_bookings_empty_state_keeps_navigation_and_explains_the_flow(
    app,
    client,
):
    user_id, _ = (
        _client_user(
            app,
            "empty-bookings@example.com",
        )
    )

    _login_session(
        client,
        user_id,
    )

    response = client.get(
        "/minhas-reservas"
    )

    assert (
        response.status_code
        == 200
    )

    html = response.get_data(
        as_text=True
    )

    assert (
        "Sua primeira experiência começa aqui."
        in html
    )

    assert (
        "Explorar experiências"
        in html
    )

    assert (
        "Minha conta"
        in html
    )

    assert (
        "Descubra"
        in html
    )

    assert (
        "Escolha"
        in html
    )

    assert (
        "Reserve"
        in html
    )

    assert (
        'href="/experiencias"'
        in html
    )


def test_booking_http_flow_confirms_and_appears_in_my_bookings(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )

    user_id, profile_id = (
        _client_user(
            app
        )
    )

    _login_session(
        client,
        user_id,
    )

    response = client.post(
        (
            "/experiencias/"
            "hair-experience-booking/"
            f"slots/{slot_ids[0]}/reservar"
        ),
        follow_redirects=False,
    )

    assert (
        response.status_code
        == 302
    )

    assert (
        "/reserva/"
        in response.headers[
            "Location"
        ]
    )

    with app.app_context():
        booking = (
            db.session.scalar(
                select(
                    Booking
                ).where(
                    Booking.client_id
                    == profile_id
                )
            )
        )

        booking_id = (
            booking.id
        )

        assert (
            booking.status
            == BookingStatus.PENDING
        )

    response = client.post(
        (
            f"/reserva/{booking_id}"
            "/confirmar"
        ),
        follow_redirects=False,
    )

    assert (
        response.status_code
        == 302
    )

    assert (
        response
        .headers["Location"]
        .endswith(
            f"/minhas-reservas?confirmada={booking_id}"
        )
    )

    response = client.get(
        "/minhas-reservas"
    )

    assert (
        response.status_code
        == 200
    )

    html = response.get_data(
        as_text=True
    )

    assert (
        "Hair Experience Booking"
        in html
    )

    assert (
        "Confirmada"
        in html
    )

    assert (
        "Solicitar cancelamento"
        in html
    )


def test_client_can_book_again_after_completed_appointment(app, client):
    experience_id, slot_ids = _catalog(app, slot_count=2)
    user_id, profile_id = _client_user(app, "returning-client@example.com")

    with app.app_context():
        experience = db.session.get(Experience, experience_id)
        experience.is_first_experience = True

        previous_slot = db.session.get(ExperienceSlot, slot_ids[0])
        previous_slot.starts_at = utcnow() - timedelta(days=7)
        previous_slot.ends_at = previous_slot.starts_at + timedelta(hours=1)
        previous_slot.status = SlotStatus.BOOKED

        completed = Booking(
            client_id=profile_id,
            experience_id=experience_id,
            professional_id=experience.professional_id,
            establishment_id=experience.establishment_id,
            slot_id=previous_slot.id,
            status=BookingStatus.COMPLETED,
            price_at_booking=experience.price,
            confirmed_at=previous_slot.starts_at - timedelta(days=1),
            completed_at=previous_slot.ends_at,
        )
        db.session.add(completed)
        db.session.commit()
        completed_id = completed.id
        expected_price = completed.price_at_booking

    _login_session(client, user_id)
    response = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[1]}/reservar",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/reserva/" in response.headers["Location"]

    with app.app_context():
        previous = db.session.get(Booking, completed_id)
        current = db.session.scalar(
            select(Booking).where(
                Booking.client_id == profile_id,
                Booking.slot_id == slot_ids[1],
            )
        )
        assert previous.status == BookingStatus.COMPLETED
        assert current is not None
        assert current.status == BookingStatus.PENDING
        assert current.price_at_booking == expected_price


def test_external_conflict_cancels_pending_hold(
    app,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )

    _, profile_id = (
        _client_user(
            app,
            "held@example.com",
        )
    )

    with app.app_context():
        profile = db.session.get(
            ClientProfile,
            profile_id,
        )

        booking = hold_slot(
            slot_ids[0],
            profile,
        )

        slot = (
            booking.slot
        )

        assert (
            mark_external_conflict(
                slot,
                provider="google",
            )
            is True
        )

        assert (
            slot.status
            == SlotStatus.BLOCKED_EXTERNAL
        )

        assert (
            booking.status
            == BookingStatus.CANCELLED
        )

        assert (
            booking.cancellation_reason
            == (
                "Horário ocupado "
                "na agenda conectada"
            )
        )


def test_calendar_reconciliation_turns_four_slots_into_three_available(
    app,
):
    from app.services.calendar_sync_service import (
        BusyWindow,
        reconcile_external_busy_windows,
    )

    _, slot_ids = _catalog(
        app,
        slot_count=4,
    )

    with app.app_context():
        target = db.session.get(
            ExperienceSlot,
            slot_ids[2],
        )

        result = (
            reconcile_external_busy_windows(
                target.professional_id,
                [
                    BusyWindow(
                        starts_at=(
                            target.starts_at
                        ),
                        ends_at=(
                            target.ends_at
                        ),
                        external_event_id=(
                            "google-occupied"
                        ),
                        label=(
                            "Cliente particular"
                        ),
                    )
                ],
                provider="google",
            )
        )

        slots = (
            db.session.scalars(
                select(
                    ExperienceSlot
                )
            ).all()
        )

        available = [
            slot
            for slot in slots
            if (
                slot.status
                == SlotStatus.AVAILABLE
            )
        ]

        blocked = [
            slot
            for slot in slots
            if (
                slot.status
                == SlotStatus.BLOCKED_EXTERNAL
            )
        ]

        assert (
            result["blocked"]
            == 1
        )

        assert (
            len(
                available
            )
            == 3
        )

        assert (
            len(
                blocked
            )
            == 1
        )

        assert (
            blocked[0]
            .external_event_id
            == "google-occupied"
        )

        result = (
            reconcile_external_busy_windows(
                target.professional_id,
                [],
                provider="google",
            )
        )

        assert (
            result["restored"]
            == 1
        )

        assert (
            target.status
            == SlotStatus.AVAILABLE
        )

def test_booking_route_rejects_slot_from_different_experience(app, client):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(
        app, "booking-mismatched-slot@example.com",
    )
    _login_session(client, user_id)

    with app.app_context():
        original_slot = db.session.get(ExperienceSlot, slot_ids[0])
        other_experience = Experience(
            professional_id=original_slot.professional_id,
            establishment_id=original_slot.establishment_id,
            title="Outra experiência publicada",
            slug="outra-experiencia-publicada",
            category="cabelo",
            short_description="Serviço diferente",
            regular_price="150.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(other_experience)
        db.session.commit()

    wrong_route = client.post(
        (
            "/experiencias/outra-experiencia-publicada/"
            f"slots/{slot_ids[0]}/reservar"
        ),
        follow_redirects=False,
    )
    assert wrong_route.status_code == 404

    with app.app_context():
        slot = db.session.get(ExperienceSlot, slot_ids[0])
        assert slot.status == SlotStatus.AVAILABLE
        assert (
            db.session.scalar(
                select(Booking).where(Booking.client_id == profile_id)
            )
            is None
        )

    # The same slot remains bookable through its actual experience URL.
    correct_route = client.post(
        (
            "/experiencias/hair-experience-booking/"
            f"slots/{slot_ids[0]}/reservar"
        ),
        follow_redirects=False,
    )
    assert correct_route.status_code == 302
    assert "/reserva/" in correct_route.headers["Location"]


def test_pending_booking_has_resume_link(app, client):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, _ = _client_user(app, 'pending-resume@example.com')
    _login_session(client, user_id)
    response = client.post(
        f'/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar',
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers['Location']
    response = client.get('/minhas-reservas')
    assert response.status_code == 200
    assert b'Continuar confirma' in response.data
    assert location in response.get_data(as_text=True)


def test_pending_hold_cannot_be_submitted_as_cancellation_request(
    app, client, monkeypatch,
):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(app, "safe-cancellation@example.com")
    _login_session(client, user_id)
    held = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar",
        follow_redirects=False,
    )
    assert held.status_code == 302
    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(Booking.client_id == profile_id)
        )
        booking_id = booking.id
    deleted = []
    monkeypatch.setattr(
        "app.routes.bookings.delete_booking_event",
        lambda booking: deleted.append(booking.id),
    )
    for _ in range(2):
        response = client.post(f"/reserva/{booking_id}/cancelar")
        assert response.status_code == 302
    assert deleted == []
    with app.app_context():
        from app.models.cancellation_request import CancellationRequest
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.PENDING
        assert booking.slot.status == SlotStatus.HELD
        assert db.session.scalar(
            select(CancellationRequest).where(
                CancellationRequest.booking_id == booking_id
            )
        ) is None


def test_cancel_request_keeps_calendar_until_executor_effectuates(
    app, client, monkeypatch,
):
    from app.models.cancellation_request import CancellationRequest
    from app.services.cancellation_request_service import execute_cancellation

    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(
        app, "confirmed-safe-cancel@example.com",
    )
    _login_session(client, user_id)
    with app.app_context():
        client_profile = db.session.get(ClientProfile, profile_id)
        confirmed = confirm_booking(
            hold_slot(slot_ids[0], client_profile).id, client_profile
        )
        booking_id = confirmed.id
        executor = User(
            name="Executor calendar", email="executor-calendar@example.com",
            role=UserRole.PROFESSIONAL,
        )
        executor.set_password("senha-forte-123")
        db.session.add(executor)
        db.session.flush()
        confirmed.professional.user_id = executor.id
        db.session.commit()
        executor_id = executor.id

    observed = []
    monkeypatch.setattr(
        "app.routes.bookings.delete_booking_event",
        lambda booking: observed.append((booking.id, booking.status)),
    )
    response = client.post(
        f"/reserva/{booking_id}/cancelar",
        data={"motivo": "Preciso cancelar"},
    )
    assert response.status_code == 302
    assert observed == []
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.slot.status == SlotStatus.BOOKED
        pending = db.session.scalar(
            select(CancellationRequest).where(
                CancellationRequest.booking_id == booking_id
            )
        )
        assert pending.status == "pending"
    _login_session(client, executor_id)
    result = client.post(
        f"/reserva/{booking_id}/cancelamento/efetivar",
        data={"motivo": "Solicitação analisada"},
    )
    assert result.status_code == 302
    assert observed == [(booking_id, BookingStatus.CANCELLED)]
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CANCELLED
        assert db.session.get(CancellationRequest, pending.id).status == "executed"


def test_v1_client_booking_is_visible_only_to_its_business(
    app, client,
):
    """End-to-end: client holds/confirms; Business views; outsider denied."""
    from flask import g
    from app.models.establishment import (
        EstablishmentUserAccess, EstablishmentAccessRole,
    )

    _, slot_ids = _catalog(app, slot_count=1)
    client_user_id, client_profile_id = _client_user(
        app, email="client-integrated-v1@example.com",
    )

    with app.app_context():
        linked_business = db.session.scalar(
            select(Establishment).where(Establishment.slug == "studio-booking")
        )
        owner = User(
            name="Gestora Studio",
            email="gestora-integrated-v1@example.com",
            role=UserRole.CLIENT,
        )
        owner.set_password("senha-forte-123")
        outsider = User(
            name="Outra gestora",
            email="outsider-integrated-v1@example.com",
            role=UserRole.CLIENT,
        )
        outsider.set_password("senha-forte-123")
        db.session.add_all([owner, outsider])
        db.session.flush()
        db.session.add(
            EstablishmentUserAccess(
                user_id=owner.id,
                establishment_id=linked_business.id,
                role=EstablishmentAccessRole.OWNER,
            )
        )
        db.session.commit()
        owner_id, outsider_id = owner.id, outsider.id
        establishment_id = linked_business.id

    _login_session(client, client_user_id)
    held = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar"
    )
    assert held.status_code == 302

    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(Booking.client_id == client_profile_id)
        )
        assert booking is not None
        assert booking.establishment_id == establishment_id
        assert booking.status == BookingStatus.PENDING
        booking_id = booking.id

    confirmed = client.post(f"/reserva/{booking_id}/confirmar")
    assert confirmed.status_code == 302

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.slot.status == SlotStatus.BOOKED

    # A client does not automatically receive access to the company's
    # internal dashboard just because they booked there.
    assert client.get("/business/studio-booking/reservas").status_code == 403

    _login_session(client, owner_id)
    g.pop("_login_user", None)

    catalog = client.get("/business/studio-booking/servicos")
    assert catalog.status_code == 200
    assert "Hair Experience Booking" in catalog.get_data(as_text=True)

    bookings_page = client.get("/business/studio-booking/reservas?status=confirmed")
    assert bookings_page.status_code == 200
    booking_html = bookings_page.get_data(as_text=True)
    assert "Hair Experience Booking" in booking_html
    assert "Cliente IDDUN" in booking_html
    assert "R$ 249,00" in booking_html

    metrics = client.get("/business/studio-booking/indicadores")
    assert metrics.status_code == 200
    metrics_html = metrics.get_data(as_text=True)
    assert "1 no total" in metrics_html
    assert "R$ 0,00" in metrics_html

    _login_session(client, outsider_id)
    g.pop("_login_user", None)
    for path in ("servicos", "reservas", "indicadores"):
        response = client.get(f"/business/studio-booking/{path}")
        assert response.status_code == 403

    # Viewing operational data cannot mutate the original reservation.
    with app.app_context():
        assert db.session.get(Booking, booking_id).status == BookingStatus.CONFIRMED


def test_v1_completed_booking_flows_from_client_through_pro_to_business(
    app, client, monkeypatch,
):
    from flask import g
    from app.models.establishment import (
        EstablishmentAccessRole, EstablishmentUserAccess,
    )

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


def test_v1_cancellation_and_no_show_update_business_without_completed_value(
    app, client, monkeypatch,
):
    """Two client bookings; Pro cancels one and flags the other as no-show."""
    from flask import g
    from app.models.establishment import (
        EstablishmentAccessRole, EstablishmentUserAccess,
    )

    _, slot_ids = _catalog(app, slot_count=2)
    first_user_id, first_profile_id = _client_user(
        app, email="v1-cancel-client@example.com",
    )
    second_user_id, second_profile_id = _client_user(
        app, email="v1-noshow-client@example.com",
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
        pro_user = User(
            name="Pro Operação",
            email="v1-cancel-noshow-pro@example.com",
            role=UserRole.PROFESSIONAL,
        )
        pro_user.set_password("senha-forte-123")
        manager = User(
            name="Gerente Operação",
            email="v1-cancel-noshow-manager@example.com",
            role=UserRole.CLIENT,
        )
        manager.set_password("senha-forte-123")
        db.session.add_all([pro_user, manager])
        db.session.flush()
        professional.user_id = pro_user.id
        db.session.add(
            EstablishmentUserAccess(
                user_id=manager.id,
                establishment_id=establishment.id,
                role=EstablishmentAccessRole.OWNER,
            )
        )
        db.session.commit()
        pro_user_id, manager_id = pro_user.id, manager.id

    booking_ids = []
    for user_id, profile_id, slot_id in (
        (first_user_id, first_profile_id, slot_ids[0]),
        (second_user_id, second_profile_id, slot_ids[1]),
    ):
        _login_session(client, user_id)
        g.pop("_login_user", None)
        assert client.post(
            f"/experiencias/hair-experience-booking/slots/{slot_id}/reservar"
        ).status_code == 302
        with app.app_context():
            booking_id = db.session.scalar(
                select(Booking.id).where(
                    Booking.client_id == profile_id,
                    Booking.status == BookingStatus.PENDING,
                )
            )
            assert booking_id is not None
        assert client.post(f"/reserva/{booking_id}/confirmar").status_code == 302
        booking_ids.append(booking_id)

    cancelled_id, no_show_id = booking_ids
    monkeypatch.setattr(
        "app.routes.platform.delete_booking_event",
        lambda booking: None,
    )
    _login_session(client, pro_user_id)
    g.pop("_login_user", None)

    cancelled = client.post(f"/pro/painel/reservas/{cancelled_id}/cancelar")
    assert cancelled.status_code == 302
    with app.app_context():
        cancelled_booking = db.session.get(Booking, cancelled_id)
        assert cancelled_booking.status == BookingStatus.CANCELLED
        assert cancelled_booking.cancelled_at is not None
        assert cancelled_booking.slot.status == SlotStatus.AVAILABLE

    # A no-show must not be recorded before the appointment begins.
    early = client.post(f"/pro/painel/reservas/{no_show_id}/no-show")
    assert early.status_code == 302
    with app.app_context():
        booking = db.session.get(Booking, no_show_id)
        assert booking.status == BookingStatus.CONFIRMED
        after_start = booking.slot.starts_at + timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.booking_service.utcnow",
        lambda: after_start,
    )
    marked = client.post(f"/pro/painel/reservas/{no_show_id}/no-show")
    assert marked.status_code == 302
    with app.app_context():
        booking = db.session.get(Booking, no_show_id)
        assert booking.status == BookingStatus.NO_SHOW
        assert booking.no_show_at is not None

    _login_session(client, manager_id)
    g.pop("_login_user", None)
    for status, expected in (
        ("cancelled", "Cancelada"),
        ("no_show", "Não compareceu"),
    ):
        response = client.get(
            f"/business/studio-booking/reservas?status={status}"
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Hair Experience Booking" in html
        assert expected in html

    indicators = client.get("/business/studio-booking/indicadores")
    assert indicators.status_code == 200
    html = indicators.get_data(as_text=True)
    assert "2 no total" in html
    assert "R$ 0,00" in html
    assert "Ainda não há atendimentos concluídos" in html

    # Business can inspect the operation but cannot mutate either booking.
    with app.app_context():
        assert db.session.get(Booking, cancelled_id).status == BookingStatus.CANCELLED
        assert db.session.get(Booking, no_show_id).status == BookingStatus.NO_SHOW


def test_v1_google_busy_window_invalidates_client_hold_and_restores_slot(
    app, client,
):
    """HTTP hold -> external collision -> no stale confirmation -> restored availability."""
    from app.services.calendar_sync_service import (
        BusyWindow,
        reconcile_external_busy_windows,
    )

    _, slot_ids = _catalog(app, slot_count=2)
    client_id, client_profile_id = _client_user(
        app, email="calendar-conflict-v1@example.com",
    )
    _login_session(client, client_id)

    held = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar"
    )
    assert held.status_code == 302

    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(Booking.client_id == client_profile_id)
        )
        assert booking is not None
        assert booking.status == BookingStatus.PENDING
        booking_id = booking.id
        conflict_slot = db.session.get(ExperienceSlot, slot_ids[0])
        non_conflicting_slot = db.session.get(ExperienceSlot, slot_ids[1])
        assert non_conflicting_slot.status == SlotStatus.AVAILABLE
        busy = BusyWindow(
            starts_at=conflict_slot.starts_at,
            ends_at=conflict_slot.ends_at,
            external_event_id="google-test-conflict-v1",
            label="Atendimento na agenda Google",
        )
        result = reconcile_external_busy_windows(
            conflict_slot.professional_id,
            [busy],
            provider="google",
        )
        assert result["blocked"] == 1
        assert db.session.get(Booking, booking_id).status == BookingStatus.CANCELLED
        assert conflict_slot.status == SlotStatus.BLOCKED_EXTERNAL
        assert conflict_slot.external_event_id == "google-test-conflict-v1"
        assert non_conflicting_slot.status == SlotStatus.AVAILABLE

    # An invalidated pending hold must not be confirmable over HTTP.
    old_confirmation = client.post(f"/reserva/{booking_id}/confirmar")
    assert old_confirmation.status_code == 302
    assert old_confirmation.headers["Location"].endswith(
        "/experiencias/hair-experience-booking"
    )
    with app.app_context():
        assert db.session.get(Booking, booking_id).status == BookingStatus.CANCELLED

    # A second attempt for the busy time cannot create another hold.
    blocked = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar"
    )
    assert blocked.status_code == 302
    with app.app_context():
        active_holds = db.session.scalars(
            select(Booking).where(
                Booking.slot_id == slot_ids[0],
                Booking.status == BookingStatus.PENDING,
            )
        ).all()
        assert active_holds == []

        target = db.session.get(ExperienceSlot, slot_ids[0])
        restored = reconcile_external_busy_windows(
            target.professional_id,
            [],
            provider="google",
        )
        assert restored["restored"] == 1
        assert target.status == SlotStatus.AVAILABLE
        assert target.external_event_id is None
        assert db.session.get(Booking, booking_id).status == BookingStatus.CANCELLED

    # Restoration reopens the slot but never resurrects the cancelled hold.
    new_hold = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar"
    )
    assert new_hold.status_code == 302
    assert "/reserva/" in new_hold.headers["Location"]
    with app.app_context():
        new_booking = db.session.scalar(
            select(Booking).where(
                Booking.slot_id == slot_ids[0],
                Booking.status == BookingStatus.PENDING,
            )
        )
        assert new_booking is not None
        assert new_booking.id != booking_id


def test_v1_google_freebusy_adapter_syncs_real_response_shape_without_network(
    app, monkeypatch,
):
    """FreeBusy adapter -> reconcile -> restore, with no external credentials."""
    from app.models.calendar import CalendarConnection, CalendarProvider
    from app.services.google_calendar_service import sync_connection
    from app.services.time_service import as_utc

    _, slot_ids = _catalog(app, slot_count=2)
    requests = []
    payloads = []

    class FakeRequest:
        def execute(self):
            return payloads.pop(0)

    class FakeFreebusy:
        def query(self, *, body):
            requests.append(body)
            return FakeRequest()

    class FakeGoogleService:
        def freebusy(self):
            return FakeFreebusy()

    monkeypatch.setattr(
        "app.services.google_calendar_service.service_for",
        lambda connection: FakeGoogleService(),
    )

    with app.app_context():
        target = db.session.get(ExperienceSlot, slot_ids[0])
        unaffected = db.session.get(ExperienceSlot, slot_ids[1])
        connection = CalendarConnection(
            professional_id=target.professional_id,
            provider=CalendarProvider.GOOGLE,
            calendar_id="primary-test@example.com",
            sync_enabled=True,
        )
        db.session.add(connection)
        db.session.commit()
        connection_id = connection.id
        busy_start = as_utc(target.starts_at).isoformat().replace("+00:00", "Z")
        busy_end = as_utc(target.ends_at).isoformat().replace("+00:00", "Z")

        payloads.append({
            "calendars": {
                "primary-test@example.com": {
                    "busy": [{"start": busy_start, "end": busy_end}],
                },
            },
        })
        first = sync_connection(connection)
        assert first["blocked"] == 1
        assert target.status == SlotStatus.BLOCKED_EXTERNAL
        assert target.external_calendar_provider == CalendarProvider.GOOGLE
        assert unaffected.status == SlotStatus.AVAILABLE
        assert connection.last_sync_status == "success"
        assert connection.last_synced_at is not None
        assert requests[0]["items"] == [{"id": "primary-test@example.com"}]
        assert requests[0]["timeMin"].endswith("Z")
        assert requests[0]["timeMax"].endswith("Z")

        payloads.append({
            "calendars": {"primary-test@example.com": {"busy": []}},
        })
        second = sync_connection(connection)
        assert second["restored"] == 1
        assert target.status == SlotStatus.AVAILABLE
        assert target.external_calendar_provider is None
        assert db.session.get(CalendarConnection, connection_id).last_sync_status == "success"


def test_v1_google_freebusy_failure_keeps_slots_and_records_error(app, monkeypatch):
    """Provider outages should never silently remove availability."""
    from app.models.calendar import CalendarConnection, CalendarProvider
    from app.services.google_calendar_service import sync_connection

    _, slot_ids = _catalog(app, slot_count=1)

    class UnavailableRequest:
        def execute(self):
            raise RuntimeError("Google FreeBusy temporariamente indisponível")

    class UnavailableService:
        def freebusy(self):
            return self

        def query(self, *, body):
            return UnavailableRequest()

    monkeypatch.setattr(
        "app.services.google_calendar_service.service_for",
        lambda connection: UnavailableService(),
    )

    with app.app_context():
        slot = db.session.get(ExperienceSlot, slot_ids[0])
        connection = CalendarConnection(
            professional_id=slot.professional_id,
            provider=CalendarProvider.GOOGLE,
            calendar_id="primary-test@example.com",
            sync_enabled=True,
        )
        db.session.add(connection)
        db.session.commit()
        connection_id = connection.id

        import pytest
        with pytest.raises(RuntimeError, match="FreeBusy"):
            sync_connection(connection)

        assert db.session.get(ExperienceSlot, slot_ids[0]).status == SlotStatus.AVAILABLE
        saved = db.session.get(CalendarConnection, connection_id)
        assert saved.last_sync_status == "error"
        assert "FreeBusy" in saved.last_sync_error


def test_booking_confirmation_feedback_is_scoped_to_confirmed_owner(app, client):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(app)
    _login_session(client, user_id)

    start = client.post(
        f"/experiencias/hair-experience-booking/slots/{slot_ids[0]}/reservar",
        follow_redirects=False,
    )
    assert start.status_code == 302

    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(Booking.client_id == profile_id)
        )
        booking_id = booking.id

    review = client.get(f"/reserva/{booking_id}/confirmar")
    assert review.status_code == 200
    assert "pagamento do serviço será combinado diretamente" in review.get_data(as_text=True)

    confirm = client.post(
        f"/reserva/{booking_id}/confirmar", follow_redirects=False
    )
    assert confirm.status_code == 302
    assert confirm.headers["Location"].endswith(
        f"/minhas-reservas?confirmada={booking_id}"
    )

    confirmed_page = client.get(confirm.headers["Location"])
    html = confirmed_page.get_data(as_text=True)
    assert "Reserva confirmada!" in html
    assert 'id="reserva-confirmada"' in html

    ordinary_page = client.get("/minhas-reservas").get_data(as_text=True)
    assert "Reserva confirmada!" not in ordinary_page

    missing_page = client.get("/minhas-reservas?confirmada=999999").get_data(as_text=True)
    assert "Reserva confirmada!" not in missing_page

def test_client_requests_and_withdraws_without_cancelling_booking(app, client):
    from app.models.cancellation_request import CancellationRequest
    from app.services.cancellation_request_service import (
        request_cancellation, withdraw_cancellation, pending_cancellation,
    )
    _, slots = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(app, "requester@example.com")
    with app.app_context():
        profile = db.session.get(ClientProfile, profile_id)
        booking = hold_slot(slots[0], profile)
        booking = confirm_booking(booking.id, profile)
        initial_slot_status = booking.slot.status
        user = db.session.get(User, user_id)
        first = request_cancellation(booking, user, "Mudança de planos")
        second = request_cancellation(booking, user, "Outro motivo")
        assert first.id == second.id
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.slot.status == initial_slot_status
        assert first.reason == "Mudança de planos"
        assert pending_cancellation(booking.id).id == first.id
        withdraw_cancellation(booking, user)
        assert booking.status == BookingStatus.CONFIRMED
        assert pending_cancellation(booking.id) is None
        assert db.session.get(CancellationRequest, first.id).status == "withdrawn"


def test_only_booking_executor_can_execute_request_and_history_remains(app, client):
    from app.models.cancellation_request import CancellationRequest
    from app.services.booking_service import BookingStateError
    from app.services.cancellation_request_service import (
        request_cancellation, execute_cancellation,
    )
    _, slots = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(app, "cancel-owner@example.com")
    with app.app_context():
        profile = db.session.get(ClientProfile, profile_id)
        booking = confirm_booking(hold_slot(slots[0], profile).id, profile)
        executor = User(name="Executor", email="executor-cancel@example.com", role=UserRole.PROFESSIONAL)
        executor.set_password("senha-forte-123")
        db.session.add(executor)
        db.session.flush()
        booking.professional.user_id = executor.id
        db.session.commit()
        owner = db.session.get(User, user_id)
        pending = request_cancellation(booking, owner, "Compromisso")
        for actor, reason in [(owner, "Não autorizado"), (executor, "")]:
            try:
                execute_cancellation(booking, actor, reason)
            except BookingStateError:
                pass
            else:
                raise AssertionError("Cancellation must require executor and reason")
        assert booking.status == BookingStatus.CONFIRMED
        execute_cancellation(booking, executor, "Cliente pediu para cancelar")
        assert booking.status == BookingStatus.CANCELLED
        audit = db.session.get(CancellationRequest, pending.id)
        assert audit.status == "executed"
        assert audit.client_user_id == owner.id
        assert audit.resolved_by_user_id == executor.id
        assert audit.resolution_reason == "Cliente pediu para cancelar"


def test_client_web_cancellation_form_creates_pending_request(app, client):
    from app.models.cancellation_request import CancellationRequest
    _, slots = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(app, "web-cancel@example.com")
    with app.app_context():
        profile = db.session.get(ClientProfile, profile_id)
        booking = confirm_booking(hold_slot(slots[0], profile).id, profile)
        booking_id = booking.id
    _login_session(client, user_id)
    html = client.get("/minhas-reservas").get_data(as_text=True)
    assert "Solicitar cancelamento" in html
    response = client.post(
        f"/reserva/{booking_id}/cancelar",
        data={"motivo": "Preciso remarcar"}, follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED
        req = db.session.scalar(select(CancellationRequest).where(CancellationRequest.booking_id == booking_id))
        assert req.status == "pending"
        assert req.reason == "Preciso remarcar"
    html = client.get("/minhas-reservas").get_data(as_text=True)
    assert "Retirar solicitação" in html
    assert "Cancelar reserva" not in html

def test_non_owner_cannot_submit_or_execute_cancellation_web(app, client):
    from app.models.cancellation_request import CancellationRequest
    _, slots = _catalog(app, slot_count=1)
    owner_id, owner_profile = _client_user(app, "owner-denied@example.com")
    attacker_id, _ = _client_user(app, "attacker-denied@example.com")
    with app.app_context():
        profile = db.session.get(ClientProfile, owner_profile)
        booking = confirm_booking(hold_slot(slots[0], profile).id, profile)
        booking_id = booking.id
    _login_session(client, attacker_id)
    response = client.post(
        f"/reserva/{booking_id}/cancelar",
        data={"motivo": "intrusão"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    response = client.post(
        f"/reserva/{booking_id}/cancelamento/efetivar",
        data={"motivo": "intrusão"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED
        assert db.session.scalar(
            select(CancellationRequest).where(CancellationRequest.booking_id == booking_id)
        ) is None
