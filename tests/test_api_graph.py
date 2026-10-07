from decimal import Decimal

from sqlalchemy import func, select

from app.extensions import db
from app.models.beauty_graph import (
    Follow,
    Save,
)
from app.models.establishment import Establishment
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.profile import ClientProfile
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.user import User, UserRole
from app.services.api_auth import issue_session


BASE = "/api/v1/graph"


def _account(
    app,
    *,
    email,
):
    with app.app_context():
        user = User(
            name="Cliente Beauty Graph",
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
                    "Bearer "
                    f"{tokens.access_token}"
                )
            },
        )


def _catalog(app):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Marina Graph",
            slug="marina-graph",
            primary_specialty="Hair Stylist",
            bio="Perfil público para testes.",
            city="Curitiba",
            state="PR",
            avatar_url="uploads/avatar.jpg",
            is_active=True,
        )

        establishment = Establishment(
            name="Studio Graph",
            slug="studio-graph",
            description="Studio público.",
            category="salao",
            city="Curitiba",
            state="PR",
            is_active=True,
        )

        db.session.add_all(
            [
                professional,
                establishment,
            ]
        )
        db.session.flush()

        portfolio = ProfessionalPortfolioItem(
            professional_id=professional.id,
            image_url=(
                "uploads/professionals/"
                "portfolio/work.jpg"
            ),
            sort_order=0,
        )

        experience = Experience(
            professional_id=professional.id,
            establishment_id=establishment.id,
            title="Corte Beauty Graph",
            slug="corte-beauty-graph",
            category="cabelo",
            short_description="Corte completo.",
            regular_price=Decimal("150.00"),
            price=Decimal("120.00"),
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )

        db.session.add_all(
            [
                portfolio,
                experience,
            ]
        )
        db.session.commit()

        return {
            "professional": professional.id,
            "establishment": establishment.id,
            "experience": experience.id,
            "portfolioItem": portfolio.id,
        }


def test_graph_requires_authentication(
    client,
):
    response = client.get(BASE)

    assert response.status_code == 401
    assert (
        response.get_json()[
            "error"
        ]["code"]
        == "authentication_required"
    )


def test_follow_professional_and_establishment_is_persisted_and_idempotent(
    app,
    client,
):
    user_id, headers = _account(
        app,
        email="follow@example.com",
    )
    catalog = _catalog(app)

    professional_url = (
        f"{BASE}/follows/"
        "professional/"
        f"{catalog['professional']}"
    )
    establishment_url = (
        f"{BASE}/follows/"
        "establishment/"
        f"{catalog['establishment']}"
    )

    first = client.put(
        professional_url,
        headers=headers,
    )
    second = client.put(
        professional_url,
        headers=headers,
    )
    establishment = client.put(
        establishment_url,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert establishment.status_code == 200

    state = client.get(
        BASE,
        headers=headers,
    )

    assert state.status_code == 200
    assert state.get_json()["follows"] == [
        {
            "targetType": "professional",
            "targetId": catalog[
                "professional"
            ],
        },
        {
            "targetType": "establishment",
            "targetId": catalog[
                "establishment"
            ],
        },
    ]

    with app.app_context():
        count = db.session.scalar(
            select(func.count())
            .select_from(Follow)
            .where(
                Follow.user_id
                == user_id
            )
        )

        assert count == 2


def test_save_targets_keep_follow_and_save_semantics_separate(
    app,
    client,
):
    user_id, headers = _account(
        app,
        email="save@example.com",
    )
    catalog = _catalog(app)

    references = [
        (
            "professional",
            catalog[
                "professional"
            ],
        ),
        (
            "establishment",
            catalog[
                "establishment"
            ],
        ),
        (
            "experience",
            catalog[
                "experience"
            ],
        ),
        (
            "portfolio_item",
            catalog[
                "portfolioItem"
            ],
        ),
    ]

    for (
        target_type,
        target_id,
    ) in references:
        response = client.put(
            (
                f"{BASE}/saves/"
                f"{target_type}/"
                f"{target_id}"
            ),
            headers=headers,
        )

        assert (
            response.status_code
            == 200
        )

    state = client.get(
        BASE,
        headers=headers,
    ).get_json()

    assert state["follows"] == []
    assert len(
        state["saves"]
    ) == 4

    with app.app_context():
        assert db.session.scalar(
            select(func.count())
            .select_from(Save)
            .where(
                Save.user_id
                == user_id
            )
        ) == 4


def test_graph_is_isolated_by_account_and_delete_only_changes_owner(
    app,
    client,
):
    _, first_headers = _account(
        app,
        email="first-graph@example.com",
    )
    _, second_headers = _account(
        app,
        email="second-graph@example.com",
    )
    catalog = _catalog(app)

    url = (
        f"{BASE}/follows/"
        "professional/"
        f"{catalog['professional']}"
    )

    assert client.put(
        url,
        headers=first_headers,
    ).status_code == 200

    assert client.get(
        BASE,
        headers=second_headers,
    ).get_json()["follows"] == []

    removed = client.delete(
        url,
        headers=second_headers,
    )

    assert removed.status_code == 200
    assert (
        removed.get_json()[
            "removed"
        ]
        is False
    )

    assert len(
        client.get(
            BASE,
            headers=first_headers,
        ).get_json()[
            "follows"
        ]
    ) == 1


def test_reconcile_unions_local_state_with_existing_account_state(
    app,
    client,
):
    _, headers = _account(
        app,
        email="reconcile@example.com",
    )
    catalog = _catalog(app)

    existing = client.put(
        (
            f"{BASE}/follows/"
            "professional/"
            f"{catalog['professional']}"
        ),
        headers=headers,
    )

    assert existing.status_code == 200

    reconciled = client.post(
        f"{BASE}/reconcile",
        headers=headers,
        json={
            "follows": [
                {
                    "targetType":
                        "establishment",
                    "targetId":
                        catalog[
                            "establishment"
                        ],
                }
            ],
            "saves": [
                {
                    "targetType":
                        "experience",
                    "targetId":
                        catalog[
                            "experience"
                        ],
                },
                {
                    "targetType":
                        "portfolio_item",
                    "targetId":
                        catalog[
                            "portfolioItem"
                        ],
                },
            ],
        },
    )

    assert reconciled.status_code == 200

    payload = reconciled.get_json()

    assert len(
        payload["state"][
            "follows"
        ]
    ) == 2
    assert len(
        payload["state"][
            "saves"
        ]
    ) == 2
    assert (
        payload["rejected"]
        == {
            "follows": [],
            "saves": [],
        }
    )


def test_reconcile_reports_unavailable_targets_without_losing_valid_state(
    app,
    client,
):
    _, headers = _account(
        app,
        email="rejected-graph@example.com",
    )
    catalog = _catalog(app)

    reconciled = client.post(
        f"{BASE}/reconcile",
        headers=headers,
        json={
            "follows": [
                {
                    "targetType":
                        "professional",
                    "targetId":
                        catalog[
                            "professional"
                        ],
                },
                {
                    "targetType":
                        "professional",
                    "targetId":
                        999999,
                },
            ],
            "saves": [],
        },
    )

    assert reconciled.status_code == 200

    payload = reconciled.get_json()

    assert len(
        payload["state"][
            "follows"
        ]
    ) == 1
    assert payload[
        "rejected"
    ]["follows"] == [
        {
            "targetType":
                "professional",
            "targetId":
                999999,
        }
    ]


def test_cannot_follow_or_save_non_public_targets(
    app,
    client,
):
    _, headers = _account(
        app,
        email="private-target@example.com",
    )

    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Private Graph",
            slug="private-graph",
            is_active=False,
        )
        db.session.add(
            professional
        )
        db.session.commit()
        professional_id = (
            professional.id
        )

    followed = client.put(
        (
            f"{BASE}/follows/"
            "professional/"
            f"{professional_id}"
        ),
        headers=headers,
    )

    saved = client.put(
        (
            f"{BASE}/saves/"
            "professional/"
            f"{professional_id}"
        ),
        headers=headers,
    )

    assert followed.status_code == 404
    assert saved.status_code == 404



def test_saved_items_returns_hydrated_real_entities(
    app,
    client,
):
    _, headers = _account(
        app,
        email="saved-items@example.com",
    )
    catalog = _catalog(app)

    for target_type, target_id in [
        (
            "professional",
            catalog["professional"],
        ),
        (
            "establishment",
            catalog["establishment"],
        ),
        (
            "experience",
            catalog["experience"],
        ),
        (
            "portfolio_item",
            catalog["portfolioItem"],
        ),
    ]:
        response = client.put(
            (
                f"{BASE}/saves/"
                f"{target_type}/"
                f"{target_id}"
            ),
            headers=headers,
        )

        assert response.status_code == 200

    response = client.get(
        f"{BASE}/saved-items",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert {
        item["name"]
        for item in payload["profiles"]
    } == {
        "Marina Graph",
        "Studio Graph",
    }

    assert payload[
        "experiences"
    ][0]["name"] == (
        "Corte Beauty Graph"
    )

    assert payload[
        "experiences"
    ][0]["entityId"] == (
        catalog["experience"]
    )

    assert payload[
        "portfolioItems"
    ][0]["authorName"] == (
        "Marina Graph"
    )

    assert payload["posts"] == []


def test_saved_items_isolated_by_account(
    app,
    client,
):
    _, first_headers = _account(
        app,
        email=(
            "saved-items-first@example.com"
        ),
    )
    _, second_headers = _account(
        app,
        email=(
            "saved-items-second@example.com"
        ),
    )
    catalog = _catalog(app)

    saved = client.put(
        (
            f"{BASE}/saves/"
            "experience/"
            f"{catalog['experience']}"
        ),
        headers=first_headers,
    )

    assert saved.status_code == 200

    second_payload = client.get(
        f"{BASE}/saved-items",
        headers=second_headers,
    ).get_json()

    assert second_payload == {
        "profiles": [],
        "experiences": [],
        "posts": [],
        "portfolioItems": [],
    }
