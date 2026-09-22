from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.extensions import db
from app.forms.calendar import CalendarSettingsForm
from app.models.calendar import CalendarConnection, CalendarProvider
from app.models.professional import ProfessionalProfile
from app.models.user import UserRole
from app.services.google_calendar_service import (
    authorization_url,
    choose_calendar,
    disconnect,
    exchange_callback,
    google_is_configured,
    list_calendars,
    sync_connection,
    upsert_connection,
)
from app.utils.admin import admin_required


calendar_bp = Blueprint("calendar", __name__)


def _professional_or_404(professional_id):
    return db.session.get(ProfessionalProfile, professional_id) or abort(404)


def _connection_for(professional_id):
    return db.session.query(CalendarConnection).filter_by(
        professional_id=professional_id,
        provider=CalendarProvider.GOOGLE,
    ).one_or_none()


@calendar_bp.route("/admin/profissionais/<int:professional_id>/integracoes/google", methods=["GET", "POST"])
@admin_required
def google_settings(professional_id):
    professional = _professional_or_404(professional_id)
    connection = _connection_for(professional_id)
    form = CalendarSettingsForm()
    calendars = []

    if connection:
        try:
            calendars = list_calendars(connection) if google_is_configured() else []
        except Exception as exc:
            connection.last_sync_status = "error"
            connection.last_sync_error = str(exc)[:500]
            db.session.commit()
            flash("Não foi possível consultar os calendários do Google agora.", "error")

        known = {item["id"] for item in calendars}
        if connection.calendar_id and connection.calendar_id not in known:
            calendars.insert(
                0,
                {
                    "id": connection.calendar_id,
                    "summary": connection.calendar_name or connection.calendar_id,
                    "primary": False,
                },
            )
        form.calendar_id.choices = [(item["id"], item["summary"]) for item in calendars]

        if request.method == "GET":
            form.calendar_id.data = connection.calendar_id
            form.sync_enabled.data = connection.sync_enabled
            form.create_booking_events.data = connection.create_booking_events

        if form.validate_on_submit():
            label = dict(form.calendar_id.choices).get(form.calendar_id.data, form.calendar_id.data)
            choose_calendar(connection, form.calendar_id.data, label)
            connection.sync_enabled = form.sync_enabled.data
            connection.create_booking_events = form.create_booking_events.data
            db.session.commit()
            flash("Preferências do Google Calendar salvas.", "success")
            return redirect(url_for("calendar.google_settings", professional_id=professional.id))

    return render_template(
        "admin/professionals/google-calendar.html",
        professional=professional,
        connection=connection,
        calendars=calendars,
        form=form,
        google_configured=google_is_configured(),
        admin_section="professionals",
    )


@calendar_bp.get("/admin/profissionais/<int:professional_id>/integracoes/google/conectar")
@admin_required
def google_connect(professional_id):
    professional = _professional_or_404(professional_id)
    if not google_is_configured():
        flash("Configure as credenciais OAuth do Google no .env antes de conectar.", "error")
        return redirect(url_for("calendar.google_settings", professional_id=professional.id))

    try:
        url, state = authorization_url(
            login_hint=professional.user.email if professional.user else None
        )
    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("calendar.google_settings", professional_id=professional.id))

    session["google_oauth_state"] = state
    session["google_oauth_professional_id"] = professional.id
    return redirect(url)


@calendar_bp.get("/integracoes/google/callback")
def google_callback():
    # OAuth started from an authenticated admin/professional session.
    if not current_user.is_authenticated:
        flash("Sua sessão expirou. Entre novamente e reconecte o Google Calendar.", "error")
        return redirect(url_for("auth.login"))

    state = session.pop("google_oauth_state", None)
    professional_id = session.pop("google_oauth_professional_id", None)
    if not state or not professional_id:
        flash("A conexão com o Google expirou. Tente novamente.", "error")
        return redirect(url_for("admin.professionals"))

    if current_user.role != UserRole.ADMIN:
        profile = current_user.professional_profile
        if profile is None or profile.id != int(professional_id):
            abort(403)

    professional = _professional_or_404(int(professional_id))
    try:
        credentials = exchange_callback(request.url, state)
        upsert_connection(professional, credentials)
    except Exception as exc:
        flash(f"Não foi possível concluir a conexão com o Google: {exc}", "error")
        return redirect(url_for("calendar.google_settings", professional_id=professional.id))

    flash("Google Calendar conectado. Agora escolha qual agenda o IDDUN deve acompanhar.", "success")
    return redirect(url_for("calendar.google_settings", professional_id=professional.id))


@calendar_bp.post("/admin/profissionais/<int:professional_id>/integracoes/google/sincronizar")
@admin_required
def google_sync(professional_id):
    _professional_or_404(professional_id)
    connection = _connection_for(professional_id)
    if connection is None:
        flash("Conecte o Google Calendar antes de sincronizar.", "error")
        return redirect(url_for("calendar.google_settings", professional_id=professional_id))

    try:
        result = sync_connection(connection)
    except Exception as exc:
        flash(f"Falha ao sincronizar: {exc}", "error")
    else:
        flash(
            f"Agenda sincronizada: {result['blocked']} bloqueado(s), "
            f"{result['restored']} reaberto(s).",
            "success",
        )
    return redirect(url_for("calendar.google_settings", professional_id=professional_id))


@calendar_bp.post("/admin/profissionais/<int:professional_id>/integracoes/google/desconectar")
@admin_required
def google_disconnect(professional_id):
    _professional_or_404(professional_id)
    connection = _connection_for(professional_id)
    if connection:
        disconnect(connection)
        flash("Google Calendar desconectado.", "info")
    return redirect(url_for("calendar.google_settings", professional_id=professional_id))
