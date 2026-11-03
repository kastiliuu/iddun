"""PR 2 do programa IDDUN 2.0 — rede real (D-SOC-05, 06).

- Ninguém segue o próprio perfil Pro nem a própria empresa (400 own_profile).
- Não existe alvo "cliente": Pro (ou qualquer conta) não segue Cliente.
- Lista paginada de seguidos, só com perfis públicos e sem foto de estoque.
- Número real de seguidores.
- Favoritos antigos da Web (slugs) entram pela reconciliação.
- Sugestões do feed com motivo verificável.
"""

from decimal import Decimal

from app.extensions import db
from app.models.beauty_graph import Follow, FollowTarget, Save
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User
from app.services.beauty_graph_service import follower_count
from app.services.client_feed_service import _recommendations
from app.services.beauty_graph_service import graph_state
from tests.test_api_graph import BASE, _account, _catalog


def _error_code(response):
    return response.get_json()["error"]["code"]


def _own_professional(app, user_id, slug="pro-propria"):
    with app.app_context():
        profile = ProfessionalProfile(
            user_id=user_id,
            display_name="Pro Própria",
            slug=slug,
            primary_specialty="Colorista",
            city="Curitiba",
            state="PR",
            is_active=True,
        )
        db.session.add(profile)
        db.session.commit()
        return profile.id


def _establishment(app, *, slug, name="Espaço Rede", city="Curitiba", category="salao", active=True):
    with app.app_context():
        item = Establishment(
            name=name,
            slug=slug,
            category=category,
            city=city,
            state="PR",
            is_active=active,
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def _grant(app, user_id, establishment_id, role):
    with app.app_context():
        db.session.add(
            EstablishmentUserAccess(
                user_id=user_id,
                establishment_id=establishment_id,
                role=role,
            )
        )
        db.session.commit()


def _professional(app, *, slug, name, specialty="Colorista", city="Curitiba", active=True, avatar=None):
    with app.app_context():
        item = ProfessionalProfile(
            display_name=name,
            slug=slug,
            primary_specialty=specialty,
            city=city,
            state="PR",
            avatar_url=avatar,
            is_active=active,
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def test_nobody_follows_their_own_professional_profile(app, client):
    user_id, headers = _account(app, email="own-pro@example.com")
    own = _own_professional(app, user_id)

    response = client.put(f"{BASE}/follows/professional/{own}", headers=headers)

    assert response.status_code == 400
    assert _error_code(response) == "own_profile"
    with app.app_context():
        assert db.session.query(Follow).count() == 0


def test_owner_cannot_follow_own_establishment_but_a_manager_can(app, client):
    owner_id, owner_headers = _account(app, email="owner-net@example.com")
    manager_id, manager_headers = _account(app, email="manager-net@example.com")
    establishment = _establishment(app, slug="espaco-do-dono")
    _grant(app, owner_id, establishment, EstablishmentAccessRole.OWNER)
    _grant(app, manager_id, establishment, EstablishmentAccessRole.MANAGER)

    owner = client.put(f"{BASE}/follows/establishment/{establishment}", headers=owner_headers)
    manager = client.put(f"{BASE}/follows/establishment/{establishment}", headers=manager_headers)

    assert owner.status_code == 400
    assert _error_code(owner) == "own_profile"
    assert manager.status_code == 200


def test_reconcile_rejects_own_profile_and_keeps_the_rest(app, client):
    user_id, headers = _account(app, email="own-reconcile@example.com")
    own = _own_professional(app, user_id, slug="pro-reconcile")
    catalog = _catalog(app)

    response = client.post(
        f"{BASE}/reconcile",
        headers=headers,
        json={
            "follows": [
                {"targetType": "professional", "targetId": own},
                {"targetType": "professional", "targetId": catalog["professional"]},
            ],
            "saves": [],
        },
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["rejected"]["follows"] == [{"targetType": "professional", "targetId": own}]
    assert body["state"]["follows"] == [
        {"targetType": "professional", "targetId": catalog["professional"]}
    ]


def test_there_is_no_client_target_to_follow(app, client):
    user_id, headers = _account(app, email="pro-follows-client@example.com")
    _own_professional(app, user_id, slug="pro-segue-cliente")
    client_id, _ = _account(app, email="followed-client@example.com")

    for target in ("client", "user"):
        response = client.put(f"{BASE}/follows/{target}/{client_id}", headers=headers)
        assert response.status_code == 404
        assert _error_code(response) == "invalid_follow_target"


def test_following_list_is_paginated_newest_first_and_public_only(app, client):
    user_id, headers = _account(app, email="following-list@example.com")
    ids = [
        _professional(app, slug=f"seguida-{index}", name=f"Seguida {index}")
        for index in range(5)
    ]
    hidden = _professional(app, slug="seguida-inativa", name="Inativa", active=False)
    business = _establishment(app, slug="espaco-seguido", name="Espaço Seguido")

    with app.app_context():
        for target in ids + [hidden]:
            db.session.add(
                Follow(user_id=user_id, target_type=FollowTarget.PROFESSIONAL, professional_id=target)
            )
        db.session.add(
            Follow(user_id=user_id, target_type=FollowTarget.ESTABLISHMENT, establishment_id=business)
        )
        db.session.commit()

    first = client.get(f"{BASE}/following?limit=4", headers=headers).get_json()

    assert first["total"] == 6
    assert [item["name"] for item in first["items"]] == [
        "Espaço Seguido", "Seguida 4", "Seguida 3", "Seguida 2",
    ]
    assert first["nextCursor"] is not None
    assert first["items"][0]["targetType"] == "establishment"
    assert first["items"][1]["avatar"] is None
    assert first["items"][1]["slug"] == "seguida-4"

    second = client.get(
        f"{BASE}/following?limit=4&cursor={first['nextCursor']}", headers=headers
    ).get_json()

    assert [item["name"] for item in second["items"]] == ["Seguida 1", "Seguida 0"]
    assert second["nextCursor"] is None


def test_following_list_is_private_and_validates_the_cursor(app, client):
    _, headers = _account(app, email="following-a@example.com")
    _, other_headers = _account(app, email="following-b@example.com")
    catalog = _catalog(app)
    client.put(f"{BASE}/follows/professional/{catalog['professional']}", headers=headers)

    assert client.get(f"{BASE}/following").status_code == 401
    assert client.get(f"{BASE}/following", headers=other_headers).get_json()["total"] == 0
    bad = client.get(f"{BASE}/following?cursor=abc", headers=headers)
    assert bad.status_code == 400
    assert _error_code(bad) == "invalid_cursor"


def test_follower_count_is_real_and_repeat_does_not_duplicate(app, client):
    catalog = _catalog(app)
    for index in range(3):
        _, headers = _account(app, email=f"fan-{index}@example.com")
        url = f"{BASE}/follows/professional/{catalog['professional']}"
        client.put(url, headers=headers)
        client.put(url, headers=headers)

    with app.app_context():
        assert follower_count(FollowTarget.PROFESSIONAL, catalog["professional"]) == 3
        assert follower_count(FollowTarget.ESTABLISHMENT, catalog["establishment"]) == 0


def test_reconcile_imports_legacy_experience_slugs(app, client):
    user_id, headers = _account(app, email="legacy-slugs@example.com")
    catalog = _catalog(app)
    payload = {"experienceSlugs": ["corte-beauty-graph", "prototipo-que-nao-existe"]}

    first = client.post(f"{BASE}/reconcile", headers=headers, json=payload)
    second = client.post(f"{BASE}/reconcile", headers=headers, json=payload)

    body = first.get_json()
    assert first.status_code == 200
    assert body["imported"]["saves"] == [
        {"targetType": "experience", "targetId": catalog["experience"]}
    ]
    assert body["rejected"]["experienceSlugs"] == ["prototipo-que-nao-existe"]
    assert second.status_code == 200
    with app.app_context():
        assert db.session.query(Save).filter_by(user_id=user_id).count() == 1


def test_reconcile_validates_legacy_slugs(app, client):
    _, headers = _account(app, email="legacy-invalid@example.com")

    for value in ("corte", [1], [""], ["x" * 201], ["a"] * 201):
        response = client.post(f"{BASE}/reconcile", headers=headers, json={"experienceSlugs": value})
        assert response.status_code == 400, value
        assert _error_code(response) == "invalid_graph_payload"


def test_draft_experience_slug_is_not_imported(app, client):
    _, headers = _account(app, email="legacy-draft@example.com")
    catalog = _catalog(app)
    with app.app_context():
        db.session.add(
            Experience(
                professional_id=catalog["professional"],
                title="Rascunho",
                slug="rascunho-legado",
                category="cabelo",
                short_description="Ainda não publicado.",
                regular_price=Decimal("10.00"),
                price=Decimal("10.00"),
                duration_minutes=30,
                status=ExperienceStatus.DRAFT,
            )
        )
        db.session.commit()

    body = client.post(
        f"{BASE}/reconcile", headers=headers, json={"experienceSlugs": ["rascunho-legado"]}
    ).get_json()

    assert body["imported"]["saves"] == []
    assert body["rejected"]["experienceSlugs"] == ["rascunho-legado"]


def test_saved_profiles_say_whether_the_photo_was_uploaded(app, client):
    _, headers = _account(app, email="saved-avatar@example.com")
    catalog = _catalog(app)
    client.put(f"{BASE}/saves/professional/{catalog['professional']}", headers=headers)
    client.put(f"{BASE}/saves/establishment/{catalog['establishment']}", headers=headers)

    profiles = client.get(f"{BASE}/saved-items", headers=headers).get_json()["profiles"]

    uploaded = {item["kind"]: item["avatarUploaded"] for item in profiles}
    assert uploaded == {"professional": True, "establishment": False}


def _suggestions(app, user_id):
    with app.app_context():
        user = db.session.get(User, user_id)
        profile = db.session.query(ClientProfile).filter_by(user_id=user_id).one()
        return _recommendations(user=user, profile=profile, graph=graph_state(user), limit=10)


def test_suggestions_explain_why_with_real_relations(app):
    user_id, _ = _account(app, email="reasons@example.com")
    followed_business = _establishment(app, slug="espaco-que-sigo", name="Espaço Que Sigo", city="Recife")
    followed_pro = _professional(app, slug="pro-que-sigo", name="Pro Que Sigo", specialty="Nail designer", city="Recife")
    works_there = _professional(app, slug="atende-la", name="Atende Lá", specialty="Barbeiro", city="Recife")
    same_specialty = _professional(app, slug="mesma-especialidade", name="Mesma Especialidade", specialty="nail designer", city="Natal")
    same_city = _professional(app, slug="mesma-cidade", name="Mesma Cidade", specialty="Maquiadora", city="Curitiba")
    nothing = _professional(app, slug="sem-motivo", name="Sem Motivo", specialty="Massagista", city="Manaus")
    pro_works_here = _establishment(app, slug="onde-a-pro-atende", name="Onde a Pro Atende", city="Belém", category="spa")

    with app.app_context():
        db.session.query(ClientProfile).filter_by(user_id=user_id).one().city = "Curitiba"
        db.session.add_all(
            [
                Follow(user_id=user_id, target_type=FollowTarget.ESTABLISHMENT, establishment_id=followed_business),
                Follow(user_id=user_id, target_type=FollowTarget.PROFESSIONAL, professional_id=followed_pro),
                ProfessionalEstablishmentMembership(
                    professional_id=works_there,
                    establishment_id=followed_business,
                    status=MembershipStatus.ACTIVE,
                ),
                ProfessionalEstablishmentMembership(
                    professional_id=followed_pro,
                    establishment_id=pro_works_here,
                    status=MembershipStatus.ACTIVE,
                ),
            ]
        )
        db.session.commit()

    result = _suggestions(app, user_id)
    reasons = {item["slug"]: item["reason"] for item in result["professionals"]}
    places = {item["slug"]: item["reason"] for item in result["establishments"]}

    assert reasons[f"atende-la"] == "Atende em Espaço Que Sigo"
    assert reasons["mesma-especialidade"] == "Mesma especialidade de quem você segue: nail designer"
    assert reasons["mesma-cidade"] == "Mesma cidade: Curitiba"
    assert reasons["sem-motivo"] is None
    assert places["onde-a-pro-atende"] == "Pro Que Sigo atende aqui"
    assert "pro-que-sigo" not in reasons
    assert nothing and same_city and same_specialty


def test_suggestion_ignores_pending_membership(app):
    user_id, _ = _account(app, email="reasons-pending@example.com")
    followed_business = _establishment(app, slug="espaco-pendente", name="Espaço Pendente", city="Recife")
    pending = _professional(app, slug="convite-pendente", name="Convite Pendente", city="Manaus")

    with app.app_context():
        db.session.add_all(
            [
                Follow(user_id=user_id, target_type=FollowTarget.ESTABLISHMENT, establishment_id=followed_business),
                ProfessionalEstablishmentMembership(
                    professional_id=pending,
                    establishment_id=followed_business,
                    status=MembershipStatus.PENDING,
                ),
            ]
        )
        db.session.commit()

    reasons = {item["slug"]: item["reason"] for item in _suggestions(app, user_id)["professionals"]}
    assert reasons["convite-pendente"] is None
