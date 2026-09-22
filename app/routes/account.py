from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.profile import ClientProfileForm
from app.services.profile_service import ensure_client_profile
from app.services.media_service import save_uploaded_image
from app.models.establishment import EstablishmentAccessStatus


account_bp = Blueprint("account", __name__)


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
            return render_template(
                "account/dashboard.html",
                form=form, profile=profile, completion=0, business_accesses=[], current_page="account"
            )
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

    completed_fields = sum(
        bool(value)
        for value in [
            current_user.name,
            current_user.email,
            profile.phone,
            profile.city,
            profile.state,
        ]
    )
    completion = round((completed_fields / 5) * 100)

    business_accesses = [
        access
        for access in current_user.establishment_accesses
        if access.status == EstablishmentAccessStatus.ACTIVE and access.establishment.is_active
    ]

    return render_template(
        "account/dashboard.html",
        form=form,
        profile=profile,
        completion=completion,
        business_accesses=business_accesses,
        current_page="account",
    )
