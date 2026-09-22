from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.auth import LoginForm, RegisterForm
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


auth_bp = Blueprint("auth", __name__)


def _safe_next_url(target):
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return None
    return target


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))

    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.strip().lower()

        existing_user = db.session.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            flash("Já existe uma conta cadastrada com este e-mail.", "error")
            return render_template("auth/register.html", form=form)

        user = User(
            name=name,
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Já existe uma conta cadastrada com este e-mail.", "error")
            return render_template("auth/register.html", form=form)

        login_user(user)
        flash("Sua conta foi criada com sucesso.", "success")
        next_url = _safe_next_url(request.args.get("next"))
        return redirect(next_url or url_for("account.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(User.email == email))

        if user is None or not user.check_password(form.password.data):
            return render_template(
                "auth/login.html",
                form=form,
                login_error="E-mail ou senha incorretos.",
            )

        if not user.is_active:
            return render_template(
                "auth/login.html",
                form=form,
                login_error="Esta conta está desativada.",
            )

        login_user(user, remember=form.remember.data)
        flash("Login realizado com sucesso.", "success")

        next_url = _safe_next_url(request.args.get("next"))
        return redirect(next_url or url_for("account.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("public.home"))
