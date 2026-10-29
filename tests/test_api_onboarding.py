from datetime import date, datetime, timezone

import pytest

from sqlalchemy import func, select

from app.models.experience import Experience, ExperienceStatus
from app.extensions import db
from app.models.establishment import (
    Establishment,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.professional_experience import (
    ProfessionalExperience,
    ProfessionalExperienceVerification,
)
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session


BASE = "/api/v1/onboarding"


def _authenticated_client(
    app,
    *,
    email="onboarding@example.com",
):
    with app.app_context():
        user = User(
            name="Profissional Mobile",
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )

        db.session.add(user)
        db.session.flush()
        db.session.add(
            ClientProfile(user=user)
        )
        db.session.commit()

        tokens = issue_session(user)

        return (
            user.id,
            {
                "Authorization": (
                    f"Bearer "
                    f"{tokens.access_token}"
                )
            },
        )


def _professional_payload(**changes):
    payload = {
        "displayName": "Marina Mobile",
        "primarySpecialty": "Nail Designer",
        "categories": [
            "unhas",
            "estetica",
        ],
        "city": "Curitiba",
        "state": "PR",
        "bio": (
            "Atendimento autoral com foco "
            "em unhas naturais."
        ),
        "phone": "41999999999",
    }
    payload.update(changes)
    return payload


def test_onboarding_api_requires_bearer_token(
    client,
):
    response = client.get(
        f"{BASE}/professional"
    )

    assert response.status_code == 401
    assert (
        response.get_json()["error"]["code"]
        == "authentication_required"
    )


def test_professional_draft_is_real_resumable_and_updatable(
    app,
    client,
):
    user_id, headers = (
        _authenticated_client(app)
    )

    created = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(),
    )

    assert created.status_code in {
        200,
        201,
    }

    profile = created.get_json()[
        "profile"
    ]

    assert profile["id"]
    assert profile["displayName"] == (
        "Marina Mobile"
    )
    assert profile["categories"] == [
        "unhas",
        "estetica",
    ]
    assert profile["isActive"] is False
    assert (
        profile["onboardingCompleted"]
        is False
    )
    assert (
        profile["completion"][
            "readyToPublish"
        ]
        is False
    )

    resumed = client.get(
        f"{BASE}/professional",
        headers=headers,
    )

    assert resumed.status_code == 200
    assert (
        resumed.get_json()["profile"]["id"]
        == profile["id"]
    )

    updated = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(
            displayName=(
                "Marina Atualizada"
            ),
        ),
    )

    assert updated.status_code == 200
    assert (
        updated.get_json()["profile"][
            "displayName"
        ]
        == "Marina Atualizada"
    )

    with app.app_context():
        assert db.session.scalar(
            select(func.count())
            .select_from(
                ProfessionalProfile
            )
            .where(
                ProfessionalProfile.user_id
                == user_id
            )
        ) == 1


def test_external_professional_experience_is_unverified(
    app,
    client,
):
    _, headers = (
        _authenticated_client(app)
    )

    client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(),
    )

    created = client.post(
        f"{BASE}/professional/experiences",
        headers=headers,
        json={
            "companyName": "Studio Externo",
            "roleTitle": "Nail Designer",
            "description": "Atendimento e nail art.",
            "startedAt": "2024-01-01",
            "endedAt": "2025-01-01",
            "isCurrent": False,
        },
    )

    assert created.status_code == 201
    experience = created.get_json()[
        "experience"
    ]
    assert (
        experience["verificationStatus"]
        == ProfessionalExperienceVerification.UNVERIFIED
    )
    assert experience["verified"] is False

    with app.app_context():
        assert db.session.scalar(
            select(func.count())
            .select_from(
                ProfessionalExperience
            )
        ) == 1


def test_membership_can_verify_professional_experience(
    app,
    client,
):
    user_id, headers = (
        _authenticated_client(app)
    )

    client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(),
    )

    with app.app_context():
        profile = db.session.scalar(
            select(
                ProfessionalProfile
            ).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )
        establishment = Establishment(
            name="Studio IDDUN",
            slug="studio-iddun",
            city="Curitiba",
            state="PR",
        )
        db.session.add(establishment)
        db.session.flush()
        db.session.add(
            ProfessionalEstablishmentMembership(
                professional_id=profile.id,
                establishment_id=(
                    establishment.id
                ),
                role_name="Nail Designer",
                status=MembershipStatus.ACTIVE,
                is_primary=True,
                started_at=date(
                    2025,
                    1,
                    1,
                ),
            )
        )
        db.session.commit()
        establishment_id = (
            establishment.id
        )

    created = client.post(
        f"{BASE}/professional/experiences",
        headers=headers,
        json={
            "companyName": "",
            "roleTitle": "Nail Designer",
            "startedAt": "2025-01-01",
            "isCurrent": True,
            "establishmentId": (
                establishment_id
            ),
        },
    )

    assert created.status_code == 201
    experience = created.get_json()[
        "experience"
    ]
    assert experience["verified"] is True
    assert (
        experience["companyName"]
        == "Studio IDDUN"
    )
    assert (
        experience["establishment"]["id"]
        == establishment_id
    )


def test_publish_requires_identity_and_modality_not_optional_media(
    app,
    client,
):
    user_id, headers = (
        _authenticated_client(app)
    )

    client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(),
    )

    incomplete = client.post(
        f"{BASE}/professional/publish",
        headers=headers,
    )

    assert incomplete.status_code == 409
    assert (
        incomplete.get_json()[
            "error"
        ]["code"]
        == "profile_incomplete"
    )

    with app.app_context():
        profile = db.session.scalar(
            select(
                ProfessionalProfile
            ).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )
        profile.attendance_modalities = "own_space"

        db.session.add(
            ProfessionalExperience(
                professional_id=profile.id,
                company_name="Studio História",
                role_title="Nail Designer",
                description="Experiência pública do perfil.",
                started_at=date(2024, 1, 1),
                ended_at=None,
                is_current=True,
                verification_status=(
                    ProfessionalExperienceVerification.UNVERIFIED
                ),
            )
        )
        db.session.commit()

    published = client.post(
        f"{BASE}/professional/publish",
        headers=headers,
    )

    assert published.status_code == 200
    payload = published.get_json()[
        "profile"
    ]
    assert payload["isActive"] is True
    assert (
        payload["onboardingCompleted"]
        is True
    )
    assert payload["publishedAt"]

    with app.app_context():
        profile = db.session.scalar(
            select(
                ProfessionalProfile
            ).where(
                ProfessionalProfile.user_id
                == user_id
            )
        )
        assert profile.is_active is True
        assert profile.avatar_url is None
        assert len(profile.portfolio_items) == 0
        assert (
            profile.profile_completion < 100
        )
        assert (
            profile.onboarding_completed
            is True
        )


    public_profile = client.get(
        f"/profissionais/{payload['slug']}"
    )

    assert public_profile.status_code == 200
    html = public_profile.get_data(
        as_text=True
    )
    assert "Experiência profissional" in html
    assert "Studio História" in html


def test_establishment_draft_updates_mobile_auth_context(
    app,
    client,
):
    _, headers = (
        _authenticated_client(
            app,
            email="business-mobile@example.com",
        )
    )

    created = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={
            "name": "Studio Mobile",
            "category": "unhas",
            "city": "Curitiba",
            "state": "PR",
            "description": "Studio especializado em unhas.",
            "phone": "41999999999",
            "neighborhood": "Batel",
        },
    )

    assert created.status_code == 201
    establishment_payload = created.get_json()["establishment"]
    # Existing contract remains untouched for previously installed clients.
    assert establishment_payload["onboardingCompleted"] is False
    assert establishment_payload["isActive"] is False
    assert isinstance(establishment_payload["profileCompletion"], int)
    assert establishment_payload["readiness"] == {
        "percentage": 71,
        "readyToPublish": False,
        "missingRequirements": ["operation_mode", "business_hours_mode"],
    }
    with app.app_context():
        draft = db.session.get(Establishment, int(establishment_payload["id"]))
        assert draft.published_at is None
        assert draft.is_active is False
        assert draft.onboarding_completed is False
        assert draft.operation_mode is None
        assert draft.business_hours_mode is None

    current = client.get(
        "/api/v1/auth/me",
        headers=headers,
    )

    assert current.status_code == 200
    payload = current.get_json()

    assert payload["role"] == "establishment"
    assert payload["businessName"] == "Studio Mobile"
    assert payload["city"] == "Curitiba"
    assert payload["neighborhood"] == "Batel"
    assert payload["profileId"] == (
        created.get_json()[
            "establishment"
        ]["id"]
    )


def test_professional_publication_requirements_separate_optional_media():
    profile = ProfessionalProfile(
        display_name="Marina",
        primary_specialty="Nail Designer",
        specialties_text="Unhas, Estética",
        bio="Atendimento em unhas naturais.",
        city="Curitiba",
        state="PR",
    )
    assert all(profile.publication_requirements.values())
    assert profile.avatar_url is None
    assert profile.cover_url is None
    assert not profile.portfolio_items


def test_professional_publication_requirements_flag_missing_identity_fields():
    profile = ProfessionalProfile(
        display_name="Marina",
        primary_specialty="",
        specialties_text="",
        bio="",
        city="Curitiba",
        state="PR",
    )
    assert profile.publication_requirements["display_name"] is True
    assert profile.publication_requirements["specialty"] is False
    assert profile.publication_requirements["categories"] is False
    assert profile.publication_requirements["bio"] is False


def test_professional_attendance_modalities_roundtrip_and_validation(app, client):
    _, headers = _authenticated_client(app, email="modalities@example.com")
    created = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(
            attendanceModalities=["own_space", "client_location"],
        ),
    )
    assert created.status_code in (200, 201)
    assert set(created.get_json()["profile"]["attendanceModalities"]) == {
        "own_space", "client_location"
    }

    refreshed = client.get(f"{BASE}/professional", headers=headers)
    assert set(refreshed.get_json()["profile"]["attendanceModalities"]) == {
        "own_space", "client_location"
    }

    invalid = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(attendanceModalities=["unsupported"]),
    )
    assert invalid.status_code == 400

    unchanged = client.get(f"{BASE}/professional", headers=headers)
    assert set(unchanged.get_json()["profile"]["attendanceModalities"]) == {
        "own_space", "client_location"
    }


def test_publication_requires_valid_identity_without_media(app, client):
    _, headers = _authenticated_client(app, email="publish-validation@example.com")
    created = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(
            attendanceModalities=["client_location"],
            bio="",
        ),
    )
    assert created.status_code in (200, 201)
    blocked = client.post(f"{BASE}/professional/publish", headers=headers)
    assert blocked.status_code == 409

    updated = client.post(
        f"{BASE}/professional",
        headers=headers,
        json=_professional_payload(attendanceModalities=["client_location"]),
    )
    assert updated.status_code == 200
    published = client.post(f"{BASE}/professional/publish", headers=headers)
    assert published.status_code == 200
    assert published.get_json()["profile"]["isActive"] is True
    assert published.get_json()["profile"]["completion"]["percentage"] < 100


def test_private_professional_services_list_scopes_owner_and_includes_drafts(app, client):
    first_id, first_headers = _authenticated_client(app, email="catalog-first@example.com")
    second_id, second_headers = _authenticated_client(app, email="catalog-second@example.com")

    assert client.get(f"{BASE}/professional/services").status_code == 401
    assert client.get(f"{BASE}/professional/services", headers=first_headers).status_code == 409

    for headers in (first_headers, second_headers):
        created = client.post(
            f"{BASE}/professional",
            headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert created.status_code in (200, 201)

    with app.app_context():
        first = db.session.scalar(select(ProfessionalProfile).where(ProfessionalProfile.user_id == first_id))
        second = db.session.scalar(select(ProfessionalProfile).where(ProfessionalProfile.user_id == second_id))
        db.session.add_all([
            Experience(
                professional_id=first.id, title="Serviço privado",
                slug="servico-privado-catalog-119", category="unhas",
                short_description="Rascunho somente do proprietário",
                regular_price=90, price=75, duration_minutes=60,
                status=ExperienceStatus.DRAFT,
            ),
            Experience(
                professional_id=second.id, title="Serviço de outro profissional",
                slug="servico-outro-catalog-119", category="unhas",
                short_description="Não deve aparecer para o primeiro",
                regular_price=100, price=100, duration_minutes=45,
                status=ExperienceStatus.PUBLISHED,
            ),
        ])
        db.session.commit()

    response = client.get(f"{BASE}/professional/services", headers=first_headers)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Serviço privado"
    assert items[0]["status"] == "draft"
    assert items[0]["price"] == 75.0
    assert items[0]["durationMinutes"] == 60


def test_mobile_service_draft_creation_requires_professional_and_valid_payload(app, client):
    _, headers = _authenticated_client(app, email="draft-pro137@example.com")
    endpoint = f"{BASE}/professional/services"
    valid = {
        "name": "Banho de gel",
        "category": "unhas",
        "shortDescription": "Aplicação profissional",
        "price": 120,
        "regularPrice": 120,
        "durationMinutes": 60,
    }
    assert client.post(endpoint, json=valid).status_code == 401
    assert client.post(endpoint, headers=headers, json=valid).status_code == 409
    profile = client.post(
        f"{BASE}/professional", headers=headers,
        json=_professional_payload(attendanceModalities=["own_space"]),
    )
    assert profile.status_code in (200, 201)
    for changes in [
        {"category": "inexistente"},
        {"price": -1},
        {"durationMinutes": 0},
        {"durationMinutes": True},
        {"price": 200, "regularPrice": 100},
        {"name": " "},
        {"price": "NaN"},
    ]:
        assert client.post(endpoint, headers=headers, json={**valid, **changes}).status_code == 400

    created = client.post(endpoint, headers=headers, json=valid)
    assert created.status_code == 201
    payload = created.get_json()["service"]
    assert payload["status"] == "draft"
    assert payload["title"] == "Banho de gel"
    with app.app_context():
        from app.models.experience import Experience
        item = db.session.get(Experience, payload["id"])
        assert item is not None
        assert item.status == "draft"
        assert item.establishment_id is None
        assert len(item.slots) == 0
    listed = client.get(endpoint, headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == payload["id"] for item in listed.get_json()["items"])


def test_professional_service_edit_keeps_owner_and_publication_state(app, client):
    _, headers = _authenticated_client(app, email="pro-edit-138@example.com")
    _, outsider = _authenticated_client(app, email="outsider-edit-138@example.com")
    for bearer in (headers, outsider):
        created_profile = client.post(
            f"{BASE}/professional", headers=bearer,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert created_profile.status_code in (200, 201)

    payload = {
        "name": "Manicure", "category": "unhas",
        "shortDescription": "Cuidado completo",
        "price": 80, "regularPrice": 80, "durationMinutes": 60,
    }
    result = client.post(f"{BASE}/professional/services", headers=headers, json=payload)
    assert result.status_code == 201
    service_id = result.get_json()["service"]["id"]
    url = f"{BASE}/professional/services/{service_id}"
    assert client.get(url).status_code == 401
    assert client.patch(url, json={"name": "Invasão"}).status_code == 401
    assert client.get(url, headers=outsider).status_code == 404
    assert client.patch(url, headers=outsider, json={"name": "Invasão"}).status_code == 404
    assert client.patch(url, headers=headers, json={"price": 900}).status_code == 400
    assert client.patch(url, headers=headers, json={"status": "published"}).status_code == 400
    assert client.patch(url, headers=headers, json={"durationMinutes": True}).status_code == 400

    changed = client.patch(url, headers=headers, json={
        "name": "Manicure premium", "price": 75, "durationMinutes": 75,
    })
    assert changed.status_code == 200
    assert changed.get_json()["service"]["status"] == "draft"
    detail = client.get(url, headers=headers)
    assert detail.status_code == 200
    assert detail.get_json()["service"]["name"] == "Manicure premium"
    with app.app_context():
        from app.models.experience import Experience, ExperienceStatus
        item = db.session.get(Experience, service_id)
        assert item.slug == "manicure"
        assert item.price == 75
        item.status = ExperienceStatus.PUBLISHED
        db.session.commit()

    assert client.patch(url, headers=headers, json={"name": "Não permitido"}).status_code == 409


def test_mobile_service_status_owner_and_transition_guards(app, client):
    _, owner = _authenticated_client(app, email="status-owner-139@example.com")
    _, other = _authenticated_client(app, email="status-other-139@example.com")
    for headers in (owner, other):
        response = client.post(
            f"{BASE}/professional", headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert response.status_code in (200, 201)

    draft = client.post(f"{BASE}/professional/services", headers=owner, json={
        "name": "Manicure status", "category": "unhas",
        "shortDescription": "Atendimento individual", "price": 90,
        "regularPrice": 90, "durationMinutes": 60,
    })
    assert draft.status_code == 201
    service_id = draft.get_json()["service"]["id"]
    endpoint = f"{BASE}/professional/services/{service_id}/status"

    assert client.post(endpoint, json={"action": "publish"}).status_code == 401
    assert client.post(endpoint, headers=other, json={"action": "publish"}).status_code == 404
    assert client.post(endpoint, headers=owner, json={"action": "pause"}).status_code == 409
    assert client.post(endpoint, headers=owner, json={"action": "delete"}).status_code == 400
    assert client.post(endpoint, headers=owner, json={"action": "publish", "status": "published"}).status_code == 400

    # Publication must use the same eligibility check as web.
    from app.models.experience import ExperienceStatus
    from app.services import admin_catalog_service
    from app.models.experience import Experience
    original = admin_catalog_service.validate_experience_publication
    admin_catalog_service.validate_experience_publication = lambda **kwargs: None
    try:
        published = client.post(endpoint, headers=owner, json={"action": "publish"})
        assert published.status_code == 200
        assert published.get_json()["service"]["status"] == ExperienceStatus.PUBLISHED
        assert client.post(endpoint, headers=owner, json={"action": "publish"}).status_code == 409
        paused = client.post(endpoint, headers=owner, json={"action": "pause"})
        assert paused.status_code == 200
        assert paused.get_json()["service"]["status"] == ExperienceStatus.PAUSED
        assert client.post(endpoint, headers=owner, json={"action": "pause"}).status_code == 409
    finally:
        admin_catalog_service.validate_experience_publication = original
    with app.app_context():
        assert db.session.get(Experience, service_id).status == ExperienceStatus.PAUSED


def test_service_establishment_requires_active_membership_and_prevents_slot_reassignment(app, client):
    _, owner = _authenticated_client(app, email="association-owner-140@example.com")
    _, stranger = _authenticated_client(app, email="association-stranger-140@example.com")
    for headers in (owner, stranger):
        response = client.post(
            f"{BASE}/professional", headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert response.status_code in (200, 201)

    draft_data = {
        "name": "Tratamento facial", "category": "estetica",
        "shortDescription": "Tratamento básico", "price": 80,
        "regularPrice": 80, "durationMinutes": 60,
    }
    with app.app_context():
        from app.models.user import User
        profiles = db.session.scalars(
            select(ProfessionalProfile).join(User).where(
                User.email.in_(["association-owner-140@example.com", "association-stranger-140@example.com"])
            )
        ).all()
        owner_profile = next(p for p in profiles if p.user.email == "association-owner-140@example.com")
        establishment = Establishment(
            name="Estúdio Teste 140", slug="estudio-teste-140",
            category="estetica", is_active=True,
        )
        db.session.add(establishment)
        db.session.flush()
        establishment_id = establishment.id
        db.session.add(ProfessionalEstablishmentMembership(
            professional_id=owner_profile.id,
            establishment_id=establishment_id,
            status=MembershipStatus.PENDING,
        ))
        db.session.commit()

    options_url = f"{BASE}/professional/service-establishments"
    assert client.get(options_url).status_code == 401
    assert client.get(options_url, headers=stranger).get_json()["items"] == []
    assert client.get(options_url, headers=owner).get_json()["items"] == []
    assert client.post(
        f"{BASE}/professional/services", headers=owner,
        json={**draft_data, "establishmentId": establishment_id},
    ).status_code == 403

    with app.app_context():
        membership = db.session.scalar(select(ProfessionalEstablishmentMembership).where(
            ProfessionalEstablishmentMembership.establishment_id == establishment_id,
        ))
        membership.status = MembershipStatus.ACTIVE
        db.session.commit()

    options = client.get(options_url, headers=owner)
    assert options.status_code == 200
    assert options.get_json()["items"][0]["id"] == establishment_id
    created = client.post(
        f"{BASE}/professional/services", headers=owner,
        json={**draft_data, "establishmentId": establishment_id},
    )
    assert created.status_code == 201
    service_id = created.get_json()["service"]["id"]
    detail_url = f"{BASE}/professional/services/{service_id}"
    assert client.get(detail_url, headers=owner).get_json()["service"]["establishmentId"] == establishment_id
    assert client.patch(detail_url, headers=stranger, json={"establishmentId": None}).status_code == 404
    assert client.patch(detail_url, headers=owner, json={"establishmentId": None}).status_code == 200
    assert client.get(detail_url, headers=owner).get_json()["service"]["establishmentId"] is None


def test_mobile_service_availability_is_private_and_uses_validation(app, client):
    _, owner = _authenticated_client(app, email="availability-owner-141@example.com")
    _, stranger = _authenticated_client(app, email="availability-other-141@example.com")
    for headers in (owner, stranger):
        response = client.post(
            f"{BASE}/professional", headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert response.status_code in (200, 201)
    created = client.post(f"{BASE}/professional/services", headers=owner, json={
        "name": "Serviço de agenda", "category": "unhas",
        "shortDescription": "Procedimento individual", "price": 75,
        "regularPrice": 75, "durationMinutes": 60,
    })
    assert created.status_code == 201
    id_ = created.get_json()["service"]["id"]
    url = f"{BASE}/professional/services/{id_}/availability"
    assert client.get(url).status_code == 401
    assert client.post(url, json={"date": "2026-11-05", "time": "14:30"}).status_code == 401
    assert client.get(url, headers=stranger).status_code == 404
    assert client.post(url, headers=stranger, json={"date": "2026-11-05", "time": "14:30"}).status_code == 404
    listing = client.get(url, headers=owner)
    assert listing.status_code == 200
    assert listing.get_json()["items"] == []
    assert client.post(url, headers=owner, json={"time": "14:30"}).status_code == 400
    assert client.post(url, headers=owner, json={"date": "2026-11-05", "time": 1430}).status_code == 400
    # Drafts are never eligible to open slots, even with valid dates and times.
    blocked = client.post(url, headers=owner, json={
        "date": "2026-11-05", "time": "14:30",
    })
    assert blocked.status_code == 409
    assert blocked.get_json()["error"]["code"] == "availability_invalid"


def test_mobile_slot_status_requires_owner_and_available_state(app, client):
    _, owner = _authenticated_client(app, email="slot-status-owner-142@example.com")
    _, outsider = _authenticated_client(app, email="slot-status-other-142@example.com")
    for headers in (owner, outsider):
        response = client.post(
            f"{BASE}/professional", headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert response.status_code in (200, 201)
    draft = client.post(f"{BASE}/professional/services", headers=owner, json={
        "name": "Slot privado", "category": "unhas",
        "shortDescription": "Atendimento", "price": 90,
        "regularPrice": 90, "durationMinutes": 60,
    })
    assert draft.status_code == 201
    service_id = draft.get_json()["service"]["id"]
    url = f"{BASE}/professional/services/{service_id}/availability/99999/status"
    assert client.post(url, json={"action": "block"}).status_code == 401
    assert client.post(url, headers=outsider, json={"action": "block"}).status_code == 404
    assert client.post(url, headers=owner, json={"action": "block"}).status_code == 404


def test_mobile_weekly_schedule_creation_requires_owner_and_valid_date(app, client):
    _, owner = _authenticated_client(app, email="weekly-slots-owner-143@example.com")
    _, outsider = _authenticated_client(app, email="weekly-slots-outsider-143@example.com")
    for headers in (owner, outsider):
        response = client.post(
            f"{BASE}/professional", headers=headers,
            json=_professional_payload(attendanceModalities=["own_space"]),
        )
        assert response.status_code in (200, 201)
    created = client.post(f"{BASE}/professional/services", headers=owner, json={
        "name": "Serviço semanal", "category": "unhas",
        "shortDescription": "Procedimento de teste", "price": 80,
        "regularPrice": 80, "durationMinutes": 60,
    })
    assert created.status_code == 201
    service_id = created.get_json()["service"]["id"]
    endpoint = f"{BASE}/professional/services/{service_id}/availability/from-schedule"
    assert client.post(endpoint, json={"date": "2026-11-05"}).status_code == 401
    assert client.post(endpoint, headers=outsider, json={"date": "2026-11-05"}).status_code == 404
    assert client.post(endpoint, headers=owner, json={"date": 123}).status_code == 400
    assert client.post(endpoint, headers=owner, json={"date": "2026-11-05", "time": "10:00"}).status_code == 400
    result = client.post(endpoint, headers=owner, json={"date": "2026-11-05"})
    assert result.status_code == 409
    assert result.get_json()["error"]["code"] == "availability_invalid"


def test_mobile_weekly_schedule_rejects_invalid_and_persists_valid_days(app, client):
    _, owner = _authenticated_client(app, email="weekly-editor-144@example.com")
    url = f"{BASE}/professional/weekly-schedule"
    assert client.get(url).status_code == 401
    assert client.put(url, json={"days": []}).status_code == 401
    assert client.get(url, headers=owner).status_code == 409
    profile = client.post(f"{BASE}/professional", headers=owner,
        json=_professional_payload(attendanceModalities=["own_space"]))
    assert profile.status_code in (200, 201)
    initial = client.get(url, headers=owner)
    assert initial.status_code == 200
    days = initial.get_json()["days"]
    assert len(days) == 7
    assert client.put(url, headers=owner, json={"days": days[:-1]}).status_code == 400
    duplicate = [dict(day) for day in days]
    duplicate[1]["weekday"] = 0
    assert client.put(url, headers=owner, json={"days": duplicate}).status_code == 400
    invalid = [dict(day) for day in days]
    invalid[0].update(enabled=True, start="18:00", end="09:00")
    assert client.put(url, headers=owner, json={"days": invalid}).status_code == 400
    changed = [dict(day) for day in days]
    for day in changed:
        day["enabled"] = day["weekday"] == 0
    changed[0].update(start="09:00", end="17:00", break_enabled=True,
        break_start="12:00", break_end="13:00")
    saved = client.put(url, headers=owner, json={"days": changed})
    assert saved.status_code == 200
    result = client.get(url, headers=owner).get_json()["days"]
    assert result[0]["enabled"] is True
    assert result[0]["break_enabled"] is True
    assert result[1]["enabled"] is False


def test_mobile_schedule_to_slots_block_reopen_and_overlap(app, client):
    """End-to-end API contract: saved shift -> real availability -> safe state changes."""
    from datetime import timedelta
    from app.models.booking import ExperienceSlot, SlotStatus
    from app.services.time_service import utcnow

    _, owner = _authenticated_client(app, email="agenda-journey-145@example.com")
    profile_response = client.post(
        f"{BASE}/professional", headers=owner,
        json=_professional_payload(attendanceModalities=["own_space"]),
    )
    assert profile_response.status_code in (200, 201)

    draft = client.post(f"{BASE}/professional/services", headers=owner, json={
        "name": "Jornada integrada", "category": "unhas",
        "shortDescription": "Sessão de uma hora", "price": 90,
        "regularPrice": 90, "durationMinutes": 60,
    })
    assert draft.status_code == 201
    service_id = draft.get_json()["service"]["id"]
    with app.app_context():
        item = db.session.get(Experience, service_id)
        item.status = ExperienceStatus.PUBLISHED
        db.session.commit()

    selected_date = (utcnow() + timedelta(days=35)).date()
    weekday = selected_date.weekday()
    schedule_url = f"{BASE}/professional/weekly-schedule"
    read_schedule = client.get(schedule_url, headers=owner)
    assert read_schedule.status_code == 200
    days = read_schedule.get_json()["days"]
    for day in days:
        day["enabled"] = day["weekday"] == weekday
    selected = days[weekday]
    selected.update(start="09:00", end="12:00", break_enabled=True,
                    break_start="10:00", break_end="11:00")
    saved = client.put(schedule_url, headers=owner, json={"days": days})
    assert saved.status_code == 200, saved.get_json()

    availability_url = f"{BASE}/professional/services/{service_id}/availability"
    generated = client.post(
        availability_url + "/from-schedule",
        headers=owner, json={"date": selected_date.isoformat()},
    )
    assert generated.status_code == 201, generated.get_json()
    assert generated.get_json()["createdCount"] == 2

    listing = client.get(availability_url, headers=owner)
    assert listing.status_code == 200
    slots = listing.get_json()["items"]
    assert len(slots) == 2
    assert all(slot["status"] == SlotStatus.AVAILABLE for slot in slots)

    # Reopening never creates a second slot and cannot circumvent overlap checks.
    slot_id = slots[0]["id"]
    status_url = availability_url + f"/{slot_id}/status"
    blocked = client.post(status_url, headers=owner, json={"action": "block"})
    assert blocked.status_code == 200
    assert blocked.get_json()["slot"]["status"] == SlotStatus.BLOCKED_MANUAL
    assert client.post(status_url, headers=owner, json={"action": "block"}).status_code == 409
    reopened = client.post(status_url, headers=owner, json={"action": "reopen"})
    assert reopened.status_code == 200
    assert reopened.get_json()["slot"]["status"] == SlotStatus.AVAILABLE
    assert client.post(status_url, headers=owner, json={"action": "reopen"}).status_code == 409

    conflict = client.post(
        availability_url, headers=owner,
        json={"date": selected_date.isoformat(), "time": "09:00"},
    )
    assert conflict.status_code == 409
    with app.app_context():
        assert db.session.scalar(
            select(func.count(ExperienceSlot.id)).where(
                ExperienceSlot.experience_id == service_id,
            )
        ) == 2


def test_business_readiness_payload_is_additive_and_preserves_published_legacy(app):
    from app.routes.api_onboarding import _establishment_payload

    with app.app_context():
        legacy = Establishment(
            name="Empresa histórica",
            slug="empresa-historica",
            category="salao",
            description="Salão já publicado antes da nova configuração.",
            city="Curitiba",
            state="PR",
            phone="41999999999",
            address_line1="Rua Comercial, 100",
            onboarding_completed=True,
            published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            is_active=True,
        )
        db.session.add(legacy)
        db.session.commit()

        original_state = (legacy.published_at, legacy.onboarding_completed, legacy.is_active)
        payload = _establishment_payload(legacy)

        # Legacy fields keep their original semantics and types.
        assert payload["onboardingCompleted"] is True
        assert payload["isActive"] is True
        assert payload["profileCompletion"] == legacy.profile_completion
        assert payload["readiness"]["readyToPublish"] is False
        assert set(payload["readiness"]["missingRequirements"]) == {
            "operation_mode", "business_hours_mode",
        }
        assert 0 <= payload["readiness"]["percentage"] < 100
        assert (legacy.published_at, legacy.onboarding_completed, legacy.is_active) == original_state
        assert not db.session.is_modified(legacy)


def test_business_readiness_payload_can_be_complete_without_publication(app):
    from app.routes.api_onboarding import _establishment_payload

    with app.app_context():
        draft = Establishment(
            name="Studio domiciliar",
            slug="studio-domiciliar",
            description="Atendimento domiciliar a clientes em Curitiba.",
            category="salao",
            city="Curitiba",
            state="PR",
            phone="41999999999",
            operation_mode="mobile",
            business_hours_mode="scheduled",
            address_line1=None,
            published_at=None,
            onboarding_completed=False,
            is_active=False,
        )
        payload = _establishment_payload(draft)
        assert payload["readiness"] == {
            "percentage": 100,
            "readyToPublish": True,
            "missingRequirements": [],
        }
        assert payload["onboardingCompleted"] is False
        assert payload["isActive"] is False
        assert draft.published_at is None
        assert draft.onboarding_completed is False



BUSINESS_DRAFT_INPUT = {
    "name": "Studio Contrato",
    "category": "unhas",
    "city": "Curitiba",
    "state": "PR",
    "description": "Serviços de beleza em atendimento personalizado.",
    "phone": "41999999999",
}


def test_business_draft_accepts_valid_optional_fields_and_stays_private(app, client):
    _, headers = _authenticated_client(app, email="business-contract@example.com")
    data = {
        **BUSINESS_DRAFT_INPUT,
        "operationMode": "physical",
        "businessHoursMode": "fixed_hours",
        "businessHours": {"monday": [{"start": "09:00", "end": "18:00"}]},
        "addressLine1": "Rua Comercial, 100",
        "commercialEmail": "Contato@Studio.Example",
    }
    response = client.post(f"{BASE}/establishment", headers=headers, json=data)
    assert response.status_code == 201
    obj = response.get_json()["establishment"]
    assert obj["operationMode"] == "physical"
    assert obj["businessHoursMode"] == "fixed_hours"
    assert obj["businessHours"] == data["businessHours"]
    assert obj["addressLine1"] == "Rua Comercial, 100"
    assert obj["commercialEmail"] == "contato@studio.example"
    assert obj["readiness"]["readyToPublish"] is True
    assert obj["onboardingCompleted"] is False
    assert obj["isActive"] is False
    with app.app_context():
        stored = db.session.get(Establishment, int(obj["id"]))
        assert stored.published_at is None
        assert stored.onboarding_completed is False
        assert stored.is_active is False

    # A retry using an older mobile client must not erase the new fields.
    retry = client.post(
        f"{BASE}/establishment", headers=headers, json=BUSINESS_DRAFT_INPUT
    )
    assert retry.status_code == 201
    previous = retry.get_json()["establishment"]
    assert previous["id"] == obj["id"]
    assert previous["operationMode"] == "physical"
    assert previous["businessHoursMode"] == "fixed_hours"
    assert previous["businessHours"] == data["businessHours"]
    assert previous["commercialEmail"] == "contato@studio.example"
    assert previous["addressLine1"] == "Rua Comercial, 100"


@pytest.mark.parametrize("changes", [
    {"operationMode": "invalid"},
    {"operationMode": ["mobile"]},
    {"businessHoursMode": "always"},
    {"businessHours": [{"monday": []}]},
    {"businessHours": {"monday": [{"start": "12:00", "end": "09:00"}]}},
    {"businessHours": {"monday": [{"start": "09:00", "end": "12:00"},
                                  {"start": "11:00", "end": "14:00"}]}},
    {"businessHours": {"monday": [{"start": "09:00", "end": "10:00"}] * 5}},
    {"businessHours": {"unknown": [{"start": "09:00", "end": "10:00"}]}},
    {"addressLine1": ["endereco"]},
    {"commercialEmail": "not-an-email"},
    {"commercialEmail": ["not-an-email"]},
])
def test_business_draft_rejects_invalid_optional_input_without_inserting(
    app, client, changes
):
    _, headers = _authenticated_client(app, email="business-invalid@example.com")
    response = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={**BUSINESS_DRAFT_INPUT, **changes},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_onboarding_data"
    with app.app_context():
        assert db.session.scalar(
            select(func.count(Establishment.id))
        ) == 0


def test_business_draft_allows_partial_details_without_publication(app, client):
    _, headers = _authenticated_client(app, email="business-partial@example.com")
    response = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={
            **BUSINESS_DRAFT_INPUT,
            "operationMode": "hybrid",
            "businessHoursMode": "fixed_hours",
        },
    )
    assert response.status_code == 201
    business = response.get_json()["establishment"]
    assert business["businessHours"] is None
    assert set(business["readiness"]["missingRequirements"]) == {
        "business_address", "business_hours",
    }
    assert business["isActive"] is False


def test_business_draft_update_keeps_legacy_publication_flags(app, client):
    _, headers = _authenticated_client(app, email="business-legacy@example.com")
    first = client.post(
        f"{BASE}/establishment", headers=headers, json=BUSINESS_DRAFT_INPUT
    )
    assert first.status_code == 201
    establishment_id = int(first.get_json()["establishment"]["id"])
    from datetime import datetime, timezone
    when = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with app.app_context():
        business = db.session.get(Establishment, establishment_id)
        business.published_at = when
        business.onboarding_completed = True
        business.is_active = True
        db.session.commit()

    updated = client.post(
        f"{BASE}/establishment",
        headers=headers,
        json={**BUSINESS_DRAFT_INPUT, "operationMode": "mobile"},
    )
    assert updated.status_code == 201
    data = updated.get_json()["establishment"]
    assert data["id"] == str(establishment_id)
    assert data["operationMode"] == "mobile"
    assert data["onboardingCompleted"] is True
    assert data["isActive"] is True
    with app.app_context():
        business = db.session.get(Establishment, establishment_id)
        assert business.published_at == when
        assert business.onboarding_completed is True
        assert business.is_active is True


def test_business_draft_rejects_unauthenticated_write(app, client):
    response = client.post(
        f"{BASE}/establishment",
        json={**BUSINESS_DRAFT_INPUT, "operationMode": "physical"},
    )
    assert response.status_code == 401
    with app.app_context():
        assert db.session.scalar(select(func.count(Establishment.id))) == 0
