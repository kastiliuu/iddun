from datetime import timedelta

from sqlalchemy import select

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
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session
from app.services.time_service import utcnow


def _catalog(app, slot_count=2):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Mobile",
            slug="profissional-mobile",
            city="Curitiba",
            state="PR",
        )

        experience = Experience(
            professional=professional,
            title="Experiência Mobile",
            slug="experiencia-mobile",
            category="unhas",
            short_description="Reserva real pelo app",
            regular_price="150.00",
            price="120.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add_all(
            [
                professional,
                experience,
            ]
        )
        db.session.flush()

        starts_at = (
            utcnow()
            + timedelta(days=2)
        )

        slots = []

        for index in range(slot_count):
            start = (
                starts_at
                + timedelta(
                    hours=index * 2
                )
            )

            slot = ExperienceSlot(
                experience=experience,
                professional=professional,
                starts_at=start,
                ends_at=(
                    start
                    + timedelta(hours=1)
                ),
                status=SlotStatus.AVAILABLE,
            )

            db.session.add(slot)
            slots.append(slot)

        db.session.commit()

        return (
            experience.id,
            [
                slot.id
                for slot in slots
            ],
        )


def _authenticated_client(
    app,
    *,
    email="mobile-booking@example.com",
):
    with app.app_context():
        user = User(
            name="Cliente Mobile",
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

        tokens = issue_session(
            user
        )

        return (
            profile.id,
            {
                "Authorization": (
                    f"Bearer "
                    f"{tokens.access_token}"
                )
            },
        )


def test_booking_api_requires_bearer_token(
    client,
):
    response = client.get(
        "/api/v1/bookings"
    )

    assert response.status_code == 401
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "authentication_required"
    )


def test_client_can_hold_confirm_and_list_booking(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )
    profile_id, headers = (
        _authenticated_client(app)
    )

    hold = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=headers,
    )

    assert hold.status_code == 201

    held = hold.get_json()[
        "booking"
    ]

    assert held["status"] == "pending"
    assert held["slot"]["id"] == slot_ids[0]
    assert held["experience"]["slug"] == (
        "experiencia-mobile"
    )
    assert held["holdExpiresAt"]
    assert held["canConfirm"] is True
    assert held["canCancel"] is True
    assert "no-store" in hold.headers[
        "Cache-Control"
    ]

    confirmed = client.post(
        (
            "/api/v1/bookings/"
            f"{held['id']}/confirm"
        ),
        headers=headers,
    )

    assert confirmed.status_code == 200
    confirmed_payload = (
        confirmed.get_json()
    )

    assert (
        confirmed_payload[
            "booking"
        ]["status"]
        == "confirmed"
    )
    assert (
        confirmed_payload[
            "booking"
        ]["canConfirm"]
        is False
    )

    listed = client.get(
        "/api/v1/bookings",
        headers=headers,
    )

    assert listed.status_code == 200

    data = listed.get_json()

    assert data["pagination"] == {
        "offset": 0,
        "limit": 20,
        "total": 1,
        "nextOffset": None,
        "hasMore": False,
    }
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == held["id"]

    with app.app_context():
        booking = db.session.scalar(
            select(Booking).where(
                Booking.client_id
                == profile_id
            )
        )

        assert (
            booking.status
            == BookingStatus.CONFIRMED
        )
        assert (
            booking.slot.status
            == SlotStatus.BOOKED
        )


def test_hold_is_idempotent_for_same_client_and_slot(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )
    _, headers = (
        _authenticated_client(app)
    )

    path = (
        "/api/v1/experiences/"
        "experiencia-mobile/"
        f"slots/{slot_ids[0]}/hold"
    )

    first = client.post(
        path,
        headers=headers,
    )
    second = client.post(
        path,
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert (
        second.get_json()[
            "booking"
        ]["id"]
        == first.get_json()[
            "booking"
        ]["id"]
    )


def test_second_client_gets_conflict_for_held_slot(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )
    _, first_headers = (
        _authenticated_client(
            app,
            email="first-mobile@example.com",
        )
    )
    _, second_headers = (
        _authenticated_client(
            app,
            email="second-mobile@example.com",
        )
    )

    first = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=first_headers,
    )

    assert first.status_code == 201

    second = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=second_headers,
    )

    assert second.status_code == 409
    assert (
        second.get_json()[
            "error"
        ]["code"]
        == "slot_unavailable"
    )


def test_client_cannot_access_another_clients_booking(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )
    _, owner_headers = (
        _authenticated_client(
            app,
            email="owner-mobile@example.com",
        )
    )
    _, other_headers = (
        _authenticated_client(
            app,
            email="other-mobile@example.com",
        )
    )

    held = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=owner_headers,
    ).get_json()["booking"]

    response = client.get(
        (
            "/api/v1/bookings/"
            f"{held['id']}"
        ),
        headers=other_headers,
    )

    assert response.status_code == 404
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "booking_not_found"
    )


def test_cancel_booking_is_idempotent(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=1,
    )
    _, headers = (
        _authenticated_client(app)
    )

    held = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=headers,
    ).get_json()["booking"]

    path = (
        "/api/v1/bookings/"
        f"{held['id']}/cancel"
    )

    first = client.post(
        path,
        headers=headers,
    )
    second = client.post(
        path,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        first.get_json()[
            "booking"
        ]["status"]
        == "cancelled"
    )
    assert (
        second.get_json()[
            "booking"
        ]["status"]
        == "cancelled"
    )

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_ids[0],
        )

        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_booking_list_can_filter_status(
    app,
    client,
):
    _, slot_ids = _catalog(
        app,
        slot_count=2,
    )
    _, headers = (
        _authenticated_client(app)
    )

    first = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=headers,
    ).get_json()["booking"]

    client.post(
        (
            "/api/v1/bookings/"
            f"{first['id']}/confirm"
        ),
        headers=headers,
    )

    second = client.post(
        (
            "/api/v1/experiences/"
            "experiencia-mobile/"
            f"slots/{slot_ids[1]}/hold"
        ),
        headers=headers,
    ).get_json()["booking"]

    client.post(
        (
            "/api/v1/bookings/"
            f"{second['id']}/cancel"
        ),
        headers=headers,
    )

    response = client.get(
        "/api/v1/bookings",
        query_string={
            "status": "confirmed",
        },
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["pagination"]["total"] == 1
    assert len(payload["items"]) == 1
    assert (
        payload["items"][0]["status"]
        == "confirmed"
    )


def test_hold_rejects_slot_from_another_experience(
    app,
    client,
):
    first_id, first_slots = _catalog(
        app,
        slot_count=1,
    )

    with app.app_context():
        first = db.session.get(
            Experience,
            first_id,
        )

        second = Experience(
            professional=first.professional,
            title="Outra experiência",
            slug="outra-experiencia-mobile",
            category="unhas",
            short_description="Outra",
            regular_price="160.00",
            price="130.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(second)
        db.session.commit()

    _, headers = (
        _authenticated_client(app)
    )

    response = client.post(
        (
            "/api/v1/experiences/"
            "outra-experiencia-mobile/"
            f"slots/{first_slots[0]}/hold"
        ),
        headers=headers,
    )

    assert response.status_code == 404
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "slot_not_found"
    )
