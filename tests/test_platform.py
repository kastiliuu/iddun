from io import BytesIO

from flask import request
from PIL import Image
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


def test_web_portfolio_removal_unpublishes_incomplete_profile(
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
        assert profile.ready_to_publish is False
        assert profile.onboarding_completed is False
        assert profile.is_active is False
        assert profile.published_at is None

    public = client.get(
        f"/profissionais/{slug}"
    )

    assert public.status_code == 404


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

