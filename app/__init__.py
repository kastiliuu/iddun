import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, request, url_for
from flask_wtf.csrf import CSRFError, generate_csrf
from sqlalchemy import text
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import csrf, db, login_manager, migrate
from app.routes.account import account_bp
from app.routes.api import api_v1_bp
from app.routes.api_auth import api_auth_bp
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.bookings import bookings_bp
from app.routes.calendar import calendar_bp
from app.routes.public import public_bp
from app.routes.platform import business_bp, professional_bp


def create_app(test_config=None):
    load_dotenv()

    app_env = os.getenv(
        "APP_ENV",
        os.getenv("FLASK_ENV", "development"),
    ).lower()

    database_url = os.getenv("DATABASE_URL")
    secret_key = os.getenv("SECRET_KEY")

    if test_config and test_config.get("TESTING"):
        database_url = test_config.get(
            "SQLALCHEMY_DATABASE_URI",
            "sqlite+pysqlite:///:memory:",
        )
        secret_key = test_config.get(
            "SECRET_KEY",
            "test-secret-key",
        )
    else:
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL não foi configurada. "
                "Verifique o arquivo .env."
            )

        if app_env == "production" and not secret_key:
            raise RuntimeError(
                "SECRET_KEY é obrigatória em produção."
            )

    app = Flask(__name__)

    # Render encerra o TLS no proxy. Confiar em exatamente um proxy mantém
    # scheme/host corretos em redirects e URLs externas sem abrir a cadeia toda.
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
    )

    app.config.from_mapping(
        APP_ENV=app_env,
        SECRET_KEY=secret_key or "dev-only-change-later",
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=app_env == "production",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=app_env == "production",
        WTF_CSRF_TIME_LIMIT=4 * 60 * 60,
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv(
            "GOOGLE_CLIENT_SECRET"
        ),
        GOOGLE_OAUTH_REDIRECT_URI=os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI"
        ),
        TOKEN_ENCRYPTION_KEY=os.getenv(
            "TOKEN_ENCRYPTION_KEY"
        ),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        UPLOAD_FOLDER=(
            os.getenv("UPLOAD_FOLDER")
            or os.path.join(
                app.root_path,
                "static",
                "uploads",
            )
        ),
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.template_filter("media_url")
    def media_url(value):
        if not value:
            return url_for(
                "static",
                filename="img/category-hair.jpg",
            )

        if value.startswith(
            ("http://", "https://", "data:", "/")
        ):
            return value

        return url_for("static", filename=value)

    @app.get("/csrf-token")
    def refresh_csrf_token():
        response = jsonify(
            {
                "csrfToken": generate_csrf(),
            }
        )
        response.headers["Cache-Control"] = (
            "private, no-store"
        )

        return response

    def same_origin_referrer():
        referrer = request.referrer

        if not referrer:
            return None

        referrer_url = urlsplit(referrer)
        host_url = urlsplit(request.host_url)

        if (
            referrer_url.scheme == host_url.scheme
            and referrer_url.netloc == host_url.netloc
        ):
            return referrer

        return None

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        message = (
            "Sua sessão de segurança expirou. "
            "Confira os dados e envie novamente."
        )

        if (
            request.path.startswith("/api/")
            or request.is_json
        ):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "csrf_failed",
                            "message": message,
                        }
                    }
                ),
                400,
            )

        reason = (error.description or "").lower()

        can_retry = (
            "expired" in reason
            or "session token is missing" in reason
        )

        if can_retry:
            flash(message, "error")

            return redirect(
                (
                    same_origin_referrer()
                    or url_for("public.home")
                ),
                code=303,
            )

        return (
            "Não foi possível validar a segurança "
            "desta solicitação.",
            400,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_error):
        max_megabytes = (
            app.config["MAX_CONTENT_LENGTH"]
            // (1024 * 1024)
        )

        message = (
            "O envio ultrapassou o limite total de "
            f"{max_megabytes} MB. "
            "Reduza a quantidade ou o tamanho das imagens "
            "e tente novamente."
        )

        if (
            request.path.startswith("/api/")
            or request.is_json
        ):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "request_too_large",
                            "message": message,
                        }
                    }
                ),
                413,
            )

        flash(message, "error")

        return redirect(
            (
                same_origin_referrer()
                or url_for("public.home")
            ),
            code=303,
        )

    from app.models.user import User

    @app.get("/health")
    def health():
        """Readiness endpoint used by Render to validate app and database."""
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            return {"status": "unhealthy"}, 503

        return {"status": "ok"}, 200

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(
                User,
                int(user_id),
            )
        except (TypeError, ValueError):
            return None

    app.register_blueprint(public_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(business_bp)

    from app.cli import register_cli

    register_cli(app)

    # Import all models so Flask-Migrate can discover their metadata.
    from app import models  # noqa: F401

    return app