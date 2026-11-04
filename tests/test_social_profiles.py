"""PR 4a do programa IDDUN 2.0 — perfis sociais (D-SOC-03, 12, 13).

- Cliente com publicação pública tem página; sem isso, 404 (sem expor nomes).
- Perfil Pro na ordem aprovada, com Publicações e rótulos declarado/verificado.
- Empresa com abas endereçáveis; Equipe só com vínculo aceito.
- Nome do autor e de quem comenta leva ao perfil certo.
- Salvos sem foto de estoque como avatar (D11).
"""

import re
from datetime import date

from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.certification import ProfessionalCertification
from app.models.establishment import (
    Establishment,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile
from app.models.professional_experience import (
    ProfessionalExperience,
    ProfessionalExperienceVerification,
)
from app.models.profile import ClientProfile
from app.models.user import User
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from tests.test_api_graph import _catalog
from tests.test_api_posts import POSTS, _user
from tests.test_client_feed import _login


def _client_profile_id(app, user_id):
    with app.app_context():
        return db.session.scalar(select(ClientProfile.id).where(ClientProfile.user_id == user_id))


def _client_text_post(client, headers, profile_id, caption="Post da Cliente"):
    response = client.post(
        POSTS,
        headers=headers,
        data={"authorType": "client", "authorId": str(profile_id), "caption": caption},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["post"]["id"]


def _as(client, user_id):
    g.pop("_login_user", None)
    _login(client, user_id)


def _html(client, path, status=200):
    response = client.get(path)
    assert response.status_code == status, (path, response.status_code)
    return response.get_data(as_text=True)


def _add_post(app, **fields):
    with app.app_context():
        post = WorkPost(status=WorkPostStatus.PUBLISHED, **fields)
        db.session.add(post)
        db.session.commit()
        return post.id


# ------------------------------------------------------------- Cliente


def test_client_page_exists_only_with_a_public_post(app, client):
    user_id, _, headers = _user(app, email="cliente-pagina@example.com", with_professional=False)
    profile_id = _client_profile_id(app, user_id)

    _html(client, f"/clientes/{profile_id}", 404)
    assert client.get(f"/api/v1/clients/{profile_id}").status_code == 404

    post_id = _client_text_post(client, headers, profile_id, "Meus cachos hoje")
    with app.app_context():
        db.session.get(ClientProfile, profile_id).city = "Cidade Privada"
        db.session.commit()

    page = _html(client, f"/clientes/{profile_id}")
    assert "Creator Test" in page
    assert "Meus cachos hoje" in page
    assert "Cliente IDDUN · 1 publicação" in page
    assert "Cidade Privada" not in page

    api = client.get(f"/api/v1/clients/{profile_id}").get_json()
    assert api["name"] == "Creator Test"
    assert [item["id"] for item in api["posts"]] == [post_id]
    assert "city" not in api and "Cidade Privada" not in str(api)

    with app.app_context():
        db.session.get(WorkPost, int(post_id)).status = WorkPostStatus.HIDDEN
        db.session.commit()
    _html(client, f"/clientes/{profile_id}", 404)

    with app.app_context():
        db.session.get(WorkPost, int(post_id)).status = WorkPostStatus.PUBLISHED
        db.session.get(User, user_id).is_active_account = False
        db.session.commit()
    _html(client, f"/clientes/{profile_id}", 404)


def test_feed_and_comments_link_to_the_client_page(app, client):
    author_id, _, author_headers = _user(app, email="autora-link@example.com", with_professional=False)
    author_profile = _client_profile_id(app, author_id)
    post_id = _client_text_post(client, author_headers, author_profile)
    _, _, silent_headers = _user(app, email="sem-posts@example.com", with_professional=False)

    client.post(f"{POSTS}/{post_id}/comments", headers=author_headers, json={"body": "Eu mesma"})
    client.post(f"{POSTS}/{post_id}/comments", headers=silent_headers, json={"body": "Sem página"})

    comments = client.get(f"{POSTS}/{post_id}/comments").get_json()["items"]
    links = {item["body"]: item["author"]["profileId"] for item in comments}
    assert links == {"Eu mesma": str(author_profile), "Sem página": None}

    _as(client, author_id)
    feed = _html(client, "/feed")
    assert f'href="/clientes/{author_profile}"' in feed
    detail = _html(client, f"/publicacoes/{post_id}")
    assert f'class="post-comment__author" href="/clientes/{author_profile}"' in detail


# ------------------------------------------------------------- Pro


def _pro_with_details(app):
    catalog = _catalog(app)
    with app.app_context():
        profile = db.session.get(ProfessionalProfile, catalog["professional"])
        profile.bio = "Cuidado com cachos e coloração natural. " * 12
        db.session.add_all(
            [
                ProfessionalExperience(
                    professional_id=profile.id,
                    company_name="Salão Declarado",
                    role_title="Colorista",
                    started_at=date(2020, 1, 1),
                    verification_status=ProfessionalExperienceVerification.UNVERIFIED,
                ),
                ProfessionalExperience(
                    professional_id=profile.id,
                    company_name="Studio Graph",
                    role_title="Hair Stylist",
                    started_at=date(2022, 1, 1),
                    is_current=True,
                    verification_status=ProfessionalExperienceVerification.VERIFIED_MEMBERSHIP,
                ),
                ProfessionalCertification(
                    professional_id=profile.id,
                    title="Colorimetria avançada",
                    issuer="Escola X",
                ),
            ]
        )
        db.session.commit()
    for index in range(7):
        _add_post(
            app,
            author_type=WorkPostAuthorType.PROFESSIONAL,
            professional_id=catalog["professional"],
            caption=f"Trabalho {index}",
        )
    return catalog


def test_professional_profile_follows_the_approved_order(app, client):
    _pro_with_details(app)
    page = _html(client, "/profissionais/marina-graph")

    kickers = re.findall(r'public-profile-section__kicker">([^<]+)<', page)
    order = ["SOBRE", "PORTFÓLIO", "SERVIÇOS", "PUBLICAÇÕES", "EXPERIÊNCIA & FORMAÇÃO",
             "AVALIAÇÕES & RECOMENDAÇÕES", "ONDE ATENDE"]
    assert [item for item in kickers if item in order] == order

    assert "Ler mais" in page
    assert len(re.findall(r'<a class="post-tile[ "]', page)) == 6
    assert 'href="/profissionais/marina-graph/publicacoes">Ver todas (7)' in page
    assert "Salão Declarado" in page
    assert page.count("Declarado pelo profissional") == 2  # experiência + certificado
    assert "Vínculo verificado no IDDUN" in page
    assert ">Ver serviços<" in page


def test_professional_posts_page_lists_all_with_pagination(app, client):
    _pro_with_details(app)
    page = _html(client, "/profissionais/marina-graph/publicacoes")
    assert "Publicações de Marina Graph" in page
    assert "7 publicações" in page
    assert len(re.findall(r'<article\s+id="post-\d+"', page)) == 7
    _html(client, "/profissionais/perfil-que-nao-existe/publicacoes", 404)


# ------------------------------------------------------------- empresa


def test_business_tabs_have_their_own_address(app, client):
    catalog = _catalog(app)
    with app.app_context():
        business = db.session.get(Establishment, catalog["establishment"])
        business.operation_mode = "physical"
        business.business_hours_mode = "fixed_hours"
        business.business_hours = {"monday": [{"start": "09:00", "end": "18:00"}]}
        pending = ProfessionalProfile(display_name="Convite Pendente", slug="convite-pendente-tab", is_active=True)
        db.session.add(pending)
        db.session.flush()
        db.session.add_all(
            [
                ProfessionalEstablishmentMembership(
                    professional_id=catalog["professional"],
                    establishment_id=business.id,
                    status=MembershipStatus.ACTIVE,
                ),
                ProfessionalEstablishmentMembership(
                    professional_id=pending.id,
                    establishment_id=business.id,
                    status=MembershipStatus.PENDING,
                ),
            ]
        )
        db.session.commit()
    _add_post(
        app,
        author_type=WorkPostAuthorType.ESTABLISHMENT,
        establishment_id=catalog["establishment"],
        caption="Novidade do studio",
    )

    base = "/estabelecimentos/studio-graph"
    expected = {"": "Início", "/servicos": "Serviços", "/equipe": "Equipe", "/publicacoes": "Publicações", "/sobre": "Sobre"}
    pages = {}
    for suffix, label in expected.items():
        pages[suffix] = _html(client, base + suffix)
        assert re.search(rf'aria-current="page">{label}<', pages[suffix]), suffix

    assert "Novidade do studio" in pages[""]
    assert "Corte Beauty Graph" in pages["/servicos"]
    assert "Marina Graph" in pages["/equipe"]
    assert "Convite Pendente" not in pages["/equipe"]
    assert re.search(r'<article\s+id="post-\d+"', pages["/publicacoes"])
    assert "No estabelecimento" in pages["/sobre"]
    assert "09:00–18:00" in pages["/sobre"]
    assert "Fechado" in pages["/sobre"]
    _html(client, base + "/vagas", 404)


def test_inactive_business_has_no_tabs(app, client):
    catalog = _catalog(app)
    with app.app_context():
        db.session.get(Establishment, catalog["establishment"]).is_active = False
        db.session.commit()
    for suffix in ("", "/servicos", "/publicacoes", "/sobre"):
        _html(client, f"/estabelecimentos/studio-graph{suffix}", 404)


# --------------------------------------------------------------- D11


def test_saved_profiles_have_no_stock_avatar(app, client):
    from tests.test_api_graph import _account

    catalog = _catalog(app)
    _, headers = _account(app, email="sem-estoque@example.com")
    client.put(f"/api/v1/graph/saves/establishment/{catalog['establishment']}", headers=headers)

    profiles = client.get("/api/v1/graph/saved-items", headers=headers).get_json()["profiles"]
    assert profiles[0]["avatar"] is None
    assert profiles[0]["avatarUploaded"] is False


# ------------------------------------------------------------- app (API)


def test_profile_api_carries_the_web_sections_for_the_app(app, client):
    """D-SOC-12: o app recebe as mesmas seções e rótulos do Web (aditivo)."""
    catalog = _pro_with_details(app)
    data = client.get("/api/v1/professionals/marina-graph").get_json()

    assert data["postsCount"] == 7
    assert {item["company"]: item["verified"] for item in data["experiences"]} == {
        "Salão Declarado": False,
        "Studio Graph": True,
    }
    assert [item["title"] for item in data["certifications"]] == ["Colorimetria avançada"]
    assert data["reviews"] == []  # nada inventado sem atendimento concluído
    assert data["recommendationLabel"] == "Sem avaliações ainda"
    assert data["whatsappUrl"] is None
    assert isinstance(data["portfolio"], list) and isinstance(data["places"], list)
    assert data["professional"]["name"] == "Marina Graph"  # contrato antigo intacto

    with app.app_context():
        business = db.session.get(Establishment, catalog["establishment"])
        business.operation_mode = "physical"
        business.business_hours_mode = "fixed_hours"
        business.business_hours = {"monday": [{"start": "09:00", "end": "18:00"}]}
        db.session.commit()

    data = client.get("/api/v1/establishments/studio-graph").get_json()
    about = data["about"]
    assert about["operationLabel"] == "No estabelecimento"
    days = {day["label"]: day["ranges"] for day in about["hours"]["days"]}
    assert days["Segunda"] == ["09:00–18:00"]
    assert days["Domingo"] == []
    assert data["reviews"] == [] and data["postsCount"] == 0
    assert data["gallery"] == []


def test_profile_api_reviews_are_real_and_show_only_the_first_name(app, client):
    from tests.test_reputation import _completed_booking, _login_session

    user_id, booking_id, _, _ = _completed_booking(app)
    with app.app_context():
        db.session.get(User, user_id).name = "Bruna Sobrenome Privado"
        db.session.commit()
    _login_session(client, user_id)
    client.post(
        f"/reserva/{booking_id}/avaliar",
        data={
            "professional_rating": "5",
            "professional_recommended": "yes",
            "professional_comment": "Resultado excelente.",
            "establishment_rating": "4",
            "establishment_recommended": "no",
            "establishment_comment": "",
        },
    )

    pro = client.get("/api/v1/professionals/camila-review").get_json()
    assert [(r["author"], r["rating"], r["comment"], r["recommended"]) for r in pro["reviews"]] == [
        ("Bruna", 5, "Resultado excelente.", True)
    ]
    assert "Sobrenome" not in str(pro["reviews"])
    assert pro["whatsappUrl"].endswith("/contato/profissional/camila-review/whatsapp")

    business = client.get("/api/v1/establishments/studio-review").get_json()
    assert [(r["author"], r["rating"], r["comment"], r["recommended"]) for r in business["reviews"]] == [
        ("Bruna", 4, None, False)
    ]
