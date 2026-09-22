from sqlalchemy import select

from app.extensions import db
from app.models.establishment import Establishment, ProfessionalEstablishmentMembership
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


def _create_user(app, role=UserRole.ADMIN, email="admin@example.com"):
    with app.app_context():
        user = User(name="Admin IDDUN", email=email, role=role)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.commit()
        return user.id


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_admin_requires_authentication(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_non_admin_cannot_access_admin(app, client):
    user_id = _create_user(app, role=UserRole.CLIENT, email="client@example.com")
    _login_session(client, user_id)
    response = client.get("/admin/")
    assert response.status_code == 403


def test_admin_dashboard_returns_200(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "OPERAÇÃO IDDUN" in response.get_data(as_text=True)


def test_admin_can_build_real_catalog(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)

    response = client.post(
        "/admin/estabelecimentos/novo",
        data={
            "name": "Studio Aurora",
            "neighborhood": "Batel",
            "city": "Curitiba",
            "state": "PR",
            "is_active": "y",
            "is_verified": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.post(
        "/admin/profissionais/novo",
        data={
            "display_name": "Laura Martins",
            "primary_specialty": "Cabeleireira",
            "city": "Curitiba",
            "state": "PR",
            "is_active": "y",
            "is_verified": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        establishment = db.session.scalar(select(Establishment).where(Establishment.name == "Studio Aurora"))
        professional = db.session.scalar(select(ProfessionalProfile).where(ProfessionalProfile.display_name == "Laura Martins"))
        establishment_id = establishment.id
        professional_id = professional.id

    response = client.post(
        "/admin/vinculos/novo",
        data={
            "professional_id": professional_id,
            "establishment_id": establishment_id,
            "role_name": "Cabeleireira",
            "status": "active",
            "is_primary": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.post(
        "/admin/experiencias/nova",
        data={
            "title": "Hair Ritual Aurora",
            "professional_id": professional_id,
            "establishment_id": establishment_id,
            "category": "cabelo",
            "short_description": "Tratamento, corte e finalização premium",
            "regular_price": "350.00",
            "price": "249.00",
            "duration_minutes": "90",
            "status": ExperienceStatus.PUBLISHED,
            "is_featured": "y",
            "is_first_experience": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        membership = db.session.scalar(select(ProfessionalEstablishmentMembership))
        experience = db.session.scalar(select(Experience).where(Experience.title == "Hair Ritual Aurora"))
        assert membership is not None
        assert membership.is_primary is True
        assert experience is not None
        assert experience.status == ExperienceStatus.PUBLISHED
        slug = experience.slug

    response = client.get("/experiencias")
    assert response.status_code == 200
    assert "Hair Ritual Aurora" in response.get_data(as_text=True)

    response = client.get(f"/experiencias/{slug}")
    assert response.status_code == 200
    assert "Hair Ritual Aurora" in response.get_data(as_text=True)


def test_admin_can_publish_opportunity_slots(app, client):
    from datetime import timedelta
    from app.services.time_service import to_local, utcnow

    user_id = _create_user(app)
    _login_session(client, user_id)

    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Agenda Pro",
            slug="agenda-pro",
            city="Curitiba",
            state="PR",
        )
        establishment = Establishment(name="Studio Agenda", slug="studio-agenda")
        db.session.add_all([professional, establishment])
        db.session.flush()
        experience = Experience(
            professional=professional,
            establishment=establishment,
            title="Experience Agenda",
            slug="experience-agenda",
            category="cabelo",
            short_description="Teste de oportunidade",
            regular_price="300.00",
            price="220.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.commit()
        experience_id = experience.id
        local_date = to_local(utcnow() + timedelta(days=3), professional.timezone).date()

    response = client.post(
        "/admin/oportunidades/nova",
        data={
            "experience_id": experience_id,
            "slot_date": local_date.isoformat(),
            "times": "10:00, 14:00",
            "booking_cutoff_minutes": "30",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        from app.models.booking import ExperienceSlot
        slots = db.session.scalars(select(ExperienceSlot)).all()
        assert len(slots) == 2
        assert all(slot.booking_cutoff_minutes == 30 for slot in slots)

    response = client.get("/admin/oportunidades")
    assert response.status_code == 200
    assert "Experience Agenda" in response.get_data(as_text=True)


def test_admin_bookings_page_returns_200(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)
    response = client.get("/admin/reservas")
    assert response.status_code == 200
    assert "Reservas" in response.get_data(as_text=True)


def test_public_handle_is_global_between_professional_and_establishment(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)

    response = client.post(
        "/admin/profissionais/novo",
        data={
            "display_name": "Studio Luz",
            "slug": "studio-luz",
            "timezone": "America/Sao_Paulo",
            "default_booking_cutoff_minutes": "60",
            "is_active": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.post(
        "/admin/estabelecimentos/novo",
        data={
            "name": "Outro Studio",
            "slug": "studio-luz",
            "timezone": "America/Sao_Paulo",
            "is_active": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Este endereço já está sendo usado" in response.get_data(as_text=True)


def test_google_calendar_settings_is_graceful_without_credentials(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)
    with app.app_context():
        professional = ProfessionalProfile(display_name="Calendar Pro", slug="calendar-pro")
        db.session.add(professional)
        db.session.commit()
        professional_id = professional.id

    response = client.get(f"/admin/profissionais/{professional_id}/integracoes/google")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Google Calendar" in body
    assert "Credenciais OAuth ainda não configuradas" in body


def test_establishment_dashboard_returns_operational_metrics(app, client):
    user_id = _create_user(app)
    _login_session(client, user_id)
    with app.app_context():
        establishment = Establishment(name="Studio Dashboard", slug="studio-dashboard")
        db.session.add(establishment)
        db.session.commit()
        establishment_id = establishment.id

    response = client.get(f"/admin/estabelecimentos/{establishment_id}/dashboard")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "DASHBOARD DO ESTABELECIMENTO" in body
    assert "Studio Dashboard" in body


def test_admin_can_edit_experience_without_reuploading_image(app, client):
    user_id = _create_user(app, email="admin-edit-experience@example.com")
    _login_session(client, user_id)

    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Edit Pro",
            slug="edit-pro",
            default_booking_cutoff_minutes=60,
        )
        establishment = Establishment(name="Edit Studio", slug="edit-studio")
        db.session.add_all([professional, establishment])
        db.session.flush()
        experience = Experience(
            professional=professional,
            establishment=establishment,
            title="Experiência Original",
            slug="experiencia-original",
            category="unhas",
            short_description="Descrição original",
            image_url="uploads/experiences/original.jpg",
            regular_price="300.00",
            price="249.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.commit()
        experience_id = experience.id
        professional_id = professional.id
        establishment_id = establishment.id

    response = client.post(
        f"/admin/experiencias/{experience_id}/editar",
        data={
            "title": "Experiência Atualizada",
            "professional_id": professional_id,
            "establishment_id": establishment_id,
            "category": "unhas",
            "short_description": "Descrição atualizada",
            "regular_price": "300.00",
            "price": "249.00",
            "duration_minutes": "60",
            "status": ExperienceStatus.PUBLISHED,
            "is_first_experience": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        experience = db.session.get(Experience, experience_id)
        assert experience.title == "Experiência Atualizada"
        assert experience.image_url == "uploads/experiences/original.jpg"


def test_experience_edit_explains_inherited_cutoff(app, client):
    user_id = _create_user(app, email="admin-cutoff-help@example.com")
    _login_session(client, user_id)

    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Cutoff Pro",
            slug="cutoff-pro",
            default_booking_cutoff_minutes=60,
        )
        experience = Experience(
            professional=professional,
            title="Cutoff Experience",
            slug="cutoff-experience",
            category="cabelo",
            short_description="Teste cutoff",
            regular_price="300.00",
            price="200.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add_all([professional, experience])
        db.session.commit()
        experience_id = experience.id

    response = client.get(f"/admin/experiencias/{experience_id}/editar")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "usa o padrão de 60 min" in body
    assert "Ex.: 60" in body


def test_admin_can_edit_membership_without_media_fields(app, client):
    user_id = _create_user(app, email="admin-edit-membership@example.com")
    _login_session(client, user_id)

    with app.app_context():
        professional = ProfessionalProfile(display_name="Member Pro", slug="member-pro")
        establishment = Establishment(name="Member Studio", slug="member-studio")
        db.session.add_all([professional, establishment])
        db.session.flush()
        membership = ProfessionalEstablishmentMembership(
            professional=professional,
            establishment=establishment,
            role_name="Nail designer",
            status="active",
            is_primary=True,
        )
        db.session.add(membership)
        db.session.commit()
        membership_id = membership.id
        professional_id = professional.id
        establishment_id = establishment.id

    response = client.post(
        f"/admin/vinculos/{membership_id}/editar",
        data={
            "professional_id": professional_id,
            "establishment_id": establishment_id,
            "role_name": "Especialista em unhas",
            "status": "active",
            "is_primary": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        membership = db.session.get(ProfessionalEstablishmentMembership, membership_id)
        assert membership.role_name == "Especialista em unhas"


def test_professional_focus_point_is_persisted(app, client):
    user_id = _create_user(app, email="admin-focus-professional@example.com")
    _login_session(client, user_id)

    response = client.post(
        "/admin/profissionais/novo",
        data={
            "display_name": "Focus Pro",
            "slug": "focus-pro",
            "timezone": "America/Sao_Paulo",
            "default_booking_cutoff_minutes": "60",
            "avatar_focus_x": "23",
            "avatar_focus_y": "71",
            "is_active": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        professional = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.slug == "focus-pro")
        )
        assert professional.avatar_focus_x == 23
        assert professional.avatar_focus_y == 71


def test_experience_focus_point_is_persisted(app, client):
    user_id = _create_user(app, email="admin-focus-experience@example.com")
    _login_session(client, user_id)

    with app.app_context():
        professional = ProfessionalProfile(display_name="Focus Exp Pro", slug="focus-exp-pro")
        db.session.add(professional)
        db.session.commit()
        professional_id = professional.id

    response = client.post(
        "/admin/experiencias/nova",
        data={
            "title": "Focus Experience",
            "professional_id": professional_id,
            "category": "unhas",
            "short_description": "Teste de enquadramento",
            "regular_price": "250.00",
            "price": "199.00",
            "duration_minutes": "60",
            "image_focus_x": "19",
            "image_focus_y": "82",
            "status": ExperienceStatus.PUBLISHED,
            "is_first_experience": "y",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        experience = db.session.scalar(
            select(Experience).where(Experience.slug == "focus-experience")
        )
        assert experience.image_focus_x == 19
        assert experience.image_focus_y == 82
