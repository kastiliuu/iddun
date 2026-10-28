"""Calendar provider boundary and reconciliation regression coverage (NV-04)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.extensions import db
from app.models.calendar import CalendarConnection
from app.models.professional import ProfessionalProfile
from app.services.calendar_sync_service import BusyWindow, _overlaps
from app.services import google_calendar_service as google


NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def _connection(app):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Calendar Test Pro", slug="calendar-test-pro",
        )
        connection = CalendarConnection(
            professional=professional, calendar_id="primary@example.com",
            sync_enabled=True,
        )
        db.session.add_all([professional, connection])
        db.session.commit()
        return professional.id, connection.id


def test_calendar_overlap_is_half_open_and_accepts_iso_z():
    slot = SimpleNamespace(
        starts_at=NOW,
        ends_at=NOW + timedelta(hours=1),
    )
    assert _overlaps(slot, BusyWindow(
        starts_at="2026-10-28T12:30:00Z",
        ends_at="2026-10-28T13:30:00Z",
    ))
    assert not _overlaps(slot, BusyWindow(
        starts_at=NOW + timedelta(hours=1),
        ends_at=NOW + timedelta(hours=2),
    ))
    assert not _overlaps(slot, BusyWindow(
        starts_at=NOW - timedelta(hours=1),
        ends_at=NOW,
    ))


def test_google_busy_windows_maps_provider_response_without_network(
    app, monkeypatch,
):
    class FakeFreeBusy:
        body = None

        def query(self, *, body):
            self.body = body
            return self

        def execute(self):
            return {"calendars": {"primary@example.com": {"busy": [{
                "start": "2026-10-28T12:00:00Z",
                "end": "2026-10-28T13:00:00Z",
            }]}}}

    fake = FakeFreeBusy()
    monkeypatch.setattr(
        google, "service_for", lambda connection: SimpleNamespace(freebusy=lambda: fake),
    )
    with app.app_context():
        connection = SimpleNamespace(calendar_id="primary@example.com")
        windows = google.fetch_busy_windows(
            connection, time_min=NOW, time_max=NOW + timedelta(days=1),
        )
    assert fake.body == {
        "timeMin": "2026-10-28T12:00:00Z",
        "timeMax": "2026-10-29T12:00:00Z",
        "items": [{"id": "primary@example.com"}],
    }
    assert len(windows) == 1
    assert windows[0].starts_at == "2026-10-28T12:00:00Z"
    assert windows[0].label == "Ocupado no Google Calendar"


def test_google_busy_windows_requires_calendar_selection(app):
    with app.app_context():
        connection = SimpleNamespace(calendar_id=None)
        try:
            google.fetch_busy_windows(connection, NOW, NOW + timedelta(days=1))
        except RuntimeError as exc:
            assert "Selecione um calendário" in str(exc)
        else:
            raise AssertionError("Expected missing calendar to be rejected")


def test_google_sync_staleness_and_failure_do_not_raise_to_caller(
    app, monkeypatch,
):
    professional_id, connection_id = _connection(app)
    calls = []

    monkeypatch.setattr(google, "google_is_configured", lambda: True)
    monkeypatch.setattr(google, "utcnow", lambda: NOW)

    def sync(connection):
        calls.append(connection.id)
        return {"blocked": 1, "restored": 0}

    monkeypatch.setattr(google, "sync_connection", sync)
    with app.app_context():
        connection = db.session.get(CalendarConnection, connection_id)
        connection.last_synced_at = NOW - timedelta(seconds=60)
        db.session.commit()
        assert google.sync_professional_if_stale(professional_id) is None
        assert calls == []

        connection.last_synced_at = NOW - timedelta(seconds=121)
        db.session.commit()
        assert google.sync_professional_if_stale(professional_id) == {
            "blocked": 1, "restored": 0,
        }
        assert calls == [connection_id]

        def fail(connection):
            raise OSError("provider unavailable")

        monkeypatch.setattr(google, "sync_connection", fail)
        assert google.sync_professional_if_stale(professional_id) is None


def test_google_sync_skips_when_disabled_or_unconfigured(app, monkeypatch):
    professional_id, connection_id = _connection(app)
    monkeypatch.setattr(google, "google_is_configured", lambda: False)
    monkeypatch.setattr(
        google, "sync_connection",
        lambda connection: (_ for _ in ()).throw(AssertionError("unexpected sync")),
    )
    with app.app_context():
        assert google.sync_professional_if_stale(professional_id) is None
        monkeypatch.setattr(google, "google_is_configured", lambda: True)
        connection = db.session.get(CalendarConnection, connection_id)
        connection.sync_enabled = False
        db.session.commit()
        assert google.sync_professional_if_stale(professional_id) is None
