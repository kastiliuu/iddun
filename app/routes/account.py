from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    logout_user,
)

from app.extensions import db, limiter
from app.forms.auth import DeleteAccountForm
from app.forms.profile import ClientProfileForm
from app.models.booking import BookingStatus
from app.services.username_service import UsernameError, change_username, next_change_at
from app.services.profile_service import ensure_client_profile
from app.services.media_service import save_uploaded_image
from app.services.personal_media_service import set_personal_avatar
from app.models.establishment import EstablishmentAccessStatus
from app.services.time_service import DEFAULT_TIMEZONE, to_local
from app.services.api_auth import (
    list_user_sessions,
    revoke_other_user_sessions,
    revoke_user_session,
)
from app.services.account_privacy import (
    AccountDeletionBlocked,
    anonymize_account,
)


account_bp = Blueprint("account", __name__)


def _profile_completion(user, profile):
    """Return completion using every editable field shown on the account page."""
    fields = {
        "nome": user.name,
        "e-mail": user.email,
        "foto": user.avatar_url or profile.avatar_url,
        "telefone": profile.phone,
        "data de nascimento": profile.birth_date,
        "cidade": profile.city,
        "UF": profile.state,
    }
    completed = sum(bool(value) for value in fields.values())
    missing = [label for label, value in fields.items() if not value]
    return round((completed / len(fields)) * 100), missing


def _active_business_accesses(user):
    """List managed businesses; keep moderated pages visible to owners only.

    The account is a management overview, not a permission grant or a
    navigation context. Moderated pages remain excluded from account_contexts.
    """
    return [
        access
        for access in user.establishment_accesses
        if access.status == EstablishmentAccessStatus.ACTIVE
        and access.establishment is not None
        and (
            access.establishment.is_active
            or access.establishment.published_at is None
            or access.role == "owner"
        )
    ]


def _dashboard_context(form, profile):
    """Keep the complete page context available on GET and validation errors."""
    completion, completion_missing = _profile_completion(current_user, profile)
    bookings = list(profile.bookings)
    active_booking_statuses = {BookingStatus.PENDING, BookingStatus.CONFIRMED}

    return {
        "form": form,
        "profile": profile,
        "username_next_change": next_change_at(current_user),
        "completion": completion,
        "completion_missing": completion_missing,
        "business_accesses": _active_business_accesses(current_user),
        "save_count": len(current_user.saves),
        "booking_count": len(bookings),
        "active_booking_count": sum(
            booking.status in active_booking_statuses for booking in bookings
        ),
        "completed_booking_count": sum(
            booking.status == BookingStatus.COMPLETED for booking in bookings
        ),
        "current_page": "account",
    }


@account_bp.route("/minha-conta/editar", methods=["GET", "POST"], endpoint="edit")
@account_bp.route("/minha-conta", methods=["GET", "POST"])
@login_required
def dashboard():
    # Keep legacy POST /minha-conta compatible with older clients.
    # The canonical editing surface has its own URL.
    editing = (
        request.path.rstrip("/") == "/minha-conta/editar"
        or request.method == "POST"
    )
    profile = ensure_client_profile(current_user)

    form = ClientProfileForm(obj=profile)
    if not form.is_submitted():
        form.name.data = current_user.name
        form.username.data = current_user.username

    if form.validate_on_submit():
        try:
            uploaded_avatar = save_uploaded_image(form.avatar_file.data, "clients")
        except ValueError as exc:
            form.avatar_file.errors.append(str(exc))
            uploaded_avatar = None
        if form.avatar_file.errors:
            return render_template("account/dashboard.html", editing=editing, **_dashboard_context(form, profile))
        requested = (form.username.data or "").strip()
        if requested:
            try:
                change_username(current_user, requested)
            except UsernameError as exc:
                form.username.errors.append(str(exc))
                db.session.rollback()
                return render_template("account/dashboard.html", editing=editing, **_dashboard_context(form, profile))
        current_user.name = form.name.data.strip()
        profile.phone = (form.phone.data or "").strip() or None
        profile.birth_date = form.birth_date.data
        profile.city = (form.city.data or "").strip() or None
        profile.state = (form.state.data or "").strip().upper() or None
        if uploaded_avatar:
            set_personal_avatar(current_user, uploaded_avatar)
        profile.recalculate_onboarding()

        db.session.commit()
        flash("Perfil atualizado com sucesso.", "success")
        return redirect(url_for("account.dashboard"))

    return render_template("account/dashboard.html", editing=editing, **_dashboard_context(form, profile))



@account_bp.route(
    "/minha-conta/privacidade",
    methods=["GET", "POST"],
)
@login_required
def privacy():
    form = DeleteAccountForm()

    if form.validate_on_submit():
        if not current_user.check_password(
            form.password.data
        ):
            form.password.errors.append(
                "Senha atual incorreta."
            )
        else:
            try:
                anonymize_account(
                    current_user
                )
            except AccountDeletionBlocked as exc:
                names = ", ".join(
                    exc.establishments
                )
                flash(
                    (
                        "Antes de excluir a conta, "
                        "transfira a titularidade de: "
                        f"{names}."
                    ),
                    "error",
                )
            else:
                logout_user()

                flash(
                    (
                        "Sua conta foi removida e "
                        "os dados pessoais foram "
                        "anonimizados."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "public.home"
                    )
                )

    return render_template(
        "account/privacy.html",
        form=form,
        app_sessions=[
            {
                "session": item,
                "seen": to_local(item.last_seen_at or item.created_at, DEFAULT_TIMEZONE),
            }
            for item in list_user_sessions(current_user.id)
        ],
        current_page="account",
    )


# DEC-ID-062/166: aparelhos com o app conectados à conta, com o mesmo
# serviço da API do app. Encerrar aqui não mexe na sessão deste navegador.
@account_bp.post("/minha-conta/sessoes/<int:session_id>/encerrar")
@login_required
@limiter.limit("30 per hour")
def revoke_app_session(session_id):
    if revoke_user_session(current_user.id, session_id):
        flash("Aparelho desconectado. O app pedirá login de novo.", "success")
    else:
        flash("Este aparelho não está conectado à sua conta.", "error")
    return redirect(url_for("account.privacy", _anchor="aparelhos"))


@account_bp.post("/minha-conta/sessoes/encerrar-todas")
@login_required
@limiter.limit("10 per hour")
def revoke_all_app_sessions():
    # Sem token de app nesta requisição: encerra todos os aparelhos do app.
    count = revoke_other_user_sessions(current_user.id, None)
    if count:
        flash(
            f"{count} aparelho{'s' if count != 1 else ''} desconectado{'s' if count != 1 else ''}.",
            "success",
        )
    else:
        flash("Nenhum aparelho estava conectado.", "info")
    return redirect(url_for("account.privacy", _anchor="aparelhos"))
