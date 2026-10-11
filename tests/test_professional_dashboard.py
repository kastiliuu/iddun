"""Regression coverage for the IDDUN Pro daily dashboard V1 and Sprint 02 operations."""

from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.time_service import (
    local_naive_to_utc,
)


FIXED_NOW = datetime(
    2026,
    10,
    8,
    15,
    0,
    tzinfo=timezone.utc,
)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(
            user_id
        )
        session["_fresh"] = True


def _catalog(app):
    with app.app_context():
        professional_user = User(
            name="Profissional Painel",
            email="pro-painel@example.com",
            role=UserRole.PROFESSIONAL,
        )
        professional_user.set_password(
            "senha-forte-123"
        )

        professional = ProfessionalProfile(
            user=professional_user,
            display_name="Marina Painel",
            slug="marina-painel",
            primary_specialty="Nail Designer",
            bio="Especialista em unhas.",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )

        client_user = User(
            name="Ana Cliente",
            email="ana-painel@example.com",
            role=UserRole.CLIENT,
        )
        client_user.set_password(
            "senha-forte-123"
        )

        client_profile = ClientProfile(
            user=client_user,
            phone="41999998888",
            city="Curitiba",
            state="PR",
        )

        db.session.add_all(
            [
                professional_user,
                professional,
                client_user,
                client_profile,
            ]
        )
        db.session.flush()

        experience = Experience(
            professional=professional,
            title="Manutenção em gel",
            slug="manutencao-painel",
            category="unhas",
            short_description=(
                "Manutenção profissional."
            ),
            regular_price="120.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add(experience)
        db.session.flush()

        booked_start = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                14,
                0,
            ),
            professional.timezone,
        )

        booked_slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=booked_start,
            ends_at=booked_start.replace(
                hour=booked_start.hour + 1
            ),
            status=SlotStatus.BOOKED,
        )

        free_start = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                15,
                0,
            ),
            professional.timezone,
        )

        free_slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            starts_at=free_start,
            ends_at=free_start.replace(
                hour=free_start.hour + 1
            ),
            status=SlotStatus.AVAILABLE,
        )

        db.session.add_all(
            [
                booked_slot,
                free_slot,
            ]
        )
        db.session.flush()

        booking = Booking(
            client=client_profile,
            experience=experience,
            professional=professional,
            slot=booked_slot,
            status=BookingStatus.CONFIRMED,
            price_at_booking=Decimal(
                "100.00"
            ),
            confirmed_at=FIXED_NOW,
        )

        db.session.add(booking)
        db.session.commit()

        return professional_user.id


def test_pro_dashboard_requires_professional_profile(
    app,
    client,
):
    with app.app_context():
        user = User(
            name="Cliente sem Pro",
            email="sem-pro@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    _login(
        client,
        user_id,
    )

    response = client.get(
        "/pro/painel",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/pro/comecar" in response.headers[
        "Location"
    ]


def test_pro_dashboard_renders_real_day_context(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    _login(
        client,
        user_id,
    )

    response = client.get(
        "/pro/painel"
    )

    assert response.status_code == 200

    html = response.get_data(
        as_text=True
    )

    assert (
        "Tudo o que importa para hoje."
        in html
    )
    # Shared Pro navigation retains operational routes and context switching.
    assert 'aria-label="Navegação IDDUN Pro"' in html
    assert 'href="/pro/clientes"' in html
    assert 'href="/pro/insights"' in html
    assert 'href="/pro/jornada"' in html
    assert 'href="/feed"' in html
    assert html.count('aria-current="page"') >= 1

    assert "Ana Cliente" in html
    assert "Manutenção em gel" in html
    assert "R$ 100,00" in html
    assert "1h" in html
    assert (
        "https://wa.me/5541999998888"
        in html
    )
    assert (
        "Oportunidades de hoje"
        in html
    )


def test_pro_dashboard_does_not_invent_occupancy(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    _login(
        client,
        user_id,
    )

    html = client.get(
        "/pro/painel"
    ).get_data(
        as_text=True
    )

    assert "ocupação semanal" not in html.lower()
    assert "ocupação mensal" not in html.lower()



def test_pro_can_block_and_reopen_own_available_slot(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "professional_dashboard_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )
    monkeypatch.setattr(
        (
            "app.services."
            "booking_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    with app.app_context():
        slot = db.session.scalar(
            db.select(
                ExperienceSlot
            ).where(
                ExperienceSlot.status
                == SlotStatus.AVAILABLE
            )
        )
        slot_id = slot.id

    _login(
        client,
        user_id,
    )

    blocked = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/bloquear"
        ),
        follow_redirects=False,
    )

    assert blocked.status_code == 302

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.BLOCKED_MANUAL
        )

    reopened = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/liberar"
        ),
        follow_redirects=False,
    )

    assert reopened.status_code == 302

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_pro_can_cancel_own_future_booking(
    app,
    client,
    monkeypatch,
):
    user_id = _catalog(app)

    monkeypatch.setattr(
        (
            "app.services."
            "booking_service."
            "utcnow"
        ),
        lambda: FIXED_NOW,
    )

    with app.app_context():
        booking = db.session.scalar(
            db.select(
                Booking
            ).where(
                Booking.status
                == BookingStatus.CONFIRMED
            )
        )
        booking_id = booking.id
        slot_id = booking.slot_id

    _login(
        client,
        user_id,
    )

    response = client.post(
        (
            "/pro/painel/reservas/"
            f"{booking_id}/cancelar"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        booking = db.session.get(
            Booking,
            booking_id,
        )
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )

        assert (
            booking.status
            == BookingStatus.CANCELLED
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_pro_cannot_operate_another_professional_slot(
    app,
    client,
):
    user_id = _catalog(app)

    with app.app_context():
        other_user = User(
            name="Outro Pro",
            email="outro-pro@example.com",
            role=UserRole.PROFESSIONAL,
        )
        other_user.set_password(
            "senha-forte-123"
        )

        other_profile = ProfessionalProfile(
            user=other_user,
            display_name="Outro Profissional",
            slug="outro-profissional",
            primary_specialty="Barbeiro",
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )

        db.session.add_all(
            [
                other_user,
                other_profile,
            ]
        )
        db.session.flush()

        experience = Experience(
            professional=other_profile,
            title="Corte de teste",
            slug="corte-outro-pro",
            category="cabelo",
            short_description="Teste",
            regular_price="80.00",
            price="70.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add(experience)
        db.session.flush()

        starts_at = local_naive_to_utc(
            datetime(
                2026,
                10,
                8,
                17,
                0,
            ),
            other_profile.timezone,
        )

        slot = ExperienceSlot(
            experience=experience,
            professional=other_profile,
            starts_at=starts_at,
            ends_at=starts_at.replace(
                hour=starts_at.hour + 1
            ),
            status=SlotStatus.AVAILABLE,
        )

        db.session.add(slot)
        db.session.commit()
        slot_id = slot.id

    _login(
        client,
        user_id,
    )

    response = client.post(
        (
            "/pro/painel/horarios/"
            f"{slot_id}/bloquear"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 404

    with app.app_context():
        slot = db.session.get(
            ExperienceSlot,
            slot_id,
        )
        assert (
            slot.status
            == SlotStatus.AVAILABLE
        )


def test_pro_services_page_shows_only_owned_catalog(app, client):
    user_id = _catalog(app)
    _login(client, user_id)
    response = client.get("/pro/servicos")
    assert response.status_code == 200
    assert b"Manuten" in response.data
    assert b"Visualizar e consultar hor" in response.data
    dashboard = client.get("/pro/painel")
    assert dashboard.status_code == 200
    assert b'href="/pro/servicos"' in dashboard.data


def test_pro_services_page_redirects_client_without_profile(app, client):
    user = User(
        name="Cliente somente", email="cliente-servicos@example.com",
        role=UserRole.CLIENT,
    )
    user.set_password("senha-forte-123")
    with app.app_context():
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    _login(client, user_id)
    response = client.get("/pro/servicos")
    assert response.status_code == 302
    assert "/pro/comecar" in response.headers["Location"]


def test_pro_creates_unpublished_service_draft(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    page = client.get("/pro/servicos/novo")
    assert page.status_code == 200
    assert b"Criar servi" in page.data

    response = client.post(
        "/pro/servicos/novo",
        data={
            "title": "Blindagem de unhas",
            "category": "unhas",
            "short_description": "Reforço para unhas naturais",
            "description": "Atendimento individualizado.",
            "regular_price": "120.00",
            "price": "100.00",
            "duration_minutes": "60",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/servicos")

    with app.app_context():
        created = db.session.scalar(
            select(Experience).where(Experience.title == "Blindagem de unhas")
        )
        assert created is not None
        assert created.status == ExperienceStatus.DRAFT
        assert created.professional.user_id == user_id
        assert created.establishment_id is None

    overview = client.get("/pro/servicos")
    assert b"Blindagem de unhas" in overview.data
    assert b"Rascunho" in overview.data


def test_pro_cannot_create_draft_with_price_above_regular_price(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    response = client.post(
        "/pro/servicos/novo",
        data={
            "title": "Preco invalido",
            "category": "unhas",
            "short_description": "Servico para rejeitar",
            "regular_price": "50.00",
            "price": "80.00",
            "duration_minutes": "60",
        },
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(
            select(Experience).where(Experience.title == "Preco invalido")
        ) is None


def test_pro_edits_own_draft_service_without_changing_publication(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    with app.app_context():
        professional = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        draft = Experience(
            professional_id=professional.id,
            title="Rascunho original",
            slug="rascunho-original",
            category="unhas",
            short_description="Descrição inicial",
            regular_price="130.00",
            price="100.00",
            duration_minutes=60,
            status=ExperienceStatus.DRAFT,
        )
        db.session.add(draft)
        db.session.commit()
        draft_id = draft.id
    _login(client, user_id)
    page = client.get(f"/pro/servicos/{draft_id}/editar")
    assert page.status_code == 200
    assert b"Rascunho original" in page.data
    updated = client.post(
        f"/pro/servicos/{draft_id}/editar",
        data={
            "title": "Rascunho atualizado",
            "category": "unhas",
            "short_description": "Descrição atualizada",
            "regular_price": "150.00",
            "price": "120.00",
            "duration_minutes": "90",
        },
        follow_redirects=False,
    )
    assert updated.status_code == 302
    with app.app_context():
        item = db.session.get(Experience, draft_id)
        assert item.title == "Rascunho atualizado"
        assert item.duration_minutes == 90
        assert item.slug == "rascunho-original"
        assert item.status == ExperienceStatus.DRAFT


def test_pro_cannot_edit_another_pro_service_or_published_one(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    with app.app_context():
        professional = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        published = db.session.scalar(
            select(Experience).where(Experience.professional_id == professional.id)
        )
        published_id = published.id
        other_user = User(
            name="Outro profissional",
            email="outro-servicos-edit@example.com",
            role=UserRole.PROFESSIONAL,
        )
        other_user.set_password("senha-forte-123")
        db.session.add(other_user)
        db.session.flush()
        other_pro = ProfessionalProfile(
            user=other_user, display_name="Outro", slug="outro-servicos-edit",
        )
        db.session.add(other_pro)
        db.session.commit()
        other_id = other_user.id
    _login(client, user_id)
    published_response = client.get(f"/pro/servicos/{published_id}/editar")
    assert published_response.status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(other_id)
    from flask import g
    g.pop("_login_user", None)
    forbidden = client.get(f"/pro/servicos/{published_id}/editar")
    assert forbidden.status_code == 404


def test_pro_can_pause_published_service_without_cancelling_bookings(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        item = db.session.scalar(
            select(Experience).where(Experience.slug == "manutencao-painel")
        )
        service_id = item.id
        booking_id = db.session.scalar(
            select(Booking).where(Booking.experience_id == service_id)
        ).id

    response = client.post(f"/pro/servicos/{service_id}/pausar")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/servicos")
    with app.app_context():
        assert db.session.get(Experience, service_id).status == ExperienceStatus.PAUSED
        assert db.session.get(Booking, booking_id).status == BookingStatus.CONFIRMED

    page = client.get("/pro/servicos")
    assert b"Republicar servi" in page.data


def test_pro_publication_reuses_existing_catalog_eligibility(app, client, monkeypatch):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        item = Experience(
            professional_id=profile.id,
            title="Catalogo Pro",
            slug="catalogo-pro-publicacao",
            category="unhas",
            short_description="Atendimento do catálogo",
            regular_price="150.00",
            price="120.00",
            duration_minutes=60,
            status=ExperienceStatus.DRAFT,
        )
        db.session.add(item)
        db.session.commit()
        service_id = item.id

    attempts = []

    def publish_existing(item):
        attempts.append(item.id)
        item.status = ExperienceStatus.PUBLISHED

    monkeypatch.setattr(
        "app.routes.platform.publish_experience", publish_existing
    )
    response = client.post(f"/pro/servicos/{service_id}/publicar")
    assert response.status_code == 302
    assert attempts == [service_id]
    with app.app_context():
        assert db.session.get(Experience, service_id).status == ExperienceStatus.PUBLISHED


def test_pro_cannot_change_another_professional_service_status(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        other_user = User(
            name="Outro Pro", email="other-pro-status@example.com",
            role=UserRole.PROFESSIONAL,
        )
        other_user.set_password("senha-forte-123")
        other_profile = ProfessionalProfile(
            user=other_user, display_name="Outro Pro",
            slug="outro-pro-status",
        )
        db.session.add_all([other_user, other_profile])
        db.session.flush()
        other_service = Experience(
            professional=other_profile,
            title="Outro servico", slug="outro-servico-status",
            category="unhas", short_description="Outro catálogo",
            regular_price="80.00", price="60.00",
            duration_minutes=60, status=ExperienceStatus.DRAFT,
        )
        db.session.add(other_service)
        db.session.commit()
        service_id = other_service.id

    for action in ("publicar", "pausar"):
        response = client.post(f"/pro/servicos/{service_id}/{action}")
        assert response.status_code == 404
    with app.app_context():
        assert db.session.get(Experience, service_id).status == ExperienceStatus.DRAFT


def test_pro_service_image_upload_on_create_and_edit(app, client):
    from io import BytesIO
    from PIL import Image
    from sqlalchemy import select

    def png_upload(name):
        data = BytesIO()
        Image.new("RGB", (16, 16), (180, 80, 120)).save(data, format="PNG")
        data.seek(0)
        return data, name

    user_id = _catalog(app)
    _login(client, user_id)
    payload = {
        "title": "Capa de gel",
        "category": "unhas",
        "short_description": "Serviço com imagem própria",
        "regular_price": "150.00",
        "price": "120.00",
        "duration_minutes": "60",
        "image_file": png_upload("capa.png"),
    }
    created = client.post(
        "/pro/servicos/novo",
        data=payload,
        content_type="multipart/form-data",
    )
    assert created.status_code == 302
    with app.app_context():
        item = db.session.scalar(
            select(Experience).where(Experience.title == "Capa de gel")
        )
        assert item is not None
        assert item.image_url
        service_id = item.id
        first_image = item.image_url

    updated = client.post(
        f"/pro/servicos/{service_id}/editar",
        data={
            "title": "Capa de gel",
            "category": "unhas",
            "short_description": "Serviço com nova imagem",
            "regular_price": "150.00",
            "price": "120.00",
            "duration_minutes": "60",
            "image_file": png_upload("nova-capa.png"),
        },
        content_type="multipart/form-data",
    )
    assert updated.status_code == 302
    with app.app_context():
        item = db.session.get(Experience, service_id)
        assert item.image_url
        assert item.image_url != first_image
        assert item.status == ExperienceStatus.DRAFT
    page = client.get("/pro/servicos")
    assert b"Capa de gel" in page.data


def test_pro_service_rejects_invalid_image_without_creating_draft(app, client):
    from io import BytesIO
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    response = client.post(
        "/pro/servicos/novo",
        data={
            "title": "Imagem inválida",
            "category": "unhas",
            "short_description": "Imagem inválida",
            "regular_price": "100.00",
            "price": "80.00",
            "duration_minutes": "60",
            "image_file": (BytesIO(b"not-an-image"), "cover.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(
            select(Experience).where(Experience.title == "Imagem inválida")
        ) is None


def test_pro_can_open_service_slot_through_existing_availability_service(
    app, client, monkeypatch,
):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        item = db.session.scalar(
            select(Experience).where(Experience.slug == "manutencao-painel")
        )
        service_id = item.id

    observed = []

    def create(**kwargs):
        observed.append({
            "user_id": kwargs["user"].id,
            "reference": kwargs["experience_reference"],
            "date": kwargs["slot_date"],
            "time": kwargs["slot_time"],
        })

    monkeypatch.setattr("app.routes.platform.create_availability", create)
    response = client.post(
        f"/pro/servicos/{service_id}/horarios",
        data={"slot_date": "2026-12-15", "slot_time": "14:00"},
    )
    assert response.status_code == 302
    assert observed == [{
        "user_id": user_id,
        "reference": str(service_id),
        "date": "2026-12-15",
        "time": "14:00",
    }]
    page = client.get("/pro/servicos")
    assert page.status_code == 200
    assert b"Disponibilizar hor" in page.data
    assert b"Pr" in page.data


def test_pro_cannot_open_another_professionals_service_slot(app, client, monkeypatch):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        owner = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        other = ProfessionalProfile(
            display_name="Outro Dono", slug="outro-dono-slots",
        )
        db.session.add(other)
        db.session.flush()
        item = Experience(
            professional=other,
            title="Servico de outro",
            slug="servico-outro-slot",
            category="unhas",
            short_description="Atendimento de outro profissional",
            regular_price="100.00",
            price="90.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(item)
        db.session.commit()
        other_service_id = item.id

    called = []
    monkeypatch.setattr(
        "app.routes.platform.create_availability",
        lambda **kwargs: called.append(kwargs),
    )
    response = client.post(
        f"/pro/servicos/{other_service_id}/horarios",
        data={"slot_date": "2026-12-15", "slot_time": "14:00"},
    )
    assert response.status_code == 404
    assert called == []


def test_pro_opens_multiple_real_slots_and_rejects_overlapping_batch(app, client):
    from sqlalchemy import select, func

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        item = db.session.scalar(
            select(Experience).where(Experience.slug == "manutencao-painel")
        )
        service_id = item.id
        starting_count = db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id
            )
        )

    created = client.post(
        f"/pro/servicos/{service_id}/horarios/lote",
        data={"slot_date": "2027-02-15", "slot_times": "09:00, 10:00, 11:00"},
    )
    assert created.status_code == 302
    with app.app_context():
        current_count = db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id
            )
        )
        assert current_count == starting_count + 3

    # Both times overlap (60 minute service); no partial batch is created.
    rejected = client.post(
        f"/pro/servicos/{service_id}/horarios/lote",
        data={"slot_date": "2027-02-16", "slot_times": "09:00, 09:30"},
    )
    assert rejected.status_code == 302
    with app.app_context():
        final_count = db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id
            )
        )
        assert final_count == current_count


def test_pro_batch_availability_denies_other_professional(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        other = ProfessionalProfile(
            display_name="Outro Pro", slug="other-batch-owner",
        )
        db.session.add(other)
        db.session.flush()
        service = Experience(
            professional=other,
            title="Outro serviço", slug="other-service-batch",
            category="unhas", short_description="Atendimento externo",
            regular_price="100.00", price="90.00", duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(service)
        db.session.commit()
        service_id = service.id
    response = client.post(
        f"/pro/servicos/{service_id}/horarios/lote",
        data={"slot_date": "2027-02-15", "slot_times": "09:00, 10:00"},
    )
    assert response.status_code == 404


def test_pro_generates_day_slots_from_weekly_shift_excluding_break(app, client):
    from datetime import time
    from sqlalchemy import select
    from app.models.professional_schedule import ProfessionalWorkingHour

    user_id = _catalog(app)
    with app.app_context():
        profile = db.session.scalar(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        service = db.session.scalar(
            select(Experience).where(Experience.slug == "manutencao-painel")
        )
        service_id = service.id
        db.session.add(
            ProfessionalWorkingHour(
                professional=profile,
                weekday=0,
                start_time=time(9, 0),
                end_time=time(14, 0),
                break_start_time=time(12, 0),
                break_end_time=time(13, 0),
            )
        )
        db.session.commit()

    _login(client, user_id)
    response = client.post(
        f"/pro/servicos/{service_id}/horarios/jornada",
        data={"slot_date": "2027-02-15"},
    )
    assert response.status_code == 302
    with app.app_context():
        slots = db.session.scalars(
            select(ExperienceSlot).where(
                ExperienceSlot.experience_id == service_id,
                ExperienceSlot.starts_at >= datetime(2027, 2, 15, tzinfo=timezone.utc),
                ExperienceSlot.starts_at < datetime(2027, 2, 17, tzinfo=timezone.utc),
            )
        ).all()
        from app.services.time_service import to_local
        times = sorted(to_local(slot.starts_at, "America/Sao_Paulo").strftime("%H:%M") for slot in slots)
        assert times == ["09:00", "10:00", "11:00", "13:00"]


def test_pro_day_schedule_rejects_unconfigured_day_without_creating_slots(app, client):
    from sqlalchemy import select, func

    user_id = _catalog(app)
    with app.app_context():
        service = db.session.scalar(
            select(Experience).where(Experience.slug == "manutencao-painel")
        )
        service_id = service.id
        original_count = db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id
            )
        )
    _login(client, user_id)
    response = client.post(
        f"/pro/servicos/{service_id}/horarios/jornada",
        data={"slot_date": "2027-02-15"},
    )
    assert response.status_code == 302
    with app.app_context():
        after = db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id
            )
        )
        assert after == original_count


def test_pro_day_schedule_denies_service_owned_by_another_professional(app, client):
    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        other = ProfessionalProfile(
            display_name="Outra profissional", slug="outra-agenda-dia",
        )
        db.session.add(other)
        db.session.flush()
        service = Experience(
            professional=other,
            title="Serviço externo", slug="servico-externo-jornada",
            category="unhas", short_description="Serviço de outra conta",
            regular_price="120.00", price="100.00",
            duration_minutes=60, status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(service)
        db.session.commit()
        service_id = service.id
    response = client.post(
        f"/pro/servicos/{service_id}/horarios/jornada",
        data={"slot_date": "2027-02-15"},
    )
    assert response.status_code == 404


def test_pro_can_manage_own_available_service_slot_from_catalog(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        slot = db.session.scalar(
            select(ExperienceSlot).where(ExperienceSlot.status == SlotStatus.AVAILABLE)
        )
        service_id = slot.experience_id
        slot_id = slot.id

    blocked = client.post(f"/pro/servicos/{service_id}/horarios/{slot_id}/bloquear")
    assert blocked.status_code == 302
    with app.app_context():
        assert db.session.get(ExperienceSlot, slot_id).status == SlotStatus.BLOCKED_MANUAL

    reopened = client.post(f"/pro/servicos/{service_id}/horarios/{slot_id}/liberar")
    assert reopened.status_code == 302
    with app.app_context():
        assert db.session.get(ExperienceSlot, slot_id).status == SlotStatus.AVAILABLE


def test_pro_service_slot_controls_never_modify_booked_slot(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        slot = db.session.scalar(
            select(ExperienceSlot).where(ExperienceSlot.status == SlotStatus.BOOKED)
        )
        service_id = slot.experience_id
        slot_id = slot.id
        booking_id = db.session.scalar(
            select(Booking).where(Booking.slot_id == slot_id)
        ).id

    for action in ("bloquear", "liberar"):
        response = client.post(
            f"/pro/servicos/{service_id}/horarios/{slot_id}/{action}"
        )
        assert response.status_code == 302
    with app.app_context():
        assert db.session.get(ExperienceSlot, slot_id).status == SlotStatus.BOOKED
        assert db.session.get(Booking, booking_id).status == BookingStatus.CONFIRMED


def test_pro_service_slot_management_rejects_wrong_service_and_owner(app, client):
    from sqlalchemy import select

    user_id = _catalog(app)
    _login(client, user_id)
    with app.app_context():
        slot = db.session.scalar(select(ExperienceSlot))
        slot_id = slot.id
        service_id = slot.experience_id
    for action in ("bloquear", "liberar"):
        wrong_service = client.post(
            f"/pro/servicos/{service_id + 9999}/horarios/{slot_id}/{action}"
        )
        assert wrong_service.status_code == 404

    with app.app_context():
        other_user = User(
            name="Outro gestor", email="other-slot-manager@example.com",
            role=UserRole.PROFESSIONAL,
        )
        other_user.set_password("senha-forte-123")
        db.session.add(other_user)
        db.session.commit()
        other_user_id = other_user.id
    _login(client, other_user_id)
    from flask import g
    g.pop("_login_user", None)
    for action in ("bloquear", "liberar"):
        response = client.post(
            f"/pro/servicos/{service_id}/horarios/{slot_id}/{action}"
        )
        assert response.status_code in (403, 404)
