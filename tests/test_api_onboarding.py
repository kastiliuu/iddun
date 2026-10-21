from datetime import date

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
