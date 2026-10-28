"""Notification HTTP authorization, validation and tenant isolation (NV-04)."""
from app.extensions import db
from app.models.notification import Notification, NotificationKind
from app.models.user import User, UserRole


BASE = "/api/v1/notifications"


def _users(app):
    with app.app_context():
        users = []
        for suffix in ("first", "second"):
            user = User(
                name="Notification " + suffix,
                email="notif-" + suffix + "@example.com",
                role=UserRole.CLIENT,
            )
            user.set_password("test-password-123")
            db.session.add(user)
            users.append(user)
        db.session.flush()
        notification = Notification(
            user_id=users[0].id,
            kind=NotificationKind.SYSTEM,
            title="Privado",
            body="Somente para a primeira conta",
        )
        db.session.add(notification)
        db.session.commit()
        return users[0].id, users[1].id, notification.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    # The app fixture keeps an application context across requests.
    # Clear Flask-Login's cached account when simulating another user.
    from flask import g
    g.pop("_login_user", None)


def test_notifications_require_auth_for_read_and_write(client):
    for path in (BASE, BASE + "/preferences"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "authentication_required"

    for path in (BASE + "/1/read", BASE + "/read-all", BASE + "/preferences"):
        response = client.put(path, json={})
        assert response.status_code == 401


def test_notifications_do_not_expose_or_mark_other_users_items(app, client):
    first, second, notification_id = _users(app)
    _login(client, second)

    response = client.get(BASE)
    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert response.headers["Cache-Control"] == "private, no-store"

    denied = client.put(f"{BASE}/{notification_id}/read", json={})
    assert denied.status_code == 404
    assert denied.get_json()["error"]["code"] == "notification_not_found"

    with app.app_context():
        item = db.session.get(Notification, notification_id)
        assert item.read_at is None

    _login(client, first)
    read = client.put(f"{BASE}/{notification_id}/read", json={})
    assert read.status_code == 200
    assert read.get_json()["notification"]["read"] is True


def test_notifications_reject_invalid_pagination_without_losing_auth(app, client):
    user_id, _, _ = _users(app)
    _login(client, user_id)
    for query in ("?offset=-1", "?limit=0", "?limit=51", "?limit=abc"):
        result = client.get(BASE + query)
        assert result.status_code == 400
        assert result.get_json()["error"]["code"] == "invalid_query_parameter"


def test_notification_preferences_reject_bad_payload_and_preserve_state(
    app, client,
):
    user_id, _, _ = _users(app)
    _login(client, user_id)

    initial = client.get(BASE + "/preferences")
    assert initial.status_code == 200
    before = initial.get_json()["preferences"]

    for data, content_type, code, status in (
        ("not-json", "text/plain", "json_required", 415),
        ('[1, 2]', "application/json", "invalid_json", 400),
        ('{"bookingEnabled": "false"}', "application/json",
         "invalid_notification_preferences", 400),
    ):
        result = client.put(
            BASE + "/preferences", data=data, content_type=content_type,
        )
        assert result.status_code == status
        assert result.get_json()["error"]["code"] == code

    after = client.get(BASE + "/preferences")
    assert after.get_json()["preferences"] == before


def test_notification_preferences_roundtrip_and_read_all(app, client):
    user_id, _, notification_id = _users(app)
    _login(client, user_id)

    result = client.put(BASE + "/preferences", json={
        "bookingEnabled": False,
        "followEnabled": True,
    })
    assert result.status_code == 200
    preferences = result.get_json()["preferences"]
    assert preferences["bookingEnabled"] is False
    assert preferences["followEnabled"] is True

    first_read_all = client.put(BASE + "/read-all", json={})
    assert first_read_all.status_code == 200
    assert first_read_all.get_json()["updated"] == 1
    assert first_read_all.get_json()["unreadCount"] == 0
    assert client.put(BASE + "/read-all", json={}).get_json()["updated"] == 0

    with app.app_context():
        assert db.session.get(Notification, notification_id).read_at is not None
