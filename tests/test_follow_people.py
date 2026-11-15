"""ID-SOC-R1-03/04 (Notion 08, 14/11/2026) — seguir pessoas.

Qualquer conta ativa segue qualquer pessoa ativa ou empresa; seguir a si
mesmo continua proibido. "professional" é o formato antigo e vira a pessoa
dona do perfil; perfil de catálogo sem conta continua seguido pelo perfil.
O estado devolve o apelido "professional" para o app instalado.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.beauty_graph import Follow, FollowTarget
from app.models.establishment import Establishment
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from app.services.api_auth import issue_session
from app.services.beauty_graph_service import (
    BeautyGraphError,
    OwnProfileError,
    follow_target,
    follower_count,
    following_page,
    graph_state,
    is_following,
    unfollow_target,
)
from app.services.feed_service import feed_page

PASSWORD = "senha-forte-123"
WHEN = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _user(name, email):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()
    return user


def _pro(user, slug):
    profile = ProfessionalProfile(
        user_id=user.id if user else None, display_name=slug.title(), slug=slug,
        city="Curitiba", state="PR", is_active=True, published_at=WHEN,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def _post(**author):
    item = WorkPost(
        caption="Trabalho real", status=WorkPostStatus.PUBLISHED, published_at=WHEN,
        image_focus_x=50, image_focus_y=50, **author,
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture()
def people(app):
    fan = _user("Fã Feed", "fan@example.com")
    client_only = _user("Clara Cliente", "clara@example.com")
    pro_user = _user("Paula Pro", "paula@example.com")
    stranger = _user("Sem Seguir", "stranger@example.com")
    pro = _pro(pro_user, "paula-unhas")
    catalogue = _pro(None, "catalogo-sem-conta")
    business = Establishment(name="Studio Seguir", slug="studio-seguir", category="salao",
                             city="Curitiba", state="PR", is_active=True, published_at=WHEN)
    db.session.add(business)
    db.session.commit()
    return {
        "fan": fan, "client_only": client_only, "pro_user": pro_user,
        "stranger": stranger, "pro": pro, "catalogue": catalogue, "business": business,
    }


def test_people_are_followed_as_person_whatever_the_old_target(app, people):
    fan = people["fan"]
    follow_target(user=fan, target_type="person", target_id=people["client_only"].id)
    via_pro = follow_target(user=fan, target_type="professional", target_id=people["pro"].id)
    again = follow_target(user=fan, target_type="person", target_id=people["pro_user"].id)
    catalogue = follow_target(user=fan, target_type="professional", target_id=people["catalogue"].id)

    assert via_pro.id == again.id
    assert (via_pro.target_type, via_pro.followed_user_id, via_pro.professional_id) == (
        "person", people["pro_user"].id, None,
    )
    # Perfil de catálogo sem conta: continua seguido pelo perfil.
    assert (catalogue.target_type, catalogue.professional_id) == ("professional", people["catalogue"].id)
    assert db.session.scalar(select(db.func.count(Follow.id)).where(Follow.user_id == fan.id)) == 3

    # Contagens e "sigo?" respondem pelo formato antigo e pelo novo.
    assert follower_count("professional", people["pro"].id) == 1
    assert follower_count("person", people["pro_user"].id) == 1
    assert follower_count("person", people["client_only"].id) == 1
    assert is_following(fan, "professional", people["pro"].id)
    assert is_following(fan, "person", people["pro_user"].id)
    assert not is_following(fan, "person", people["stranger"].id)


def test_state_keeps_professional_alias_and_true_count(app, people):
    fan = people["fan"]
    follow_target(user=fan, target_type="professional", target_id=people["pro"].id)
    follow_target(user=fan, target_type="person", target_id=people["client_only"].id)
    follow_target(user=fan, target_type="establishment", target_id=people["business"].id)

    state = graph_state(fan)
    refs = {(item["targetType"], item["targetId"]) for item in state["follows"]}
    assert refs == {
        ("person", people["pro_user"].id),
        ("person", people["client_only"].id),
        ("establishment", people["business"].id),
        ("professional", people["pro"].id),  # apelido para o app instalado
    }
    assert state["followingCount"] == 3

    page = following_page(fan)
    assert page["total"] == 3
    by_type = {(item["targetType"], item["targetId"]): item for item in page["items"]}
    paula = by_type[("person", people["pro_user"].id)]
    assert paula["username"] == people["pro_user"].username
    assert paula["slug"] == "paula-unhas" and paula["professionalId"] == people["pro"].id
    clara = by_type[("person", people["client_only"].id)]
    assert clara["slug"] is None and clara["location"] is None  # cidade pessoal é privada
    assert clara["clientProfileId"] == people["client_only"].client_profile.id


def test_self_inactive_and_unknown_targets_are_refused(app, people):
    pro_user = people["pro_user"]
    with pytest.raises(OwnProfileError):
        follow_target(user=pro_user, target_type="person", target_id=pro_user.id)
    with pytest.raises(OwnProfileError):
        follow_target(user=pro_user, target_type="professional", target_id=people["pro"].id)

    people["stranger"].is_active_account = False
    db.session.commit()
    with pytest.raises(BeautyGraphError):
        follow_target(user=people["fan"], target_type="person", target_id=people["stranger"].id)
    with pytest.raises(BeautyGraphError):
        follow_target(user=people["fan"], target_type="person", target_id=999999)
    with pytest.raises(BeautyGraphError):
        follow_target(user=people["fan"], target_type="client", target_id=people["client_only"].id)
    assert db.session.scalar(select(Follow)) is None


def test_unfollow_by_old_or_new_target_removes_the_person_follow(app, people):
    fan = people["fan"]
    follow_target(user=fan, target_type="person", target_id=people["pro_user"].id)
    assert unfollow_target(user=fan, target_type="professional", target_id=people["pro"].id) is True
    assert not is_following(fan, "person", people["pro_user"].id)
    assert unfollow_target(user=fan, target_type="professional", target_id=424242) is False


def test_following_feed_shows_only_followed_people_and_their_old_pro_posts(app, people):
    fan = people["fan"]
    clara_post = _post(author_type=WorkPostAuthorType.CLIENT, client_profile_id=people["client_only"].client_profile.id)
    paula_old = _post(author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=people["pro"].id)
    paula_new = _post(author_type=WorkPostAuthorType.CLIENT, client_profile_id=people["pro_user"].client_profile.id)
    catalogue_post = _post(author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=people["catalogue"].id)
    business_post = _post(author_type=WorkPostAuthorType.ESTABLISHMENT, establishment_id=people["business"].id)
    stranger_post = _post(author_type=WorkPostAuthorType.CLIENT, client_profile_id=people["stranger"].client_profile.id)

    def following_ids():
        return {int(item["id"]) for item in feed_page(mode="following", user=fan)["items"]}

    assert following_ids() == set()
    follow_target(user=fan, target_type="person", target_id=people["client_only"].id)
    follow_target(user=fan, target_type="professional", target_id=people["pro"].id)
    follow_target(user=fan, target_type="professional", target_id=people["catalogue"].id)
    follow_target(user=fan, target_type="establishment", target_id=people["business"].id)

    ids = following_ids()
    assert ids == {clara_post.id, paula_old.id, paula_new.id, catalogue_post.id, business_post.id}
    assert stranger_post.id not in ids


def test_api_accepts_person_and_old_professional_targets(client, app, people):
    fan_id, pro_id, clara_id, pro_user_id = (
        people["fan"].id, people["pro"].id, people["client_only"].id, people["pro_user"].id,
    )
    tokens = issue_session(db.session.get(User, fan_id), device_name="Teste", platform="ios")
    headers = {"Authorization": f"Bearer {tokens.access_token}"}

    person = client.put(f"/api/v1/graph/follows/person/{clara_id}", headers=headers)
    assert person.status_code == 200
    legacy = client.put(f"/api/v1/graph/follows/professional/{pro_id}", headers=headers)
    assert legacy.status_code == 200 and legacy.get_json()["targetType"] == "professional"
    own = client.put(f"/api/v1/graph/follows/person/{fan_id}", headers=headers)
    assert own.status_code == 400 and own.get_json()["error"]["code"] == "own_profile"

    state = client.get("/api/v1/graph", headers=headers).get_json()
    assert {"targetType": "person", "targetId": pro_user_id} in state["follows"]
    assert {"targetType": "professional", "targetId": pro_id} in state["follows"]
    assert state["followingCount"] == 2

    profile = client.get(
        f"/api/v1/clients/{people['client_only'].client_profile.id}", headers=headers
    ).get_json()
    assert profile["username"] == people["client_only"].username
    assert (profile["userId"], profile["followerCount"], profile["following"]) == (clara_id, 1, True)

    removed = client.delete(f"/api/v1/graph/follows/person/{clara_id}", headers=headers)
    assert removed.get_json()["removed"] is True


def test_personal_page_exists_without_posts_and_has_follow(client, app, people):
    clara = people["client_only"]
    page = client.get(f"/clientes/{clara.client_profile.id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert f"@{clara.username}" in html
    assert 'data-target-type="person"' in html
    assert "0 seguidores" in html
    # Cidade e dados privados continuam fora da página.
    clara.client_profile.city = "Cidade Privada"
    db.session.commit()
    assert "Cidade Privada" not in client.get(f"/clientes/{clara.client_profile.id}").get_data(as_text=True)

    clara.is_active_account = False
    db.session.commit()
    assert client.get(f"/clientes/{clara.client_profile.id}").status_code == 404
