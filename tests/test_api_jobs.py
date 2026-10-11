from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.job import (
    JobApplicationStatus,
    JobPostStatus,
)
from app.models.professional import (
    ProfessionalProfile,
)
from app.models.user import (
    User,
    UserRole,
)
from app.services.api_auth import (
    issue_session,
)


def _user(
    email,
    *,
    professional=False,
):
    user = User(
        name=email.split("@")[0],
        email=email,
        role=(
            UserRole.PROFESSIONAL
            if professional
            else UserRole.CLIENT
        ),
    )
    user.set_password(
        "senha-forte-123"
    )
    db.session.add(user)
    db.session.flush()

    if professional:
        profile = ProfessionalProfile(
            user_id=user.id,
            display_name=(
                f"Profissional {user.name}"
            ),
            slug=f"job-pro-{user.id}",
            primary_specialty=(
                "Cabeleireiro"
            ),
            city="Curitiba",
            state="PR",
            is_active=True,
        )
        db.session.add(profile)
        db.session.flush()

    return user


def _establishment(slug):
    establishment = Establishment(
        name=f"Studio {slug}",
        slug=slug,
        city="Curitiba",
        state="PR",
        neighborhood="Batel",
        is_active=True,
    )
    db.session.add(
        establishment
    )
    db.session.flush()

    return establishment


def _grant_access(
    user,
    establishment,
    role=EstablishmentAccessRole.OWNER,
):
    access = EstablishmentUserAccess(
        user_id=user.id,
        establishment_id=(
            establishment.id
        ),
        role=role,
        status=(
            EstablishmentAccessStatus.ACTIVE
        ),
    )
    db.session.add(access)
    db.session.flush()

    return access


def _login(
    client,
    user_id,
):
    with client.session_transaction() as session:
        session["_user_id"] = str(
            user_id
        )
        session["_fresh"] = True


def _bearer(
    token,
):
    return {
        "Authorization":
            f"Bearer {token}"
    }


def _create_job(
    client,
    establishment_slug,
    *,
    token=None,
):
    return client.post(
        (
            f"/api/v1/establishments/"
            f"{establishment_slug}/jobs"
        ),
        json={
            "title":
                "Cabeleireiro(a)",
            "specialty":
                "Cabelo",
            "description":
                "Buscamos profissional para integrar a equipe.",
            "employmentType":
                "parceria",
            "compensationText":
                "A combinar",
        },
        headers=(
            _bearer(token)
            if token
            else None
        ),
    )


def test_jobs_management_requires_authentication(
    app,
    client,
):
    with app.app_context():
        establishment = (
            _establishment(
                "jobs-auth"
            )
        )
        db.session.commit()
        slug = (
            establishment.slug
        )

    response = client.get(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs"
        )
    )

    assert response.status_code == 401
    assert response.get_json()[
        "error"
    ]["code"] == (
        "authentication_required"
    )


def test_owner_can_create_publish_and_list_public_job(
    app,
    client,
):
    with app.app_context():
        owner = _user(
            "jobs-owner@example.com"
        )
        establishment = (
            _establishment(
                "jobs-studio"
            )
        )
        _grant_access(
            owner,
            establishment,
        )
        db.session.commit()

        owner_token = (
            issue_session(
                owner
            ).access_token
        )
        slug = (
            establishment.slug
        )

    created = _create_job(
        client,
        slug,
        token=owner_token,
    )

    assert created.status_code == 201
    job = created.get_json()[
        "job"
    ]
    assert job["status"] == (
        JobPostStatus.DRAFT
    )
    job_id = int(job["id"])

    public_before = client.get(
        f"/api/v1/jobs/{job_id}"
    )
    assert (
        public_before.status_code
        == 404
    )

    published = client.put(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs/{job_id}/publish"
        ),
        headers=_bearer(
            owner_token
        ),
    )

    assert published.status_code == 200
    assert published.get_json()[
        "job"
    ]["status"] == (
        JobPostStatus.PUBLISHED
    )

    listing = client.get(
        "/api/v1/jobs?city=Curitiba"
    )

    assert listing.status_code == 200
    payload = listing.get_json()
    assert payload[
        "pagination"
    ]["total"] == 1
    assert payload["items"][0][
        "title"
    ] == "Cabeleireiro(a)"
    assert payload["items"][0][
        "establishment"
    ]["routeId"] == slug


def test_user_without_establishment_access_cannot_create_job(
    app,
    client,
):
    with app.app_context():
        user = _user(
            "jobs-no-access@example.com"
        )
        establishment = (
            _establishment(
                "jobs-private"
            )
        )
        db.session.commit()

        user_token = (
            issue_session(
                user
            ).access_token
        )
        slug = (
            establishment.slug
        )

    response = _create_job(
        client,
        slug,
        token=user_token,
    )

    assert response.status_code == 400
    assert response.get_json()[
        "error"
    ]["code"] == (
        "invalid_job"
    )


def test_professional_can_apply_once_and_withdraw(
    app,
    client,
):
    with app.app_context():
        owner = _user(
            "jobs-apply-owner@example.com"
        )
        professional = _user(
            "jobs-pro@example.com",
            professional=True,
        )
        establishment = (
            _establishment(
                "jobs-apply"
            )
        )
        _grant_access(
            owner,
            establishment,
        )
        db.session.commit()

        owner_token = (
            issue_session(
                owner
            ).access_token
        )
        professional_token = (
            issue_session(
                professional
            ).access_token
        )
        slug = (
            establishment.slug
        )

    created = _create_job(
        client,
        slug,
        token=owner_token,
    )
    job_id = int(
        created.get_json()[
            "job"
        ]["id"]
    )

    published = client.put(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs/{job_id}/publish"
        ),
        headers=_bearer(
            owner_token
        ),
    )
    assert published.status_code == 200, (
        published.get_json()
    )

    applied = client.post(
        (
            f"/api/v1/jobs/"
            f"{job_id}/apply"
        ),
        json={
            "message":
                "Tenho experiência na área.",
        },
        headers=_bearer(
            professional_token
        ),
    )

    assert applied.status_code == 201, (
        applied.get_json()
    )
    assert applied.get_json()[
        "application"
    ]["status"] == (
        JobApplicationStatus.SUBMITTED
    )

    duplicate = client.post(
        (
            f"/api/v1/jobs/"
            f"{job_id}/apply"
        ),
        json={},
        headers=_bearer(
            professional_token
        ),
    )

    assert duplicate.status_code == 409

    mine = client.get(
        "/api/v1/jobs/applications/mine",
        headers=_bearer(
            professional_token
        ),
    )
    assert mine.status_code == 200
    assert len(
        mine.get_json()[
            "items"
        ]
    ) == 1

    withdrawn = client.delete(
        (
            f"/api/v1/jobs/"
            f"{job_id}/apply"
        ),
        headers=_bearer(
            professional_token
        ),
    )

    assert withdrawn.status_code == 200
    assert withdrawn.get_json()[
        "application"
    ]["status"] == (
        JobApplicationStatus.WITHDRAWN
    )


def test_owner_can_view_submitted_applications_and_close_job(
    app,
    client,
):
    with app.app_context():
        owner = _user(
            "jobs-candidates-owner@example.com"
        )
        professional = _user(
            "jobs-candidate@example.com",
            professional=True,
        )
        establishment = (
            _establishment(
                "jobs-candidates"
            )
        )
        _grant_access(
            owner,
            establishment,
        )
        db.session.commit()

        owner_token = (
            issue_session(
                owner
            ).access_token
        )
        professional_token = (
            issue_session(
                professional
            ).access_token
        )
        slug = (
            establishment.slug
        )

    created = _create_job(
        client,
        slug,
        token=owner_token,
    )
    job_id = int(
        created.get_json()[
            "job"
        ]["id"]
    )
    published = client.put(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs/{job_id}/publish"
        ),
        headers=_bearer(
            owner_token
        ),
    )
    assert published.status_code == 200, (
        published.get_json()
    )

    applied = client.post(
        f"/api/v1/jobs/{job_id}/apply",
        json={},
        headers=_bearer(
            professional_token
        ),
    )
    assert applied.status_code == 201, (
        applied.get_json()
    )

    candidates = client.get(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs/{job_id}/applications"
        ),
        headers=_bearer(
            owner_token
        ),
    )

    assert candidates.status_code == 200
    items = candidates.get_json()[
        "items"
    ]
    assert len(items) == 1
    assert items[0][
        "professional"
    ]["routeId"].startswith(
        "job-pro-"
    )

    closed = client.put(
        (
            f"/api/v1/establishments/"
            f"{slug}/jobs/{job_id}/close"
        ),
        headers=_bearer(
            owner_token
        ),
    )

    assert closed.status_code == 200
    assert closed.get_json()[
        "job"
    ]["status"] == (
        JobPostStatus.CLOSED
    )

    hidden = client.get(
        f"/api/v1/jobs/{job_id}"
    )
    assert hidden.status_code == 404


def test_job_applications_are_private_to_authorized_establishment(
    app,
    client,
):
    """Candidate data must not leak across tenants or to applicants."""
    with app.app_context():
        owner_a = _user("qa-jobs-owner-a@example.com")
        owner_b = _user("qa-jobs-owner-b@example.com")
        candidate = _user(
            "qa-jobs-candidate@example.com",
            professional=True,
        )
        business_a = _establishment("qa-jobs-business-a")
        business_b = _establishment("qa-jobs-business-b")
        access_a = _grant_access(owner_a, business_a)
        _grant_access(owner_b, business_b)
        db.session.commit()
        owner_a_token = issue_session(owner_a).access_token
        owner_b_token = issue_session(owner_b).access_token
        candidate_token = issue_session(candidate).access_token
        slug_a, slug_b = business_a.slug, business_b.slug
        access_a_id = access_a.id

    created = _create_job(client, slug_a, token=owner_a_token)
    assert created.status_code == 201, created.get_json()
    job_id = int(created.get_json()["job"]["id"])
    publish = client.put(
        f"/api/v1/establishments/{slug_a}/jobs/{job_id}/publish",
        headers=_bearer(owner_a_token),
    )
    assert publish.status_code == 200, publish.get_json()
    applied = client.post(
        f"/api/v1/jobs/{job_id}/apply",
        json={"message": "Private QA candidate details"},
        headers=_bearer(candidate_token),
    )
    assert applied.status_code == 201, applied.get_json()

    endpoint_a = (
        f"/api/v1/establishments/{slug_a}/jobs/"
        f"{job_id}/applications"
    )
    endpoint_b = (
        f"/api/v1/establishments/{slug_b}/jobs/"
        f"{job_id}/applications"
    )
    allowed = client.get(endpoint_a, headers=_bearer(owner_a_token))
    assert allowed.status_code == 200
    assert len(allowed.get_json()["items"]) == 1
    assert "private" in allowed.headers.get("Cache-Control", "").lower()
    assert "no-store" in allowed.headers.get("Cache-Control", "").lower()

    # All denied requests must exclude applicant data entirely.
    for endpoint, token in (
        (endpoint_a, owner_b_token),
        (endpoint_b, owner_b_token),
        (endpoint_a, candidate_token),
    ):
        denied = client.get(endpoint, headers=_bearer(token))
        assert denied.status_code == 403
        assert "Private QA candidate details" not in denied.get_data(
            as_text=True
        )
        assert "qa-jobs-candidate" not in denied.get_data(
            as_text=True
        )

    with app.app_context():
        access = db.session.get(EstablishmentUserAccess, access_a_id)
        access.status = EstablishmentAccessStatus.INACTIVE
        db.session.commit()

    revoked = client.get(endpoint_a, headers=_bearer(owner_a_token))
    assert revoked.status_code == 403
    assert "Private QA candidate details" not in revoked.get_data(
        as_text=True
    )
