"""PR 2 do programa IDDUN 2.0 — rede real na Web (D-SOC-05, 06, 07).

- Perfis Pro e empresa com Seguir real e o número de seguidores.
- Corações do catálogo e do diretório salvam pela API (sem localStorage).
- Página /favoritos com Seguindo e Salvos; o painel de salvos saiu do feed.
- Sem Seguir no próprio perfil ou empresa.
- Sugestões do feed com motivo.
"""

import re
from pathlib import Path

from flask import g

from app.extensions import db
from app.models.beauty_graph import Follow, FollowTarget, Save, SaveTarget
from app.models.establishment import EstablishmentAccessRole, EstablishmentUserAccess
from app.models.professional import ProfessionalProfile
from tests.test_api_graph import _account, _catalog
from tests.test_client_feed import _login

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"


def _as(client, user_id):
    g.pop("_login_user", None)
    _login(client, user_id)


def _html(client, path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    return response.get_data(as_text=True)


def _button(html, kind, target_type, target_id):
    pattern = (
        r"<button[^>]*data-" + kind + r"-button[^>]*"
        r'data-target-type="' + target_type + r'"[^>]*'
        r'data-target-id="' + str(target_id) + r'"[^>]*>'
    )
    match = re.search(pattern, html, re.DOTALL)
    return match.group(0) if match else None


def _follow(app, user_id, target_type, target_id):
    with app.app_context():
        column = "professional_id" if target_type == FollowTarget.PROFESSIONAL else "establishment_id"
        db.session.add(Follow(user_id=user_id, target_type=target_type, **{column: target_id}))
        db.session.commit()


def test_professional_profile_has_real_follow_and_follower_count(app, client):
    catalog = _catalog(app)
    fan_id, _ = _account(app, email="fan-web@example.com")
    _follow(app, fan_id, FollowTarget.PROFESSIONAL, catalog["professional"])

    anonymous = _html(client, "/profissionais/marina-graph")
    button = _button(anonymous, "follow", "professional", catalog["professional"])
    assert button is not None
    assert 'aria-pressed="false"' in button
    assert 'data-login-url="/login?next=/profissionais/marina-graph"' in button
    assert re.search(r'data-follower-count[^>]*data-count="1"[^>]*>1 seguidor<', anonymous)
    assert "data-favorite" not in anonymous

    _as(client, fan_id)
    following = _html(client, "/profissionais/marina-graph")
    button = _button(following, "follow", "professional", catalog["professional"])
    assert 'aria-pressed="true"' in button
    assert re.search(r"<span data-graph-label>Seguindo</span>", following)


def test_establishment_profile_has_follow_and_owner_does_not(app, client):
    catalog = _catalog(app)
    owner_id, _ = _account(app, email="owner-web@example.com")
    with app.app_context():
        db.session.add(
            EstablishmentUserAccess(
                user_id=owner_id,
                establishment_id=catalog["establishment"],
                role=EstablishmentAccessRole.OWNER,
            )
        )
        db.session.commit()

    anonymous = _html(client, "/estabelecimentos/studio-graph")
    assert _button(anonymous, "follow", "establishment", catalog["establishment"]) is not None
    assert ">0 seguidores<" in anonymous

    _as(client, owner_id)
    owner = _html(client, "/estabelecimentos/studio-graph")
    assert _button(owner, "follow", "establishment", catalog["establishment"]) is None


def test_own_professional_profile_has_no_follow_button(app, client):
    catalog = _catalog(app)
    user_id, _ = _account(app, email="pro-own-web@example.com")
    with app.app_context():
        db.session.get(ProfessionalProfile, catalog["professional"]).user_id = user_id
        db.session.commit()

    _as(client, user_id)
    html = _html(client, "/profissionais/marina-graph")
    assert _button(html, "follow", "professional", catalog["professional"]) is None
    assert "0 seguidores" in html


def test_catalog_and_directory_hearts_save_through_the_api(app, client):
    catalog = _catalog(app)
    user_id, _ = _account(app, email="hearts-web@example.com")
    with app.app_context():
        db.session.add(
            Save(user_id=user_id, target_type=SaveTarget.EXPERIENCE, experience_id=catalog["experience"])
        )
        db.session.commit()

    _as(client, user_id)
    services = _html(client, "/experiencias")
    heart = _button(services, "save", "experience", catalog["experience"])
    assert heart is not None
    assert 'aria-pressed="true"' in heart
    assert 'data-active="true"' in heart
    assert "data-favorite-id" not in services

    directory = _html(client, "/profissionais")
    heart = _button(directory, "save", "professional", catalog["professional"])
    assert heart is not None
    assert 'aria-pressed="false"' in heart
    assert 'aria-label="Salvar Marina Graph"' in heart


def test_favorites_page_lists_following_and_saved(app, client):
    catalog = _catalog(app)
    user_id, _ = _account(app, email="favorites-web@example.com")
    _follow(app, user_id, FollowTarget.PROFESSIONAL, catalog["professional"])
    _follow(app, user_id, FollowTarget.ESTABLISHMENT, catalog["establishment"])
    with app.app_context():
        db.session.add(
            Save(user_id=user_id, target_type=SaveTarget.EXPERIENCE, experience_id=catalog["experience"])
        )
        db.session.commit()

    assert client.get("/favoritos").status_code == 302

    _as(client, user_id)
    following = _html(client, "/favoritos")
    assert re.search(r'aria-current="page"[^>]*>\s*Seguindo <span class="favorites-tabs__count">2</span>', following)
    assert 'Salvos <span class="favorites-tabs__count">1</span>' in following
    assert following.index("Studio Graph") < following.index("Marina Graph")
    assert 'aria-pressed="true"' in _button(following, "follow", "professional", catalog["professional"])
    assert 'href="/favoritos"' in following
    assert re.search(r'class="feed-header__nav-item is-active"\s*href="/favoritos"', following)

    saved = _html(client, "/favoritos?aba=salvos")
    assert "Corte Beauty Graph" in saved
    assert 'aria-pressed="true"' in _button(saved, "save", "experience", catalog["experience"])


def test_favorites_empty_states_and_pagination(app, client):
    user_id, _ = _account(app, email="favorites-empty@example.com")
    _as(client, user_id)

    assert "Você ainda não segue ninguém." in _html(client, "/favoritos")
    assert "Sua coleção começa com uma descoberta." in _html(client, "/favoritos?aba=salvos")
    assert "Você ainda não segue ninguém." in _html(client, "/favoritos?aba=qualquer")

    with app.app_context():
        for index in range(22):
            profile = ProfessionalProfile(
                display_name=f"Pro Lista {index:02d}",
                slug=f"pro-lista-{index}",
                is_active=True,
            )
            db.session.add(profile)
            db.session.flush()
            db.session.add(
                Follow(user_id=user_id, target_type=FollowTarget.PROFESSIONAL, professional_id=profile.id)
            )
        db.session.commit()

    first = _html(client, "/favoritos")
    more = re.search(r'href="/favoritos\?cursor=(\d+)"', first)
    assert more is not None
    assert first.count('class="favorites-row"') == 20
    second = _html(client, f"/favoritos?cursor={more.group(1)}")
    assert second.count('class="favorites-row"') == 2
    assert "Pro Lista 00" in second
    assert "Voltar ao início da lista" in second


def test_feed_has_no_saved_panel_and_old_links_still_work(app, client):
    user_id, _ = _account(app, email="feed-panel@example.com")
    _as(client, user_id)
    feed = _html(client, "/feed")

    assert "data-saved-panel" not in feed
    assert "data-saved-trigger" not in feed
    assert 'href="/favoritos?aba=salvos"' in feed
    script = (STATIC / "js" / "app-header.js").read_text()
    assert "window.location.replace('/favoritos?aba=salvos')" in script


def test_feed_suggestion_shows_its_reason(app, client):
    catalog = _catalog(app)
    user_id, _ = _account(app, email="feed-reason@example.com")
    with app.app_context():
        from app.models.profile import ClientProfile

        db.session.query(ClientProfile).filter_by(user_id=user_id).one().city = "Curitiba"
        db.session.commit()

    _as(client, user_id)
    feed = _html(client, "/feed")
    assert '<small class="feed-recommendation__reason">Mesma cidade: Curitiba</small>' in feed
    assert catalog


def test_scripts_no_longer_keep_favorites_only_in_the_browser():
    marketplace = (STATIC / "js" / "marketplace.js").read_text()
    professionals = (STATIC / "js" / "professionals.js").read_text()
    graph = (STATIC / "js" / "graph.js").read_text()

    assert "localStorage.setItem" not in marketplace
    assert "data-favorite" not in professionals
    assert "localStorage.setItem" not in graph
    assert "/api/v1/graph/reconcile" in graph
    assert "experienceSlugs" in graph
    assert "fetchWithCsrf" in graph
