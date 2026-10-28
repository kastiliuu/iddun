"""Google Calendar OAuth, token refresh and booking event tests (NV-04).

Only test doubles: no Google API calls, no production mocks.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models.booking import BookingStatus, ExperienceSlot, SlotStatus
from app.models.calendar import CalendarConnection
from app.models.experience import Experience
from app.models.professional import ProfessionalProfile
from app.services import google_calendar_service as google


NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def _calendar(app):
    with app.app_context():
        pro = ProfessionalProfile(
            display_name="Google Test Pro", slug="google-test-pro",
            timezone="America/Sao_Paulo",
        )
        experience = Experience(
            professional=pro, title="Corte", slug="google-test-corte",
            category="cabelo", short_description="Teste de agenda",
            regular_price="100.00", price="80.00", duration_minutes=60,
        )
        slot = ExperienceSlot(
            professional=pro, experience=experience,
            starts_at=NOW + timedelta(days=2),
            ends_at=NOW + timedelta(days=2, hours=1),
            status=SlotStatus.BOOKED,
        )
        connection = CalendarConnection(
            professional=pro, calendar_id="owner@example.com",
            access_token_encrypted="cipher-access",
            refresh_token_encrypted="cipher-refresh",
        )
        db.session.add_all([pro, experience, slot, connection])
        db.session.commit()
        return pro.id, slot.id, connection.id


def _booking(app, pro_id, slot_id, status=BookingStatus.CONFIRMED):
    pro = db.session.get(ProfessionalProfile, pro_id)
    slot = db.session.get(ExperienceSlot, slot_id)
    return SimpleNamespace(
        id=777, status=status, professional_id=pro_id,
        professional=pro, slot=slot, slot_id=slot.id,
        experience=slot.experience,
        client=SimpleNamespace(user=SimpleNamespace(name="Cliente Privado")),
    )


def test_google_oauth_requires_complete_configuration(app):
    with app.app_context():
        app.config.update(
            GOOGLE_CLIENT_ID="id", GOOGLE_CLIENT_SECRET=None,
            GOOGLE_OAUTH_REDIRECT_URI="https://iddun.example/callback",
        )
        assert not google.google_is_configured()
        with pytest.raises(RuntimeError, match="ainda não está configurado"):
            google._client_config()

        app.config["GOOGLE_CLIENT_SECRET"] = "secret"
        assert google.google_is_configured()
        cfg = google._client_config()["web"]
        assert cfg["client_id"] == "id"
        assert cfg["client_secret"] == "secret"
        assert cfg["redirect_uris"] == ["https://iddun.example/callback"]


def test_google_oauth_authorization_and_callback_preserve_state_without_network(
    app, monkeypatch,
):
    captured = {}

    class FakeFlow:
        credentials = SimpleNamespace(token="oauth-access")

        @classmethod
        def from_client_config(cls, config, scopes, state):
            captured["config"] = config
            captured["scopes"] = scopes
            captured["state"] = state
            return cls()

        def authorization_url(self, **kwargs):
            captured["auth"] = kwargs
            return "https://accounts.google.com/auth", "state-value"

        def fetch_token(self, **kwargs):
            captured["callback"] = kwargs

    monkeypatch.setattr(
        google, "_google_dependencies", lambda: (None, None, FakeFlow, None),
    )
    with app.app_context():
        app.config.update(
            GOOGLE_CLIENT_ID="google-id", GOOGLE_CLIENT_SECRET="google-secret",
            GOOGLE_OAUTH_REDIRECT_URI="https://iddun.example/oauth",
            APP_ENV="production",
        )
        url, state = google.authorization_url(login_hint="pro@example.com")
        assert url == "https://accounts.google.com/auth"
        assert state == "state-value"
        assert captured["auth"]["access_type"] == "offline"
        assert captured["auth"]["prompt"] == "consent"
        assert captured["auth"]["login_hint"] == "pro@example.com"
        assert captured["scopes"] == google.GOOGLE_SCOPES
        result = google.exchange_callback(
            "https://iddun.example/oauth?code=example", state,
        )
        assert result.token == "oauth-access"
        assert captured["state"] == state
        assert captured["callback"] == {
            "authorization_response": "https://iddun.example/oauth?code=example"
        }


def test_google_expired_token_refresh_persists_rotated_credentials(
    app, monkeypatch,
):
    _, _, connection_id = _calendar(app)
    called = []

    class FakeCredentials:
        def __init__(self, **kwargs):
            called.append(kwargs)
            self.token = kwargs["token"]
            self.refresh_token = kwargs["refresh_token"]
            self.expired = True
            self.expiry = None

        def refresh(self, request):
            called.append("refresh")
            self.token = "new-access"
            self.refresh_token = "new-refresh"
            self.expiry = NOW.replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr(
        google, "_google_dependencies",
        lambda: (lambda: object(), FakeCredentials, None, None),
    )
    monkeypatch.setattr(google, "decrypt_secret", lambda value: value.removeprefix("cipher-"))
    monkeypatch.setattr(google, "encrypt_secret", lambda value: "cipher-" + value)
    with app.app_context():
        app.config.update(GOOGLE_CLIENT_ID="id", GOOGLE_CLIENT_SECRET="secret")
        connection = db.session.get(CalendarConnection, connection_id)
        credentials = google._credentials_for(connection)
        assert credentials.token == "new-access"
        assert called[0]["refresh_token"] == "refresh"
        assert called[0]["token_uri"] == "https://oauth2.googleapis.com/token"
        assert "refresh" in called
        db.session.expire_all()
        saved = db.session.get(CalendarConnection, connection_id)
        assert saved.access_token_encrypted == "cipher-new-access"
        assert saved.refresh_token_encrypted == "cipher-new-refresh"
        assert saved.token_expiry is not None


def test_google_missing_refresh_token_does_not_write_rotated_credentials(
    app, monkeypatch,
):
    _, _, connection_id = _calendar(app)

    class FakeCredentials:
        def __init__(self, **kwargs):
            self.token = kwargs["token"]
            self.refresh_token = kwargs["refresh_token"]
            self.expired = True
            self.expiry = None

        def refresh(self, request):
            raise AssertionError("Do not refresh without a refresh token")

    monkeypatch.setattr(
        google, "_google_dependencies",
        lambda: (lambda: object(), FakeCredentials, None, None),
    )
    monkeypatch.setattr(google, "decrypt_secret", lambda value: value)
    with app.app_context():
        connection = db.session.get(CalendarConnection, connection_id)
        connection.refresh_token_encrypted = None
        db.session.commit()
        result = google._credentials_for(connection)
        assert result.refresh_token is None
        assert connection.access_token_encrypted == "cipher-access"


class FakeEvents:
    def __init__(self, failure=False):
        self.calls = []
        self.failure = failure

    def insert(self, **kwargs):
        self.calls.append(("insert", kwargs))
        return self

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))
        return self

    def execute(self):
        if self.failure:
            raise OSError("Google unavailable")
        return {"id": "google-event-777"}


def test_google_create_event_sends_booking_identity_and_persists_external_id(
    app, monkeypatch,
):
    pro_id, slot_id, _ = _calendar(app)
    events = FakeEvents()
    monkeypatch.setattr(
        google, "service_for", lambda connection: SimpleNamespace(events=lambda: events),
    )
    with app.app_context():
        booking = _booking(app, pro_id, slot_id)
        event = google.create_booking_event(booking)
        assert event["id"] == "google-event-777"
        assert len(events.calls) == 1
        name, args = events.calls[0]
        assert name == "insert"
        assert args["calendarId"] == "owner@example.com"
        body = args["body"]
        assert body["summary"] == "IDDUN · Corte"
        assert "Cliente Privado" in body["description"]
        assert body["extendedProperties"]["private"] == {
            "iddun_booking_id": "777", "iddun_slot_id": str(slot_id),
        }
        assert body["start"]["timeZone"] == "America/Sao_Paulo"
        db.session.expire_all()
        slot = db.session.get(ExperienceSlot, slot_id)
        assert slot.external_calendar_provider == "google"
        assert slot.external_event_id == "google-event-777"


def test_google_create_event_skips_unconfirmed_booking(app, monkeypatch):
    pro_id, slot_id, _ = _calendar(app)
    monkeypatch.setattr(
        google, "service_for",
        lambda connection: (_ for _ in ()).throw(AssertionError("unexpected API call")),
    )
    with app.app_context():
        booking = _booking(app, pro_id, slot_id, BookingStatus.PENDING)
        assert google.create_booking_event(booking) is None


@pytest.mark.parametrize("fails", [False, True])
def test_google_delete_event_clears_only_after_provider_success(
    app, monkeypatch, fails,
):
    pro_id, slot_id, _ = _calendar(app)
    events = FakeEvents(failure=fails)
    monkeypatch.setattr(
        google, "service_for", lambda connection: SimpleNamespace(events=lambda: events),
    )
    with app.app_context():
        slot = db.session.get(ExperienceSlot, slot_id)
        slot.external_calendar_provider = "google"
        slot.external_event_id = "external-id"
        slot.external_block_reason = "old reason"
        db.session.commit()
        booking = _booking(app, pro_id, slot_id)
        assert google.delete_booking_event(booking) is (not fails)
        assert events.calls[0] == (
            "delete", {"calendarId": "owner@example.com", "eventId": "external-id"},
        )
        db.session.expire_all()
        saved = db.session.get(ExperienceSlot, slot_id)
        if fails:
            assert saved.external_event_id == "external-id"
            assert saved.external_calendar_provider == "google"
        else:
            assert saved.external_event_id is None
            assert saved.external_calendar_provider is None
            assert saved.external_block_reason is None


def test_google_delete_event_without_provider_marker_is_noop(app, monkeypatch):
    pro_id, slot_id, _ = _calendar(app)
    monkeypatch.setattr(
        google, "service_for",
        lambda connection: (_ for _ in ()).throw(AssertionError("unexpected API call")),
    )
    with app.app_context():
        assert google.delete_booking_event(_booking(app, pro_id, slot_id)) is False
