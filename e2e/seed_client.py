"""Seed a real client solely in the disposable QA browser database.

Fails closed unless explicitly enabled AND pointed to the exact CI SQLite URL.
Never run against Render, staging, or production.
"""

import os

from app import create_app
from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


CI_SQLITE_URL = "sqlite:////tmp/iddun-web-e2e.db"
E2E_EMAIL = "qa-browser-client@example.com"
E2E_PASSWORD = "QA-browser-only-password-123!"
# Professional account for the media preview/crop journeys (PR-1).
E2E_PRO_EMAIL = "qa-browser-pro@example.com"
# Business page owned by the professional account (contrast journeys, PR-3).
E2E_BUSINESS_SLUG = "espaco-qa-navegador"


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

        pro = User(
            name="Profissional QA Navegador",
            email=E2E_PRO_EMAIL,
            role=UserRole.PROFESSIONAL,
        )
        pro.set_password(E2E_PASSWORD)
        db.session.add(pro)
        db.session.flush()
        db.session.add(ClientProfile(user=pro))
        profile = ProfessionalProfile(
            user_id=pro.id,
            display_name="Profissional QA Navegador",
            slug="profissional-qa-navegador",
            primary_specialty="Colorista",
            city="Curitiba",
            state="PR",
        )
        db.session.add(profile)

        business = Establishment(
            name="Espaço QA Navegador",
            slug=E2E_BUSINESS_SLUG,
            category="salao",
            description="Espaço descartável usado apenas nos testes de navegador do CI.",
            address_line1="Rua QA, 100",
            city="Curitiba",
            state="PR",
            is_active=True,
            onboarding_completed=True,
        )
        db.session.add(business)
        db.session.flush()
        db.session.add(
            EstablishmentUserAccess(
                user=pro,
                establishment=business,
                role=EstablishmentAccessRole.OWNER,
                status=EstablishmentAccessStatus.ACTIVE,
            )
        )
        db.session.add(
            Experience(
                professional=profile,
                establishment=business,
                title="Coloração QA",
                slug="coloracao-qa-navegador",
                category="cabelo",
                short_description="Serviço descartável do CI.",
                regular_price="150.00",
                price="150.00",
                duration_minutes=60,
                status=ExperienceStatus.PUBLISHED,
            )
        )
        db.session.commit()


if __name__ == "__main__":
    main()
