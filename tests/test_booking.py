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
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )

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