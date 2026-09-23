from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.profile import ClientProfileForm
from app.models.booking import BookingStatus
from app.services.profile_service import ensure_client_profile
from app.services.media_service import save_uploaded_image
from app.models.establishment import EstablishmentAccessStatus


account_bp = Blueprint("account", __name__)


def _profile_completion(user, profile):
    """Return completion using every editable field shown on the account page."""
    fields = {
        "nome": user.name,
        "e-mail": user.email,
        "foto": profile.avatar_url,
        "telefone": profile.phone,
        "data de nascimento": profile.birth_date,
        "cidade": profile.city,
        "UF": profile.state,
    }
    completed = sum(bool(value) for value in fields.values())
    missing = [label for label, value in fields.items() if not value]
    return round((completed / len(fields)) * 100), missing


def _active_business_accesses(user):
    return [
        access
        for access in user.establishment_accesses
        if access.status == EstablishmentAccessStatus.ACTIVE and access.establishment.is_active
    ]


def _dashboard_context(form, profile):
    """Keep the complete page context available on GET and validation errors."""
    completion, completion_missing = _profile_completion(current_user, profile)
    bookings = list(profile.bookings)
    active_booking_statuses = {BookingStatus.PENDING, BookingStatus.CONFIRMED}

    return {
        "form": form,
        "profile": profile,
        "completion": completion,
        "completion_missing": completion_missing,
        "business_accesses": _active_business_accesses(current_user),
        "booking_count": len(bookings),
        "active_booking_count": sum(
            booking.status in active_booking_statuses for booking in bookings
        ),
        "completed_booking_count": sum(
            booking.status == BookingStatus.COMPLETED for booking in bookings
        ),
        "current_page": "account",
    }


@account_bp.route("/minha-conta", methods=["GET", "POST"])
@login_required
def dashboard():
    profile = ensure_client_profile(current_user)

    form = ClientProfileForm(obj=profile)
    if not form.is_submitted():
        form.name.data = current_user.name

    if form.validate_on_submit():
        try:
            uploaded_avatar = save_uploaded_image(form.avatar_file.data, "clients")
        except ValueError as exc:
            form.avatar_file.errors.append(str(exc))
            uploaded_avatar = None
        if form.avatar_file.errors:
            return render_template("account/dashboard.html", **_dashboard_context(form, profile))
        current_user.name = form.name.data.strip()
        profile.phone = (form.phone.data or "").strip() or None
        profile.birth_date = form.birth_date.data
        profile.city = (form.city.data or "").strip() or None
        profile.state = (form.state.data or "").strip().upper() or None
        if uploaded_avatar:
            profile.avatar_url = uploaded_avatar
        profile.recalculate_onboarding()

        db.session.commit()
        flash("Perfil atualizado com sucesso.", "success")
        return redirect(url_for("account.dashboard"))

    return render_template("account/dashboard.html", **_dashboard_context(form, profile))
