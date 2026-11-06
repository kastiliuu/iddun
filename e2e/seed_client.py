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
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
)
from datetime import date

from app.models.experience import Experience, ExperienceStatus
from app.models.professional_experience import (
    ProfessionalExperience,
    ProfessionalExperienceVerification,
)
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from app.services.time_service import utcnow
from app.models.professional import ProfessionalPortfolioItem, ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


CI_SQLITE_URL = "sqlite:////tmp/iddun-web-e2e.db"
E2E_EMAIL = "qa-browser-client@example.com"
E2E_PASSWORD = "QA-browser-only-password-123!"
# Professional account for the media preview/crop journeys (PR-1).
E2E_PRO_EMAIL = "qa-browser-pro@example.com"
# Business page owned by the professional account (contrast journeys, PR-3).
E2E_BUSINESS_SLUG = "espaco-qa-navegador"
# Perfil Pro só de leitura para a ordem das seções (PR 4a, D-SOC-12).
# Nenhuma jornada edita ou desativa este perfil.
E2E_PROFILE_SLUG = "pro-perfil-social-navegador"
# Tipografia de dados (DS-TYPO-001): serviço com horários às 16:30 e uma
# reserva confirmada de uma cliente própria. Nomes sem "QA" para não mudar a
# ordem das buscas por "QA" de outras jornadas.
E2E_TYPO_SERVICE_SLUG = "escova-tipografia-navegador"
E2E_TYPO_CLIENT_EMAIL = "typo-browser-client@example.com"
E2E_TYPO_ADMIN_EMAIL = "typo-browser-admin@example.com"


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
        # Remoção no portfólio e na galeria (V-03). Endereços externos de
        # exemplo: nenhum arquivo local é apagado pelos testes.
        for index in range(2):
            db.session.add(
                ProfessionalPortfolioItem(
                    professional=profile,
                    image_url=f"https://example.com/qa-portfolio-{index}.jpg",
                    sort_order=index,
                )
            )

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
            EstablishmentGalleryItem(
                establishment=business,
                image_url="https://example.com/qa-galeria-0.jpg",
                sort_order=0,
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
        social = ProfessionalProfile(
            display_name="Pro Perfil Social",
            slug=E2E_PROFILE_SLUG,
            primary_specialty="Hair stylist",
            bio="Perfil descartável do CI para a ordem das seções. " * 8,
            city="Curitiba",
            state="PR",
            is_active=True,
        )
        db.session.add(social)
        db.session.flush()
        db.session.add(
            ProfessionalExperience(
                professional_id=social.id,
                company_name="Salão Declarado QA",
                role_title="Colorista",
                started_at=date(2020, 1, 1),
                verification_status=ProfessionalExperienceVerification.UNVERIFIED,
            )
        )
        for index in range(7):
            db.session.add(
                WorkPost(
                    author_type=WorkPostAuthorType.PROFESSIONAL,
                    professional_id=social.id,
                    status=WorkPostStatus.PUBLISHED,
                    published_at=utcnow(),
                    caption=f"Trabalho QA {index + 1}",
                )
            )
        db.session.commit()
        _seed_typography()


def _seed_typography():
    """Reserva confirmada às 16:30 (horário local) daqui a dois dias.

    Serviço sem estabelecimento para não entrar nas buscas por "QA".
    """
    from datetime import datetime, timedelta

    from app.models.booking import ExperienceSlot, SlotStatus
    from app.services.booking_service import confirm_booking, hold_slot
    from app.services.time_service import local_naive_to_utc, to_local

    profile = ProfessionalProfile(
        display_name="Pro Tipografia",
        slug="pro-tipografia-navegador",
        primary_specialty="Escovista",
        city="Curitiba",
        state="PR",
        is_active=True,
    )
    db.session.add(profile)
    service = Experience(
        professional=profile,
        title="Escova Tipografia",
        slug=E2E_TYPO_SERVICE_SLUG,
        category="cabelo",
        short_description="Serviço descartável do CI para a tipografia de dados.",
        regular_price="180.00",
        price="150.00",
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(service)
    today = to_local(utcnow()).date()
    slots = []
    for days in range(2, 6):
        start = local_naive_to_utc(datetime.combine(today + timedelta(days=days), datetime.min.time()).replace(hour=16, minute=30))
        slot = ExperienceSlot(
            experience=service,
            professional=profile,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            status=SlotStatus.AVAILABLE,
        )
        db.session.add(slot)
        slots.append(slot)

    client = User(name="Cliente Tipografia", email=E2E_TYPO_CLIENT_EMAIL, role=UserRole.CLIENT)
    client.set_password(E2E_PASSWORD)
    admin = User(name="Admin Tipografia", email=E2E_TYPO_ADMIN_EMAIL, role=UserRole.ADMIN)
    admin.set_password(E2E_PASSWORD)
    db.session.add_all([client, admin])
    db.session.flush()
    client_profile = ClientProfile(user=client)
    db.session.add(client_profile)
    db.session.commit()

    confirm_booking(hold_slot(slots[0].id, client_profile).id, client_profile)


if __name__ == "__main__":
    main()
