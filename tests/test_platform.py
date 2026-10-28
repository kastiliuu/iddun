from io import BytesIO

from flask import request
from PIL import Image
import pytest
from sqlalchemy import select

from app.extensions import csrf, db
from app.models.establishment import (
    Establishment,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _create_user(
    app,
    email="pro@example.com",
    name="Profissional Teste",
):
    with app.app_context():
        user = User(
            name=name,
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password("senha-forte-123")

        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user=user))
        db.session.commit()

        return user.id


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _image(filename):
    output = BytesIO()
    image_format = (
        "PNG"
        if filename.lower().endswith(".png")
        else "JPEG"
    )
    Image.new(
        "RGB",
        (8, 8),
        (120, 80, 160),
    ).save(
        output,
        format=image_format,
    )
    output.seek(0)

    return (
        output,
        filename,
    )


def test_professional_start_requires_login(client):
    response = client.get("/pro/comecar")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_professional_onboarding_creates_portfolio_and_public_profile(
    app,
    client,
):
    user_id = _create_user(app)
    _login_session(client, user_id)

    response = client.post(
        "/pro/onboarding",
        data={
            "attendance_modalities": ["own_space"],
            "display_name": "Camila Teste",
            "headline": "Especialista em transformações",
            "primary_specialty": "Hair Stylist",
            "specialties_text": "Loiros, Corte",
            "bio": (
                "Profissional com experiência em transformações, "
                "corte e atendimento personalizado."
            ),
            "phone": "41999999999",
            "instagram": "@camilateste",
            "city": "Curitiba",
            "state": "PR",
            "visual_theme": "beauty",
            "avatar_focus_x": "37",
            "avatar_focus_y": "62",
            "cover_focus_x": "44",
            "cover_focus_y": "55",
            "avatar_file": _image("avatar.jpg"),
            "portfolio_files": [
                _image("trabalho-1.jpg"),
                _image("trabalho-2.jpg"),
                _image("trabalho-3.jpg"),
            ],
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/pro" in response.headers["Location"]

    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id == user_id
            )
        )

        assert profile is not None
        assert profile.plan_tier == "free"
        assert profile.onboarding_completed is True
        assert (
            profile.avatar_focus_x,
            profile.avatar_focus_y,
        ) == (37, 62)
        assert (
            profile.cover_focus_x,
            profile.cover_focus_y,
        ) == (44, 55)

        portfolio = db.session.scalars(
            select(ProfessionalPortfolioItem).where(
                ProfessionalPortfolioItem.professional_id
                == profile.id
            )
        ).all()

        assert len(portfolio) == 3

        slug = profile.slug

    public_response = client.get(
        f"/profissionais/{slug}"
    )

    public_html = public_response.get_data(
        as_text=True
    )

    assert public_response.status_code == 200
    assert "Camila Teste" in public_html
    assert "Trabalhos recentes" in public_html


def test_web_can_publish_professional_without_optional_media(app, client):
    user_id = _create_user(app, email="no-media-web@example.com")
    _login_session(client, user_id)

    response = client.post(
        "/pro/onboarding",
        data={
            "attendance_modalities": ["own_space"],
            "display_name": "Profissional Sem Fotos",
            "primary_specialty": "Nail Designer",
            "specialties_text": "",
            "bio": "Atendimento profissional dedicado com qualidade e cuidado.",
            "city": "Curitiba",
            "state": "PR",
            "visual_theme": "beauty",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id == user_id
            )
        )
        assert profile is not None
        assert profile.is_active is True
        assert profile.ready_to_publish is True
        assert profile.avatar_url is None
        assert profile.cover_url is None
        assert len(profile.portfolio_items) == 0
        assert profile.attendance_modalities == "own_space"
        slug = profile.slug

    assert client.get(f"/profissionais/{slug}").status_code == 200


def test_web_portfolio_removal_preserves_published_profile(
    app,
    client,
):
    user_id = _create_user(
        app,
        email="portfolio-removal@example.com",
    )
    _login_session(
        client,
        user_id,
    )

    created = client.post(
        "/pro/onboarding",
        data={
            "attendance_modalities": ["own_space"],
            "display_name": "Perfil Remoção",
            "headline": "Perfil completo",
            "primary_specialty": "Nail Designer",
            "specialties_text": "Unhas",
            "bio": (
                "Perfil criado para validar "
                "remoção de mídia obrigatória."
            ),
            "phone": "41999999999",
            "city": "Curitiba",
            "state": "PR",
            "visual_theme": "beauty",
            "avatar_file": _image(
                "avatar-removal.jpg"
            ),
            "portfolio_files": [
                _image("removal-1.jpg"),
                _image("removal-2.jpg"),
                _image("removal-3.jpg"),
            ],
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert created.status_code == 302

    with app.app_context():
        profile = db.session.scalar(
            select(
                ProfessionalProfile
            ).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )

        assert profile is not None
        assert profile.is_active is True
        assert profile.ready_to_publish is True

        item_id = (
            profile.portfolio_items[
                0
            ].id
        )
        slug = profile.slug

    removed = client.post(
        (
            "/pro/portfolio/"
            f"{item_id}/remover"
        ),
        follow_redirects=False,
    )

    assert removed.status_code == 302

    with app.app_context():
        profile = db.session.scalar(
            select(
                ProfessionalProfile
            ).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )

        assert profile is not None
        assert profile.ready_to_publish is True
        assert profile.onboarding_completed is True
        assert profile.is_active is True
        assert profile.published_at is not None

    public = client.get(
        f"/profissionais/{slug}"
    )

    assert public.status_code == 200


def test_business_onboarding_creates_owner_access_and_public_page(
    app,
    client,
):
    user_id = _create_user(
        app,
        email="dono@example.com",
        name="Dono Studio",
    )

    _login_session(client, user_id)

    response = client.post(
        "/business/onboarding",
        data={
            "name": "Studio Aurora",
            "category": "salao",
            "description": (
                "Um espaço dedicado a experiências de beleza, "
                "atendimento e transformação com cuidado."
            ),
            "phone": "41988888888",
            "email": "contato@aurora.com",
            "instagram": "@studioaurora",
            "address_line1": "Rua Teste, 100",
            "address_line2": "Sala 2",
            "neighborhood": "Batel",
            "city": "Curitiba",
            "state": "PR",
            "postal_code": "80000000",
            "logo_focus_x": "41",
            "logo_focus_y": "52",
            "cover_focus_x": "63",
            "cover_focus_y": "48",
            "logo_file": _image("logo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/business/" in response.headers["Location"]

    with app.app_context():
        establishment = db.session.scalar(
            select(Establishment).where(
                Establishment.name == "Studio Aurora"
            )
        )

        assert establishment is not None
        assert (
            establishment.logo_focus_x,
            establishment.logo_focus_y,
        ) == (41, 52)
        assert (
            establishment.cover_focus_x,
            establishment.cover_focus_y,
        ) == (63, 48)

        access = db.session.scalar(
            select(EstablishmentUserAccess).where(
                EstablishmentUserAccess.user_id
                == user_id,
                EstablishmentUserAccess.establishment_id
                == establishment.id,
            )
        )

        assert access is not None
        assert access.role == "owner"

        slug = establishment.slug

    public_response = client.get(
        f"/estabelecimentos/{slug}"
    )

    public_html = public_response.get_data(
        as_text=True
    )

    assert public_response.status_code == 200
    assert "Studio Aurora" in public_html
    assert "Profissionais deste lugar" in public_html


@pytest.mark.filterwarnings(
    "error:Object of type <ExperienceSlot> not in session:sqlalchemy.exc.SAWarning"
)
def test_same_account_can_be_client_professional_and_business_owner(
    app,
    client,
):
    user_id = _create_user(
        app,
        email="multi@example.com",
        name="Conta Multi",
    )

    _login_session(client, user_id)

    client.post(
        "/pro/onboarding",
        data={
            "attendance_modalities": ["own_space"],
            "display_name": "Conta Multi Pro",
            "primary_specialty": "Barbeiro",
            "bio": (
                "Profissional independente com foco em "
                "atendimento, identidade e experiência "
                "personalizada."
            ),
            "city": "Curitiba",
            "state": "PR",
            "visual_theme": "barber",
            "avatar_file": _image("avatar.jpg"),
            "portfolio_files": [
                _image("1.jpg"),
                _image("2.jpg"),
                _image("3.jpg"),
            ],
        },
        content_type="multipart/form-data",
    )

    client.post(
        "/business/onboarding",
        data={
            "name": "Barbearia Multi",
            "category": "barbearia",
            "description": (
                "Barbearia contemporânea focada em corte, "
                "barba, identidade e atendimento cuidadoso."
            ),
            "address_line1": "Rua Multi, 10",
            "city": "Curitiba",
            "state": "PR",
            "logo_file": _image("logo.jpg"),
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        user = db.session.get(User, user_id)

        assert user.client_profile is not None
        assert user.professional_profile is not None
        assert len(user.establishment_accesses) == 1

        establishment = user.establishment_accesses[0].establishment
        slug = establishment.slug
        db.session.add_all([
            Experience(
                professional=user.professional_profile,
                establishment=establishment,
                title="Corte empresarial publicado",
                slug="corte-empresarial-publicado",
                category="barbearia",
                short_description="Serviço real vinculado à empresa.",
                regular_price="80.00",
                price="75.00",
                duration_minutes=45,
                status=ExperienceStatus.PUBLISHED,
            ),
            Experience(
                professional=user.professional_profile,
                establishment=establishment,
                title="Oferta empresarial em rascunho",
                slug="oferta-empresarial-rascunho",
                category="barbearia",
                short_description="Não deve aparecer no catálogo.",
                regular_price="80.00",
                price="70.00",
                duration_minutes=45,
                status=ExperienceStatus.DRAFT,
            ),
        ])
        db.session.commit()

    html = client.get(f"/business/{slug}/painel").get_data(as_text=True)
    assert "Corte empresarial publicado" in html
    assert "R$ 75,00" in html
    assert "Oferta empresarial em rascunho" not in html
    assert 'href="/experiencias/corte-empresarial-publicado"' in html

    # Business managers see their complete internal catalog, while the
    # dashboard preview continues showing only published services.
    response = client.get(f"/business/{slug}/servicos")
    assert response.status_code == 200
    full_catalog = response.get_data(as_text=True)
    assert "Corte empresarial publicado" in full_catalog
    assert "Oferta empresarial em rascunho" in full_catalog
    assert "1 publicados" in full_catalog
    assert "/pro/servicos/" not in full_catalog

    dashboard_html = client.get(f"/business/{slug}/painel").get_data(as_text=True)
    assert f'/business/{slug}/servicos' in dashboard_html

    # Bookings are private to the establishment and read-only in Business.
    from datetime import datetime, timezone
    from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
    with app.app_context():
        establishment = db.session.scalar(
            select(Establishment).where(Establishment.slug == slug)
        )
        professional = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        service = db.session.scalar(
            select(Experience).where(Experience.slug == "corte-empresarial-publicado")
        )
        slot = ExperienceSlot(
            professional=professional,
            experience=service,
            establishment=establishment,
            starts_at=datetime(2027, 2, 15, 13, 0, tzinfo=timezone.utc),
            ends_at=datetime(2027, 2, 15, 13, 45, tzinfo=timezone.utc),
            status=SlotStatus.BOOKED,
        )
        booking = Booking(
            client=db.session.get(User, user_id).client_profile,
            professional=professional,
            experience=service,
            establishment=establishment,
            slot=slot,
            status=BookingStatus.CONFIRMED,
            price_at_booking="75.00",
        )
        db.session.add_all([slot, booking])
        db.session.commit()

    booking_page = client.get(f"/business/{slug}/reservas?date=2027-02-15&status=confirmed")
    assert booking_page.status_code == 200
    booking_html = booking_page.get_data(as_text=True)
    assert "Corte empresarial publicado" in booking_html
    assert "Conta Multi" in booking_html
    assert "Confirmada" in booking_html
    assert "R$ 75,00" in booking_html
    insights_response = client.get(f"/business/{slug}/indicadores")
    assert insights_response.status_code == 200
    assert "1 no total" in insights_response.get_data(as_text=True)
    assert "R$ 0,00" in insights_response.get_data(as_text=True)
    assert client.get(f"/business/{slug}/reservas?status=unknown").status_code == 400
    assert client.get(f"/business/{slug}/reservas?date=invalid").status_code == 400

    # A different logged-in account cannot read another company's drafts.
    other_id = _create_user(
        app, email="other-business-catalog@example.com", name="Sem acesso",
    )
    with client.session_transaction() as session:
        session["_user_id"] = str(other_id)
        session["_fresh"] = True
    from flask import g
    g.pop("_login_user", None)
    denied = client.get(f"/business/{slug}/servicos")
    assert denied.status_code == 403
    denied_bookings = client.get(f"/business/{slug}/reservas")
    assert denied_bookings.status_code == 403
    assert client.get(f"/business/{slug}/indicadores").status_code == 403




def test_business_invitation_requires_professional_acceptance(
    app,
    client,
):
    professional_user_id = _create_user(
        app,
        email="invite-pro@example.com",
        name="Pro Convidada",
    )

    _login_session(
        client,
        professional_user_id,
    )

    client.post(
        "/pro/onboarding",
        data={
            "attendance_modalities": ["own_space"],
            "display_name": "Pro Convidada",
            "primary_specialty": "Nail Designer",
            "bio": (
                "Profissional especializada em unhas, "
                "acabamento cuidadoso e experiências "
                "personalizadas."
            ),
            "city": "Curitiba",
            "state": "PR",
            "visual_theme": "beauty",
            "avatar_file": _image("avatar.jpg"),
            "portfolio_files": [
                _image("1.jpg"),
                _image("2.jpg"),
                _image("3.jpg"),
            ],
        },
        content_type="multipart/form-data",
    )

    owner_id = _create_user(
        app,
        email="invite-owner@example.com",
        name="Studio Convite",
    )

    _login_session(client, owner_id)

    client.post(
        "/business/onboarding",
        data={
            "name": "Studio Convite",
            "category": "unhas",
            "description": (
                "Um espaço profissional criado para "
                "experiências de beleza cuidadosas e "
                "atendimento personalizado."
            ),
            "address_line1": "Rua Convite, 10",
            "city": "Curitiba",
            "state": "PR",
            "logo_file": _image("logo.jpg"),
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        establishment = db.session.scalar(
            select(Establishment).where(
                Establishment.name == "Studio Convite"
            )
        )

        slug = establishment.slug

    dashboard = client.get(f"/business/{slug}/painel")
    assert dashboard.status_code == 200
    dashboard_html = dashboard.get_data(as_text=True)
    assert 'aria-label="Seções do painel Business"' in dashboard_html
    for anchor in (
        "business-overview",
        "business-operations",
        "business-catalog",
        "business-team",
        "business-reputation",
        "business-gallery",
    ):
        assert f'id="{anchor}"' in dashboard_html
        assert f'href="#{anchor}"' in dashboard_html
    assert "Voltar ao Cliente" in dashboard_html
    assert "Visão geral da operação" in dashboard_html
    assert "Reservas confirmadas" in dashboard_html
    assert "Serviços publicados" in dashboard_html
    assert "Ainda não há serviços publicados vinculados" in dashboard_html
    assert "Receita realizada" not in dashboard_html

    response = client.post(
        f"/business/{slug}/painel",
        data={
            "email": "invite-pro@example.com",
            "role_name": "Nail Designer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        membership = db.session.scalar(
            select(
                ProfessionalEstablishmentMembership
            )
        )

        assert (
            membership.status
            == MembershipStatus.PENDING
        )

        membership_id = membership.id

    public_before_acceptance = client.get(
        f"/estabelecimentos/{slug}"
    ).get_data(as_text=True)

    assert (
        "<strong>Pro Convidada</strong>"
        not in public_before_acceptance
    )

    _login_session(
        client,
        professional_user_id,
    )

    dashboard = client.get(
        "/pro/painel"
    ).get_data(as_text=True)

    assert "Convite pendente" in dashboard

    response = client.post(
        f"/pro/vinculos/{membership_id}/aceitar",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        membership = db.session.get(
            ProfessionalEstablishmentMembership,
            membership_id,
        )

        assert (
            membership.status
            == MembershipStatus.ACTIVE
        )

    public_after_acceptance = client.get(
        f"/estabelecimentos/{slug}"
    ).get_data(as_text=True)

    assert (
        "<strong>Pro Convidada</strong>"
        in public_after_acceptance
    )


def test_platform_upload_limit_supports_declared_onboarding_capacity(
    app,
):
    assert (
        app.config["MAX_CONTENT_LENGTH"]
        == 64 * 1024 * 1024
    )


def test_oversized_onboarding_upload_returns_to_form_with_message(
    app,
    client,
):
    user_id = _create_user(
        app,
        email="large-upload@example.com",
    )

    _login_session(client, user_id)

    app.config["MAX_CONTENT_LENGTH"] = (
        1024 * 1024
    )

    response = client.post(
        "/pro/onboarding",
        data={
            "avatar_file": (
                BytesIO(
                    b"x" * (1024 * 1024 + 1)
                ),
                "avatar.jpg",
            ),
        },
        content_type="multipart/form-data",
        headers={
            "Referer": (
                "http://localhost/pro/onboarding"
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["Location"]
        == "http://localhost/pro/onboarding"
    )

    with client.session_transaction() as session:
        flashes = session.get("_flashes", [])

    assert any(
        category == "error"
        and (
            "ultrapassou o limite total de 1 MB"
            in message
        )
        for category, message in flashes
    )

    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )

    assert profile is None


def test_oversized_auth_request_keeps_stricter_api_limit(
    app,
    client,
):
    app.config["MAX_CONTENT_LENGTH"] = (
        1024 * 1024
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "x" * (1024 * 1024 + 1),
            "email": "large-api@example.com",
            "password": "senha-forte-123",
            "role": "client",
        },
    )

    assert response.status_code == 413

    assert response.get_json() == {
        "message": "A solicitação é muito grande.",
        "error": {
            "code": "request_too_large",
            "message": "A solicitação é muito grande.",
        },
    }


def test_global_oversized_api_request_returns_structured_json(
    app,
    client,
):
    app.config["MAX_CONTENT_LENGTH"] = (
        1024 * 1024
    )

    @csrf.exempt
    def oversized_api_probe():
        request.get_data()

        return {
            "status": "ok",
        }

    app.add_url_rule(
        "/api/test/request-size",
        endpoint="oversized_api_probe",
        view_func=oversized_api_probe,
        methods=["POST"],
    )

    response = client.post(
        "/api/test/request-size",
        data=b"x" * (1024 * 1024 + 1),
        content_type="application/octet-stream",
    )

    assert response.status_code == 413

    message = (
        "O envio ultrapassou o limite "
        "total de 1 MB. "
        "Reduza a quantidade ou o tamanho "
        "das imagens e tente novamente."
    )

    assert response.get_json() == {
        "message": message,
        "error": {
            "code": "request_too_large",
            "message": message,
        },
    }



def test_pro_can_add_work_experience_and_view_in_edit_form(app, client):
    from datetime import date
    from app.models.professional_experience import ProfessionalExperience

    user_id = _create_user(app, email="pro-history@example.com")
    with app.app_context():
        user = db.session.get(User, user_id)
        db.session.add(ProfessionalProfile(
            user=user,
            display_name="Pro History",
            slug="pro-history",
        ))
        db.session.commit()

    _login_session(client, user_id)
    response = client.post(
        "/pro/experiencia-profissional/adicionar",
        data={
            "company_name": "Studio Batel",
            "role_title": "Nail Designer",
            "started_at": "2024-01-15",
            "ended_at": "",
            "is_current": "y",
            "description": "Atendimento e esmaltação",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/pro/perfil/editar" in response.headers["Location"]

    with app.app_context():
        experience = db.session.scalar(
            select(ProfessionalExperience).where(
                ProfessionalExperience.company_name == "Studio Batel"
            )
        )
        assert experience is not None
        assert experience.professional.user_id == user_id
        assert experience.started_at == date(2024, 1, 15)
        assert experience.ended_at is None
        assert experience.is_current is True

    edit = client.get("/pro/perfil/editar")
    assert edit.status_code == 200
    assert b"Studio Batel" in edit.data


@pytest.mark.filterwarnings(
    "error:Object of type <ProfessionalExperience> not in session:sqlalchemy.exc.SAWarning"
)
def test_pro_work_experience_rejects_invalid_dates(app, client):
    from app.models.professional_experience import ProfessionalExperience

    user_id = _create_user(app, email="pro-bad-history@example.com")
    with app.app_context():
        user = db.session.get(User, user_id)
        db.session.add(ProfessionalProfile(
            user=user, display_name="History Bad", slug="history-bad",
        ))
        db.session.commit()
    _login_session(client, user_id)

    response = client.post(
        "/pro/experiencia-profissional/adicionar",
        data={
            "company_name": "Studio Teste",
            "role_title": "Designer",
            "started_at": "2025-07-01",
            "ended_at": "2024-07-01",
        },
    )
    assert response.status_code == 422
    assert b"Studio Teste" in response.data
    assert b"Designer" in response.data
    assert b"2025-07-01" in response.data
    assert b"2024-07-01" in response.data
    with app.app_context():
        assert db.session.scalar(
            select(ProfessionalExperience).where(
                ProfessionalExperience.company_name == "Studio Teste"
            )
        ) is None


def test_pro_can_edit_and_remove_only_own_work_experience(app, client):
    from datetime import date
    from app.models.professional_experience import ProfessionalExperience

    owner_id = _create_user(app, email="pro-history-owner@example.com")
    other_id = _create_user(app, email="pro-history-other@example.com")
    with app.app_context():
        owner = ProfessionalProfile(
            user_id=owner_id, display_name="Pro Owner", slug="pro-history-owner",
        )
        other = ProfessionalProfile(
            user_id=other_id, display_name="Pro Other", slug="pro-history-other",
        )
        db.session.add_all([owner, other])
        db.session.flush()
        history = ProfessionalExperience(
            professional_id=owner.id,
            company_name="Studio Antigo",
            role_title="Designer",
            started_at=date(2023, 1, 1),
            is_current=True,
        )
        db.session.add(history)
        db.session.commit()
        history_id = history.id

    _login_session(client, other_id)
    for suffix in ("editar", "remover"):
        forbidden = client.post(
            f"/pro/experiencia-profissional/{history_id}/{suffix}",
            data={
                "company_name": "Invasão",
                "role_title": "Gestor",
                "started_at": "2024-01-01",
            },
        )
        assert forbidden.status_code == 404
    assert client.get(
        f"/pro/perfil/editar?experiencia={history_id}"
    ).status_code == 404

    _login_session(client, owner_id)
    # The test fixture keeps an application context active, and Flask-Login
    # caches the first user on g. Clear it when simulating a second login.
    from flask import g
    g.pop("_login_user", None)

    view = client.get(f"/pro/perfil/editar?experiencia={history_id}")
    assert view.status_code == 200
    assert b"Studio Antigo" in view.data
    assert b"Salvar altera" in view.data

    update = client.post(
        f"/pro/experiencia-profissional/{history_id}/editar",
        data={
            "company_name": "Studio Novo",
            "role_title": "Nail Designer",
            "started_at": "2024-02-01",
            "ended_at": "2025-02-01",
            "description": "Atendimentos",
        },
    )
    assert update.status_code == 302
    with app.app_context():
        updated = db.session.get(ProfessionalExperience, history_id)
        assert updated.company_name == "Studio Novo"
        assert updated.is_current is False
        assert updated.ended_at == date(2025, 2, 1)

    removed = client.post(
        f"/pro/experiencia-profissional/{history_id}/remover"
    )
    assert removed.status_code == 302
    with app.app_context():
        assert db.session.get(ProfessionalExperience, history_id) is None


def test_pro_work_experience_invalid_required_fields_rerenders_422(app, client):
    from app.models.professional_experience import ProfessionalExperience

    user_id = _create_user(app, email="invalid-required-pro@example.com")
    with app.app_context():
        db.session.add(ProfessionalProfile(
            user_id=user_id, display_name="Pro Required", slug="pro-required",
        ))
        db.session.commit()
    _login_session(client, user_id)

    response = client.post(
        "/pro/experiencia-profissional/adicionar",
        data={
            "company_name": "Studio Salvo",
            "role_title": "",
            "started_at": "2024-01-05",
            "description": "Descrição preservada da experiência",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert b"Studio Salvo" in response.data
    assert b"Descri" in response.data
    assert b"2024-01-05" in response.data
    with app.app_context():
        assert db.session.scalar(select(ProfessionalExperience).where(
            ProfessionalExperience.company_name == "Studio Salvo"
        )) is None


def test_pro_work_experience_edit_invalid_preserves_post_and_database(app, client):
    from datetime import date
    from app.models.professional_experience import ProfessionalExperience

    user_id = _create_user(app, email="invalid-update-pro@example.com")
    with app.app_context():
        profile = ProfessionalProfile(
            user_id=user_id, display_name="Pro Update", slug="pro-update",
        )
        record = ProfessionalExperience(
            professional=profile, company_name="Antiga Empresa",
            role_title="Designer", started_at=date(2022, 1, 1),
            is_current=True,
        )
        db.session.add_all([profile, record])
        db.session.commit()
        record_id = record.id
    _login_session(client, user_id)

    response = client.post(
        f"/pro/experiencia-profissional/{record_id}/editar",
        data={
            "company_name": "Nova Empresa",
            "role_title": "Gestora",
            "started_at": "2025-05-01",
            "ended_at": "2024-05-01",
            "description": "Novo texto não gravado",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert b"Nova Empresa" in response.data
    assert b"Gestora" in response.data
    assert b"Novo texto" in response.data
    assert b"2025-05-01" in response.data
    assert b"2024-05-01" in response.data
    assert b"Salvar altera" in response.data

    with app.app_context():
        unchanged = db.session.get(ProfessionalExperience, record_id)
        assert unchanged.company_name == "Antiga Empresa"
        assert unchanged.role_title == "Designer"
        assert unchanged.started_at == date(2022, 1, 1)


def test_pro_portfolio_removal_returns_to_portfolio_anchor(app, client):
    user_id = _create_user(app, email="pro-anchor@example.com")
    with app.app_context():
        profile = ProfessionalProfile(
            user_id=user_id, display_name="Pro Portfolio", slug="pro-portfolio",
        )
        db.session.add(profile)
        db.session.flush()
        item = ProfessionalPortfolioItem(
            professional=profile, image_url="https://cdn.example.com/work.jpg"
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    _login_session(client, user_id)
    response = client.post(f"/pro/portfolio/{item_id}/remover")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/perfil/editar#portfolio")
    with app.app_context():
        assert db.session.get(ProfessionalPortfolioItem, item_id) is None
