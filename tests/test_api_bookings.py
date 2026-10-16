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


def test_other_client_cannot_confirm_or_cancel_booking(
    app,
    client,
):
    """Neither mutation nor existence disclosure is allowed across clients."""
    _, slot_ids = _catalog(app, slot_count=1)
    _, owner_headers = _authenticated_client(
        app, email="qa-booking-owner@example.com",
    )
    _, attacker_headers = _authenticated_client(
        app, email="qa-booking-attacker@example.com",
    )
    held = client.post(
        (
            "/api/v1/experiences/experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=owner_headers,
    )
    assert held.status_code in (200, 201), held.get_json()
    booking_id = int(held.get_json()["booking"]["id"])

    for operation in ("confirm", "cancel"):
        denied = client.post(
            f"/api/v1/bookings/{booking_id}/{operation}",
            headers=attacker_headers,
        )
        assert denied.status_code == 404
        assert denied.get_json()["error"]["code"] == "booking_not_found"
        assert "qa-booking-owner@example.com" not in denied.get_data(
            as_text=True
        )

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == BookingStatus.PENDING
        assert booking.slot.status == SlotStatus.HELD

    # Owner can still access the booking after unauthorized mutations.
    allowed = client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=owner_headers,
    )
    assert allowed.status_code == 200
    assert "private" in allowed.headers.get("Cache-Control", "").lower()
    assert "no-store" in allowed.headers.get("Cache-Control", "").lower()


def test_booking_list_is_scoped_to_authenticated_client(
    app,
    client,
):
    _, slot_ids = _catalog(app, slot_count=1)
    _, owner_headers = _authenticated_client(
        app, email="qa-list-owner@example.com",
    )
    _, outsider_headers = _authenticated_client(
        app, email="qa-list-outsider@example.com",
    )

    held = client.post(
        (
            "/api/v1/experiences/experiencia-mobile/"
            f"slots/{slot_ids[0]}/hold"
        ),
        headers=owner_headers,
    )
    assert held.status_code in (200, 201), held.get_json()
    booking_id = held.get_json()["booking"]["id"]

    other_list = client.get(
        "/api/v1/bookings",
        headers=outsider_headers,
    )
    assert other_list.status_code == 200
    assert str(booking_id) not in [
        str(item["id"])
        for item in other_list.get_json()["items"]
    ]
    assert "private" in other_list.headers.get("Cache-Control", "").lower()
    assert "no-store" in other_list.headers.get("Cache-Control", "").lower()

    owner_list = client.get(
        "/api/v1/bookings",
        headers=owner_headers,
    )
    assert owner_list.status_code == 200
    assert str(booking_id) in [
        str(item["id"])
        for item in owner_list.get_json()["items"]
    ]


def test_mobile_reschedule_and_cancellation_requests_are_scoped_and_reversible(app, client):
    from app.models.reschedule_request import RescheduleRequest
    _, slots = _catalog(app, slot_count=3)
    profile_id, headers = _authenticated_client(app, email="mobile-parity-owner@example.com")
    _, outsider = _authenticated_client(app, email="mobile-parity-outsider@example.com")
    hold = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold", headers=headers
    )
    assert hold.status_code == 201
    booking_id = hold.get_json()["booking"]["id"]
    assert client.post(f"/api/v1/bookings/{booking_id}/confirm", headers=headers).status_code == 200
    actions_url = f"/api/v1/bookings/{booking_id}/actions"
    assert client.get(actions_url, headers=outsider).status_code == 404
    actions = client.get(actions_url, headers=headers)
    assert actions.status_code == 200
    assert slots[1] in [row["id"] for row in actions.get_json()["rescheduleSlots"]]
    requested = client.post(
        f"/api/v1/bookings/{booking_id}/reschedule-request",
        headers=headers, json={"slotId": slots[1]},
    )
    assert requested.status_code == 200
    assert requested.get_json()["rescheduleRequest"]["status"] == "pending"
    listing = client.get("/api/v1/bookings", headers=headers).get_json()["items"]
    assert listing[0]["rescheduleRequestStatus"] == "pending"
    assert client.get(actions_url, headers=headers).get_json()["rescheduleSlots"] == []
    assert client.post(
        f"/api/v1/bookings/{booking_id}/reschedule-request/withdraw",
        headers=outsider,
    ).status_code == 404
    withdrawn = client.post(
        f"/api/v1/bookings/{booking_id}/reschedule-request/withdraw", headers=headers
    )
    assert withdrawn.status_code == 200
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        assert booking.slot_id == slots[0]
        assert booking.status == BookingStatus.CONFIRMED
        assert db.session.scalar(select(RescheduleRequest)).status == "withdrawn"
    cancellation = client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=headers, json={}
    )
    assert cancellation.status_code == 200
    assert cancellation.get_json()["booking"]["status"] == "confirmed"
    assert client.get("/api/v1/bookings", headers=headers).get_json()["items"][0]["cancellationRequestStatus"] == "pending"
    assert client.post(
        f"/api/v1/bookings/{booking_id}/cancel-request/withdraw", headers=headers
    ).status_code == 200


def test_booking_timeline_private_and_chronological(app, client):
    _, slots = _catalog(app, slot_count=2)
    _, owner_headers = _authenticated_client(app, email="timeline-owner@example.com")
    _, outsider_headers = _authenticated_client(app, email="timeline-outsider@example.com")
    held = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold",
        headers=owner_headers,
    )
    booking_id = held.get_json()["booking"]["id"]
    assert client.post(f"/api/v1/bookings/{booking_id}/confirm", headers=owner_headers).status_code == 200
    path = f"/api/v1/bookings/{booking_id}/timeline"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=outsider_headers).status_code == 404
    result = client.get(path, headers=owner_headers)
    assert result.status_code == 200
    assert "no-store" in result.headers["Cache-Control"]
    events = result.get_json()["items"]
    assert [entry["label"] for entry in events][:2] == ["Reserva iniciada", "Reserva confirmada"]
    assert [entry["at"] for entry in events] == sorted(entry["at"] for entry in events)
    requested = client.post(
        f"/api/v1/bookings/{booking_id}/reschedule-request",
        headers=owner_headers, json={"slotId": slots[1]},
    )
    assert requested.status_code == 200
    events = client.get(path, headers=owner_headers).get_json()["items"]
    assert "Reagendamento solicitado" in [entry["label"] for entry in events]


def test_mobile_no_show_dispute_owner_validation_and_immutable_history(app, client):
    from app.models.no_show_dispute import NoShowDispute
    _, slots = _catalog(app, slot_count=1)
    _, owner_headers = _authenticated_client(app, email="dispute-mobile-owner@example.com")
    _, outsider_headers = _authenticated_client(app, email="dispute-mobile-outsider@example.com")
    hold = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold",
        headers=owner_headers,
    )
    booking_id = hold.get_json()["booking"]["id"]
    assert client.post(
        f"/api/v1/bookings/{booking_id}/confirm", headers=owner_headers
    ).status_code == 200
    path = f"/api/v1/bookings/{booking_id}/no-show-disputes"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=outsider_headers).status_code == 404
    assert client.post(path, headers=outsider_headers, json={
        "justification": "Estou contestando o registro de ausência."
    }).status_code == 404
    assert client.post(path, headers=owner_headers, json={
        "justification": "Estou contestando o registro de ausência."
    }).status_code == 409
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.status = BookingStatus.NO_SHOW
        booking.no_show_at = utcnow()
        db.session.commit()
        original = booking.no_show_at
    created = client.post(path, headers=owner_headers, json={
        "justification": "Compareci à experiência no horário reservado.",
        "evidenceReference": "Protocolo particular 456",
    })
    assert created.status_code == 201
    assert created.get_json()["dispute"]["status"] == "pending"
    assert client.post(path, headers=owner_headers, json={
        "justification": "Outra contestação enquanto pendente."
    }).status_code == 409
    history = client.get(path, headers=owner_headers)
    assert history.status_code == 200
    assert "no-store" in history.headers["Cache-Control"]
    assert history.get_json()["canDispute"] is False
    assert history.get_json()["items"][0]["evidenceReference"] == "Protocolo particular 456"
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        assert booking.status == BookingStatus.NO_SHOW
        assert booking.no_show_at == original
        assert db.session.scalar(select(NoShowDispute)).client_user_id is not None


def test_mobile_review_only_after_completion_and_scoped_to_owner(app, client):
    from app.models.reputation import Review, ReviewTarget
    _, slots = _catalog(app, slot_count=1)
    _, owner = _authenticated_client(app, email="review-mobile-owner@example.com")
    _, outsider = _authenticated_client(app, email="review-mobile-outsider@example.com")
    held = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold",
        headers=owner,
    )
    booking_id = held.get_json()["booking"]["id"]
    assert client.post(f"/api/v1/bookings/{booking_id}/confirm", headers=owner).status_code == 200
    path = f"/api/v1/bookings/{booking_id}/review"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=outsider).status_code == 404
    assert client.post(path, headers=outsider, json={"rating": 5, "recommended": True}).status_code == 404
    assert client.get(path, headers=owner).get_json()["eligible"] is False
    assert client.post(path, headers=owner, json={"rating": 5, "recommended": True}).status_code == 409
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.status = BookingStatus.COMPLETED
        booking.completed_at = utcnow()
        db.session.commit()
    assert client.post(path, headers=owner, json={"rating": 6, "recommended": True}).status_code == 409
    saved = client.post(path, headers=owner, json={"rating": 5, "recommended": True, "comment": "Atendimento excelente"})
    assert saved.status_code == 200
    assert client.get(path, headers=owner).get_json()["review"]["rating"] == 5
    assert client.post(path, headers=owner, json={"rating": 4, "recommended": False}).status_code == 200
    with app.app_context():
        reviews = db.session.scalars(
            select(Review).where(Review.booking_id == int(booking_id), Review.target_type == ReviewTarget.PROFESSIONAL)
        ).all()
        assert len(reviews) == 1
        assert reviews[0].rating == 4


def test_mobile_calendar_share_owner_status_privacy_and_reschedule_freshness(app, client):
    _, slots = _catalog(app, slot_count=2)
    _, owner = _authenticated_client(app, email="calendar-mobile-owner@example.com")
    _, outsider = _authenticated_client(app, email="calendar-mobile-outsider@example.com")
    held = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold",
        headers=owner,
    )
    booking_id = held.get_json()["booking"]["id"]
    prefix = f"/api/v1/bookings/{booking_id}"
    assert client.get(prefix + "/calendar").status_code == 401
    assert client.get(prefix + "/share", headers=outsider).status_code == 404
    assert client.get(prefix + "/calendar", headers=owner).status_code == 409
    assert client.post(prefix + "/confirm", headers=owner).status_code == 200
    calendar = client.get(prefix + "/calendar", headers=owner)
    sharing = client.get(prefix + "/share", headers=owner)
    assert calendar.status_code == sharing.status_code == 200
    assert "no-store" in calendar.headers["Cache-Control"]
    assert "no-store" in sharing.headers["Cache-Control"]
    event = calendar.get_json()
    assert "BEGIN:VCALENDAR" in event["ics"]
    assert "DTSTART:" in event["ics"]
    assert event["uid"] in event["ics"]
    assert "Authorization" not in event["ics"]
    message = sharing.get_json()["message"]
    assert "http" not in message.lower()
    assert "Bearer" not in message
    assert "@" not in message
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.slot_id = slots[1]
        db.session.commit()
    revised = client.get(prefix + "/calendar", headers=owner).get_json()
    assert revised["uid"] == event["uid"]
    assert revised["startsAt"] != event["startsAt"]
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = utcnow()
        db.session.commit()
    assert client.get(prefix + "/calendar", headers=owner).status_code == 409
    assert client.get(prefix + "/share", headers=owner).status_code == 409


def test_native_calendar_event_is_owner_scoped_and_reschedule_updates_time(app, client):
    _, slots = _catalog(app, slot_count=2)
    _, owner = _authenticated_client(app, email="native-calendar-owner@example.com")
    _, outsider = _authenticated_client(app, email="native-calendar-outsider@example.com")
    hold = client.post(
        f"/api/v1/experiences/experiencia-mobile/slots/{slots[0]}/hold",
        headers=owner,
    )
    booking_id = hold.get_json()["booking"]["id"]
    url = f"/api/v1/bookings/{booking_id}/calendar"
    assert client.get(url, headers=outsider).status_code == 404
    assert client.get(url, headers=owner).status_code == 409
    assert client.post(f"/api/v1/bookings/{booking_id}/confirm", headers=owner).status_code == 200
    first = client.get(url, headers=owner).get_json()
    assert "iddun-booking-" in first["uid"]
    assert first["startsAt"] and first["endsAt"]
    assert "no-store" in client.get(url, headers=owner).headers["Cache-Control"]
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.slot_id = slots[1]
        db.session.commit()
    changed = client.get(url, headers=owner).get_json()
    assert changed["uid"] == first["uid"]
    assert changed["startsAt"] != first["startsAt"]
    with app.app_context():
        booking = db.session.get(Booking, int(booking_id))
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = utcnow()
        db.session.commit()
    assert client.get(url, headers=owner).status_code == 409
