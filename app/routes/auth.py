from urllib.parse import urlsplit

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.auth import (
    LoginForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    RegisterForm,
)
from app.models.account_token import (
    AccountTokenPurpose,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.account_notifications import (
    send_email_verification,
    send_password_reset_email,
)
from app.services.account_security import (
    get_valid_account_token,
    reset_password_token,
    verify_email_token,
)


auth_bp = Blueprint(
    "auth",
    __name__,
)


def _safe_next_url(target):
    if not target:
        return None

    parsed = urlsplit(
        target
    )

    if (
        parsed.scheme
        or parsed.netloc
        or not target.startswith("/")
    ):
        return None

    return target


def _try_send_verification(
    user,
):
    try:
        return send_email_verification(
            user
        )
    except Exception:
        current_app.logger.exception(
            (
                "Falha inesperada ao preparar "
                "verificação de e-mail user_id=%s"
            ),
            user.id,
        )
        return False


def _try_send_password_reset(
    user,
):
    try:
        return send_password_reset_email(
            user
        )
    except Exception:
        current_app.logger.exception(
            (
                "Falha inesperada ao preparar "
                "recuperação de senha user_id=%s"
            ),
            user.id,
        )
        return False


@auth_bp.route(
    "/cadastro",
    methods=["GET", "POST"],
)
def register():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "account.dashboard"
            )
        )

    form = RegisterForm()

    if form.validate_on_submit():
        name = (
            form.name.data
            .strip()
        )
        email = (
            form.email.data
            .strip()
            .lower()
        )

        existing_user = (
            db.session.scalar(
                select(User).where(
                    User.email
                    == email
                )
            )
        )

        if existing_user:
            flash(
                (
                    "Já existe uma conta cadastrada "
                    "com este e-mail."
                ),
                "error",
            )
            return render_template(
                "auth/register.html",
                form=form,
            )

        user = User(
            name=name,
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password(
            form.password.data
        )

        db.session.add(
            user
        )
        db.session.flush()
        db.session.add(
            ClientProfile(
                user=user
            )
        )

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                (
                    "Já existe uma conta cadastrada "
                    "com este e-mail."
                ),
                "error",
            )
            return render_template(
                "auth/register.html",
                form=form,
            )

        _try_send_verification(
            user
        )

        login_user(
            user
        )

        flash(
            (
                "Sua conta foi criada com sucesso. "
                "Enviamos um link para confirmar "
                "seu e-mail."
            ),
            "success",
        )

        next_url = (
            _safe_next_url(
                request.args.get(
                    "next"
                )
            )
        )

        return redirect(
            next_url
            or url_for(
                "account.dashboard"
            )
        )

    return render_template(
        "auth/register.html",
        form=form,
    )


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "account.dashboard"
            )
        )

    form = LoginForm()

    if form.validate_on_submit():
        email = (
            form.email.data
            .strip()
            .lower()
        )

        user = db.session.scalar(
            select(User).where(
                User.email
                == email
            )
        )

        if (
            user is None
            or not user.check_password(
                form.password.data
            )
        ):
            return render_template(
                "auth/login.html",
                form=form,
                login_error=(
                    "E-mail ou senha incorretos."
                ),
            )

        if not user.is_active:
            return render_template(
                "auth/login.html",
                form=form,
                login_error=(
                    "Esta conta está desativada."
                ),
            )

        login_user(
            user,
            remember=(
                form.remember.data
            ),
        )

        flash(
            (
                "Login realizado com sucesso."
            ),
            "success",
        )

        next_url = (
            _safe_next_url(
                request.args.get(
                    "next"
                )
            )
        )

        return redirect(
            next_url
            or url_for(
                "account.dashboard"
            )
        )

    return render_template(
        "auth/login.html",
        form=form,
    )


@auth_bp.route(
    "/senha/esqueci",
    methods=["GET", "POST"],
)
def forgot_password():
    form = (
        PasswordResetRequestForm()
    )
    submitted = False

    if form.validate_on_submit():
        submitted = True

        email = (
            form.email.data
            .strip()
            .lower()
        )

        user = db.session.scalar(
            select(User).where(
                User.email
                == email,
                User.is_active_account.is_(
                    True
                ),
            )
        )

        # A resposta é idêntica exista ou não a conta,
        # evitando enumeração de e-mails.
        if user is not None:
            _try_send_password_reset(
                user
            )

    return render_template(
        "auth/forgot-password.html",
        form=form,
        submitted=submitted,
    )


@auth_bp.route(
    "/senha/redefinir/<token>",
    methods=["GET", "POST"],
)
def reset_password(token):
    token_record = (
        get_valid_account_token(
            token,
            AccountTokenPurpose.PASSWORD_RESET,
        )
    )

    form = PasswordResetForm()

    if (
        token_record is not None
        and form.validate_on_submit()
    ):
        user = (
            reset_password_token(
                token,
                form.password.data,
            )
        )

        if user is not None:
            if (
                current_user.is_authenticated
            ):
                logout_user()

            flash(
                (
                    "Senha redefinida com sucesso. "
                    "Entre novamente para continuar."
                ),
                "success",
            )

            return redirect(
                url_for(
                    "auth.login"
                )
            )

        token_record = None

    return render_template(
        "auth/reset-password.html",
        form=form,
        token_valid=(
            token_record
            is not None
        ),
    )


@auth_bp.get(
    "/email/verificar/<token>"
)
def verify_email(token):
    user = verify_email_token(
        token
    )

    return render_template(
        "auth/email-verification.html",
        verified=(
            user is not None
        ),
    )


@auth_bp.post(
    "/email/verificacao/reenviar"
)
@login_required
def resend_email_verification():
    if (
        current_user.is_email_verified
    ):
        flash(
            (
                "Seu e-mail já está confirmado."
            ),
            "info",
        )
    else:
        _try_send_verification(
            current_user
        )
        flash(
            (
                "Se o envio estiver disponível, "
                "um novo link de confirmação "
                "chegará ao seu e-mail."
            ),
            "success",
        )

    return redirect(
        url_for(
            "account.dashboard"
        )
    )


@auth_bp.post(
    "/logout"
)
@login_required
def logout():
    logout_user()

    flash(
        (
            "Você saiu da sua conta."
        ),
        "success",
    )

    return redirect(
        url_for(
            "public.home"
        )
    )
