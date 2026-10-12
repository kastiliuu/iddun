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
            "/minhas-reservas"
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
        "Cancelar reserva"
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


def test_invalid_repeat_cancellation_does_not_delete_calendar_event(
    app, client, monkeypatch,
):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(
        app, "safe-cancellation@example.com",
    )
    _login_session(client, user_id)

    held = client.post(
        (
            "/experiencias/hair-experience-booking/"
            f"slots/{slot_ids[0]}/reservar"
        ),
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

    first = client.post(f"/reserva/{booking_id}/cancelar")
    assert first.status_code == 302
    second = client.post(f"/reserva/{booking_id}/cancelar")
    assert second.status_code == 302
    assert deleted == []

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CANCELLED


def test_confirmed_cancellation_deletes_calendar_after_database_update(
    app, client, monkeypatch,
):
    _, slot_ids = _catalog(app, slot_count=1)
    user_id, profile_id = _client_user(
        app, "confirmed-safe-cancel@example.com",
    )
    _login_session(client, user_id)

    with app.app_context():
        client_profile = db.session.get(ClientProfile, profile_id)
        held = hold_slot(slot_ids[0], client_profile)
        confirmed = confirm_booking(held.id, client_profile)
        booking_id = confirmed.id

    observed = []

    def observe_deleted(booking):
        observed.append((booking.id, booking.status))

    monkeypatch.setattr(
        "app.routes.bookings.delete_booking_event",
        observe_deleted,
    )
    response = client.post(f"/reserva/{booking_id}/cancelar")
    assert response.status_code == 302
    assert observed == [(booking_id, BookingStatus.CANCELLED)]


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
