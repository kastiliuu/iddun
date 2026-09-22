import os
from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models.booking import BookingStatus, ExperienceSlot
from app.models.calendar import CalendarConnection, CalendarProvider
from app.services.calendar_sync_service import BusyWindow, reconcile_external_busy_windows
from app.services.credential_service import decrypt_secret, encrypt_secret
from app.services.time_service import as_utc, utcnow


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
    "https://www.googleapis.com/auth/calendar.events",
]


def _google_dependencies():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Dependências do Google Calendar ausentes. Execute pip install -r requirements.txt."
        ) from exc
    return Request, Credentials, Flow, build


def google_is_configured():
    return bool(
        current_app.config.get("GOOGLE_CLIENT_ID")
        and current_app.config.get("GOOGLE_CLIENT_SECRET")
        and current_app.config.get("GOOGLE_OAUTH_REDIRECT_URI")
    )


def _client_config():
    if not google_is_configured():
        raise RuntimeError(
            "Google Calendar ainda não está configurado. Defina GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET e GOOGLE_OAUTH_REDIRECT_URI no .env."
        )
    return {
        "web": {
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [current_app.config["GOOGLE_OAUTH_REDIRECT_URI"]],
        }
    }


def oauth_flow(state=None):
    redirect_uri = current_app.config["GOOGLE_OAUTH_REDIRECT_URI"]
    if (
        current_app.config.get("APP_ENV") != "production"
        and redirect_uri
        and redirect_uri.startswith(("http://localhost", "http://127.0.0.1"))
    ):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    _, _, Flow, _ = _google_dependencies()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = current_app.config["GOOGLE_OAUTH_REDIRECT_URI"]
    return flow


def authorization_url(login_hint=None):
    flow = oauth_flow()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=login_hint,
    )
    return url, state


def exchange_callback(authorization_response, state):
    flow = oauth_flow(state=state)
    flow.fetch_token(authorization_response=authorization_response)
    return flow.credentials


def _credentials_for(connection):
    Request, Credentials, _, _ = _google_dependencies()
    creds = Credentials(
        token=decrypt_secret(connection.access_token_encrypted),
        refresh_token=decrypt_secret(connection.refresh_token_encrypted),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=current_app.config.get("GOOGLE_CLIENT_SECRET"),
        scopes=(connection.scopes or "").split() or GOOGLE_SCOPES,
    )
    if connection.token_expiry:
        creds.expiry = as_utc(connection.token_expiry).replace(tzinfo=None)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        connection.access_token_encrypted = encrypt_secret(creds.token)
        if creds.refresh_token:
            connection.refresh_token_encrypted = encrypt_secret(creds.refresh_token)
        connection.token_expiry = creds.expiry
        db.session.commit()
    return creds


def service_for(connection):
    _, _, _, build = _google_dependencies()
    return build("calendar", "v3", credentials=_credentials_for(connection), cache_discovery=False)


def upsert_connection(professional, credentials):
    connection = db.session.query(CalendarConnection).filter_by(
        professional_id=professional.id,
        provider=CalendarProvider.GOOGLE,
    ).one_or_none()
    if connection is None:
        connection = CalendarConnection(
            professional=professional,
            provider=CalendarProvider.GOOGLE,
        )
        db.session.add(connection)

    connection.access_token_encrypted = encrypt_secret(credentials.token)
    if credentials.refresh_token:
        connection.refresh_token_encrypted = encrypt_secret(credentials.refresh_token)
    connection.token_expiry = credentials.expiry
    connection.scopes = " ".join(credentials.scopes or GOOGLE_SCOPES)
    connection.sync_enabled = True
    connection.last_sync_error = None
    db.session.flush()

    calendars = list_calendars(connection)
    primary = next((item for item in calendars if item.get("primary")), calendars[0] if calendars else None)
    if primary:
        connection.calendar_id = primary["id"]
        connection.calendar_name = primary.get("summary") or "Agenda principal"
        connection.account_email = primary.get("id") if "@" in primary.get("id", "") else None
    db.session.commit()
    return connection


def list_calendars(connection):
    service = service_for(connection)
    result = service.calendarList().list(minAccessRole="reader").execute()
    return [
        {
            "id": item["id"],
            "summary": item.get("summary", item["id"]),
            "primary": bool(item.get("primary")),
            "access_role": item.get("accessRole"),
        }
        for item in result.get("items", [])
    ]


def choose_calendar(connection, calendar_id, calendar_name=None):
    connection.calendar_id = calendar_id
    connection.calendar_name = calendar_name or calendar_id
    connection.last_sync_error = None
    db.session.commit()
    return connection


def _sync_window_for_professional(professional_id):
    now = utcnow()
    future = db.session.query(ExperienceSlot).filter(
        ExperienceSlot.professional_id == professional_id,
        ExperienceSlot.ends_at > now,
    ).order_by(ExperienceSlot.ends_at.desc()).first()
    horizon = as_utc(future.ends_at) + timedelta(days=1) if future else now + timedelta(days=60)
    return now, min(horizon, now + timedelta(days=180))


def fetch_busy_windows(connection, time_min=None, time_max=None):
    if not connection.calendar_id:
        raise RuntimeError("Selecione um calendário antes de sincronizar.")
    if time_min is None or time_max is None:
        time_min, time_max = _sync_window_for_professional(connection.professional_id)

    service = service_for(connection)
    body = {
        "timeMin": as_utc(time_min).isoformat().replace("+00:00", "Z"),
        "timeMax": as_utc(time_max).isoformat().replace("+00:00", "Z"),
        "items": [{"id": connection.calendar_id}],
    }
    response = service.freebusy().query(body=body).execute()
    busy = response.get("calendars", {}).get(connection.calendar_id, {}).get("busy", [])
    return [
        BusyWindow(
            starts_at=item["start"],
            ends_at=item["end"],
            label="Ocupado no Google Calendar",
        )
        for item in busy
    ]


def sync_connection(connection):
    try:
        windows = fetch_busy_windows(connection)
        result = reconcile_external_busy_windows(
            connection.professional_id,
            windows,
            provider=CalendarProvider.GOOGLE,
        )
        connection.last_synced_at = utcnow()
        connection.last_sync_status = "success"
        connection.last_sync_error = None
        db.session.commit()
        return result
    except Exception as exc:
        db.session.rollback()
        connection = db.session.get(CalendarConnection, connection.id)
        connection.last_synced_at = utcnow()
        connection.last_sync_status = "error"
        connection.last_sync_error = str(exc)[:500]
        db.session.commit()
        raise


def sync_professional_if_stale(professional_id, stale_after_seconds=120):
    connection = db.session.query(CalendarConnection).filter_by(
        professional_id=professional_id,
        provider=CalendarProvider.GOOGLE,
        sync_enabled=True,
    ).one_or_none()
    if connection is None or not google_is_configured() or not connection.calendar_id:
        return None
    now = utcnow()
    if connection.last_synced_at:
        age = now - as_utc(connection.last_synced_at)
        if age.total_seconds() < stale_after_seconds:
            return None
    try:
        return sync_connection(connection)
    except Exception:
        return None


def sync_all_enabled_connections():
    connections = db.session.query(CalendarConnection).filter_by(
        provider=CalendarProvider.GOOGLE,
        sync_enabled=True,
    ).all()
    summary = {"connections": len(connections), "success": 0, "errors": 0, "blocked": 0, "restored": 0}
    for connection in connections:
        try:
            result = sync_connection(connection)
        except Exception:
            summary["errors"] += 1
        else:
            summary["success"] += 1
            summary["blocked"] += result.get("blocked", 0)
            summary["restored"] += result.get("restored", 0)
    return summary


def create_booking_event(booking):
    if booking.status != BookingStatus.CONFIRMED:
        return None
    connection = db.session.query(CalendarConnection).filter_by(
        professional_id=booking.professional_id,
        provider=CalendarProvider.GOOGLE,
        create_booking_events=True,
    ).one_or_none()
    if connection is None or not connection.calendar_id:
        return None

    service = service_for(connection)
    client_name = booking.client.user.name if booking.client and booking.client.user else "Cliente IDDUN"
    body = {
        "summary": f"IDDUN · {booking.experience.title}",
        "description": (
            f"Reserva IDDUN #{booking.id}\n"
            f"Cliente: {client_name}\n"
            "Gerencie esta reserva pelo IDDUN."
        ),
        "start": {
            "dateTime": as_utc(booking.slot.starts_at).isoformat(),
            "timeZone": booking.professional.timezone,
        },
        "end": {
            "dateTime": as_utc(booking.slot.ends_at).isoformat(),
            "timeZone": booking.professional.timezone,
        },
        "extendedProperties": {
            "private": {
                "iddun_booking_id": str(booking.id),
                "iddun_slot_id": str(booking.slot_id),
            }
        },
    }
    event = service.events().insert(calendarId=connection.calendar_id, body=body).execute()
    booking.slot.external_calendar_provider = CalendarProvider.GOOGLE
    booking.slot.external_event_id = event.get("id")
    db.session.commit()
    return event


def delete_booking_event(booking):
    slot = booking.slot
    if slot.external_calendar_provider != CalendarProvider.GOOGLE or not slot.external_event_id:
        return False
    connection = db.session.query(CalendarConnection).filter_by(
        professional_id=booking.professional_id,
        provider=CalendarProvider.GOOGLE,
    ).one_or_none()
    if connection is None or not connection.calendar_id:
        return False
    try:
        service = service_for(connection)
        service.events().delete(
            calendarId=connection.calendar_id,
            eventId=slot.external_event_id,
        ).execute()
    except Exception:
        # A reserva ainda pode ser cancelada no IDDUN; uma próxima sincronização
        # reconcilia o estado caso o evento externo já tenha sido removido.
        return False
    slot.external_event_id = None
    slot.external_calendar_provider = None
    slot.external_block_reason = None
    db.session.commit()
    return True


def disconnect(connection):
    db.session.delete(connection)
    db.session.commit()
