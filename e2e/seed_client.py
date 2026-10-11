"""Seed a real client solely in the disposable QA browser database.

Fails closed unless explicitly enabled AND pointed to the exact CI SQLite URL.
Never run against Render, staging, or production.
"""

import os

from app import create_app
from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


CI_SQLITE_URL = "sqlite:////tmp/iddun-web-e2e.db"
E2E_EMAIL = "qa-browser-client@example.com"
E2E_PASSWORD = "QA-browser-only-password-123!"


def main():
    if (
        os.environ.get("IDDUN_E2E_SEED") != "1"
        or os.environ.get("DATABASE_URL") != CI_SQLITE_URL
        or os.environ.get("APP_ENV") != "development"
    ):
        raise RuntimeError(
            "E2E seed may only run with explicit flag and disposable CI database."
        )

    app = create_app()
    with app.app_context():
        user = User(
            name="Cliente QA Navegador",
            email=E2E_EMAIL,
            role=UserRole.CLIENT,
        )
        user.set_password(E2E_PASSWORD)
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        db.session.commit()


if __name__ == "__main__":
    main()
