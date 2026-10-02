from datetime import timedelta
from io import BytesIO

from sqlalchemy import select

from app.extensions import db
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.certification import ProfessionalCertification
from app.models.establishment import Establishment
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.reputation import ContactClick, Review, ReviewTarget
from app.models.user import User, UserRole
from app.services.reputation_service import (
    reputation_summary,
    save_booking_reviews,
)
from app.services.time_service import utcnow


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _user(app, email, name="Cliente"):
    with app.app_context():
        user = User(name=name, email=email, role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        profile = ClientProfile(user=user)
        db.session.add_all([user, profile])
        db.session.commit()
        return user.id, profile.id


def _completed_booking(app):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Camila Review",
            slug="camila-review",
            primary_specialty="Hair Stylist",
            bio="Especialista em transformações e experiências personalizadas de beleza.",
            city="Curitiba",
            state="PR",
            phone="41999999999",
            whatsapp_enabled=True,
        )
        establishment = Establishment(
            name="Studio Review",
            slug="studio-review",
            description="Espaço para experiências de beleza e atendimento personalizado.",
            category="salao",
            city="Curitiba",
            state="PR",
            phone="41988888888",
            whatsapp_enabled=True,
        )
        user = User(name="Cliente Review", email="review@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        client_profile = ClientProfile(user=user)
        db.session.add_all([professional, establishment, user, client_profile])
        db.session.flush()
        experience = Experience(
            professional=professional,
            establishment=establishment,
            title="Experiência Review",
            slug="experiencia-review",
            category="cabelo",
            short_description="Experiência para avaliação verificada",
            regular_price="400.00",
            price="400.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.flush()
        start = utcnow() - timedelta(days=1)
        slot = ExperienceSlot(
            experience=experience,
            professional=professional,
            establishment=establishment,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            status=SlotStatus.BOOKED,
        )
        db.session.add(slot)
        db.session.flush()
        booking = Booking(
            client=client_profile,
            experience=experience,
            professional=professional,
            establishment=establishment,
            slot=slot,
            status=BookingStatus.COMPLETED,
            price_at_booking="400.00",
            completed_at=utcnow(),
        )
        db.session.add(booking)
        db.session.commit()
        return user.id, booking.id, professional.id, establishment.id


def test_completed_booking_can_create_verified_professional_and_business_reviews(app, client):
    user_id, booking_id, professional_id, establishment_id = _completed_booking(app)
    _login_session(client, user_id)

    response = client.post(
        f"/reserva/{booking_id}/avaliar",
        data={
            "professional_rating": "5",
            "professional_recommended": "yes",
            "professional_comment": "Resultado excelente e atendimento impecável.",
            "establishment_rating": "4",
            "establishment_recommended": "yes",
            "establishment_comment": "Ambiente muito bom e equipe atenciosa.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/minhas-reservas")

    with app.app_context():
        reviews = db.session.scalars(select(Review).order_by(Review.target_type)).all()
        assert len(reviews) == 2
        assert {item.target_type for item in reviews} == {
            ReviewTarget.PROFESSIONAL,
            ReviewTarget.ESTABLISHMENT,
        }
        pro = db.session.get(ProfessionalProfile, professional_id)
        business = db.session.get(Establishment, establishment_id)
        assert reputation_summary(pro.reviews_received)["average"] == 5
        assert reputation_summary(business.reviews_received)["average"] == 4
        assert reputation_summary(pro.reviews_received)["recommendation_percent"] == 100

        from app.services.experience_service import get_experience_by_slug

        catalog_item = get_experience_by_slug("experiencia-review")
        assert catalog_item["rating"] == 5
        assert catalog_item["reviews"] == 1
        assert catalog_item["establishment_rating"] == 4
        assert catalog_item["establishment_reviews"] == 1


def test_non_completed_booking_cannot_be_reviewed(app, client):
    user_id, booking_id, _, _ = _completed_booking(app)
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        booking.status = BookingStatus.CONFIRMED
        db.session.commit()
    _login_session(client, user_id)

    response = client.get(f"/reserva/{booking_id}/avaliar", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/minhas-reservas")


def test_professional_can_add_certificate(app, client):
    user_id, _ = _user(app, "pro-cert@example.com", "Profissional Cert")
    with app.app_context():
        user = db.session.get(User, user_id)
        professional = ProfessionalProfile(
            user=user,
            display_name="Profissional Cert",
            slug="profissional-cert",
            primary_specialty="Colorista",
            bio="Profissional especializada em cor, técnica e atendimento personalizado.",
            city="Curitiba",
            state="PR",
        )
        db.session.add(professional)
        db.session.commit()
    _login_session(client, user_id)

    response = client.post(
        "/pro/certificacoes",
        data={
            "title": "Colorimetria Avançada",
            "issuer": "Academia IDDUN",
            "credential_id": "CERT-2026",
            "verification_url": "https://example.com/cert/CERT-2026",
            "is_public": "y",
            "document_file": (
                BytesIO(b"%PDF-1.4\n%%EOF\n"),
                "certificado.pdf",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pro/certificacoes")
    with app.app_context():
        cert = db.session.scalar(select(ProfessionalCertification))
        assert cert is not None
        assert cert.title == "Colorimetria Avançada"
        assert cert.is_public is True
        assert cert.document_url.endswith(".pdf")


def test_whatsapp_redirect_records_lead(app, client):
    _, _, professional_id, establishment_id = _completed_booking(app)

    response = client.get("/contato/profissional/camila-review/whatsapp", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://wa.me/5541999999999")

    response = client.get("/contato/estabelecimento/studio-review/whatsapp", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://wa.me/5541988888888")

    with app.app_context():
        clicks = db.session.scalars(select(ContactClick).order_by(ContactClick.id)).all()
        assert len(clicks) == 2
        assert clicks[0].professional_id == professional_id
        assert clicks[1].establishment_id == establishment_id



def test_establishment_not_recommended_boolean_is_persisted(
    app,
):
    (
        _user_id,
        booking_id,
        _professional_id,
        establishment_id,
    ) = _completed_booking(app)

    with app.app_context():
        booking = db.session.get(
            Booking,
            booking_id,
        )

        save_booking_reviews(
            booking=booking,
            client_profile=booking.client,
            professional_rating=5,
            professional_recommended=True,
            professional_comment="Excelente.",
            establishment_rating=3,
            establishment_recommended=False,
            establishment_comment=(
                "Bom atendimento, mas eu não retornaria ao local."
            ),
        )

        establishment_review = (
            db.session.scalar(
                select(Review).where(
                    Review.booking_id
                    == booking_id,
                    Review.target_type
                    == ReviewTarget.ESTABLISHMENT,
                )
            )
        )

        assert establishment_review is not None
        assert (
            establishment_review.establishment_id
            == establishment_id
        )
        assert (
            establishment_review.recommended
            is False
        )
