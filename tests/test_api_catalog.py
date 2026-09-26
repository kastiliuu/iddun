from datetime import timedelta

from app.extensions import db
from app.models.booking import ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.services.time_service import utcnow


def test_catalog_api_only_exposes_published_real_experiences_and_slots(app, client):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional Real",
            slug="profissional-real",
            city="Curitiba",
        )
        published = Experience(
            professional=professional,
            title="Experiência Real",
            slug="experiencia-real",
            category="unhas",
            short_description="Atendimento presencial",
            regular_price="150.00",
            price="120.00",
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        draft = Experience(
            professional=professional,
            title="Experiência Rascunho",
            slug="experiencia-rascunho",
            category="unhas",
            short_description="Ainda não publicada",
            regular_price="100.00",
            price="90.00",
            status=ExperienceStatus.DRAFT,
        )
        starts_at = utcnow() + timedelta(days=3)
        slot = ExperienceSlot(
            experience=published,
            professional=professional,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            status=SlotStatus.AVAILABLE,
        )
        db.session.add_all([professional, published, draft, slot])
        db.session.commit()
        slot_id = slot.id

    response = client.get("/api/v1/experiences?category=unhas")
    assert response.status_code == 200
    result = response.get_json()
    assert result["total"] == 1
    assert result["nextOffset"] is None
    assert result["items"][0]["id"] == "experiencia-real"
    assert result["items"][0]["price"] == 120
    assert result["items"][0]["availableSlotsCount"] == 1
    assert result["items"][0]["webUrl"].endswith("/experiencias/experiencia-real")
    assert result["items"][0]["imageUrl"].startswith("http")

    detail = client.get("/api/v1/experiences/experiencia-real")
    assert detail.status_code == 200
    assert detail.get_json()["professional"] == "Profissional Real"

    availability = client.get("/api/v1/experiences/experiencia-real/availability")
    assert availability.status_code == 200
    assert availability.get_json()["days"][0]["slots"][0]["id"] == slot_id

    assert client.get("/api/v1/experiences/experiencia-rascunho").status_code == 404
    assert client.get("/api/v1/experiences/hair-experience-camila-rocha").status_code == 404
    assert client.get("/api/v1/experiences/hair-experience-camila-rocha/availability").status_code == 404

